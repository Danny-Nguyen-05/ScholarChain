#!/usr/bin/env python3
"""Structured helpers for the Phase 13 scripts (stdlib only; run with python3 -I).

Subcommands (each prints findings on stdout and exits 0 on success, 1 on a finding, 2 on usage):
  ecs-arch FILE                          print linux/amd64 or linux/arm64 from cpu_architecture
  json-parse FILE...                     fail if any file is not valid JSON
  dockerfile-check --dockerfile F --repo R --mains "m1 m2"
  image-inspect FILE                     print "<os>/<arch> <image-id>" from `docker image inspect` JSON
  release-manifest --facts F --out O     facts file (tab separated) to release-manifest.json
  verify-release-manifest --manifest M --head SHA --platform P --services "a b" [--ecs-arch P]
  deploy-manifest --facts F --out O --root R   facts file to deploy-manifest.json (created exclusively)
  verify-deploy-manifest --manifest M --services "a b" [--require-stage S] [--account-sha256 H] [--region R]
                         [--repositories "r1 r2"] [--require-ecs-services]
                                         (the optional flags BIND the manifest to one deployment; the infrastructure
                                         rollback that keeps the runtime uses all of them)
  digests --manifest M                   print "<service> <repository> <tag> <digest>" lines
  release-images --manifest M            print "<service> <local image> <local image id> <os/arch>" lines
"""
import argparse
import glob
import hashlib
import json
import os
import re
import sys

