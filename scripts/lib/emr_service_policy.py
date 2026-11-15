#!/usr/bin/env python3
"""Render and check the EMR service policy text for the private tfvars (offline, stdlib only; run with python3 -I).

`emr_service_policy_json` is built from infra/terraform/environments/emr-service-policy.json.example by replacing three
placeholders: <region>, <12-digit-account-id> and <environment>. This helper does exactly that, writes the result as a
ready-to-append tfvars assignment (heredoc) into a NEW private file, and checks the result with the same rules as the Terraform
variable validation (infra/terraform/phase12b-variables.tf, emr_service_policy_json) plus the reviewed shape of the example
(13 statements, the exact statement ids, the one iam:PassRole). It makes no network or AWS call and never reads a tfvars file.

Usage:
  emr_service_policy.py render --region R --environment E (--account-env VAR | --account-id 12DIGITS)
                               --out FILE [--format tfvars|json] [--example FILE]
      Writes FILE exclusively (mode 600, refuses an existing file or a symlink). The file holds the account id, so it is
      private: keep it under target/ (ignored), append it to course.local.tfvars, then delete it. Prefer --account-env (the
      NAME of an environment variable that holds the id, for example one filled with `read -r ACCT; export ACCT`) so the id is
      not on a command line. Prints only a masked summary (statement ids, counts, sha256 of the written file).
  emr_service_policy.py check --file FILE [--region R --environment E] [--example FILE]
      FILE may be the tfvars heredoc or plain JSON. Prints OK/FAIL lines (the account id is shown as <acct>) and one final
      `RESULT:` line. With --region and --environment it also requires every non-global ARN to name that region and the one
      12-digit account found in the file, and the PassRole target scholarchain-<environment>-emr-ec2.

Exit codes: 0 success; 1 the check failed; 2 usage or input error.
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_EXAMPLE = os.path.normpath(os.path.join(HERE, "..", "..", "infra", "terraform", "environments", "emr-service-policy.json.example"))
EXPECTED_SIDS = (
    "CreateInTaggedNetwork",
    "CreateEMRTaggedInstancesAndVolumes",
    "ResourcesToLaunchEC2",
    "ManageEMRTaggedResources",
    "ManageTagsOnEMRTaggedResources",
    "CreateNetworkInterfaceNeededForPrivateSubnet",
    "TagOnCreateTaggedEMRResources",
    "ListActionsForEC2Resources",
    "CreateDefaultSecurityGroupWithEMRTags",
    "CreateDefaultSecurityGroupInVPCWithEMRTags",
    "TagOnCreateDefaultSecurityGroupWithEMRTags",
    "ManageSecurityGroups",
    "PassTheProjectInstanceRoleToEC2",
)
PLACEHOLDERS = ("<region>", "<12-digit-account-id>", "<environment>")
ARN_RE = re.compile(r"^arn:aws:[a-z0-9-]+:[a-z0-9-]*:([0-9]{12})?:.+$")  # the Terraform validator's regex
ACCOUNT_RE = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")
REGION_RE = re.compile(r"^[a-z]{2}(-[a-z]+)+-[0-9]$")
ENVIRONMENT_RE = re.compile(r"^[a-z][a-z0-9-]{1,20}$")
HEREDOC_RE = re.compile(r"^\s*emr_service_policy_json\s*=\s*<<-?EOT\n(.*)\n\s*EOT\s*$", re.S)


class Problem(Exception):
    pass


def render_text(example_text, region, account, environment):
    if not REGION_RE.match(region):
        raise Problem("region must look like us-east-2")
    if not re.fullmatch(r"[0-9]{12}", account):
        raise Problem("the account id must be exactly 12 digits")
    if not ENVIRONMENT_RE.match(environment):
        raise Problem("environment must be a short lowercase name such as course")
    text = example_text
    for placeholder, value in zip(PLACEHOLDERS, (region, account, environment)):
        text = text.replace(placeholder, value)
    document = json.loads(text)  # raises ValueError when the example is not JSON
    return json.dumps(document, indent=2) + "\n"


def extract_json(text):
    match = HEREDOC_RE.match(text)
    return match.group(1) if match else text


def check_text(text, region=None, environment=None):
    """Return a list of (ok, message). The account id never appears in a message."""
    results = []

    def ok(flag, message):
        results.append((bool(flag), message))

    body = extract_json(text)
    try:
        document = json.loads(body)
    except ValueError as error:
        return [(False, "not valid JSON: %s" % error)]
    statements = document.get("Statement") if isinstance(document, dict) else None
    ok(isinstance(document, dict) and document.get("Version") == "2012-10-17", "Version is 2012-10-17")
    if not isinstance(statements, list) or not statements:
        return results + [(False, "Statement is a non-empty list")]
    ok(len(statements) == 13, "13 statements (found %d)" % len(statements))
    ok([s.get("Sid") for s in statements] == list(EXPECTED_SIDS), "statement ids are exactly the reviewed 13, in order")
    ok(all(s.get("Effect") == "Allow" for s in statements), "every statement is Allow")
    ok(not any(p in body for p in PLACEHOLDERS) and "<" not in body and ">" not in body, "no placeholder is left")
    actions = [a for s in statements for a in (s.get("Action") or [])]
    resources = [(s, r) for s in statements for r in (s.get("Resource") or [])]
    ok(actions and not any(re.search(r"[?*]", a) for a in actions), "no wildcard in any action (the Terraform validator rejects it)")
    bad_arns = [r for s, r in resources if r != "*" and not ARN_RE.match(r)]
    ok(not bad_arns, "every resource is a concrete ARN (partition, service, region and account without a wildcard)")
    star_ok = all(all(a.startswith("ec2:Describe") for a in s["Action"]) for s, r in resources if r == "*")
    ok(star_ok, "\"*\" appears only on ec2:Describe actions")
    pass_role = [s for s in statements if "iam:PassRole" in s.get("Action", [])]
    ok(len(pass_role) == 1 and pass_role[0].get("Condition", {}).get("StringEquals", {}).get("iam:PassedToService") == "ec2.amazonaws.com",
       "exactly one iam:PassRole, passed to ec2.amazonaws.com only")
    accounts = {m for _, r in resources for m in ACCOUNT_RE.findall(r)}
    ok(len(accounts) == 1, "every ARN with an account names the same single 12-digit account (found %d distinct)" % len(accounts))
    if region is not None:
        regional = [r for _, r in resources if r.startswith("arn:aws:ec2:")]
        ok(regional and all(r.startswith("arn:aws:ec2:%s:" % region) for r in regional), "every ec2 ARN names region %s" % region)
    if environment is not None:
        want = "role/scholarchain-%s-emr-ec2" % environment
        ok(len(pass_role) == 1 and all(r.endswith(want) for r in pass_role[0].get("Resource", [])), "PassRole targets %s only" % want)
    return results


def mask(message, account_ids):
    for account in account_ids:
        message = message.replace(account, "<acct>")
    return message


def write_exclusive(path, data):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("render")
    r.add_argument("--region", required=True)
    r.add_argument("--environment", required=True)
    group = r.add_mutually_exclusive_group(required=True)
    group.add_argument("--account-env")
    group.add_argument("--account-id")
    r.add_argument("--out", required=True)
    r.add_argument("--format", choices=["tfvars", "json"], default="tfvars")
    r.add_argument("--example", default=DEFAULT_EXAMPLE)
    c = sub.add_parser("check")
    c.add_argument("--file", required=True)
    c.add_argument("--region")
    c.add_argument("--environment")
    c.add_argument("--example", default=DEFAULT_EXAMPLE)
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return 2 if error.code else 0
    try:
        if args.command == "render":
            account = os.environ.get(args.account_env, "") if args.account_env else args.account_id
            with open(args.example, "r", encoding="utf-8") as handle:
                body = render_text(handle.read(), args.region, account, args.environment)
            text = body if args.format == "json" else "emr_service_policy_json = <<-EOT\n%sEOT\n" % body
            problems = [m for good, m in check_text(text, args.region, args.environment) if not good]
            if problems:
                print("RESULT: FAIL the rendered text does not pass its own check: %s" % "; ".join(problems), file=sys.stderr)
                return 1
            write_exclusive(args.out, text.encode("utf-8"))
            document = json.loads(body)
            print("EMR-POLICY: statements=%d sids=%s" % (len(document["Statement"]), ",".join(s["Sid"] for s in document["Statement"])))
            print("EMR-POLICY-FILE: %s sha256=%s format=%s (holds the account id: private; append to course.local.tfvars, then delete)"
                  % (args.out, hashlib.sha256(text.encode("utf-8")).hexdigest(), args.format))
            print("RESULT: PASS rendered and checked")
            return 0
        with open(args.file, "r", encoding="utf-8") as handle:
            text = handle.read()
        accounts = set(ACCOUNT_RE.findall(text))
        results = check_text(text, args.region, args.environment)
        for good, message in results:
            print("%s: %s" % ("OK" if good else "FAIL", mask(message, accounts)))
        passed = all(good for good, _ in results)
        print("RESULT: %s" % ("PASS" if passed else "FAIL"))
        return 0 if passed else 1
    except (OSError, ValueError, Problem) as error:
        print("RESULT: ERROR %s" % mask(str(error), ACCOUNT_RE.findall(str(error))), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
