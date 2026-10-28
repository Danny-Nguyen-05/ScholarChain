"""Reconcile a completed local full check with named coverage and frozen sources."""

from pathlib import Path
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]


def read(name):
    return json.loads((OUT / name).read_text())


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


start = read("full-check-start.json")
result = read("full-check-result.json")
assert result["exit_code"] == 0, result
assert not result["rewritten_sources"], "Source changed during full gate"
raw = Path(result["raw_log"]).read_bytes()
assert hashlib.sha256(raw).hexdigest() == result["raw_sha256"]
modules = ["modules/core", "modules/hadoop", "modules/entity-resolution", "modules/spark",
           "modules/storage", "modules/rag", "modules/services", "tests", "build-verification"]
rows = []
all_cases = set()
for module in modules:
    paths = sorted((ROOT / module / "target/test-reports").glob("*.xml"))
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    for path in paths:
        assert path.stat().st_mtime >= start["start_epoch"], f"Stale JUnit: {path}"
        suite = ET.parse(path).getroot()
        for key in counts:
            counts[key] += int(suite.get(key, 0))
        for case in suite.findall("testcase"):
            all_cases.add((suite.get("name").split(".")[-1], case.get("name")))
    rows.append(dict(module=module, reports=len(paths), **counts))
totals = {k: sum(r[k] for r in rows) for k in ["reports", "tests", "failures", "errors", "skipped"]}
assert totals["failures"] == totals["errors"] == totals["skipped"] == 0, totals
new = read("new-tests.json")
defects = read("defects.json")
exposed = {(d["suite"], d["name"]) for d in defects["exposed_defects"]}
assert totals["tests"] == read("baseline-test-counts.json")["totals"]["tests"] + len(new) - len(exposed)
coverage = read("coverage.json")
mapped = {tuple(t) for c in coverage.values() for kind in ["existing", "new"] for t in c[kind]}
assert mapped - exposed <= all_cases, f"Mapped tests absent: {mapped - exposed - all_cases}"
assert {tuple(t) for t in new} - exposed <= all_cases
group_counts = [int(v) for v in re.findall(r"Total number of tests run: (\d+)", raw.decode(errors="replace"))]
assert len(group_counts) == len(modules) and sum(group_counts) == totals["tests"], group_counts
source = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in start["source_files"]}
assert source == start["source_files"] == result["source_files_after"]
tracked = subprocess.check_output(["git", "ls-files", "modules", "tests", "project", "build.sbt", "prompts"], cwd=ROOT, text=True).splitlines()
protected = {}
for label, prefixes in {"modules": ["modules/"], "build": ["project/", "build.sbt"],
                        "existing_independent_tests": ["tests/"], "prompt_assets": ["prompts/"]}.items():
    chosen = sorted(p for p in tracked if any(p.startswith(x) for x in prefixes))
    digest = hashlib.sha256()
    for p in chosen:
        digest.update(p.encode() + b"\0" + hashlib.sha256((ROOT / p).read_bytes()).digest())
    protected[label] = dict(files=len(chosen), aggregate_sha256=digest.hexdigest())
assert protected == read("protected-source-before.json"), "Protected files changed"
save("full-check-summary.json", dict(
    totals=totals, rows=rows, log_group_counts=group_counts,
    source_files=source, protected_source_after=protected,
    raw_log=result["raw_log"], raw_bytes=len(raw), raw_sha256=result["raw_sha256"],
    exit_code=0, mapped_distinct=len(mapped), new_tests=len(new), exposed_defect_count=len(exposed),
    notes=["Every JUnit file is fresh after this gate's single-write start record.",
           "Raw logs live in /tmp; committed excerpts and hashes are durable."]
))
save("coverage-validation.json", dict(
    categories={k: dict(existing=len(v["existing"]), new=len(v["new"]), total=len(v["existing"])+len(v["new"])) for k, v in coverage.items()},
    existing_distinct=len({tuple(t) for v in coverage.values() for t in v["existing"]}),
    new_distinct=len({tuple(t) for v in coverage.values() for t in v["new"]}),
    combined_distinct=len(mapped), mapped_tests_missing_from_fresh_reports=[],
    exposed_tests_intentionally_excluded_from_full_check=sorted(exposed),
))
print(json.dumps(totals))
