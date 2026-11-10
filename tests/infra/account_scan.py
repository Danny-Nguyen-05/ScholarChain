"""Scan for a real 12-digit AWS account ID in what the working tree ADDS (test-engineer, Phase 14B replan decision 3 of the user's
2026-11-08 answers: "No raw account ID in any new or changed file"; the legacy Phase 12 evidence keeps its existing mentions).

Scope: the lines the working tree adds relative to the point where this branch left the main line (`git merge-base HEAD main`, falling
back to `origin/main`; `git diff -U0 <base>` compares that commit with the working tree, so committed AND uncommitted work is covered and
the scan is not vacuous on a committed tree), and every line of every untracked, non-ignored file. If no base can be found the scan
FAILS (BaseNotFound); it never passes by scanning nothing. `docs/agent-runs/phase-12/**` is excluded by decision. Binary or very large files are not read. A match is a run
of exactly 12 digits that is not part of a longer alphanumeric token and not the last group of a UUID. Only the synthetic IDs below
are allowed (plus the named, file-scoped entries below). Findings carry the path, the line number and the category only: the matched digits are NEVER returned or printed (a
finding may be a real account ID).
"""
import re
import subprocess
from typing import NamedTuple, Optional

from infra_support import REPO

# Allowed everywhere (the order is irrelevant): the documentation-style placeholders used by the repository's synthetic fixtures.
SYNTHETIC = frozenset({"1111" + "2222" + "3333", "0000" + "0000" + "0000"})  # split so that this file holds no literal run
# Narrow, file-scoped additions. Each entry is a ScopedSynthetic: a NAME, the exact value, and either an exact repository-relative
# `path` (matched by string equality) or, for the two older entries only, a `pattern` (compiled regex). Exactly one of the two is set.
# Obviously fake second accounts used by infra-engineer tests were found in the 14B tree on 2026-11-08 (kept unchanged, pattern-scoped).
# Anything else outside SYNTHETIC and these entries is a finding.
#
# User decision of 2026-11-09 (Phase 14B repair round 2), verbatim: "accepted, under these conditions. It covers only AWS's
# documentation example account (the digits 1 to 9, then 0, 1, 2; not written out here), only in AwsTestSupport.scala. Record it as a named, file-scoped allowlist entry, not a
# pattern. The scanner must still fail on any other 12-digit account ID in that file, and on that example ID in any other file."
# That is the entry named AWS_DOCUMENTATION_EXAMPLE_ACCOUNT below: one value, one exact path, no pattern. The value is the account ID
# that the AWS documentation itself uses in every example (counting digits 1 to 9, then 0, 1, 2); it is split here so that this file
# holds no literal 12-digit run.
AWS_DOCUMENTATION_EXAMPLE_ACCOUNT = "aws-documentation-example-account"


class ScopedSynthetic(NamedTuple):
    name: str
    value: str
    path: Optional[str] = None  # exact repository-relative path, compared with ==
    pattern: Optional["re.Pattern"] = None  # legacy regex scope; not used by the AWS documentation entry

    def covers(self, value, path):
        if value != self.value:
            return False
        if self.path is not None:
            return path == self.path
        return self.pattern is not None and self.pattern.match(path) is not None


SCOPED_SYNTHETIC = (
    ScopedSynthetic("infra-tftest-second-account", "0000" + "0000" + "0001",
                    pattern=re.compile(r"^infra/terraform/(?:deployer/)?tests/[A-Za-z0-9_]+\.tftest\.hcl$")),
    ScopedSynthetic("upload-slice-test-account", "9999" + "8888" + "7777",
                    pattern=re.compile(r"^scripts/tests/test_upload_slice\.py$")),
    ScopedSynthetic(AWS_DOCUMENTATION_EXAMPLE_ACCOUNT, "1234" + "5678" + "9012",
                    path="modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/AwsTestSupport.scala"),
)
EXCLUDED = re.compile(r"^docs/agent-runs/phase-12/")
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
TWELVE = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")
MAX_BYTES = 2_000_000


def disallowed(path, text):
    """Line numbers (1-based) of `text` holding a 12-digit run that is neither SYNTHETIC nor scoped-synthetic for `path`."""
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        for found in TWELVE.findall(UUID.sub("", line)):
            if found in SYNTHETIC:
                continue
            if any(entry.covers(found, path) for entry in SCOPED_SYNTHETIC):
                continue
            lines.append(number)
    return sorted(set(lines))


class BaseNotFound(AssertionError):
    """No merge base with the main line: a scan against nothing would pass vacuously, so it is an error."""


def base_commit():
    for ref in ("main", "origin/main"):
        done = subprocess.run(["git", "-C", str(REPO), "merge-base", "HEAD", ref], capture_output=True, text=True)
        out = done.stdout.strip()
        if done.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", out):
            return out
    raise BaseNotFound("no merge base of HEAD with main or origin/main: the account-ID scan has nothing to compare against "
                       "(fetch the main branch; a scan of an empty diff would pass vacuously)")


def _git(*args):
    return subprocess.run(["git", "-C", str(REPO)] + list(args), capture_output=True, check=True).stdout


def added_lines():
    """{path: [(line number in the new file, text)]} for the lines the working tree adds to tracked files relative to the merge base."""
    out = _git("diff", "-U0", "--no-color", "--no-ext-diff", base_commit(), "--").decode("utf-8", "replace")
    result, path, new_line = {}, None, 0
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            new_line = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            result.setdefault(path, []).append((new_line, line[1:]))
            new_line += 1
    return result


def untracked_files():
    names = _git("ls-files", "-z", "--others", "--exclude-standard").decode("utf-8", "replace").split("\0")
    return sorted(n for n in names if n)


def scan_tree():
    """(findings, files_scanned): findings are {"path", "line", "category"} dicts with category "account-id-literal"."""
    findings, scanned = [], set()
    for path, rows in added_lines().items():
        if EXCLUDED.match(path):
            continue
        scanned.add(path)
        for number, text in rows:
            if disallowed(path, text):
                findings.append({"path": path, "line": number, "category": "account-id-literal"})
    for path in untracked_files():
        if EXCLUDED.match(path):
            continue
        file = REPO / path
        try:
            if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_BYTES:
                continue
            text = file.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned.add(path)
        for number in disallowed(path, text):
            findings.append({"path": path, "line": number, "category": "account-id-literal"})
    return findings, scanned
