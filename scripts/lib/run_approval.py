#!/usr/bin/env python3
"""Parse the human approval record of run-bounded-pipeline.sh and run-experiment.sh (stdlib; python3 -I).

  parse --file F --action ACTION
        Prints the validated "KEY=value" lines (one per required key) on stdout, exit 0. Exit 1 with one
        "APPROVAL-REFUSED: <reason>" line per problem when the file is missing or unreadable, or a required line is
        missing, duplicated or malformed, or a forbidden line is present.

Record format (the human writes it; the scripts never do): each line is exactly KEY=value, with no quotes, no spaces
around "=" and no CR; each key appears exactly once; any other text (prose, headings) is ignored, exactly like the
13A deploy approval record. A key counts as present when a line starts with the key (optionally indented) followed
by optional spaces and "=": a malformed, indented or duplicated line is refused, never skipped. Any APPROVED_* line
whose key is not listed below is refused as an extra key; text that is not an APPROVED_* line is ignored.

Keys (all required unless stated):
  APPROVED_ACTION=run-bounded-pipeline|run-experiment      must equal the action being run
  APPROVED_COMMIT=<40 lowercase hex>                         HEAD of a clean work tree
  APPROVED_ACCOUNT_SHA256=<64 lowercase hex>                 sha256 of the 12-digit account ID string, no newline
  APPROVED_REGION=<aws region>
  APPROVED_CLUSTER_ID=<EMR cluster id, j-...>               the existing Terraform-created cluster
  APPROVED_RUN_CONFIG_SHA256=<64 hex>                        printed by the dry run as RUN-CONFIG-SHA256
  APPROVED_MANIFEST_SHA256=<64 hex>                          run-experiment only (sha256 of the committed manifest);
                                                             forbidden for run-bounded-pipeline
  APPROVED_BUDGET_USD=<decimal>                              the declared budget (at most the per-run cap)
  APPROVED_MAX_CAPACITY=<integer>                            maximum instances (primary + core + task)
  APPROVED_MAX_RUNTIME_MINUTES=<integer>                     hard runtime cap
  APPROVED_TEARDOWN=auto-termination                         the cluster tears itself down when idle
  APPROVED_PRESPEND_SHA256=<64 hex>                          sha256 of the pre-spend receipt
"""
import argparse
import re
import sys

HEX64 = r"[0-9a-f]{64}"
PATTERNS = {
    "APPROVED_ACTION": r"(run-bounded-pipeline|run-experiment)",
    "APPROVED_COMMIT": r"[0-9a-f]{40}",
    "APPROVED_ACCOUNT_SHA256": HEX64,
    "APPROVED_REGION": r"[a-z]{2}(-[a-z0-9]+)+-[0-9]+",
    "APPROVED_CLUSTER_ID": r"j-[A-Z0-9]{3,32}",
    "APPROVED_RUN_CONFIG_SHA256": HEX64,
    "APPROVED_MANIFEST_SHA256": HEX64,
    "APPROVED_BUDGET_USD": r"[0-9]+(\.[0-9]{1,4})?",
    "APPROVED_MAX_CAPACITY": r"[1-9][0-9]{0,2}",
    "APPROVED_MAX_RUNTIME_MINUTES": r"[1-9][0-9]{0,4}",
    "APPROVED_TEARDOWN": r"auto-termination",
    "APPROVED_PRESPEND_SHA256": HEX64,
}
COMMON = [
    "APPROVED_ACTION",
    "APPROVED_COMMIT",
    "APPROVED_ACCOUNT_SHA256",
    "APPROVED_REGION",
    "APPROVED_CLUSTER_ID",
    "APPROVED_RUN_CONFIG_SHA256",
    "APPROVED_BUDGET_USD",
    "APPROVED_MAX_CAPACITY",
    "APPROVED_MAX_RUNTIME_MINUTES",
    "APPROVED_TEARDOWN",
    "APPROVED_PRESPEND_SHA256",
]
EXPERIMENT_ONLY = ["APPROVED_MANIFEST_SHA256"]


def required_keys(action):
    return COMMON + (EXPERIMENT_ONLY if action == "run-experiment" else [])


def forbidden_keys(action):
    return EXPERIMENT_ONLY if action == "run-bounded-pipeline" else []


def parse(path, action):
    """Returns (values dict, problems list)."""
    problems = []
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return {}, ["approval record not found or unreadable"]
    lines = text.split("\n")
    values = {}
    for key in required_keys(action):
        loose = re.compile(r"^[ \t]*%s[ \t]*=" % key)
        hits = [line for line in lines if loose.match(line)]
        if not hits:
            problems.append("approval record has no %s line" % key)
            continue
        if len(hits) > 1:
            problems.append("approval record has %d %s lines; exactly one is required" % (len(hits), key))
            continue
        exact = re.fullmatch(r"%s=(.*)" % key, hits[0])
        if exact is None:
            problems.append("approval record line for %s must be exactly KEY=value with no spaces, indent, quotes or CR" % key)
            continue
        value = exact.group(1)
        if re.fullmatch(PATTERNS[key], value) is None:
            problems.append("approval record value for %s is malformed" % key)
            continue
        values[key] = value
    # Any other APPROVED_* line is an extra key (a misspelt or foreign key): refused, never ignored.
    for line in lines:
        found = re.match(r"^[ \t]*(APPROVED_[A-Za-z0-9_]*)[ \t]*=", line)
        if found and found.group(1) not in PATTERNS:
            problems.append("approval record has an unknown key %s (any extra APPROVED_* key refuses)" % found.group(1))
    for key in forbidden_keys(action):
        loose = re.compile(r"^[ \t]*%s[ \t]*=" % key)
        if any(loose.match(line) for line in lines):
            problems.append("the approval record for %s must not contain a %s line" % (action, key))
    return values, problems


def cmd_parse(args):
    values, problems = parse(args.file, args.action)
    for problem in problems:
        print("APPROVAL-REFUSED: %s" % problem)
    if problems:
        return 1
    for key in required_keys(args.action):
        print("%s=%s" % (key, values[key]))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse")
    p.add_argument("--file", required=True)
    p.add_argument("--action", required=True, choices=["run-bounded-pipeline", "run-experiment"])
    p.set_defaults(fn=cmd_parse)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))
