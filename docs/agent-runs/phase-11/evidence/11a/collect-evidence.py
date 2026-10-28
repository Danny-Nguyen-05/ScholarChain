"""Collect local gate evidence after sbt exits; never starts tests or remote clients."""

from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


start = json.loads((OUT / "full-check-start.json").read_text())
exit_code = int((OUT / "full-check-exit.txt").read_text())
assert exit_code == 0, f"Full check exited {exit_code}"
raw = Path(start["raw_log"]).read_bytes()
lines = raw.decode(errors="replace").splitlines()
selected = []
for number, line in enumerate(lines, 1):
    if (
        re.match(r"\[info\] [\w.]+Spec:", line)
        or any(token in line for token in (
            "Total number of tests run:", "Suites: completed", "Tests: succeeded",
            "All tests passed.", "injected format-stage failure", "TestRunMarker",
            "*** FAILED ***", "[success]", "welcome to sbt", "compiling ",
        ))
        or line.startswith(("real ", "user ", "sys "))
    ):
        selected.append(f"{number}: {line}")
(OUT / "full-check-excerpt.txt").write_text("\n".join(selected) + "\n")

modules = ["modules/core", "modules/hadoop", "modules/entity-resolution",
           "modules/spark", "modules/storage", "modules/rag", "modules/services",
           "tests", "build-verification"]
rows = []
all_cases = set()
for module in modules:
    reports = sorted((ROOT / module / "target/test-reports").glob("*.xml"))
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    for path in reports:
        assert path.stat().st_mtime >= start["start_epoch"], f"Stale report: {path}"
        suite = ET.parse(path).getroot()
        for key in counts:
            counts[key] += int(suite.attrib.get(key, 0))
        for case in suite.findall("testcase"):
            all_cases.add((suite.attrib["name"].split(".")[-1], case.attrib["name"]))
    rows.append(dict(module=module, reports=len(reports), **counts))
totals = {key: sum(row[key] for row in rows)
          for key in ["reports", "tests", "failures", "errors", "skipped"]}
assert not (totals["failures"] or totals["errors"] or totals["skipped"]), totals
new = json.loads((OUT / "new-tests.json").read_text())
assert totals["tests"] == 1216 + len(new), totals
coverage = json.loads((OUT / "coverage.json").read_text())
missing = [(suite, name) for value in coverage.values()
           for kind in ["existing", "new"] for suite, name in value[kind]
           if (suite, name) not in all_cases]
assert not missing, f"Mapped tests absent from fresh JUnit: {missing}"
observed_totals = [int(m.group(1)) for line in lines
                   if (m := re.search(r"Total number of tests run: (\d+)", line))]
assert sum(observed_totals) == totals["tests"], observed_totals
assert len(observed_totals) == len(modules), observed_totals
source = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
          for name in start["source_files"]}
assert source == start["source_files"], "New test source changed during gate"
tracked = subprocess.check_output(
    ["git", "ls-files", "modules", "tests", "project", "build.sbt"], cwd=ROOT, text=True
).splitlines()
paths = [Path(p) for p in tracked
         if Path(p).suffix in {".scala", ".sbt", ".java", ".json", ".conf", ".xml", ".yaml", ".yml"}
         and "src/test/resources" not in p]
before = json.loads((OUT / "protected-source-before.json").read_text())
protected = {}
for label, prefixes in {"production": ["modules/"], "build": ["project/", "build.sbt"],
                        "existing_independent_tests": ["tests/"]}.items():
    chosen = sorted(p for p in paths if any(str(p).startswith(x) for x in prefixes))
    digest = hashlib.sha256()
    for path in chosen:
        digest.update(str(path).encode() + b"\0" + hashlib.sha256((ROOT / path).read_bytes()).digest())
    protected[label] = dict(files=len(chosen), aggregate_sha256=digest.hexdigest())
    assert protected[label] == before[label], f"Protected tracked source changed: {label}"
save("full-check-summary.json", dict(
    exit_code=exit_code, raw_log=start["raw_log"], raw_bytes=len(raw),
    raw_sha256=hashlib.sha256(raw).hexdigest(), rows=rows, totals=totals,
    log_group_counts=observed_totals, mapped_tests_missing_from_fresh_reports=missing,
    final_new_source_hashes=source, protected_source_after=protected,
    notes=["All JUnit reports are newer than gate start; counts corroborate log groups.",
           "Protected module fingerprint includes module tests/config; excludes test resources.",
           "Raw logs remain in /tmp only; retained excerpts and hashes survive reboot."]
))
print(json.dumps(totals))
