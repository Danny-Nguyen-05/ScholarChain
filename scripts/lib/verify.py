#!/usr/bin/env python3
"""Verification helpers for the Phase 13 deploy, plan and cleanup scripts (stdlib only; python3 -I).

Every subcommand prints findings on stdout and exits 0 (ok), 1 (a finding: the caller refuses) or
2 (usage). None of them prints a raw account ID, a variable value or a secret.

  git-tree --repo R --exempt PATH
        porcelain v1 -z parse of `git status`; exit 0 clean, 1 dirty, 2 git failed or unparsable.
        Only the LITERAL path PATH is exempt (exact string comparison, never a git pathspec).
  prespend --file F --max-age-hours H (--min-headroom D | --no-headroom-floor) [--clock-file C --label L]
        human-written pre-spend receipt: monitoring true, fresh snapshot, numeric cost fields,
        remaining headroom >= D. A missing, null or non-numeric field is never treated as zero.
        --clock-file is the TEST-ONLY controllable clock: a JSON object {"<label>": "<UTC time>", "default": ...};
        the caller passes it only when the announced SCHOLARCHAIN_CONFIG_FILE mechanism is active.
  plan-target --show-json F --region R --account-sha256 H --environment E --project P
              (--image-revision X | --no-image-revision)
        the saved plan's own provider region, aws_account_id, environment, project and image_revision variables.
  plan-provenance --receipt F ...
        the plan receipt written by plan.sh binds the plan checksum to clean provenance.
  prepare-policy --show-json F [rules] --allowed-attrs "type:a+b,..."
        the cleanup-preparation plan may only UPDATE teardown resources and only their protection/force flags.
  protection-state --state-json F [rules] --rules "type:attr=value,..."
        teardown resources of the current state whose deletion protection is still active.
  classify-state --state-file F [rules]   split `terraform state list` into teardown/preserve/unlisted
  destroy-policy --show-json F [rules]    list every destructive action of a saved destroy plan and
                                          check it against the preservation policy
  destroy-token --plan-sha256 H --account-sha256 H --region R --environment E --actions-file F
  runtime-live --state F --module M --indicators "type=N,type=LOW-HIGH,..." [--types T]
        T1: is the runtime DEPLOYED in the live local state file? Decided only from the indicator types (resources that
        exist solely while the runtime is deployed: ECS services, query load balancer, target group, listener), never
        from base-apply resources (ECS cluster, ECR repositories). Prints RUNTIME-LIVE: no | yes | partial; exit 0 for
        no/yes, exit 1 for an ambiguous PARTIAL runtime or an unreadable state (fail closed), exit 2 for a malformed or
        inconsistent configuration (with --types every indicator type must also be a protected type). Only the module
        path, resource type, mode and instance count are read from the state: no attribute or value.
  runtime-preservation --state F --module M --indicators I --types T (--receipt F | --show-json F) [--expect live|not-live|any]
        S1 safety net: when the live state shows the deployed runtime, a plan that deletes or replaces any resource of a
        protected type (T: the indicator types plus the ECS cluster) is refused (fail closed); a PARTIAL runtime is always
        refused; --expect pins whether the state must (or must not) show the runtime.
  s3-checksum --file F --checksum VALUE [--parts-file P]
        compare the S3-computed ChecksumSHA256 of an uploaded object (base64 of the raw sha256; a multipart object has a
        composite "<b64>-<parts>" value, checked against the part list S3 reports) with the private copy that was uploaded.
  ecs-services --file F --services "a b"  parse `aws ecs describe-services` text output
  image-ref --file F --expected REF [--expected-digest-ref REF]
  push-digest --file F                    digest printed by `docker push`
"""
import argparse
import base64
import datetime
import hashlib
import json
import math
import os
import re
import subprocess
import sys

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PORCELAIN = re.compile(r"^[ MTADRCU?!]{2} .+$", re.S)
STAGES = ("base-apply", "push", "runtime-apply")
ACCOUNT_RE = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")


def redact_account(text):
    return ACCOUNT_RE.sub("<acct>", text)


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------------------------
# git-tree
# ---------------------------------------------------------------------------------------------

def parse_porcelain_z(raw):
    """Return the list of (xy, path, is_rename) records, or None when the output is unparsable."""
    if raw == b"":
        return []
    if not raw.endswith(b"\0"):
        return None
    parts = raw.decode("utf-8", errors="surrogateescape").split("\0")[:-1]
    records, index = [], 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not PORCELAIN.match(entry):
            return None
        xy, path = entry[:2], entry[3:]
        renamed = "R" in xy or "C" in xy
        if renamed:
            if index >= len(parts):
                return None
            index += 1  # the original path of a rename or copy
        records.append((xy, path, renamed))
    return records


