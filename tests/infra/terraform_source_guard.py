#!/usr/bin/env python3
"""Small literal-source checks; not an HCL evaluator, IAM simulator or secret scanner.

Only Git-visible .tf/.tfvars below infra/terraform are opened. Dynamic policies,
interpolated resource scope and service effectiveness need the native plan tests
and manual review. Findings deliberately omit the offending source/value.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from dataclasses import dataclass, field


@dataclass
class Token:
    value: str
    start: int
    quoted: bool = False
    owner: int = 0


@dataclass
class Object:
    parent: int
    end: int = 0
    resource_type: str = ""
    fields: dict = field(default_factory=dict)
    start: int = 0


def tokens(source):
    """Keep strings whole, including quotes inside ${...}; ignore comments."""
    result = []
    i = 0
    while i < len(source):
        if source[i].isspace():
            i += 1
        elif source.startswith(("#", "//"), i):
            end = source.find("\n", i)
            i = len(source) if end < 0 else end
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = len(source) if end < 0 else end + 2
        elif source[i] == '"':
            start = i
            i += 1
            interpolation = 0
            nested_quote = False
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                    continue
                if not interpolation and source.startswith("${", i):
                    interpolation = 1
                    i += 2
                    continue
                if interpolation:
                    if source[i] == '"':
                        nested_quote = not nested_quote
                    elif not nested_quote and source[i] == "{":
                        interpolation += 1
                    elif not nested_quote and source[i] == "}":
                        interpolation -= 1
                elif source[i] == '"':
                    i += 1
                    break
                i += 1
            raw = source[start:i]
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = raw[1:-1]
            result.append(Token(value, start, True))
        else:
            match = re.match(r"[A-Za-z_][A-Za-z_0-9-]*|.", source[i:])
            value = match.group()
            result.append(Token(value, i))
            i += len(value)
    return result


# Exact actions with no IAM resource type, per the AWS Service Authorization Reference
# (list_resourcegroupstaggingapi, list_emr, list_kms). Statement-level, exact match only:
# no wildcards and no service-wide entries. A statement is exempt only if every action
# is in this set (or is another already-exempt action).
NO_RESOURCE_TYPE_ACTIONS = frozenset({
    "tag:GetResources",
    "elasticmapreduce:ListClusters",
    "elasticmapreduce:ListSecurityConfigurations",
    "elasticmapreduce:DescribeSecurityConfiguration",
    "elasticmapreduce:CreateSecurityConfiguration",
    "elasticmapreduce:DeleteSecurityConfiguration",
    "elasticmapreduce:RunJobFlow",
    "kms:CreateKey",
    "kms:ListAliases",
})


# Actions with no IAM resource type are scoped ONLY by request tags (and the region): an Allow for them with no
# Condition, an empty Condition, or a literal Condition without an aws:RequestTag/ key is an unscoped grant (12D
# review item 10: kms:CreateKey on "*" with the condition stripped used to pass). A condition built from locals or
# functions (merge(...)) cannot be evaluated by this literal-source check and is accepted here; the rendered
# policy is asserted by tests/infra/test_deployer_hardening.py.
REQUEST_TAG_SCOPED_ACTIONS = frozenset({
    "kms:CreateKey",
    "elasticmapreduce:RunJobFlow",
})


def scan(path, source):
    ts = tokens(source)
    objects = [Object(0, len(ts))]
    stack = [0]
    for i, token in enumerate(ts):
        token.owner = stack[-1]
        if not token.quoted and token.value == "{":
            resource = ""
            if i >= 3 and ts[i - 3].value in ("resource", "data"):
                resource = ts[i - 2].value
            objects.append(Object(stack[-1], resource_type=resource, start=i + 1))
            stack.append(len(objects) - 1)
        elif not token.quoted and token.value == "}" and len(stack) > 1:
            objects[stack.pop()].end = i
    for i, token in enumerate(ts[:-1]):
        if (token.quoted or re.fullmatch(r"[A-Za-z_][A-Za-z_0-9-]*", token.value)) and ts[
            i + 1
        ].value in ("=", ":"):
            objects[token.owner].fields[token.value.lower()] = i

    def values(obj_id, key):
        obj = objects[obj_id]
        if key not in obj.fields:
            return []
        start = obj.fields[key]
        end = min([v for v in obj.fields.values() if v > start] + [obj.end])
        return [t.value for t in ts[start + 2 : end] if t.quoted]

    def effect(obj_id):
        while obj_id:
            found = values(obj_id, "effect")
            if found:
                return found[0].lower()
            obj_id = objects[obj_id].parent
        return ""

    def inside_key_policy(obj_id):
        while obj_id:
            if objects[obj_id].resource_type == "aws_kms_key":
                return True
            obj_id = objects[obj_id].parent
        return False

    def condition_is_unscoped(obj_id):
        """True when a statement has no usable Condition for a request-tag-scoped action (see above)."""
        obj = objects[obj_id]
        if "condition" not in obj.fields:
            return True
        start = obj.fields["condition"]
        end = min([v for v in obj.fields.values() if v > start] + [obj.end])
        span = ts[start + 2 : end]
        if not [t for t in span if t.quoted or t.value not in ("{", "}", "[", "]", ",", "null")]:
            return True  # Condition = {} or null
        literal = [t.value for t in span if t.quoted]
        return bool(literal) and not any(v.lower().startswith("aws:requesttag/") for v in literal)

    findings = set()

    def report(category, position):
        findings.add((source.count("\n", 0, position) + 1, category))

    # Wildcard action literals in locals are checked too; only their enclosing
    # literal Deny statement can exempt them. Comments and descriptive prose do not match.
    for token in ts:
        if token.quoted and re.fullmatch(r"[a-z0-9-]+:[A-Za-z*?]+", token.value):
            if any(c in token.value for c in "*?") and effect(token.owner) != "deny":
                report("wildcard-iam-action", token.start)

    for obj_id, obj in enumerate(objects):
        effects = values(obj_id, "effect")
        if effects and effects[0].lower() == "allow":
            actions = values(obj_id, "action") + values(obj_id, "actions")
            if any(a in ("*", "?") for a in actions):
                key = "action" if "action" in obj.fields else "actions"
                report("wildcard-iam-action", ts[obj.fields[key]].start)
            if any(a in REQUEST_TAG_SCOPED_ACTIONS for a in actions) and condition_is_unscoped(obj_id):
                key = "action" if "action" in obj.fields else "actions"
                report("unconditioned-request-scoped-action", ts[obj.fields[key]].start)
            resource_key = "resource" if "resource" in obj.fields else "resources"
            resources = values(obj_id, resource_key)
            for resource in resources:
                exception = inside_key_policy(obj_id) or actions == ["ecr:GetAuthorizationToken"]
                exception = exception or bool(actions) and all(
                    re.fullmatch(r"ec2:Describe[A-Za-z]+", a) or a in NO_RESOURCE_TYPE_ACTIONS
                    for a in actions
                )
                broad = resource in ("*", "?")
                if resource.startswith("arn:"):
                    parts = resource.split(":", 5)
                    broad = len(parts) != 6 or any(
                        c in part for part in parts[1:5] for c in "*?"
                    ) or parts[5] in ("*", "?")
                if broad and not (resource == "*" and exception):
                    report("global-iam-resource", ts[obj.fields[resource_key]].start)
            principal_key = "principal" if "principal" in obj.fields else "principals"
            if any(v in ("*", "?") for v in values(obj_id, principal_key)):
                report("public-allow-principal", ts[obj.fields[principal_key]].start)
        if "acl" in obj.fields:
            if any(v in ("public-read", "public-read-write", "authenticated-read") for v in values(obj_id, "acl")):
                report("public-bucket-acl", ts[obj.fields["acl"]].start)
        if obj.resource_type == "aws_s3_bucket_acl":
            # Nested grants are represented by descendants; all-users URIs are public grants.
            for token in ts[obj.start:obj.end]:
                if token.quoted and token.value.endswith(("/AllUsers", "/AuthenticatedUsers")):
                    report("public-bucket-grant", token.start)

    credential_name = re.compile(
        r"(?:aws_)?(?:access_key(?:_id)?|secret_key|secret_access_key)|"
        r"secret_string|secret_binary|password|api_key|token", re.I
    )
    placeholder = re.compile(r"(?:<.*>|REPLACE_ME|CHANGEME|PLACEHOLDER)", re.I)
    for i, token in enumerate(ts):
        if not token.quoted:
            continue
        if re.search(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}", token.value):
            report("secret-shaped-literal", token.start)
        if i >= 2 and ts[i - 1].value in ("=", ":") and credential_name.fullmatch(ts[i - 2].value):
            if token.value and "${" not in token.value and not placeholder.fullmatch(token.value):
                report("literal-credential-value", token.start)
    return [{"path": path, "line": line, "category": category} for line, category in sorted(findings)]


class GuardExamples(unittest.TestCase):
    def test_rejects_wildcard_allow_beside_valid_deny_and_key_policy(self):
        source = '''resource "aws_kms_key" "k" { policy = jsonencode({Statement = [
          {Effect="Allow", Action=["kms:Decrypt"], Resource="*"}]}) }
          locals { statements = [
          {Effect="Deny", Action=["s3:*"], Principal="*", Resource="*"},
          {Effect="Allow", Action=["s3:*"], Resource=["arn:aws:s3:::course/*"]}] }'''
        found = scan("synthetic.tf", source)
        self.assertEqual([f["category"] for f in found], ["wildcard-iam-action"])

    def test_rejects_global_resources_and_public_access(self):
        examples = (
            ('{Effect="Allow", Action=["*"], Resource=["arn:aws:s3:::course/*"]}', "wildcard-iam-action"),
            ('{Effect="Allow", Action=["ec2:TerminateInstances"], Resource=["arn:aws:ec2:*:*:instance/*"]}', "global-iam-resource"),
            ('{Effect="Allow", Action=["s3:GetObject"], Resource=["arn:*"]}', "global-iam-resource"),
            ('{Effect="Allow", Action=["s3:GetObject"], Principal={AWS="*"}, Resource=["arn:aws:s3:::course/*"]}', "public-allow-principal"),
            ('resource "aws_s3_bucket_acl" "b" { acl="public-read" }', "public-bucket-acl"),
            ('resource "aws_s3_bucket_acl" "b" { access_control_policy { grant { grantee { uri="http://acs.amazonaws.com/groups/global/AllUsers" } } } }', "public-bucket-grant"),
        )
        for source, category in examples:
            with self.subTest(category=category):
                self.assertIn(category, [f["category"] for f in scan("synthetic.tf", source)])

    def test_secret_findings_do_not_echo_values(self):
        synthetic = "AKIA" + "A" * 16
        found = scan("synthetic.tfvars", 'access_key = "' + synthetic + '"')
        self.assertEqual({f["category"] for f in found}, {"secret-shaped-literal", "literal-credential-value"})
        self.assertNotIn(synthetic, json.dumps(found))

    def test_allows_scoped_globs_and_statement_local_exceptions(self):
        source = '''locals { statements = [
          {Effect="Allow", Action=["s3:GetObject"], Resource=["${var.bucket_arns["graph"]}/*"]},
          {Effect="Allow", Action=["logs:PutLogEvents"], Resource=["arn:aws:logs:${var.region}:${var.account}:log-group:/course/api:log-stream:*"]},
          {Effect="Allow", Action=["ecr:GetAuthorizationToken"], Resource=["*"]},
          {Effect="Allow", Action=["ec2:DescribeInstances"], Resource=["*"]},
          {Effect="Deny", Action=["s3:*"], Resource="*", Principal="*"}] }
          # Effect="Allow", Action=["iam:*"], Resource="*"
          /* acl="public-read" */'''
        self.assertEqual(scan("synthetic.tf", source), [])

    def test_exact_no_resource_type_actions_pass_on_global_resource(self):
        scoped = ', Condition={StringEquals={"aws:RequestTag/scholarchain:stack"="spike-emr"}}'
        for action in sorted(NO_RESOURCE_TYPE_ACTIONS):
            with self.subTest(action=action):
                source = '{Effect="Allow", Action=["%s"], Resource="*"%s}' % (action, scoped)
                self.assertEqual(scan("synthetic.tf", source), [])
        multi = '{Effect="Allow", Action=["kms:CreateKey", "kms:ListAliases", "ec2:DescribeVpcs"], Resource=["*"]%s}' % scoped
        self.assertEqual(scan("synthetic.tf", multi), [])

    def test_no_resource_type_exemption_is_narrow(self):
        examples = (
            ('{Effect="Allow", Action=["kms:CreateKey", "kms:PutKeyPolicy"], Resource="*"}', "global-iam-resource"),
            ('{Effect="Allow", Action=["tag:GetResources", "iam:CreateRole"], Resource="*"}', "global-iam-resource"),
            ('{Effect="Allow", Action=["elasticmapreduce:*"], Resource="*"}', "wildcard-iam-action"),
            ('{Effect="Allow", Action=["elasticmapreduce:*"], Resource="*"}', "global-iam-resource"),
            ('{Effect="Allow", Action=["kms:Create*"], Resource="*"}', "wildcard-iam-action"),
            ('{Effect="Allow", Action=["kms:Create*"], Resource="*"}', "global-iam-resource"),
            ('{Effect="Allow", Action=["iam:CreateRole"], Resource="*"}', "global-iam-resource"),
            ('{Effect="Allow", Action=["elasticmapreduce:TerminateJobFlows"], Resource="*"}', "global-iam-resource"),
            ('{Effect="Allow", Action=["kms:CreateKey"], Resource=["arn:aws:kms:*:*:key/*"]}', "global-iam-resource"),
        )
        for source, category in examples:
            with self.subTest(source=source, category=category):
                self.assertIn(category, [f["category"] for f in scan("synthetic.tf", source)])

    def test_neighbouring_rogue_allow_is_still_rejected_beside_exempt_action(self):
        source = '''locals { statements = [
          {Effect="Allow", Action=["kms:CreateKey"], Resource="*", Condition={StringEquals={"aws:RequestTag/x"="y"}}},
          {Effect="Allow", Action=["iam:PassRole"], Resource="*"}] }'''
        found = scan("synthetic.tf", source)
        self.assertEqual([(f["line"], f["category"]) for f in found], [(3, "global-iam-resource")])

    def test_request_tag_scoped_actions_must_keep_a_request_tag_condition(self):
        """12D item 10: a condition-stripped or weakened statement is rejected; a request-tag condition passes."""
        rejected = (
            '{Effect="Allow", Action=["kms:CreateKey"], Resource="*"}',
            '{Effect="Allow", Action=["kms:CreateKey"], Resource=["*"], Condition={}}',
            '{Effect="Allow", Action=["kms:CreateKey"], Resource=["*"], Condition=null}',
            '{Effect="Allow", Action=["kms:CreateKey"], Resource="*", Condition={StringEquals={"aws:RequestedRegion"="us-east-2"}}}',
            '{Effect="Allow", Action=["elasticmapreduce:RunJobFlow"], Resource="*"}',
            '{Effect="Allow", Action=["elasticmapreduce:RunJobFlow"], Resource="*", Condition={StringEquals={"aws:RequestedRegion"="us-east-2"}}}',
            '{"Effect":"Allow","Action":["kms:CreateKey"],"Resource":"*"}',
            '{Effect="Allow", Action=["kms:CreateKey", "kms:ListAliases"], Resource="*"}',
        )
        for source in rejected:
            with self.subTest(source=source):
                self.assertIn("unconditioned-request-scoped-action", [f["category"] for f in scan("synthetic.tf", source)])
        accepted = (
            '{Effect="Allow", Action=["kms:CreateKey"], Resource="*", Condition={StringEquals={"aws:RequestTag/scholarchain:stack"="spike-emr"}}}',
            '{Effect="Allow", Action=["elasticmapreduce:RunJobFlow"], Resource="*", Condition={StringEquals={"aws:RequestedRegion"="us-east-2", "aws:RequestTag/scholarchain:stack"="spike-emr"}}}',
            '{Effect="Allow", Action=["kms:CreateKey"], Resource="*", Condition={StringEquals=merge(local.c_region, local.c_req_stack)}}',
            '{"Effect":"Allow","Action":["kms:CreateKey"],"Resource":"*","Condition":{"StringEquals":{"aws:RequestTag/x":"y"}}}',
            '{Effect="Deny", Action=["kms:CreateKey"], Resource="*"}',
        )
        for source in accepted:
            with self.subTest(source=source):
                self.assertEqual(scan("synthetic.tf", source), [])

    def test_unconditioned_finding_reports_only_path_line_and_category(self):
        found = scan("synthetic.tf", '{Effect="Allow", Action=["kms:CreateKey"], Resource="*"}')
        self.assertEqual(found, [{"path": "synthetic.tf", "line": 1, "category": "unconditioned-request-scoped-action"}])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(GuardExamples))
        return 0 if result.wasSuccessful() else 1
    root = args.repo_root.resolve()
    listed = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "infra/terraform"], cwd=root
    ).decode().split("\0")
    paths = sorted({p for p in listed if p.endswith((".tf", ".tfvars"))})
    if not paths:
        parser.error("no Git-visible Terraform source files found")
    findings = []
    for path in paths:
        file = root / path
        if file.is_symlink():
            findings.append({"path": path, "line": 0, "category": "source-symlink-not-inspected"})
        else:
            findings.extend(scan(path, file.read_text()))
    print(json.dumps({"scope": "literal-source-only", "files": len(paths), "findings": findings}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
