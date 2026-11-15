#!/usr/bin/env python3
"""Offline derivation and live comparison of the expected runtime-apply plans (stdlib only; run with python3 -I).

Why this exists: the live session makes two incremental runtime-apply plans after the first runtime plan: the pointer
apply (runtime_artifact_* values) and the EMR apply (emr_config). Terraform cannot plan against a state offline, so the
expected lists are DERIVED from three plan-only `terraform test -verbose` runs with the mock provider
(infra/terraform/tests/phase14b_plan_deltas.tftest.hcl): the difference between consecutive full plans is the incremental
plan. The reviewed result is scripts/config/expected-plan-deltas.json. The real plan is compared against it in the session.
A match is a review aid, never an approval to apply.

Usage:
  plan_deltas.py derive --verbose-output FILE
      Parse the output of `terraform test -verbose -filter=tests/phase14b_plan_deltas.tftest.hcl` (three runs) and print the
      derived delta as JSON (added addresses, changed addresses). Exit 0; 2 when the output cannot be parsed.
  plan_deltas.py check --stage pointer-apply|emr-apply --plan-log FILE [--expected FILE]
      Read the `PLAN-ACTION: <actions> <address>` lines of a plan.sh log and compare them with the reviewed list. Prints
      MATCH / MISSING / UNEXPECTED / ACTION-DIFFERS lines and one final `RESULT:` line. Exit 0 identical; 1 differences
      (a human decides whether they are explainable); 2 usage or parse error.

Limits (stated, not hidden): the mock provider fills computed attributes with random 8-character strings, so lines whose value
is such a string are ignored when two plans are compared; a real change that happens to be an 8-character lowercase value would
be missed (the tftest assertions pin the substantive parts). The mock also fills the task definition ARN with a constant, so the
in-place update of the ECS service that follows a task definition replacement cannot be seen offline: it is recorded in the
reviewed list with basis "hand-derived".
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXPECTED = os.path.join(HERE, "..", "config", "expected-plan-deltas.json")
RUN_RE = re.compile(r'^  run "([A-Za-z0-9_]+)"\.\.\.')
HEADER_RE = re.compile(r"^  # (.+) will be created$")
NOISE_RE = re.compile(r'= "[a-z0-9]{8}"$')
ACTION_RE = re.compile(r"^PLAN-ACTION: (\S+) (.+)$")
EXPECTED_RUNS = (
    "plan_1_first_runtime_shape_has_no_pointer_and_no_emr",
    "plan_2_pointer_changes_only_the_query_api_task_definition",
    "plan_3_emr_adds_the_emr_resources_and_changes_no_runtime_or_iam_document",
)


def parse_verbose(text):
    """Return {run name: {address: [attribute lines without mock noise]}} from `terraform test -verbose` output."""
    runs, current, address = {}, None, None
    for line in text.split("\n"):
        match = RUN_RE.match(line)
        if match:
            current, address = match.group(1), None
            runs[current] = {}
            continue
        if current is None:
            continue
        match = HEADER_RE.match(line)
        if match:
            address = match.group(1)
            runs[current][address] = []
            continue
        if line.startswith("Plan:"):
            address = None
            continue
        if address is not None and not NOISE_RE.search(line):
            runs[current][address].append(line)
    return runs


def delta(before, after):
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "changed": sorted(a for a in set(before) & set(after) if before[a] != after[a]),
    }


def derive(text):
    runs = parse_verbose(text)
    missing = [r for r in EXPECTED_RUNS if r not in runs or not runs[r]]
    if missing:
        raise ValueError("verbose output lacks plans for runs: %s" % ", ".join(missing))
    one, two, three = (runs[r] for r in EXPECTED_RUNS)
    return {
        "plan_sizes": {r: len(runs[r]) for r in EXPECTED_RUNS},
        "pointer-apply": delta(one, two),
        "emr-apply": delta(two, three),
    }


def normalize_actions(text):
    parts = text.split("+")
    return "replace" if sorted(parts) == ["create", "delete"] else text


def load_expected(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def check(stage, log_text, expected):
    """Return (lines, ok) comparing PLAN-ACTION lines with the reviewed list of the stage."""
    entry = expected["stages"][stage]
    want = {e["address"]: normalize_actions(e["actions"]) for e in entry["actions"]}
    got = {}
    for line in log_text.split("\n"):
        match = ACTION_RE.match(line.strip())
        if match:
            got[match.group(2)] = normalize_actions(match.group(1))
    lines = []
    for address in sorted(set(want) | set(got)):
        if address in want and address in got:
            if want[address] == got[address]:
                lines.append("MATCH: %s %s" % (got[address], address))
            else:
                lines.append("ACTION-DIFFERS: %s expected=%s actual=%s" % (address, want[address], got[address]))
        elif address in want:
            lines.append("MISSING: %s %s (expected, not in the plan)" % (want[address], address))
        else:
            lines.append("UNEXPECTED: %s %s (in the plan, not in the reviewed list)" % (got[address], address))
    ok = bool(got) and all(line.startswith("MATCH:") for line in lines)
    return lines, ok


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("derive")
    d.add_argument("--verbose-output", required=True)
    c = sub.add_parser("check")
    c.add_argument("--stage", required=True, choices=["pointer-apply", "emr-apply"])
    c.add_argument("--plan-log", required=True)
    c.add_argument("--expected", default=DEFAULT_EXPECTED)
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return 2 if error.code else 0
    try:
        if args.command == "derive":
            with open(args.verbose_output, "r", encoding="utf-8") as handle:
                print(json.dumps(derive(handle.read()), indent=2, sort_keys=True))
            return 0
        with open(args.plan_log, "r", encoding="utf-8") as handle:
            log_text = handle.read()
        lines, ok = check(args.stage, log_text, load_expected(args.expected))
    except (OSError, ValueError, KeyError) as error:
        print("RESULT: ERROR %s" % error, file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    if not lines:
        print("RESULT: DIFFERS no PLAN-ACTION lines found in the log")
        return 1
    print("RESULT: %s stage=%s compared against the reviewed offline derivation (not an approval to apply)" % ("IDENTICAL" if ok else "DIFFERS", args.stage))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
