#!/usr/bin/env python3
"""Evidence archive for scripts/archive-evidence.sh (stdlib; python3 -I).

  scan   --out PLAN --include CATEGORY=PATH ... [--external-location KEY=LOCATION ...] --max-copy-bytes N
         Walks the sources (no symlink is followed), classifies every file and writes a plan JSON. Refuses (exit 1,
         "ARCHIVE-REFUSED: ..." lines) when a source is missing or a symlink, a file name marks private material
         (state, plan binary, raw plan JSON, variable files, keys, login material, dotenv files), or a file that
         cannot be copied (larger than the limit, or binary) has no external location.
  write  --plan PLAN --dest-root DIR --dest DIR --phase NN --label L --commit C --created-utc T [--redact-file F]
         Creates DIR (it must NOT exist: a versioned evidence directory is never overwritten) with every copied file
         (text redacted) and INDEX.json, exclusively and symlink-safely (safeio).
  tar    --dest DIR --out FILE
         Builds a .tar.gz of DIR with Python tarfile: it contains only the listed regular files, never a macOS
         "._" AppleDouble member or .DS_Store, and records no owner names. The output is created exclusively. The
         listing is read back (python tarfile and the system tar with COPYFILE_DISABLE=1) and must hold no "._" entry.
  verify --dest DIR [--redact-file F]
         Re-reads the evidence directory: every copied file matches its recorded archived sha256, no name starts with
         "._", and no text holds a 12-digit account id, a registered secret, a known credential shape or a generic secret, token, password
         or api-key assignment.

Thresholds: a file of at most --max-copy-bytes (default ARCHIVE_MAX_COPY_BYTES, 1 MiB) that is valid UTF-8 text is copied
after redaction. A larger file, or any binary file (it cannot be redacted), is NOT copied: the index records its
sha256, size and the REQUIRED external location (an s3:// URI or a Drive reference) instead.
Categories: test-reports plan-receipts image-digests run-manifests metric-exports experiment-outputs release-metadata.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tarfile

CATEGORIES = (
    "test-reports",
    "plan-receipts",
    "image-digests",
    "run-manifests",
    "metric-exports",
    "experiment-outputs",
    "release-metadata",
)
EXTERNAL = re.compile(r"^(s3://[A-Za-z0-9][^\s]*|drive:\S[^\n]*|https://drive\.google\.com/\S+)$")
METADATA_NAME = re.compile(r"^(\._.*|\.DS_Store)$")
# Names that mark private material: refused outright (fail closed), never copied or indexed.
PRIVATE_NAME = re.compile(
    r"(\.tfstate(\.|$)|\.tfvars(\.json)?$|^[.]env($|[.])|\.pem$|\.key$|\.p12$|\.pfx$|^id_(rsa|ed25519|ecdsa)|credentials|"
    r"\.tfplan$|\.tfplan\.json$|\.tfplan\.txt$|\.tfplan\.log$|\.tfplan\.tfplan$)",
    re.I,
)
ALLOWED_PLAN_SIDECARS = re.compile(r"\.tfplan\.(receipt\.json|sha256)$")
SECRET_SHAPES = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "<redacted-private-key>"),
    (re.compile(r"(?<![A-Z0-9])(AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"), "<redacted-access-key-id>"),
    (re.compile(r"(?i)(aws_secret_access_key|aws_session_token|secret_access_key|session_token)(\s*[=:]\s*)\S+"), r"\1\2<redacted>"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{12,}"), r"\1<redacted>"),
    (re.compile(r"(?i)(authorization\s*:\s*)\S.*"), r"\1<redacted>"),
)
# Generic secret-like assignments (key and separator lengths are bounded so a megabyte of one character cannot cause
# quadratic backtracking): a key whose name contains secret, token, password, passwd, api key, access key, private
# key or credential, then "=" or ":", then a value (bare, single- or double-quoted; also JSON "secret": "..."). Pure numbers,
# booleans, null and already redacted placeholders are left alone, so counters such as max_tokens: 4096 and checksums survive.
GENERIC_ASSIGNMENT = re.compile(
    r"""(?i)(?<![A-Za-z0-9_.-])(?P<key>["']?[A-Za-z0-9_.-]{0,40}(?:secret|token|passw(?:or)?d|passwd|api[_-]?key|apikey|access[_-]?key|private[_-]?key|credential)[A-Za-z0-9_.-]{0,40}["']?[ \t]{0,8}[=:][ \t]{0,8})"""
    r"""(?P<value>"[^"\n]*"|'[^'\n]*'|[^\s,;}\]"']+)"""
)
HARMLESS_VALUE = re.compile(r"""^["']?(?:[0-9]+(?:\.[0-9]+)?|true|false|null|none|<redacted[^>]*>|<acct>)["']?$""", re.I)


CHECKSUM_KEY = re.compile(r"(?i)(sha256|sha1|checksum|digest|hash)")


def _harmless(match):
    value = match.group("value")
    return bool(HARMLESS_VALUE.match(value)) or bool(CHECKSUM_KEY.search(match.group("key")) and re.fullmatch(r"[\"']?[0-9a-fA-F]{32,128}[\"']?", value))


def _generic_replace(match):
    value = match.group("value")
    if _harmless(match):
        return match.group(0)
    quote = value[0] if value[0] in "\"'" and value[-1] == value[0] and len(value) >= 2 else ""
    return match.group("key") + quote + "<redacted>" + quote


def generic_remaining(text):
    """Assignments that still hold a secret-like value (used by the post-write verification)."""
    return [m.group(0) for m in GENERIC_ASSIGNMENT.finditer(text) if not _harmless(m)]


SHAPE_CHECKS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?<![A-Z0-9])(AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*[A-Za-z0-9/+=]{20,}"),
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def is_text(data):
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def redact_text(text, values):
    """Returns (redacted text, number of replaced items). Uses scripts/lib/redact.py plus credential shapes."""
    redactor = _load("sc_redact", "redact.py")
    count = 0
    out = redactor.redact(text, values)
    if out != text:
        count += 1
    for pattern, replacement in SECRET_SHAPES:
        new, n = pattern.subn(replacement, out)
        count += n
        out = new
    changed = []

    def generic(match):
        result = _generic_replace(match)
        if result != match.group(0):
            changed.append(1)
        return result

    out = GENERIC_ASSIGNMENT.sub(generic, out)
    return out, count + len(changed)


def walk(path):
    """Yields (absolute path, relative path) of regular files below PATH (a file yields itself)."""
    if os.path.islink(path):
        raise ValueError("%s is a symlink" % path)
    if os.path.isfile(path):
        yield path, os.path.basename(path)
        return
    if not os.path.isdir(path):
        raise ValueError("%s does not exist" % path)
    for base, dirs, files in os.walk(path, followlinks=False):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(base, name)
            if os.path.islink(full):
                raise ValueError("%s is a symlink" % full)
            yield full, os.path.relpath(full, path)
        for name in list(dirs):
            if os.path.islink(os.path.join(base, name)):
                raise ValueError("%s is a symlink" % os.path.join(base, name))


def cmd_scan(args):
    problems = []
    externals = {}
    for item in args.external_location or []:
        key, _, location = item.partition("=")
        if not key or not EXTERNAL.match(location):
            problems.append("--external-location %r must be NAME=<s3://... or drive:... or a Drive URL>" % item.split("=")[0])
            continue
        externals[key] = location
    entries = []
    seen = {}
    for item in args.include or []:
        category, _, source = item.partition("=")
        if category not in CATEGORIES or not source:
            problems.append("--include must be CATEGORY=PATH with CATEGORY one of %s" % ", ".join(CATEGORIES))
            continue
        try:
            files = list(walk(source))
        except ValueError as error:
            problems.append("source refused: %s" % error)
            continue
        if not files:
            problems.append("source %s holds no file" % source)
        for full, rel in files:
            name = os.path.basename(full)
            if METADATA_NAME.match(name):
                entries.append({"category": category, "path": "%s/%s" % (category, rel.replace(os.sep, "/")), "status": "skipped-metadata", "size": os.path.getsize(full), "source": full})
                continue
            if PRIVATE_NAME.search(name) and not ALLOWED_PLAN_SIDECARS.search(name):
                problems.append("%s looks like private material (state, plan binary or raw plan JSON, variable file, key or credential): never archive it" % rel)
                continue
            st = os.lstat(full)
            if not stat.S_ISREG(st.st_mode):
                problems.append("%s is not a regular file" % rel)
                continue
            dest_rel = "%s/%s" % (category, rel.replace(os.sep, "/"))
            if dest_rel in seen:
                problems.append("two sources map to %s" % dest_rel)
                continue
            seen[dest_rel] = True
            with open(full, "rb") as handle:
                data = handle.read(args.max_copy_bytes + 1) if st.st_size <= args.max_copy_bytes else None
            entry = {"category": category, "path": dest_rel, "size": st.st_size, "source": full}
            if data is not None and is_text(data):
                entry["status"] = "copy"
            else:
                entry["status"] = "external"
                entry["reason"] = "larger than %d bytes" % args.max_copy_bytes if data is None else "binary (cannot be redacted)"
                location = externals.get(dest_rel) or externals.get(rel.replace(os.sep, "/")) or externals.get(name)
                if not location:
                    problems.append("%s (%d bytes, %s) is not copied and has no required external location: pass --external-location %s=<s3://... or drive:...>" % (dest_rel, st.st_size, entry["reason"], dest_rel))
                else:
                    entry["external_location"] = location
            entries.append(entry)
    if not entries and not problems:
        problems.append("no source was given (use --include CATEGORY=PATH)")
    for problem in problems:
        print("ARCHIVE-REFUSED: %s" % problem)
    if problems:
        return 1
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"entries": entries, "max_copy_bytes": args.max_copy_bytes}, handle)
    counts = {}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    print("ARCHIVE-SCAN: %s" % " ".join("%s=%d" % (k, counts[k]) for k in sorted(counts)))
    return 0


