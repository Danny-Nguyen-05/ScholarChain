#!/usr/bin/env python3
"""Small literal-source checks; not an HCL evaluator, IAM simulator or secret scanner.

Only Git-visible .tf/.tfvars, policy JSON templates (*.json.tftpl) and
environments/*.json.example below infra/terraform are opened. Template interpolations
(${...}, %{...}) are blanked before scanning, so they are never read as wildcards and
their rendered value is not evaluated. Dynamic policies, interpolated resource scope and
service effectiveness need the native plan tests and manual review. Findings
deliberately omit the offending source/value.
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


@dataclass(frozen=True)
class GlobalGrant:
    """One reviewed Allow statement that may name Resource "*" because its actions have no usable resource-level scope.

    The exemption is per statement: the file path AND the exact action set must both match (no wildcard, no subset or
    superset, and the same actions in another file are still flagged). `requires_condition` additionally demands that the
    statement keep a non-empty Condition (the region condition) so that deleting it is reported. Each entry is a reviewed
    claim by the infra owner, derived from the statement comment in the source and deployer/README.md "Honest list"; this
    guard does not fetch or re-verify the cited page.
    """

    path: str
    actions: frozenset
    justification: str
    url: str
    requires_condition: bool = True
    # Replan W5a: each element is a group of alternatives; the statement Condition must contain, for every group, at least one
    # token (an identifier such as `c_region` or a quoted literal such as "acm:ValidationMethod"). A trailing "/" in an
    # alternative matches by prefix ("aws:RequestTag/"). Empty = only the non-empty-Condition rule applies.
    condition_requires: tuple = ()


SAR = "https://docs.aws.amazon.com/service-authorization/latest/reference/"
PHASE14_MAIN = "infra/terraform/deployer/phase14_main.tf"
RUNTIME_BOUNDARY = "infra/terraform/deployer/boundaries/runtime.json.tftpl"
NEPTUNE_TUNNEL = "infra/terraform/modules/identity/neptune_tunnel.tf"
ECS_EXEC_ACTIONS = frozenset({
    "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
    "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel",
})
ECS_EXEC_JUSTIFICATION = (
    "The four ssmmessages channel actions ECS Exec needs. Per the Service Authorization Reference "
    "(list_ssmmessages.html) CreateControlChannel, CreateDataChannel and OpenControlChannel list NO resource type; "
    "OpenDataChannel lists the `session` resource type (arn:<partition>:ssm:<region>:<account>:session/<SessionId>), but "
    "the session ID is generated when the ECS Exec session opens, so no ARN exists at authoring time, and the AWS ECS "
    "developer guide (task-iam-roles.html, ECS Exec permissions) grants all four on Resource \"*\". Exactly these four "
    "actions, in this one file; no data access."
)
ACM_REQUEST_CONDITION = (
    ("c_region", "aws:RequestedRegion"),  # region lock
    ("acm:ValidationMethod",),  # DNS validation (the literal "DNS" is checked by the statement test)
    ("DNS",),
    ("c_req_main", "aws:RequestTag/"),  # request tags (project, environment)
)
GLOBAL_RESOURCE_ALLOWLIST = (
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({
            "rds:DescribeDBClusters", "rds:DescribeDBInstances", "rds:DescribeDBSubnetGroups",
            "rds:DescribeDBClusterParameterGroups", "rds:DescribeDBClusterParameters", "rds:DescribeDBParameterGroups",
            "rds:DescribeDBParameters", "rds:DescribeDBClusterSnapshots", "rds:DescribeDBEngineVersions",
            "rds:DescribeGlobalClusters",
        }),
        "Neptune is managed through the rds API namespace. The provider refreshes a cluster, instance or parameter group "
        "with list-style Describe calls (a filter, not a resource ARN), and DescribeDBEngineVersions and "
        "DescribeGlobalClusters name no resource, so a resource ARN cannot scope them. Read-only; region-locked by "
        "aws:RequestedRegion. Every create, modify and delete action stays on the scholarchain-<env>-* ARNs.",
        SAR + "list_amazonrds.html",
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({"cloudwatch:DescribeAlarms", "cloudwatch:ListDashboards"}),
        "DescribeAlarms (the target-tracking alarms ECS autoscaling creates are read by a name filter) and ListDashboards are "
        "list-style reads that take no resource ARN. Read-only; region-locked. PutMetricAlarm, DeleteAlarms and the dashboard "
        "writes stay on the scholarchain-<env>-* alarm and dashboard ARNs.",
        SAR + "list_amazoncloudwatch.html",
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({"ecs:RegisterTaskDefinition"}),
        "RegisterTaskDefinition creates a new task-definition revision and has no resource type that exists before the call. "
        "It is scoped by the request tags (project, environment) and by aws:RequestedRegion, and the family is limited by "
        "iam:PassRole, which only allows the scholarchain-<env> task and execution roles.",
        SAR + "list_amazonelasticcontainerservice.html",
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({"ecs:DeregisterTaskDefinition", "ecs:DescribeTaskDefinition", "ecs:DeleteTaskDefinitions"}),
        "The task-definition family name is not carried in the request ARN for every one of these calls (Describe takes a "
        "family or revision, Delete takes a list), so the scholarchain-<env> family cannot be matched by an ARN pattern. "
        "Region-locked by aws:RequestedRegion; the role cannot create or run a task definition without the request tags.",
        SAR + "list_amazonelasticcontainerservice.html",
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({
            "elasticloadbalancing:DescribeLoadBalancers", "elasticloadbalancing:DescribeLoadBalancerAttributes",
            "elasticloadbalancing:DescribeTargetGroups", "elasticloadbalancing:DescribeTargetGroupAttributes",
            "elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeListenerAttributes",
            "elasticloadbalancing:DescribeTags", "elasticloadbalancing:DescribeTargetHealth",
            "elasticloadbalancing:DescribeCapacityReservation", "acm:DescribeCertificate",
        }),
        "Elastic Load Balancing v2 Describe* calls are list-style reads that take names or ARNs in the request body and no "
        "resource-level permission, and the provider also reads the listener certificate with acm:DescribeCertificate. "
        "Read-only; region-locked. Create, modify and delete stay on the scholarchain-<env>-* load balancer, target group and "
        "listener ARNs.",
        SAR + "list_elasticloadbalancingv2.html",
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({
            "servicediscovery:GetOperation", "application-autoscaling:DescribeScalableTargets",
            "application-autoscaling:DescribeScalingPolicies", "application-autoscaling:DescribeScalingActivities",
        }),
        "servicediscovery:GetOperation polls an asynchronous Cloud Map operation by an ID that exists only after the call, and "
        "the application-autoscaling Describe* calls are list-style reads; none takes a resource ARN. Read-only; region-locked. "
        "Register, deregister, put and delete stay on scalable-target and the scholarchain-<env> namespace and service ARNs.",
        SAR + "list_awscloudmap.html and " + SAR + "list_applicationautoscaling.html",
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({
            "route53:CreateHostedZone", "route53:GetHostedZone", "route53:ListHostedZonesByName",
            "route53:DeleteHostedZone", "route53:ChangeResourceRecordSets", "route53:ListResourceRecordSets",
            "route53:GetChange", "route53:ListTagsForResource", "route53:ChangeTagsForResource",
        }),
        "Cloud Map creates and deletes the private hosted zone for the service-discovery namespace with the caller's own "
        "permissions. The hosted-zone ID does not exist before CreateHostedZone, and Route 53 is a global service, so there "
        "is neither a pre-known ARN nor a regional condition (no aws:RequestedRegion). Recorded as the largest "
        "service-level residual of this set in deployer/README.md.",
        SAR + "list_amazonroute53.html",
        requires_condition=False,
    ),
    GlobalGrant(
        PHASE14_MAIN,
        frozenset({"acm:RequestCertificate"}),
        "acm:RequestCertificate lists no resource type in the Service Authorization Reference (list_acm.html; only condition "
        "keys): the certificate ARN is created by the call. It is scoped by aws:RequestedRegion, acm:ValidationMethod = DNS "
        "and the project request tags, and the statement must keep all three. The certificate is then managed only under "
        "the tag-scoped statements.",
        SAR + "list_acm.html",
        condition_requires=ACM_REQUEST_CONDITION,
    ),
    GlobalGrant(
        RUNTIME_BOUNDARY, ECS_EXEC_ACTIONS, ECS_EXEC_JUSTIFICATION, SAR + "list_ssmmessages.html",
        requires_condition=False,
    ),
    GlobalGrant(
        NEPTUNE_TUNNEL, ECS_EXEC_ACTIONS, ECS_EXEC_JUSTIFICATION, SAR + "list_ssmmessages.html",
        requires_condition=False,
    ),
)
_GRANTS = {(g.path, g.actions): g for g in GLOBAL_RESOURCE_ALLOWLIST}
assert len(_GRANTS) == len(GLOBAL_RESOURCE_ALLOWLIST), "duplicate allowlist key"


def blank_interpolations(source):
    """Replace every Terraform template interpolation (`${...}` or `%{...}`) with `x` of equal length (newlines kept) so that
    a template is scanned as plain JSON: a placeholder is never read as a wildcard and positions are unchanged."""
    out, i = [], 0
    while i < len(source):
        if source.startswith(("${", "%{"), i) and not source.startswith(("$${", "%%{"), i - 1 if i else 0):
            depth, j, quoted = 1, i + 2, False
            while j < len(source) and depth:
                ch = source[j]
                if ch == "\\":
                    j += 2
                    continue
                if ch == '"':
                    quoted = not quoted
                elif not quoted and ch == "{":
                    depth += 1
                elif not quoted and ch == "}":
                    depth -= 1
                j += 1
            out.append("".join("\n" if c == "\n" else "x" for c in source[i:j]))
            i = j
        else:
            out.append(source[i])
            i += 1
    return "".join(out)


def scan(path, source, used=None):
    """Findings for one file. `used`, when given, collects the GlobalGrant entries that exempted a statement."""
    if path.endswith(".tftpl"):
        source = blank_interpolations(source)
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

    def condition_missing(obj_id):
        """True when a statement has no Condition, an empty one, or null."""
        obj = objects[obj_id]
        if "condition" not in obj.fields:
            return True
        start = obj.fields["condition"]
        end = min([v for v in obj.fields.values() if v > start] + [obj.end])
        return not [t for t in ts[start + 2 : end] if t.quoted or t.value not in ("{", "}", "[", "]", ",", "null")]

    def condition_has(obj_id, alternatives):
        """True when the statement Condition contains one of the alternative tokens (see GlobalGrant.condition_requires)."""
        obj = objects[obj_id]
        if "condition" not in obj.fields:
            return False
        start = obj.fields["condition"]
        end = min([v for v in obj.fields.values() if v > start] + [obj.end])
        span = [t.value for t in ts[start + 2 : end]]
        return any(v == a or (a.endswith("/") and v.startswith(a)) for v in span for a in alternatives)

    def resolved_actions(obj_id):
        """Literal action strings of a statement; `Action = local.name` is resolved from the one literal `name = [...]` in the
        same file (so a shared locals list is checked as if inlined; anything else stays unresolved and is not exempt)."""
        obj = objects[obj_id]
        found = values(obj_id, "action") + values(obj_id, "actions")
        key = "action" if "action" in obj.fields else "actions" if "actions" in obj.fields else None
        if found or key is None:
            return found
        head = [t.value for t in ts[obj.fields[key] + 2 : obj.fields[key] + 5]]
        if head[:2] == ["local", "."] and len(head) == 3:
            owners = [i for i, o in enumerate(objects) if head[2].lower() in o.fields and i != obj_id]
            if len(owners) == 1:
                return values(owners[0], head[2].lower())
        return found

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
            actions = resolved_actions(obj_id)
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
                grant = _GRANTS.get((path, frozenset(actions))) if actions and resource == "*" else None
                if broad and grant is not None and not exception:
                    if used is not None:
                        used.add(grant)
                    if grant.requires_condition and condition_missing(obj_id):
                        report("unconditioned-allowlisted-global-grant", ts[obj.fields[resource_key]].start)
                    elif any(not condition_has(obj_id, group) for group in grant.condition_requires):
                        report("weakened-allowlisted-global-grant", ts[obj.fields[resource_key]].start)
                elif broad and not (resource == "*" and exception):
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


    def test_global_resource_allowlist_entries_are_justified_and_narrow(self):
        self.assertEqual(len(GLOBAL_RESOURCE_ALLOWLIST), 10)
        self.assertEqual(
            sorted({g.path for g in GLOBAL_RESOURCE_ALLOWLIST}),
            sorted([NEPTUNE_TUNNEL, PHASE14_MAIN, RUNTIME_BOUNDARY]),
        )
        for grant in GLOBAL_RESOURCE_ALLOWLIST:
            with self.subTest(actions=sorted(grant.actions)):
                self.assertGreaterEqual(len(grant.justification), 80)
                self.assertIn("https://docs.aws.amazon.com/service-authorization/latest/reference/list_", grant.url)
                self.assertTrue(grant.actions)
                for action in grant.actions:
                    self.assertRegex(action, r"^[a-z0-9-]+:[A-Za-z]+$")  # exact actions, never a wildcard
                    self.assertFalse(action.endswith(("Create*", "*")))

    def test_global_resource_allowlist_is_per_statement(self):
        for grant in GLOBAL_RESOURCE_ALLOWLIST:
            actions = sorted(grant.actions)
            listed = ", ".join('"%s"' % a for a in actions)
            statement = '{Effect="Allow", Action=[%s], Resource=["*"], ' + good_condition(grant) + '}'
            with self.subTest(actions=actions):
                self.assertEqual(scan(grant.path, statement % listed), [])
                # The same actions in another file are not exempt.
                self.assertEqual([f["category"] for f in scan("infra/terraform/other.tf", statement % listed)], ["global-iam-resource"])
                # A superset is not exempt (an extra action rides along).
                self.assertIn("global-iam-resource", [f["category"] for f in scan(grant.path, statement % (listed + ', "iam:CreateRole"'))])
                # A subset is not exempt either (the entry is the reviewed action set, exactly).
                if len(actions) > 1:
                    subset = ", ".join('"%s"' % a for a in actions[1:])
                    self.assertIn("global-iam-resource", [f["category"] for f in scan(grant.path, statement % subset)])

    def test_allowlisted_statement_keeps_its_condition_unless_the_service_is_global(self):
        for grant in GLOBAL_RESOURCE_ALLOWLIST:
            listed = ", ".join('"%s"' % a for a in sorted(grant.actions))
            for condition in ("", ", Condition={}", ", Condition=null"):
                source = '{Effect="Allow", Action=[%s], Resource=["*"]%s}' % (listed, condition)
                with self.subTest(actions=sorted(grant.actions), condition=condition):
                    expected = ["unconditioned-allowlisted-global-grant"] if grant.requires_condition else []
                    self.assertEqual([f["category"] for f in scan(grant.path, source)], expected)

    def test_ecs_exec_channels_pass_only_as_the_exact_four_in_their_two_files(self):
        """Replan W5a/W5b: the four ssmmessages ECS Exec actions on Resource "*" (boundary template and the tunnel task role)."""
        listed = ", ".join('"%s"' % a for a in sorted(ECS_EXEC_ACTIONS))
        template = '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": [%s], "Resource": ["*"]}]}' % (
            listed.replace(", ", ", ")
        )
        self.assertEqual(scan(RUNTIME_BOUNDARY, template), [])
        self.assertEqual(scan(NEPTUNE_TUNNEL, '{Effect="Allow", Action=[%s], Resource="*"}' % listed), [])
        # The same four in any other file are flagged (a different policy needs its own reviewed entry).
        for other in ("infra/terraform/other.tf", "infra/terraform/deployer/boundaries/other.json.tftpl",
                      "infra/terraform/modules/runtime/neptune_tunnel.tf"):
            with self.subTest(other=other):
                found = scan(other, template if other.endswith(".tftpl") else '{Effect="Allow", Action=[%s], Resource="*"}' % listed)
                self.assertEqual([f["category"] for f in found], ["global-iam-resource"])
        # Any other action, an added action, a missing action, or a wildcard still fails in the allowed files.
        three = ", ".join('"%s"' % a for a in sorted(ECS_EXEC_ACTIONS)[1:])
        for path in (RUNTIME_BOUNDARY, NEPTUNE_TUNNEL):
            for extra in ('"ssm:StartSession"', '"ssmmessages:Anything"', '"s3:GetObject"', '"iam:PassRole"'):
                with self.subTest(path=path, extra=extra):
                    found = scan(path, '{Effect="Allow", Action=[%s, %s], Resource="*"}' % (listed, extra))
                    self.assertIn("global-iam-resource", [f["category"] for f in found])
            with self.subTest(path=path, case="missing one"):
                self.assertIn("global-iam-resource", [f["category"] for f in scan(path, '{Effect="Allow", Action=[%s], Resource="*"}' % three)])
            with self.subTest(path=path, case="wildcard"):
                found = scan(path, '{Effect="Allow", Action=["ssmmessages:*"], Resource="*"}')
                self.assertEqual({f["category"] for f in found}, {"wildcard-iam-action", "global-iam-resource"})
        # A different action on "*" in the same file is still flagged.
        self.assertEqual([f["category"] for f in scan(NEPTUNE_TUNNEL, '{Effect="Allow", Action=["sts:AssumeRole"], Resource="*"}')], ["global-iam-resource"])

    def test_action_resolved_from_a_same_file_local_is_judged_exactly(self):
        """neptune_tunnel.tf writes `Action = local.neptune_tunnel_actions`; the guard resolves one same-file literal list."""
        def source(actions, ref="local.neptune_tunnel_actions"):
            return ('locals { neptune_tunnel_actions = [%s] }\n'
                    'resource "aws_iam_role_policy" "p" { policy = jsonencode({Statement = [{Effect = "Allow", Action = %s, Resource = "*"}]}) }'
                    % (actions, ref))
        four = ", ".join('"%s"' % a for a in sorted(ECS_EXEC_ACTIONS))
        self.assertEqual(scan(NEPTUNE_TUNNEL, source(four)), [])
        self.assertEqual([f["category"] for f in scan(NEPTUNE_TUNNEL, source(four + ', "iam:CreateRole"'))], ["global-iam-resource"])
        self.assertIn("wildcard-iam-action", [f["category"] for f in scan(NEPTUNE_TUNNEL, source('"ssmmessages:*"'))])
        # An unresolvable or ambiguous reference never exempts.
        self.assertEqual([f["category"] for f in scan(NEPTUNE_TUNNEL, source(four, ref="local.other_name"))], ["global-iam-resource"])
        self.assertEqual([f["category"] for f in scan(NEPTUNE_TUNNEL, source(four, ref="var.actions"))], ["global-iam-resource"])
        twice = 'locals { neptune_tunnel_actions = ["s3:GetObject"] }\n' + source(four)
        self.assertEqual([f["category"] for f in scan(NEPTUNE_TUNNEL, twice)], ["global-iam-resource"])

    def test_acm_request_certificate_needs_region_dns_validation_and_request_tags(self):
        def statement(condition, action='"acm:RequestCertificate"'):
            return '{Effect="Allow", Action=[%s], Resource=["*"]%s}' % (action, condition)
        good = ', Condition={StringEquals=merge(local.c_region, local.c_req_main, {"acm:ValidationMethod" = "DNS"})}'
        self.assertEqual(scan(PHASE14_MAIN, statement(good)), [])
        literal = (', Condition={StringEquals={"aws:RequestedRegion"="us-east-2", "acm:ValidationMethod"="DNS", '
                   '"aws:RequestTag/project"="x"}}')
        self.assertEqual(scan(PHASE14_MAIN, statement(literal)), [])
        weakened = {
            "no condition": "",
            "empty condition": ", Condition={}",
            "region only": ", Condition={StringEquals=local.c_region}",
            "no validation method": ", Condition={StringEquals=merge(local.c_region, local.c_req_main)}",
            "email validation": ', Condition={StringEquals=merge(local.c_region, local.c_req_main, {"acm:ValidationMethod"="EMAIL"})}',
            "no request tags": ', Condition={StringEquals=merge(local.c_region, {"acm:ValidationMethod"="DNS"})}',
            "no region": ', Condition={StringEquals=merge(local.c_req_main, {"acm:ValidationMethod"="DNS"})}',
        }
        for name, condition in weakened.items():
            with self.subTest(name):
                categories = [f["category"] for f in scan(PHASE14_MAIN, statement(condition))]
                self.assertEqual(len(categories), 1)
                self.assertIn(categories[0], ("unconditioned-allowlisted-global-grant", "weakened-allowlisted-global-grant"))
        # Neighbouring ACM actions and any other action on "*" are not covered by this entry.
        for other in ('"acm:RequestCertificate", "acm:DeleteCertificate"', '"acm:DeleteCertificate"', '"acm:ListCertificates"',
                      '"acm:ImportCertificate"', '"acm:*"', '"acm:AddTagsToCertificate"'):
            with self.subTest(other=other):
                self.assertIn("global-iam-resource", [f["category"] for f in scan(PHASE14_MAIN, statement(good, other))])
        self.assertEqual([f["category"] for f in scan("infra/terraform/other.tf", statement(good))], ["global-iam-resource"])

    def test_an_unlisted_action_on_a_global_resource_still_fails_in_every_allowlisted_file(self):
        for path in (PHASE14_MAIN, RUNTIME_BOUNDARY, NEPTUNE_TUNNEL):
            for action in ("iam:PassRole", "sts:AssumeRole", "ssm:StartSession", "acm:ExportCertificate", "s3:GetObject"):
                with self.subTest(path=path, action=action):
                    found = scan(path, '{Effect="Allow", Action=["%s"], Resource="*", Condition={StringEquals=local.c_region}}' % action)
                    self.assertEqual([f["category"] for f in found], ["global-iam-resource"])

    def test_a_new_unjustified_global_grant_still_fails_beside_an_allowlisted_one(self):
        grant = GLOBAL_RESOURCE_ALLOWLIST[0]
        listed = ", ".join('"%s"' % a for a in sorted(grant.actions))
        source = (
            '{Effect="Allow", Action=[%s], Resource=["*"], Condition={StringEquals=local.c_region}},\n'
            '{Effect="Allow", Action=["ec2:TerminateInstances"], Resource=["*"], Condition={StringEquals=local.c_region}}' % listed
        )
        self.assertEqual([(f["line"], f["category"]) for f in scan(grant.path, source)], [(2, "global-iam-resource")])

    def test_policy_json_templates_are_scanned_without_reading_interpolations_as_wildcards(self):
        clean = """{"Version": "2012-10-17", "Statement": [
          {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": ["arn:aws:s3:::${mp}-${acct}-*/*"]},
          {"Effect": "Allow", "Action": ["bedrock:InvokeModel"], "Resource": [${fm_arns}, "arn:aws:bedrock:::foundation-model/*"]},
          {"Effect": "Allow", "Action": ["ecr:GetAuthorizationToken"], "Resource": ["*"]},
          {"Effect": "Allow", "Action": ["dynamodb:GetItem"], "Resource": ["${table_arn}"]},
          {"Effect": "Allow", "Action": ["sqs:SendMessage"], "Resource": "${join(\",\", queues)}"}]}"""
        self.assertEqual(scan("infra/terraform/deployer/boundaries/x.json.tftpl", clean), [])

    def test_policy_json_templates_reject_unjustified_wildcards_with_the_original_line(self):
        examples = (
            ('{"Effect": "Allow", "Action": ["iam:PassRole"], "Resource": ["*"]}', "global-iam-resource"),
            ('{"Effect": "Allow", "Action": ["s3:*"], "Resource": ["arn:aws:s3:::${mp}-x"]}', "wildcard-iam-action"),
            ('{"Effect": "Allow", "Action": "*", "Resource": ["arn:aws:s3:::${mp}-x"]}', "wildcard-iam-action"),
            ('{"Effect": "Allow", "Action": ["ec2:TerminateInstances"], "Resource": ["arn:aws:ec2:*:${acct}:instance/*"]}', "global-iam-resource"),
            ('{"Effect": "Allow", "Action": ["s3:GetObject"], "Principal": "*", "Resource": ["arn:aws:s3:::${mp}-x"]}', "public-allow-principal"),
            ('{"Effect": "Allow", "Action": ["${svc}:*"], "Resource": ["arn:aws:s3:::${mp}-x"]}', "wildcard-iam-action"),
        )
        for statement, category in examples:
            with self.subTest(category=category, statement=statement):
                source = '{"Version": "2012-10-17",\n "Statement": [\n ' + statement + ']}'
                names = ("x.json.tftpl",) if "${" in statement else ("x.json.tftpl", "infra/terraform/environments/y.json.example")
                for suffix in names:
                    found = scan(suffix, source)
                    self.assertIn((3, category), [(f["line"], f["category"]) for f in found])

    def test_scanned_file_set_includes_templates_and_environment_json_examples_only(self):
        self.assertTrue(is_scanned("infra/terraform/deployer/boundaries/runtime.json.tftpl"))
        self.assertTrue(is_scanned("infra/terraform/environments/emr-service-policy.json.example"))
        self.assertTrue(is_scanned("infra/terraform/main.tf"))
        self.assertFalse(is_scanned("infra/terraform/environments/nested/y.json.example"))
        self.assertFalse(is_scanned("infra/terraform/tests/x.tftest.hcl"))
        self.assertFalse(is_scanned("infra/terraform/deployer/README.md"))


def good_condition(grant):
    """A Condition that satisfies `grant` (used by the self-tests)."""
    if grant.condition_requires:
        return 'Condition={StringEquals=merge(local.c_region, local.c_req_main, {"acm:ValidationMethod"="DNS"})}'
    return "Condition={StringEquals=local.c_region}"


def is_scanned(path):
    """Which Git-visible files below infra/terraform are opened: Terraform sources, variable files, policy JSON templates
    (*.json.tftpl anywhere) and the JSON examples that sit directly in environments/."""
    if path.endswith((".tf", ".tfvars", ".json.tftpl")):
        return True
    parent, _, name = path.rpartition("/")
    return parent == "infra/terraform/environments" and name.endswith(".json.example")


def stale_allowlist_findings(used):
    return [
        {"path": g.path, "line": 0, "category": "stale-global-allowlist-entry"}
        for g in GLOBAL_RESOURCE_ALLOWLIST
        if g not in used
    ]


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
    paths = sorted({p for p in listed if is_scanned(p)})
    if not [p for p in paths if p.endswith((".tf", ".tfvars"))]:
        parser.error("no Git-visible Terraform source files found")
    findings = []
    used = set()
    for path in paths:
        file = root / path
        if file.is_symlink():
            findings.append({"path": path, "line": 0, "category": "source-symlink-not-inspected"})
        else:
            findings.extend(scan(path, file.read_text(), used))
    # An allowlist entry that exempts nothing is stale (the statement moved, changed or was removed): drop or re-justify it.
    # Only judged against a tree that contains the entry's file, so a partial checkout does not raise it.
    present = set(paths)
    findings.extend(f for f in stale_allowlist_findings(used) if f["path"] in present)
    print(json.dumps({"scope": "literal-source-only", "files": len(paths), "findings": findings}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