ECS_ARCH_MAP = {"X86_64": "linux/amd64", "ARM64": "linux/arm64"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(root):
    """sha256 over sorted 'relative-path sha256 size' lines, plus file count and total bytes."""
    lines, total = [], 0
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            size = os.path.getsize(path)
            total += size
            lines.append("%s %s %d" % (rel, sha256_file(path), size))
    lines.sort()
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return digest, len(lines), total


def cmd_ecs_arch(args):
    with open(args.file, encoding="utf-8") as handle:
        text = handle.read()
    found = sorted(set(re.findall(r'cpu_architecture\s*=\s*"([^"]*)"', text)))
    if not found:
        print("no cpu_architecture assignment found in %s" % args.file, file=sys.stderr)
        return 1
    if len(found) > 1:
        print("conflicting cpu_architecture values in %s: %s" % (args.file, ",".join(found)), file=sys.stderr)
        return 1
    if found[0] not in ECS_ARCH_MAP:
        print("unrecognized cpu_architecture %r in %s" % (found[0], args.file), file=sys.stderr)
        return 1
    print(ECS_ARCH_MAP[found[0]])
    return 0


def cmd_json_parse(args):
    bad = 0
    for path in args.files:
        try:
            with open(path, encoding="utf-8") as handle:
                json.load(handle)
        except Exception as error:  # noqa: BLE001 - report any parse problem
            bad += 1
            print("INVALID-JSON %s: %s" % (path, str(error)[:120]))
    return 1 if bad else 0


def _join_continuations(text):
    out, pending = [], ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.endswith("\\"):
            pending += line[:-1] + " "
            continue
        out.append(pending + line)
        pending = ""
    if pending:
        out.append(pending)
    return out


def cmd_dockerfile_check(args):
    problems = []
    with open(args.dockerfile, encoding="utf-8") as handle:
        lines = _join_continuations(handle.read())
    stages = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        keyword = parts[0].upper()
        if keyword == "FROM":
            rest = [p for p in parts[1:] if not p.startswith("--")]
            image = rest[0] if rest else ""
            if len(rest) >= 3 and rest[1].upper() == "AS":
                stages.add(rest[2])
            if image != "scratch" and image not in stages:
                if not re.search(r"@sha256:[0-9a-f]{64}$", image):
                    problems.append("FROM %s is not pinned by sha256 digest" % image)
        elif keyword in ("COPY", "ADD"):
            rest = [p for p in parts[1:] if not p.startswith("--")]
            if any(p.startswith("--from=") for p in parts[1:]):
                continue
            for source in rest[:-1]:
                if re.match(r"^[a-z]+://", source):
                    continue
                path = os.path.join(args.repo, source.rstrip("/"))
                if not (os.path.exists(path) or glob.glob(path)):
                    problems.append("COPY source missing after packaging: %s" % source)
    joined = "\n".join(lines)
    match = re.search(r'case\s+"?\$\{?MAIN_CLASS\}?"?\s+in(.*?)esac', joined, re.S)
    expected = sorted(args.mains.split())
    if not match:
        problems.append("no MAIN_CLASS allowlist (case ... esac) in the Dockerfile")
    else:
        found = sorted(set(re.findall(r"([A-Za-z_][A-Za-z0-9_.]*\.[A-Za-z0-9_]+)\s*[|)]", match.group(1))))
        if found != expected:
            problems.append("MAIN_CLASS allowlist %s != configured service mains %s" % (found, expected))
    for problem in problems:
        print("DOCKERFILE-CHECK-FAILED: %s" % problem)
    if not problems:
        print("dockerfile ok: FROM pinned by digest, COPY sources exist, MAIN_CLASS allowlist matches config")
    return 1 if problems else 0


def cmd_image_inspect(args):
    try:
        with open(args.file, encoding="utf-8") as handle:
            data = json.load(handle)
        entry = data[0]
        os_name = entry["Os"]
        arch = entry["Architecture"]
        image_id = entry.get("Id", "")
    except Exception as error:  # noqa: BLE001
        print("cannot parse docker image inspect output: %s" % str(error)[:100], file=sys.stderr)
        return 1
    print("%s/%s %s" % (os_name, arch, image_id))
    return 0


def _read_facts(path):
    facts = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line:
                facts.append(line.split("\t"))
    return facts


def _artifact_entry(name, kind, path):
    entry = {"name": name, "path": path, "kind": kind}
    if not os.path.exists(path):
        entry["status"] = "missing"
        return entry
    if kind == "file":
        entry.update(size=os.path.getsize(path), sha256=sha256_file(path), status="present")
    else:
        digest, count, total = tree_digest(path)
        entry.update(size=total, sha256=digest, files=count, status="present", sha256_kind="tree-digest")
        jar = os.path.join(path, "services.jar")
        if os.path.isfile(jar):
            entry["services_jar_sha256"] = sha256_file(jar)
    return entry


def cmd_release_manifest(args):
    meta, toolchain, artifacts, images, archive = {}, {}, [], [], {}
    for fact in _read_facts(args.facts):
        kind = fact[0]
        if kind == "meta":
            meta[fact[1]] = fact[2]
        elif kind == "toolchain":
            toolchain[fact[1]] = fact[2]
        elif kind == "artifact":
            artifacts.append(_artifact_entry(fact[1], fact[2], fact[3]))
        elif kind == "image":
            images.append(
                {
                    "service": fact[1],
                    "image": fact[2],
                    "status": fact[3],
                    "local_image_id": fact[4],
                    "os_arch": fact[5],
                }
            )
        elif kind == "archive":
            archive = {
                "status": fact[1],
                "path": fact[2],
                "size": int(fact[3]) if fact[3].isdigit() else None,
                "sha256": fact[4],
                "expected_size": int(fact[5]) if fact[5].isdigit() else None,
                "expected_sha256": fact[6],
            }
    built = [i for i in images if i["status"] == "built"]
    manifest = {
        "schema": "scholarchain.release-manifest.v1",
        "commit": meta["commit"],
        "dirty": meta["dirty"] == "true",
        "created_utc": meta["created_utc"],
        "run_id": meta["run_id"],
        "image_tag": meta["image_tag"],
        "image_platform": meta["image_platform"],
        "ecs_architecture": meta["ecs_architecture"],
        "arch_gate": {
            "passed": meta["arch_gate"] == "passed",
            "detail": meta.get("arch_gate_detail", ""),
        },
        "status": "complete" if built and len(built) == len(images) else "partial-no-images",
        "toolchain": toolchain,
        "artifacts": artifacts,
        "images": images,
        "runtime_archive": archive,
        "warnings": [w for w in meta.get("warnings", "").split("|") if w],
        "notes": (
            "Registry digests are assigned at push time by deploy.sh; only local image IDs are recorded here. "
            "The Hadoop submit JAR embeds timestamps and is not byte-reproducible: its sha256 is of this build."
        ),
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("wrote %s" % args.out)
    return 0


def cmd_verify_release_manifest(args):
    problems = []
    try:
        with open(args.manifest, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except Exception as error:  # noqa: BLE001
        print("MANIFEST-CHECK-FAILED: unreadable release manifest: %s" % str(error)[:100])
        return 1
    if manifest.get("schema") != "scholarchain.release-manifest.v1":
        problems.append("unexpected manifest schema")
    if manifest.get("commit") != args.head:
        problems.append("manifest commit does not equal HEAD")
    if manifest.get("dirty") is not False:
        problems.append("manifest was built from a dirty tree")
    if manifest.get("status") != "complete":
        problems.append("manifest status is %r (images missing or skipped)" % manifest.get("status"))
    if manifest.get("image_platform") != args.platform:
        problems.append("manifest image_platform %r != configured %r" % (manifest.get("image_platform"), args.platform))
    if args.ecs_arch and manifest.get("ecs_architecture") != args.ecs_arch:
        problems.append("manifest ecs_architecture %r != %r" % (manifest.get("ecs_architecture"), args.ecs_arch))
    if not manifest.get("arch_gate", {}).get("passed"):
        problems.append("manifest architecture gate did not pass")
    by_service = {i.get("service"): i for i in manifest.get("images", [])}
    for service in args.services.split():
        image = by_service.get(service)
        if image is None:
            problems.append("no image recorded for service %s" % service)
            continue
        if image.get("status") != "built":
            problems.append("image for %s is %s, not built" % (service, image.get("status")))
        if image.get("os_arch") != args.platform:
            problems.append("image for %s has architecture %s, expected %s" % (service, image.get("os_arch"), args.platform))
        if str(image.get("image", "")).endswith("-dirty"):
            problems.append("image for %s carries a -dirty tag" % service)
    for problem in problems:
        print("MANIFEST-CHECK-FAILED: %s" % problem)
    if not problems:
        print("release manifest ok: commit=HEAD, clean, %s, all images present" % args.platform)
    return 1 if problems else 0


def cmd_deploy_manifest(args):
    meta, images, ecs, archive = {}, [], [], {}
    for fact in _read_facts(args.facts):
        kind = fact[0]
        if kind == "meta":
            meta[fact[1]] = fact[2]
        elif kind == "image":
            images.append({"service": fact[1], "repository": fact[2], "tag": fact[3], "registry_digest": fact[4]})
        elif kind == "ecs":
            ecs.append({"service": fact[1], "task_definition": fact[2]})
        elif kind == "archive":
            archive = {"s3_uri_env": fact[1], "status": fact[2], "sha256": fact[3], "size": fact[4]}
    manifest = {
        "schema": "scholarchain.deploy-manifest.v1",
        "stage": meta.get("stage", ""),
        "commit": meta["commit"],
        "image_revision": meta["image_revision"],
        "region": meta["region"],
        "account_sha256": meta["account_sha256"],
        "plan_sha256": meta["plan_sha256"],
        "deployed_utc": meta["deployed_utc"],
        "run_id": meta["run_id"],
        "images": images,
        "ecs_services": ecs,
        "runtime_archive": archive,
    }
    # Created exclusively (O_EXCL | O_NOFOLLOW, never truncated) below the repository root.
    import importlib.util

    spec = importlib.util.spec_from_file_location("sc_safeio", os.path.join(os.path.dirname(os.path.abspath(__file__)), "safeio.py"))
    safeio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(safeio)
    try:
        handle = safeio.open_new(args.root, args.out)
    except safeio.Refused as error:
        print("deploy manifest not written: %s" % error)
        return 1
    with handle:
        handle.write((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print("wrote %s" % args.out)
    return 0


def cmd_verify_deploy_manifest(args):
    problems = []
    try:
        with open(args.manifest, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except Exception as error:  # noqa: BLE001
        print("MANIFEST-CHECK-FAILED: unreadable deploy manifest: %s" % str(error)[:100])
        return 1
    if manifest.get("schema") != "scholarchain.deploy-manifest.v1":
        problems.append("unexpected manifest schema")
    if not HEX40.match(str(manifest.get("image_revision", ""))):
        problems.append("image_revision is not a 40-hex commit SHA")
    by_service = {i.get("service"): i for i in manifest.get("images", [])}
    for service in args.services.split():
        image = by_service.get(service)
        if image is None:
            problems.append("no recorded digest for service %s" % service)
        elif not DIGEST.match(str(image.get("registry_digest", ""))):
            problems.append("recorded digest for %s is not sha256:<64 hex>" % service)
        elif image.get("tag") != manifest.get("image_revision"):
            problems.append("image tag for %s differs from image_revision" % service)
    if args.require_stage and manifest.get("stage") != args.require_stage:
        problems.append("manifest stage %s is not %s: only the manifest of a verified %s proves the revision was deployed" % (manifest.get("stage"), args.require_stage, args.require_stage))
    if args.account_sha256 and manifest.get("account_sha256") != args.account_sha256:
        problems.append("manifest account differs from the approved account")
    if args.region and manifest.get("region") != args.region:
        problems.append("manifest region differs from the deployment region")
    if args.repositories:
        for service, repository in zip(args.services.split(), args.repositories.split()):
            image = by_service.get(service)
            if image is not None and image.get("repository") != repository:
                problems.append("manifest repository for %s differs from %s" % (service, repository))
    if args.require_ecs_services:
        recorded = {}
        for entry in manifest.get("ecs_services") or []:
            if isinstance(entry, dict) and entry.get("service") and entry.get("task_definition"):
                recorded.setdefault(entry["service"], []).append(entry["task_definition"])
        for service in args.services.split():
            if len(recorded.get(service, [])) != 1:
                problems.append("manifest has no verified ECS task definition for %s" % service)
    for problem in problems:
        print("MANIFEST-CHECK-FAILED: %s" % problem)
    if not problems:
        print("deploy manifest ok: image_revision=%s" % manifest.get("image_revision"))
    return 1 if problems else 0


def cmd_digests(args):
    with open(args.manifest, encoding="utf-8") as handle:
        manifest = json.load(handle)
    for image in manifest.get("images", []):
        print("%s %s %s %s" % (image["service"], image["repository"], image["tag"], image["registry_digest"]))
    print("IMAGE_REVISION %s" % manifest.get("image_revision", ""))
    return 0


def cmd_release_images(args):
    with open(args.manifest, encoding="utf-8") as handle:
        manifest = json.load(handle)
    for image in manifest.get("images", []):
        print("%s %s %s %s" % (image.get("service", ""), image.get("image", ""), image.get("local_image_id", ""), image.get("os_arch", "")))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ecs-arch")
    p.add_argument("file")
    p.set_defaults(fn=cmd_ecs_arch)
    p = sub.add_parser("json-parse")
    p.add_argument("files", nargs="+")
    p.set_defaults(fn=cmd_json_parse)
    p = sub.add_parser("dockerfile-check")
    p.add_argument("--dockerfile", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--mains", required=True)
    p.set_defaults(fn=cmd_dockerfile_check)
    p = sub.add_parser("image-inspect")
    p.add_argument("file")
    p.set_defaults(fn=cmd_image_inspect)
    p = sub.add_parser("release-manifest")
    p.add_argument("--facts", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_release_manifest)
    p = sub.add_parser("verify-release-manifest")
    p.add_argument("--manifest", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--platform", required=True)
    p.add_argument("--services", required=True)
    p.add_argument("--ecs-arch")
    p.set_defaults(fn=cmd_verify_release_manifest)
    p = sub.add_parser("deploy-manifest")
    p.add_argument("--facts", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--root", required=True)
    p.set_defaults(fn=cmd_deploy_manifest)
    p = sub.add_parser("verify-deploy-manifest")
    p.add_argument("--manifest", required=True)
    p.add_argument("--services", required=True)
    p.add_argument("--require-stage")
    p.add_argument("--account-sha256")
    p.add_argument("--region")
    p.add_argument("--repositories")
    p.add_argument("--require-ecs-services", action="store_true")
    p.set_defaults(fn=cmd_verify_deploy_manifest)
    p = sub.add_parser("digests")
    p.add_argument("--manifest", required=True)
    p.set_defaults(fn=cmd_digests)
    p = sub.add_parser("release-images")
    p.add_argument("--manifest", required=True)
    p.set_defaults(fn=cmd_release_images)
    return parser


if __name__ == "__main__":
    ns = build_parser().parse_args(sys.argv[1:])
    sys.exit(ns.fn(ns))