def cmd_write(args):
    safeio = _load("sc_safeio", "safeio.py")
    redactor = _load("sc_redact", "redact.py")
    values = redactor.load_values(args.redact_file)
    with open(args.plan, encoding="utf-8") as handle:
        plan = json.load(handle)
    root = os.path.realpath(args.dest_root)
    if not os.path.isdir(root):
        print("ARCHIVE-REFUSED: the destination root %s does not exist" % args.dest_root)
        return 1
    expected = os.path.join(root, "phase-%s" % args.phase, "evidence", args.label)
    dest = os.path.normpath(args.dest)
    try:
        resolved = safeio.resolve_under_root(root, dest)
    except safeio.Refused as error:
        print("ARCHIVE-REFUSED: %s" % error)
        return 1
    if resolved != expected:
        print("ARCHIVE-REFUSED: the destination must be <root>/phase-%s/evidence/%s" % (args.phase, args.label))
        return 1
    try:
        safeio.check_no_symlink_chain(root, resolved)
        if os.path.lexists(resolved):
            raise safeio.Refused("the evidence directory already exists (a versioned evidence directory is never overwritten): %s" % os.path.relpath(resolved, root))
        safeio.ensure_dirs(root, os.path.dirname(resolved))
        os.mkdir(resolved, 0o700)
        os.chmod(resolved, 0o755)
        index_entries = []
        for entry in plan["entries"]:
            record = {k: entry[k] for k in ("category", "path", "status", "size") if k in entry}
            if entry["status"] == "skipped-metadata":
                record["reason"] = "macOS or editor metadata file (name starts with ._ or is .DS_Store); never archived"
                index_entries.append(record)
                continue
            with open(entry["source"], "rb") as handle:
                data = handle.read()
            record["sha256"] = sha256_bytes(data)
            record["size"] = len(data)
            if entry["status"] == "copy":
                text, count = redact_text(data.decode("utf-8"), values)
                out = text.encode("utf-8")
                target = os.path.join(resolved, *entry["path"].split("/"))
                safeio.ensure_dirs(root, os.path.dirname(target))
                with safeio.open_new(root, target, 0o644) as handle:
                    handle.write(out)
                record["status"] = "copied"
                record["archived_sha256"] = sha256_bytes(out)
                record["redactions"] = count
            else:
                record["status"] = "indexed-external"
                record["reason"] = entry["reason"]
                record["external_location"] = entry["external_location"]
            index_entries.append(record)
        index = {
            "schema": "scholarchain.evidence-index.v1",
            "phase": args.phase,
            "label": args.label,
            "commit": args.commit,
            "created_utc": args.created_utc,
            "max_copy_bytes": plan["max_copy_bytes"],
            "entries": sorted(index_entries, key=lambda item: item["path"]),
        }
        with safeio.open_new(root, os.path.join(resolved, "INDEX.json"), 0o644) as handle:
            handle.write((json.dumps(index, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    except (safeio.Refused, OSError) as error:
        print("ARCHIVE-REFUSED: %s" % (error if isinstance(error, safeio.Refused) else type(error).__name__))
        return 1
    copied = sum(1 for e in index_entries if e["status"] == "copied")
    external = sum(1 for e in index_entries if e["status"] == "indexed-external")
    skipped = sum(1 for e in index_entries if e["status"] == "skipped-metadata")
    print("ARCHIVE-WRITTEN: %s copied=%d indexed-external=%d skipped-metadata=%d" % (os.path.relpath(resolved, root), copied, external, skipped))
    return 0


def cmd_tar(args):
    safeio = _load("sc_safeio", "safeio.py")
    dest = os.path.realpath(args.dest)
    names = []
    for base, dirs, files in os.walk(dest, followlinks=False):
        dirs.sort()
        for name in sorted(files):
            if METADATA_NAME.match(name):
                continue
            names.append(os.path.relpath(os.path.join(base, name), dest))
    parent = os.path.dirname(dest)
    try:
        handle = safeio.open_new(parent, os.path.realpath(args.out), 0o644)
    except safeio.Refused as error:
        print("ARCHIVE-REFUSED: %s" % error)
        return 1
    label = os.path.basename(dest)
    with handle:
        with tarfile.open(fileobj=handle, mode="w:gz") as archive:
            for name in names:
                info = archive.gettarinfo(os.path.join(dest, name), arcname="%s/%s" % (label, name.replace(os.sep, "/")))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                with open(os.path.join(dest, name), "rb") as source:
                    archive.addfile(info, source)
    listing = []
    with tarfile.open(args.out, "r:gz") as archive:
        listing = archive.getnames()
    bad = [n for n in listing if METADATA_NAME.match(os.path.basename(n))]
    system_listing = subprocess.run(["tar", "-tzf", args.out], capture_output=True, text=True, env=dict(os.environ, COPYFILE_DISABLE="1")).stdout.splitlines()
    bad += [n for n in system_listing if METADATA_NAME.match(os.path.basename(n.rstrip("/")))]
    if bad:
        print("ARCHIVE-FAILED: the tar listing holds macOS metadata members: %s" % ", ".join(sorted(set(bad))[:5]))
        return 1
    print("ARCHIVE-TAR: %s members=%d no ._ or .DS_Store member (checked with python tarfile and tar -tzf, COPYFILE_DISABLE=1) sha256=%s" % (os.path.basename(args.out), len(listing), sha256_bytes(open(args.out, "rb").read())))
    return 0


def cmd_verify(args):
    redactor = _load("sc_redact", "redact.py")
    values = redactor.load_values(args.redact_file)
    dest = os.path.realpath(args.dest)
    problems = []
    try:
        with open(os.path.join(dest, "INDEX.json"), encoding="utf-8") as handle:
            index = json.load(handle)
    except (OSError, ValueError):
        print("ARCHIVE-FAILED: INDEX.json is missing or invalid")
        return 1
    listed = {}
    for entry in index["entries"]:
        listed[entry["path"]] = entry
        if entry["status"] == "indexed-external":
            if not HEX64.match(entry.get("sha256", "")) or not isinstance(entry.get("size"), int) or not EXTERNAL.match(entry.get("external_location", "")):
                problems.append("%s lacks a sha256, a size or an external location" % entry["path"])
    present = set()
    for base, _dirs, files in os.walk(dest, followlinks=False):
        for name in files:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, dest).replace(os.sep, "/")
            if METADATA_NAME.match(name):
                problems.append("macOS or editor metadata file present: %s" % rel)
            if rel == "INDEX.json":
                continue
            present.add(rel)
            entry = listed.get(rel)
            with open(full, "rb") as handle:
                data = handle.read()
            if not entry or entry["status"] != "copied":
                problems.append("%s is present but not recorded as copied" % rel)
                continue
            if sha256_bytes(data) != entry["archived_sha256"]:
                problems.append("%s does not match its recorded archived sha256" % rel)
            text = data.decode("utf-8", errors="replace")
            if redactor.ACCOUNT_RE.search(text):
                problems.append("%s still holds a 12-digit run (an AWS account id)" % rel)
            for kind, value in values:
                if len(value) >= 3 and value in text:
                    problems.append("%s still holds a registered secret or account value" % rel)
            for shape in SHAPE_CHECKS:
                if shape.search(text):
                    problems.append("%s still holds a credential shape" % rel)
            if generic_remaining(text):
                problems.append("%s still holds a secret, token, password or api-key assignment" % rel)
    for rel, entry in listed.items():
        if entry["status"] == "copied" and rel not in present:
            problems.append("%s is recorded as copied but missing" % rel)
    for problem in problems:
        print("ARCHIVE-FAILED: %s" % problem)
    if problems:
        return 1
    print("ARCHIVE-VERIFIED: %d copied file(s) match their recorded sha256, no metadata member, no account id, secret or credential shape" % len(present))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("--out", required=True)
    p.add_argument("--include", action="append")
    p.add_argument("--external-location", action="append")
    p.add_argument("--max-copy-bytes", type=int, required=True)
    p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("write")
    for name in ("plan", "dest-root", "dest", "phase", "label", "commit", "created-utc"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--redact-file", default="")
    p.set_defaults(fn=cmd_write)
    p = sub.add_parser("tar")
    p.add_argument("--dest", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_tar)
    p = sub.add_parser("verify")
    p.add_argument("--dest", required=True)
    p.add_argument("--redact-file", default="")
    p.set_defaults(fn=cmd_verify)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))