def cmd_git_tree(args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        completed = subprocess.run(
            ["git", "-C", args.repo, "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            capture_output=True,
            env=env,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        print("git status could not run: %s" % type(error).__name__)
        return 2
    if completed.returncode != 0:
        print("git status failed with exit %d" % completed.returncode)
        return 2
    records = parse_porcelain_z(completed.stdout)
    if records is None:
        print("git status output could not be parsed")
        return 2
    dirty = [path for _xy, path, renamed in records if renamed or path != args.exempt]
    if not dirty:
        print("clean")
        return 0
    print("dirty: %d path(s), for example %s" % (len(dirty), ", ".join(sorted(dirty)[:5])))
    return 1


# ---------------------------------------------------------------------------------------------
# prespend
# ---------------------------------------------------------------------------------------------

def _reject_constant(name):
    raise ValueError("non-finite JSON constant %s" % name)


def _number(document, key, problems, minimum=0.0):
    value = document.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        problems.append("%s is missing or not a number" % key)
        return None
    if not math.isfinite(value) or value < minimum:
        problems.append("%s must be a finite number >= %s" % (key, minimum))
        return None
    return float(value)


def _clock_now(args):
    """The current time, or the test-only controllable clock for this label (fails closed when unreadable)."""
    if not args.clock_file:
        return datetime.datetime.now(datetime.timezone.utc)
    with open(args.clock_file, encoding="utf-8") as handle:
        table = json.load(handle)
    text = table.get(args.label or "", table.get("default"))
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def cmd_prespend(args):
    problems = []
    try:
        now = _clock_now(args)
    except (OSError, ValueError, TypeError, AttributeError):
        print("PRESPEND-CHECK-FAILED: the test clock file is unreadable or malformed")
        return 1
    try:
        with open(args.file, encoding="utf-8") as handle:
            document = json.load(handle, parse_constant=_reject_constant)
    except (OSError, ValueError) as error:
        print("PRESPEND-CHECK-FAILED: receipt unreadable or not valid JSON: %s" % type(error).__name__)
        return 1
    if not isinstance(document, dict):
        print("PRESPEND-CHECK-FAILED: receipt must be a JSON object")
        return 1
    if document.get("monitoring_confirmed_active") is not True:
        problems.append("monitoring_confirmed_active is not true")
    snapshot = document.get("cost_snapshot_utc")
    age_hours = None
    if not isinstance(snapshot, str):
        problems.append("cost_snapshot_utc is missing")
    else:
        try:
            when = datetime.datetime.strptime(snapshot, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
            age_hours = (now - when).total_seconds() / 3600.0
        except ValueError:
            problems.append("cost_snapshot_utc must look like 2026-11-05T12:00:00Z")
    if age_hours is not None:
        if age_hours > args.max_age_hours:
            problems.append("cost snapshot is %.1f h old; at most %s h is accepted" % (age_hours, args.max_age_hours))
        if age_hours < -0.1:
            problems.append("cost snapshot is in the future")
    _number(document, "reported_spend_usd", problems)
    _number(document, "unreported_usage_allowance_usd", problems)
    _number(document, "reserves_usd", problems)
    headroom = _number(document, "remaining_headroom_usd", problems, minimum=-1e18)
    if args.no_headroom_floor:
        # Teardown-only stage (deploy.sh passes this flag only for --stage cleanup-prepare): the headroom value must
        # still be a finite number (checked above) but is NOT compared with any floor, so overspend never blocks cleanup.
        if headroom is not None:
            print("PRESPEND: cleanup-prepare has no headroom floor (remaining_headroom_usd=%.2f)" % headroom)
    elif headroom is not None and headroom < args.min_headroom:
        problems.append("remaining headroom %.2f USD is below the required %s USD" % (headroom, args.min_headroom))
    for problem in problems:
        print("PRESPEND-CHECK-FAILED: %s" % problem)
    if not problems:
        print("pre-spend receipt ok: monitoring active, snapshot %.1f h old, headroom %.2f USD" % (age_hours, headroom))
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------
# plan-target
# ---------------------------------------------------------------------------------------------

def _variable(document, name):
    entry = (document.get("variables") or {}).get(name)
    return entry.get("value") if isinstance(entry, dict) else None


def planned_regions(document, problems):
    regions = set()
    providers = (document.get("configuration") or {}).get("provider_config") or {}
    found = False
    for config in providers.values():
        if not isinstance(config, dict) or config.get("name") != "aws":
            continue
        found = True
        expression = (config.get("expressions") or {}).get("region") or {}
        if isinstance(expression.get("constant_value"), str):
            regions.add(expression["constant_value"])
        elif "var.aws_region" in (expression.get("references") or []):
            value = _variable(document, "aws_region")
            if isinstance(value, str) and value:
                regions.add(value)
            else:
                problems.append("the plan has no aws_region variable value")
        else:
            problems.append("cannot determine the aws provider region from the plan")
    if not found:
        problems.append("the plan has no aws provider configuration")
    return regions


def cmd_plan_target(args):
    problems = []
    try:
        with open(args.show_json, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        print("PLAN-TARGET-CHECK-FAILED: terraform show -json output unreadable: %s" % type(error).__name__)
        return 1
    if not isinstance(document, dict):
        print("PLAN-TARGET-CHECK-FAILED: unexpected terraform show -json document")
        return 1
    regions = planned_regions(document, problems)
    if regions and regions != {args.region}:
        problems.append("planned provider region %s != expected %s" % (",".join(sorted(regions)), args.region))
    variable_region = _variable(document, "aws_region")
    if isinstance(variable_region, str) and variable_region != args.region:
        problems.append("planned aws_region variable %s != expected %s" % (variable_region, args.region))
    for name, expected in (("environment", args.environment), ("project", args.project)):
        planned = _variable(document, name)
        if not isinstance(planned, str) or not planned:
            problems.append("PLANNED-%s-MISSING: the plan has no %s variable value" % (name.upper(), name))
        elif planned != expected:
            problems.append("planned %s %s != expected %s" % (name, planned, expected))
    account = _variable(document, "aws_account_id")
    if not isinstance(account, str) or not account:
        problems.append("ACCOUNT-BINDING-MISMATCH: the plan has no aws_account_id variable")
    elif sha256_hex(account) != args.account_sha256:
        problems.append("ACCOUNT-BINDING-MISMATCH: the plan's aws_account_id does not match the approved account")
    revision = _variable(document, "image_revision")
    if args.no_image_revision:
        if revision not in (None, ""):
            problems.append("the plan carries an image_revision but this stage expects none")
    elif revision != args.image_revision:
        problems.append("planned image_revision %s != expected %s" % (revision, args.image_revision))
    for problem in problems:
        print("PLAN-TARGET-CHECK-FAILED: %s" % problem)
    if not problems:
        print(
            "saved plan target ok: provider region %s, account hash matches, environment %s, project %s, image_revision %s"
            % (args.region, args.environment, args.project, "none" if args.no_image_revision else args.image_revision)
        )
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------
# plan-provenance
# ---------------------------------------------------------------------------------------------

def cmd_plan_provenance(args):
    problems = []
    try:
        with open(args.receipt, encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, ValueError) as error:
        print("PLAN-PROVENANCE-FAILED: plan receipt unreadable: %s" % type(error).__name__)
        return 1
    if not isinstance(receipt, dict) or receipt.get("schema") != "scholarchain.plan-receipt.v2":
        print("PLAN-PROVENANCE-FAILED: unexpected plan receipt schema (re-run plan.sh)")
        return 1
    expect = [
        ("plan_sha256", args.plan_sha256, "receipt plan_sha256 differs from the plan checksum"),
        ("commit", args.source_commit, "receipt commit differs from the source commit being deployed"),
        ("scripts_commit", args.scripts_commit, "receipt scripts_commit differs from HEAD"),
        ("account_sha256", args.account_sha256, "receipt account differs from the approved account"),
        ("region", args.region, "receipt region differs from the approved region"),
        ("env", args.environment, "receipt environment differs from the deployment environment"),
        ("terraform_version", args.terraform_version, "receipt terraform_version differs from the running CLI"),
    ]
    for key, wanted, message in expect:
        if receipt.get(key) != wanted:
            problems.append(message)
    if receipt.get("clean") is not True:
        problems.append("receipt records a dirty work tree at plan time")
    for key, wanted, message in (
        ("planned_environment", args.environment, "receipt planned_environment differs from the deployment environment"),
        ("planned_project", args.project, "receipt planned_project differs from the deployment project"),
    ):
        if receipt.get(key) != wanted:
            problems.append(message)
    if receipt.get("purpose", "deploy-plan") != args.purpose:
        problems.append("receipt purpose %s differs from the expected %s" % (receipt.get("purpose", "deploy-plan"), args.purpose))
    revision = receipt.get("image_revision")
    if args.no_image_revision:
        if revision not in (None, ""):
            problems.append("receipt image_revision is set but this stage expects none")
    elif revision != args.image_revision:
        problems.append("receipt image_revision differs from the deployment image revision")
    if not isinstance(receipt.get("created_utc"), str) or not receipt.get("created_utc"):
        problems.append("receipt has no created_utc")
    for problem in problems:
        print("PLAN-PROVENANCE-FAILED: %s" % problem)
    if not problems:
        print("plan provenance ok: receipt binds plan sha256, clean source commit, account, region, environment and revision")
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------
# cleanup classification and destroy policy
# ---------------------------------------------------------------------------------------------

def _split(value):
    return [item for item in re.split(r"[,\s]+", value or "") if item]


def base_address(address):
    return re.sub(r"\[[^\]]*\]", "", address)


class Rules:
    """Pinned classification: PRESERVE wins over TEARDOWN; anything else is UNLISTED."""

    def __init__(self, args):
        self.preserve_types = _split(args.preserve_types)
        self.preserve_addresses = _split(args.preserve_addresses)
        self.teardown_addresses = _split(args.teardown_addresses)

    @staticmethod
    def _address_match(base, pattern):
        return base == pattern or (pattern.endswith(".") and base.startswith(pattern))

    def classify(self, address, rtype=""):
        base = base_address(address)
        if not rtype:
            rtype = base.rsplit(".", 2)[-2] if base.count(".") >= 1 else ""
        for prefix in self.preserve_types:
            if rtype.startswith(prefix):
                return "preserve", "type %s" % prefix
        for pattern in self.preserve_addresses:
            if self._address_match(base, pattern):
                return "preserve", "address %s" % pattern
        for pattern in self.teardown_addresses:
            if self._address_match(base, pattern):
                return "teardown", "address %s" % pattern
        return "unlisted", "no teardown rule"


def _rule_args(parser):
    parser.add_argument("--preserve-types", default="")
    parser.add_argument("--preserve-addresses", default="")
    parser.add_argument("--teardown-addresses", default="")


def cmd_classify_state(args):
    rules = Rules(args)
    targets, lines = [], []
    with open(args.state_file, encoding="utf-8") as handle:
        for raw in handle:
            address = raw.strip()
            if not address or address.startswith("data.") or ".data." in address:
                continue
            kind, why = rules.classify(address)
            if kind == "teardown":
                base = base_address(address)
                if base not in targets:
                    targets.append(base)
                lines.append("TEARDOWN %s" % address)
            elif kind == "preserve":
                lines.append("PRESERVE %s (%s)" % (address, why))
            else:
                lines.append("NOT-TARGETED %s (%s)" % (address, why))
    for line in sorted(lines):
        print(redact_account(line))
    with open(args.targets_out, "w", encoding="utf-8") as handle:
        for target in sorted(targets):
            handle.write(target + "\n")
    return 0


def plan_actions(document):
    """[(verb, address, type)] for every resource change that is not a no-op or a read."""
    found = []
    for change in document.get("resource_changes") or []:
        actions = list((change.get("change") or {}).get("actions") or [])
        if actions in (["no-op"], ["read"], []):
            continue
        if actions == ["delete"]:
            verb = "delete"
        elif sorted(actions) == ["create", "delete"]:
            verb = "replace"
        else:
            verb = "+".join(actions)
        found.append((verb, change.get("address", ""), change.get("type", "")))
    return found


def cmd_destroy_policy(args):
    rules = Rules(args)
    try:
        with open(args.show_json, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        print("POLICY-VIOLATION: destroy plan JSON unreadable: %s" % type(error).__name__)
        return 1
    actions = plan_actions(document)
    violations, lines = [], []
    for verb, address, rtype in actions:
        shown = redact_account(address)
        lines.append("%s %s" % (verb, shown))
        kind, why = rules.classify(address, rtype)
        if kind == "preserve" and verb in ("delete", "replace"):
            violations.append("protected resource would be %sd: %s (%s)" % (verb, shown, why))
        elif verb not in ("delete",):
            violations.append("unexpected %s action in a destroy plan: %s" % (verb, shown))
        elif kind == "unlisted":
            violations.append("delete is not in the teardown set: %s" % shown)
    lines.sort()
    if args.actions_out:
        with open(args.actions_out, "w", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")
    for line in lines:
        print("DESTROY-ACTION: %s" % line)
    for violation in sorted(violations):
        print("POLICY-VIOLATION: %s" % violation)
    if not lines:
        print("destroy plan holds no destructive action")
    return 1 if violations else 0


def _parse_allowed_attrs(text):
    """"type:a+b,type2:c" -> {type: {a, b}, type2: {c}}"""
    table = {}
    for entry in _split(text):
        rtype, _, attrs = entry.partition(":")
        if rtype and attrs:
            table[rtype] = {attr for attr in attrs.split("+") if attr}
    return table


def _changed_attributes(change):
    """Top-level attribute names whose planned value differs from the current one (unknown counts as changed)."""
    before = change.get("before") if isinstance(change.get("before"), dict) else {}
    after = change.get("after") if isinstance(change.get("after"), dict) else {}
    unknown = change.get("after_unknown") if isinstance(change.get("after_unknown"), dict) else {}
    changed = set()
    for key in set(before) | set(after) | set(unknown):
        if before.get(key) != after.get(key) or unknown.get(key) not in (None, False, {}, []):
            changed.add(key)
    return changed


def cmd_prepare_policy(args):
    """The cleanup-preparation plan: only in-place updates of teardown resources, only their protection flags."""
    rules = Rules(args)
    allowed = _parse_allowed_attrs(args.allowed_attrs)
    try:
        with open(args.show_json, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        print("POLICY-VIOLATION: preparation plan JSON unreadable: %s" % type(error).__name__)
        return 1
    violations, lines = [], []
    for change in document.get("resource_changes") or []:
        detail = change.get("change") or {}
        actions = list(detail.get("actions") or [])
        if actions in (["no-op"], ["read"], []):
            continue
        address = redact_account(change.get("address", ""))
        rtype = change.get("type", "")
        if actions != ["update"]:
            verb = "+".join(actions)
            violations.append("preparation plan may only update in place, but plans %s for %s" % (verb, address))
            continue
        kind, _why = rules.classify(change.get("address", ""), rtype)
        if kind != "teardown":
            violations.append("preparation plan changes a resource outside the teardown set (%s): %s" % (kind, address))
            continue
        extra = sorted(_changed_attributes(detail) - allowed.get(rtype, set()))
        if extra:
            violations.append("preparation plan changes attributes other than protection flags on %s: %s" % (address, ", ".join(extra)))
            continue
        lines.append("update %s" % address)
    for line in sorted(lines):
        print("PREPARE-CHANGE: %s" % line)
    for violation in sorted(violations):
        print("POLICY-VIOLATION: %s" % violation)
    if not lines and not violations:
        print("preparation plan holds no change")
    return 1 if violations else 0


def _state_resources(module):
    for resource in module.get("resources") or []:
        yield resource
    for child in module.get("child_modules") or []:
        for resource in _state_resources(child):
            yield resource


def cmd_protection_state(args):
    """Teardown resources whose protection flag is still active in the current state."""
    rules = Rules(args)
    try:
        with open(args.state_json, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError) as error:
        print("PROTECTION-CHECK-FAILED: state JSON unreadable: %s" % type(error).__name__)
        return 2
    wanted = {}
    for entry in _split(args.rules):
        rtype, _, rest = entry.partition(":")
        attr, _, value = rest.partition("=")
        if rtype and attr and value in ("true", "false"):
            wanted.setdefault(rtype, []).append((attr, value == "true"))
    root = ((document.get("values") or {}).get("root_module")) or {}
    active = []
    for resource in _state_resources(root):
        rtype = resource.get("type", "")
        if rtype not in wanted:
            continue
        address = resource.get("address", "")
        kind, _why = rules.classify(address, rtype)
        if kind != "teardown":
            continue
        values = resource.get("values") or {}
        for attr, active_value in wanted[rtype]:
            if values.get(attr) is active_value:
                active.append("%s %s=%s" % (redact_account(address), attr, "true" if active_value else "false"))
    for line in sorted(active):
        print("PROTECTION-ACTIVE: %s" % line)
    if args.targets_out:
        with open(args.targets_out, "w", encoding="utf-8") as handle:
            for address in sorted({line.split(" ", 1)[0] for line in active}):
                handle.write(address + "\n")
    if not active:
        print("no teardown resource has active deletion protection")
    return 1 if active else 0


def cmd_destroy_token(args):
    with open(args.actions_file, encoding="utf-8") as handle:
        actions = sorted(line.rstrip("\n") for line in handle if line.strip())
    body = "scholarchain-destroy-token-v1\nplan_sha256=%s\naccount_sha256=%s\nregion=%s\nenvironment=%s\n" % (
        args.plan_sha256,
        args.account_sha256,
        args.region,
        args.environment,
    )
    body += "".join(action + "\n" for action in actions)
    print(sha256_hex(body))
    return 0


# ---------------------------------------------------------------------------------------------
# runtime preservation (S1)
# ---------------------------------------------------------------------------------------------

INDICATOR_ENTRY = re.compile(r"^([a-z0-9_]+)=([0-9]+)(?:-([0-9]+))?$")


def parse_indicators(text):
    """{type: (low, high)} from "type=N" or "type=LOW-HIGH" entries (the instance count of a COMPLETE deployed runtime), or
    None when the list is empty or malformed, a type repeats, a range is inverted, or no type is required (low >= 1): then
    "no runtime" and "complete runtime" could not be told apart."""
    found = {}
    for entry in _split(text):
        match = INDICATOR_ENTRY.match(entry)
        if not match or match.group(1) in found:
            return None
        low = int(match.group(2))
        high = int(match.group(3)) if match.group(3) is not None else low
        if high < low:
            return None
        found[match.group(1)] = (low, high)
    if not found or not any(low >= 1 for low, _high in found.values()):
        return None
    return found


def runtime_state(path, module, indicators):
    """(verdict, counts, problem) for the live local state file at `path`.

    verdict is "absent" (no instance of any indicator type in `module`: the runtime is not deployed; base-apply resources
    such as the ECS cluster and the ECR repositories are deliberately not indicators), "live" (every indicator type's
    instance count is within its complete-runtime range) or "partial" (anything else: ambiguous, the caller refuses).
    A missing file is "absent" (plan.sh and deploy.sh refuse a missing state themselves). Only each resource's module
    path, mode, type and instance count are read; no attribute, output or value is looked at."""
    counts = dict.fromkeys(indicators, 0)
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except FileNotFoundError:
        return "absent", counts, None
    except (OSError, ValueError) as error:
        return None, counts, "the live state file is unreadable: %s" % type(error).__name__
    resources = document.get("resources") if isinstance(document, dict) else None
    if not isinstance(resources, list):
        return None, counts, "the live state file has no resource list"
    for resource in resources:
        if not isinstance(resource, dict) or resource.get("mode", "managed") != "managed" or resource.get("type") not in counts:
            continue
        where = resource.get("module") or ""
        if where == module or where.startswith(module + "."):
            instances = resource.get("instances")
            counts[resource["type"]] += len(instances) if isinstance(instances, list) else 1
    if not any(counts.values()):
        return "absent", counts, None
    if all(low <= counts[rtype] <= high for rtype, (low, high) in indicators.items()):
        return "live", counts, None
    return "partial", counts, None


def _range_text(low, high):
    return str(low) if low == high else "%d-%d" % (low, high)


def describe_runtime(verdict, counts, indicators, module):
    found = " ".join("%s=%d" % (rtype, counts[rtype]) for rtype in indicators)
    total = sum(counts.values())
    word = {"absent": "no", "live": "yes", "partial": "partial"}[verdict]
    text = "RUNTIME-LIVE: %s (%d deployed-runtime indicator instance(s) of %s in the live state: %s" % (word, total, module, found)
    if verdict != "live":
        text += "; a complete runtime has %s" % " ".join("%s=%s" % (rtype, _range_text(*bounds)) for rtype, bounds in indicators.items())
    if verdict == "absent":
        text += "; the ECS cluster and ECR repositories of a runtime-disabled base apply are not indicators"
    return text + ")"


PARTIAL_REASON = (
    "the live state holds an INCOMPLETE runtime (some, but not all, of the deployed-runtime resources): it is neither "
    "runtime-disabled nor a complete live runtime, so no rollback or base-apply plan can be shown to keep or to leave it "
    "as it is; refusing (fail closed). Inspect the state and route the recovery to the human architect"
)


def _indicator_args(args, label):
    """(indicators, problem): the parsed --indicators list; with --types every indicator type must be protected too."""
    indicators = parse_indicators(args.indicators)
    if indicators is None:
        return None, "%s: the indicator list %r is empty or malformed (type=N or type=LOW-HIGH, at least one required type)" % (label, args.indicators)
    if args.types is not None:
        missing = sorted(set(indicators) - set(_split(args.types)))
        if missing:
            return None, "%s: indicator type(s) %s are not protected types; the pinned configuration is inconsistent" % (label, ",".join(missing))
    return indicators, None


def cmd_runtime_live(args):
    indicators, problem = _indicator_args(args, "RUNTIME-LIVE-CHECK-FAILED")
    if problem:
        print(problem)
        return 2
    verdict, counts, problem = runtime_state(args.state, args.module, indicators)
    if problem:
        print("RUNTIME-LIVE-CHECK-FAILED: %s" % problem)
        return 1
    print(describe_runtime(verdict, counts, indicators, args.module))
    if verdict == "partial":
        print("RUNTIME-LIVE-CHECK-FAILED: %s" % PARTIAL_REASON)
        return 1
    return 0


def _destructive_from_receipt(path, module, types):
    """[(verb, address)] runtime-class deletes or replaces listed in the plan receipt, or None when unreadable."""
    try:
        with open(path, encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, ValueError):
        return None
    actions = receipt.get("actions") if isinstance(receipt, dict) else None
    if not isinstance(actions, list):
        return None
    wanted = set(_split(types))
    found = []
    for entry in actions:
        if not isinstance(entry, dict):
            return None
        verbs = str(entry.get("actions", "")).split("+")
        address = str(entry.get("address", ""))
        if entry.get("type") in wanted and address.startswith(module + ".") and "delete" in verbs:
            found.append(("replace" if "create" in verbs else "delete", address))
    return found


def _destructive_from_show(path, module, types):
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        return None
    changes = document.get("resource_changes") if isinstance(document, dict) else None
    if not isinstance(changes, list):
        return None
    wanted = set(_split(types))
    found = []
    for change in changes:
        if not isinstance(change, dict):
            return None
        verbs = list((change.get("change") or {}).get("actions") or [])
        address = str(change.get("address", ""))
        if change.get("type") in wanted and address.startswith(module + ".") and "delete" in verbs:
            found.append(("replace" if "create" in verbs else "delete", address))
    return found


def cmd_runtime_preservation(args):
    indicators, problem = _indicator_args(args, "RUNTIME-PRESERVATION-FAILED")
    if problem:
        print(problem)
        return 2
    verdict, counts, problem = runtime_state(args.state, args.module, indicators)
    if problem:
        print("RUNTIME-PRESERVATION-FAILED: %s" % problem)
        return 1
    print(describe_runtime(verdict, counts, indicators, args.module))
    if verdict == "partial":
        print("RUNTIME-PRESERVATION-FAILED: %s" % PARTIAL_REASON)
        return 1
    live = verdict == "live"
    problems = []
    if args.expect == "live" and not live:
        problems.append("the bound state shows no live runtime, but this operation keeps a running runtime (applying it would CREATE the runtime): use the runtime-disabled path")
    if args.expect == "not-live" and live:
        problems.append("the bound state shows a LIVE runtime: an infrastructure rollback of it must carry the deployed image revision (--deployed-manifest or --deployed-push-record); without one the plan would delete the runtime")
    if live:
        found = _destructive_from_receipt(args.receipt, args.module, args.types) if args.receipt else _destructive_from_show(args.show_json, args.module, args.types)
        source = "plan receipt action list" if args.receipt else "terraform show -json of the verified plan"
        if found is None:
            problems.append("the %s is unreadable or holds no action list; refusing (fail closed)" % source)
        else:
            for verb, address in sorted(found):
                problems.append("the plan would %s the live runtime resource %s" % (verb, redact_account(address)))
    for item in problems:
        print("RUNTIME-PRESERVATION-FAILED: %s" % item)
    if not problems:
        if live:
            print("runtime preservation ok: the plan deletes or replaces no protected resource of the live runtime")
        else:
            print("runtime preservation ok: the bound state shows no live runtime; nothing to preserve")
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------
# S3 object checksum (N5)
# ---------------------------------------------------------------------------------------------

PLAIN_CHECKSUM = re.compile(r"^[A-Za-z0-9+/]{43}=$")
COMPOSITE_CHECKSUM = re.compile(r"^([A-Za-z0-9+/]{43}=)-([0-9]+)$")


def _b64(raw):
    return base64.b64encode(raw).decode("ascii")


def _range_digest(handle, size):
    digest = hashlib.sha256()
    remaining = size
    while remaining > 0:
        block = handle.read(min(1024 * 1024, remaining))
        if not block:
            raise ValueError("the file is shorter than the part list says")
        digest.update(block)
        remaining -= len(block)
    return digest.digest()


def cmd_s3_checksum(args):
    value = (args.checksum or "").strip()
    try:
        file_size = os.path.getsize(args.file)
    except OSError as error:
        print("S3-CHECKSUM-FAILED: the private copy is unreadable: %s" % type(error).__name__)
        return 1
    if PLAIN_CHECKSUM.match(value):
        digest = hashlib.sha256()
        with open(args.file, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if _b64(digest.digest()) != value:
            print("S3-CHECKSUM-FAILED: the S3-computed ChecksumSHA256 differs from the sha256 of the verified private copy")
            return 1
        print("S3-computed ChecksumSHA256 equals the sha256 of the verified private copy")
        return 0
    composite = COMPOSITE_CHECKSUM.match(value)
    if not composite:
        print("S3-CHECKSUM-FAILED: S3 returned no usable ChecksumSHA256 (the object was uploaded with --checksum-algorithm SHA256)")
        return 1
    parts_expected = int(composite.group(2))
    if not args.parts_file:
        print("S3-CHECKSUM-FAILED: a composite (multipart) checksum needs the part list S3 reports")
        return 1
    parts = []
    try:
        with open(args.parts_file, encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
                    parts.append((int(fields[0]), int(fields[1]), fields[2]))
    except OSError as error:
        print("S3-CHECKSUM-FAILED: the part list is unreadable: %s" % type(error).__name__)
        return 1
    parts.sort()
    problems = []
    if [number for number, _size, _sum in parts] != list(range(1, parts_expected + 1)):
        problems.append("S3 reported %d part(s) but the checksum names %d (a truncated or missing part list)" % (len(parts), parts_expected))
    elif sum(size for _n, size, _c in parts) != file_size:
        problems.append("the part sizes S3 reports do not add up to the size of the private copy")
    else:
        raws = []
        with open(args.file, "rb") as handle:
            try:
                for number, size, reported in parts:
                    raw = _range_digest(handle, size)
                    raws.append(raw)
                    if _b64(raw) != reported:
                        problems.append("the S3-computed checksum of part %d differs from the private copy" % number)
            except ValueError as error:
                problems.append(str(error))
        if not problems and _b64(hashlib.sha256(b"".join(raws)).digest()) + "-%d" % parts_expected != value:
            problems.append("the composite checksum is not the checksum of the reported part checksums")
    for item in problems:
        print("S3-CHECKSUM-FAILED: %s" % item)
    if not problems:
        print("S3-computed composite ChecksumSHA256 (%d parts) equals the part-by-part sha256 of the verified private copy" % parts_expected)
    return 1 if problems else 0


# ---------------------------------------------------------------------------------------------
# ECS and registry checks
# ---------------------------------------------------------------------------------------------

def cmd_ecs_services(args):
    wanted = args.services.split()
    seen = {}
    with open(args.file, encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 2 and fields[0].strip():
                seen.setdefault(fields[0].strip(), []).append(fields[1].strip())
    problems = []
    for service in wanted:
        arns = seen.get(service, [])
        if len(arns) != 1 or not arns[0] or arns[0] == "None":
            problems.append("ECS service %s is missing or has no active task definition" % service)
    for problem in problems:
        print("ECS-CHECK-FAILED: %s" % problem)
    if problems:
        return 1
    for service in wanted:
        print("%s %s" % (service, seen[service][0]))
    return 0


def cmd_image_ref(args):
    with open(args.file, encoding="utf-8") as handle:
        images = [token for token in re.split(r"\s+", handle.read()) if token]
    accepted = {args.expected}
    if args.expected_digest_ref:
        accepted.add(args.expected_digest_ref)
    if any(image in accepted for image in images):
        print("task definition references the expected image")
        return 0
    print("ECS-CHECK-FAILED: the active task definition does not reference the expected image (found %d container image(s))" % len(images))
    return 1


def cmd_push_digest(args):
    with open(args.file, encoding="utf-8", errors="replace") as handle:
        matches = re.findall(r"digest:\s*(sha256:[0-9a-f]{64})", handle.read())
    if not matches:
        print("no digest line found in the docker push output")
        return 1
    print(matches[-1])
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("git-tree")
    p.add_argument("--repo", required=True)
    p.add_argument("--exempt", required=True)
    p.set_defaults(fn=cmd_git_tree)

    p = sub.add_parser("prespend")
    p.add_argument("--file", required=True)
    p.add_argument("--max-age-hours", type=float, required=True)
    # Exactly one of the two is required: a spending stage gives --min-headroom, the teardown-only stage gives
    # --no-headroom-floor. Giving both or neither is a usage error (exit 2), so a floor can never silently vanish.
    floor = p.add_mutually_exclusive_group(required=True)
    floor.add_argument("--min-headroom", type=float)
    floor.add_argument("--no-headroom-floor", action="store_true")
    p.add_argument("--clock-file")
    p.add_argument("--label")
    p.set_defaults(fn=cmd_prespend)

    p = sub.add_parser("plan-target")
    p.add_argument("--show-json", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--account-sha256", required=True)
    p.add_argument("--environment", required=True)
    p.add_argument("--project", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--image-revision")
    group.add_argument("--no-image-revision", action="store_true")
    p.set_defaults(fn=cmd_plan_target)

    p = sub.add_parser("plan-provenance")
    p.add_argument("--receipt", required=True)
    p.add_argument("--plan-sha256", required=True)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--scripts-commit", required=True)
    p.add_argument("--account-sha256", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--environment", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--purpose", default="deploy-plan")
    p.add_argument("--terraform-version", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--image-revision")
    group.add_argument("--no-image-revision", action="store_true")
    p.set_defaults(fn=cmd_plan_provenance)

    p = sub.add_parser("classify-state")
    p.add_argument("--state-file", required=True)
    p.add_argument("--targets-out", required=True)
    _rule_args(p)
    p.set_defaults(fn=cmd_classify_state)

    p = sub.add_parser("destroy-policy")
    p.add_argument("--show-json", required=True)
    p.add_argument("--actions-out")
    _rule_args(p)
    p.set_defaults(fn=cmd_destroy_policy)

    p = sub.add_parser("prepare-policy")
    p.add_argument("--show-json", required=True)
    p.add_argument("--allowed-attrs", required=True)
    _rule_args(p)
    p.set_defaults(fn=cmd_prepare_policy)

    p = sub.add_parser("protection-state")
    p.add_argument("--state-json", required=True)
    p.add_argument("--rules", required=True)
    p.add_argument("--targets-out")
    _rule_args(p)
    p.set_defaults(fn=cmd_protection_state)

    p = sub.add_parser("destroy-token")
    p.add_argument("--plan-sha256", required=True)
    p.add_argument("--account-sha256", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--environment", required=True)
    p.add_argument("--actions-file", required=True)
    p.set_defaults(fn=cmd_destroy_token)

    p = sub.add_parser("runtime-live")
    p.add_argument("--state", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--indicators", required=True)
    p.add_argument("--types")
    p.set_defaults(fn=cmd_runtime_live)

    p = sub.add_parser("runtime-preservation")
    p.add_argument("--state", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--indicators", required=True)
    p.add_argument("--types", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--receipt")
    group.add_argument("--show-json")
    p.add_argument("--expect", choices=["live", "not-live", "any"], default="any")
    p.set_defaults(fn=cmd_runtime_preservation)

    p = sub.add_parser("s3-checksum")
    p.add_argument("--file", required=True)
    p.add_argument("--checksum", required=True)
    p.add_argument("--parts-file")
    p.set_defaults(fn=cmd_s3_checksum)

    p = sub.add_parser("ecs-services")
    p.add_argument("--file", required=True)
    p.add_argument("--services", required=True)
    p.set_defaults(fn=cmd_ecs_services)

    p = sub.add_parser("image-ref")
    p.add_argument("--file", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--expected-digest-ref")
    p.set_defaults(fn=cmd_image_ref)

    p = sub.add_parser("push-digest")
    p.add_argument("--file", required=True)
    p.set_defaults(fn=cmd_push_digest)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))
