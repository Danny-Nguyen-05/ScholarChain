#!/usr/bin/env python3
"""Summarize `terraform show -json <plan>` into a plan receipt (stdlib only; run with python3 -I).

Usage:
  plan_summary.py --show-json FILE --plan-file FILE --out RECEIPT
      --commit SHA --scripts-commit SHA --clean true|false --region R --account-sha256 HEX
      --env NAME --terraform-version V --created-utc T --run-id ID [--profile P]
      [--image-revision SHA] --env-tfvars PATH [--private-vars-supplied] [--text-file FILE]
      --stateful-prefixes a,b --iam-prefixes a,b
      --root REPO_ROOT --source-tree-sha256 HEX --state-json FILE [--purpose deploy-plan|cleanup-prepare]

Receipt schema scholarchain.plan-receipt.v2 (repair round 2 adds purpose, source_tree_sha256 = hash of the
materialized source the plan was made from, state = the live local state identity {present, lineage, serial,
sha256} at plan time, and planned_environment / planned_project read from the saved plan's own variables).
The receipt is created exclusively (O_EXCL | O_NOFOLLOW, never truncated) below --root. --commit is the commit of the Terraform SOURCE that was
planned (the previous commit for an infrastructure rollback); --scripts-commit is HEAD of the
checkout whose scripts ran; --clean records whether that work tree was clean. The receipt carries the
plan sha256, account sha256 (never the raw ID), region, environment, image_revision, terraform
version and UTC time, plus the COMPLETE list of resource actions (address + action, never an
attribute value or variable value). The same list is printed as PLAN-ACTION lines (never truncated).

When the plan's aws_account_id variable is present, only its sha256 is compared with
--account-sha256; a mismatch exits 4 (the plan targets a different account than the credentials).

Exit codes: 0 receipt written; 2 usage/parse error; 4 account binding mismatch.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys

ACCOUNT_RE = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")
IGNORED = ("no-op", "read")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify(actions):
    key = tuple(actions)
    if key == ("no-op",):
        return "no_op"
    if key == ("read",):
        return "read"
    if key == ("create",):
        return "create"
    if key == ("update",):
        return "update"
    if key == ("delete",):
        return "delete"
    if sorted(actions) == ["create", "delete"]:
        return "replace"
    if key == ("forget",):
        return "forget"
    return "other"


def summarize(document, stateful_prefixes, iam_prefixes):
    counts = {k: 0 for k in ("create", "update", "delete", "replace", "no_op", "read", "forget", "other")}
    iam, stateful, actions_all = [], [], []
    for change in document.get("resource_changes", []):
        actions = change.get("change", {}).get("actions", [])
        kind = classify(actions)
        counts[kind] += 1
        if kind in ("no_op", "read"):
            continue
        entry = {"address": ACCOUNT_RE.sub("<acct>", change.get("address", "")), "type": change.get("type", ""), "actions": "+".join(actions)}
        actions_all.append(entry)
        rtype = entry["type"]
        if any(rtype.startswith(p) for p in iam_prefixes if p):
            iam.append(entry)
        if any(rtype.startswith(p) for p in stateful_prefixes if p):
            stateful.append(entry)
    iam.sort(key=lambda e: e["address"])
    stateful.sort(key=lambda e: e["address"])
    actions_all.sort(key=lambda e: e["address"])
    return {
        "all_actions": actions_all,
        "add": counts["create"],
        "change": counts["update"],
        "destroy": counts["delete"],
        "replace": counts["replace"],
        "no_op": counts["no_op"],
        "read": counts["read"],
        "other": counts["other"] + counts["forget"],
        "iam_resource_changes": iam,
        "stateful_resource_changes": stateful,
    }


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--show-json", required=True)
    p.add_argument("--plan-file", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--scripts-commit", required=True)
    p.add_argument("--clean", required=True, choices=["true", "false"])
    p.add_argument("--text-file", default="")
    p.add_argument("--region", required=True)
    p.add_argument("--account-sha256", required=True)
    p.add_argument("--env", required=True)
    p.add_argument("--terraform-version", required=True)
    p.add_argument("--created-utc", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--profile", default="")
    p.add_argument("--image-revision", default="")
    p.add_argument("--env-tfvars", required=True)
    p.add_argument("--private-vars-supplied", action="store_true")
    p.add_argument("--stateful-prefixes", default="")
    p.add_argument("--iam-prefixes", default="")
    p.add_argument("--root", required=True)
    p.add_argument("--source-tree-sha256", required=True)
    p.add_argument("--state-json", required=True)
    p.add_argument("--purpose", default="deploy-plan", choices=["deploy-plan", "cleanup-prepare"])
    args = p.parse_args(argv)

    try:
        with open(args.show_json, encoding="utf-8") as handle:
            document = json.load(handle)
    except Exception as error:  # noqa: BLE001
        print("cannot parse terraform show -json output: %s" % str(error)[:100], file=sys.stderr)
        return 2

    try:
        with open(args.state_json, encoding="utf-8") as handle:
            state = json.load(handle)
        if not isinstance(state, dict) or not isinstance(state.get("present"), bool):
            raise ValueError("bad state record")
    except (OSError, ValueError) as error:
        print("cannot read the state identity: %s" % type(error).__name__, file=sys.stderr)
        return 2
    if not re.fullmatch(r"[0-9a-f]{64}", args.source_tree_sha256):
        print("--source-tree-sha256 must be 64 lowercase hex", file=sys.stderr)
        return 2
    planned_variables = document.get("variables", {}) if isinstance(document.get("variables"), dict) else {}

    def planned_value(name):
        entry = planned_variables.get(name)
        return entry.get("value") if isinstance(entry, dict) and isinstance(entry.get("value"), str) else None

    binding = "not-in-plan"
    planned = document.get("variables", {}).get("aws_account_id", {}).get("value")
    if isinstance(planned, str) and planned:
        planned_hash = hashlib.sha256(planned.encode("utf-8")).hexdigest()
        if planned_hash != args.account_sha256:
            print("ACCOUNT-BINDING-MISMATCH: the plan's aws_account_id does not match the credentials' account", file=sys.stderr)
            return 4
        binding = "matched"

    summary = summarize(
        document,
        [x for x in args.stateful_prefixes.split(",") if x],
        [x for x in args.iam_prefixes.split(",") if x],
    )
    all_actions = summary.pop("all_actions")
    receipt = {
        "schema": "scholarchain.plan-receipt.v2",
        "purpose": args.purpose,
        "created_utc": args.created_utc,
        "run_id": args.run_id,
        "env": args.env,
        "commit": args.commit,
        "scripts_commit": args.scripts_commit,
        "clean": args.clean == "true",
        "region": args.region,
        "account_sha256": args.account_sha256,
        "account_binding": binding,
        "profile": args.profile,
        "terraform_version": args.terraform_version,
        "planned_environment": planned_value("environment"),
        "planned_project": planned_value("project"),
        "source_tree_sha256": args.source_tree_sha256,
        "state": state,
        "image_revision": args.image_revision or None,
        "plan_file": args.plan_file,
        "plan_sha256": sha256_file(args.plan_file),
        "plan_json_sha256": sha256_file(args.show_json),
        "plan_text_file": args.text_file or None,
        "plan_text_sha256": sha256_file(args.text_file) if args.text_file else None,
        "actions": all_actions,
        "var_files": {"environment": args.env_tfvars, "private_vars_supplied": bool(args.private_vars_supplied)},
        "summary": summary,
        "notes": "Plan file, show JSON and full plan text stay git-ignored and private; only checksums, this action list and the summary are shareable. Never applied by plan.sh.",
    }
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("sc_safeio", os.path.join(here, "safeio.py"))
    safeio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(safeio)
    try:
        handle = safeio.open_new(args.root, args.out)
    except safeio.Refused as error:
        print("receipt not written: %s" % error, file=sys.stderr)
        return 2
    with handle:
        handle.write((json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print("PLAN-ACTIONS-BEGIN count=%d (address and action only; no attribute or variable values)" % len(all_actions))
    for entry in all_actions:
        print("PLAN-ACTION: %s %s" % (entry["actions"], entry["address"]))
    print("PLAN-ACTIONS-END count=%d" % len(all_actions))
    print(
        "summary: add=%d change=%d destroy=%d replace=%d iam_changes=%d stateful_changes=%d"
        % (
            summary["add"],
            summary["change"],
            summary["destroy"],
            summary["replace"],
            len(summary["iam_resource_changes"]),
            len(summary["stateful_resource_changes"]),
        )
    )
    print("plan_sha256=%s" % receipt["plan_sha256"])
    print("account_binding=%s" % binding)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
