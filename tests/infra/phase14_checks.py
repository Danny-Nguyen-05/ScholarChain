"""Named invariants for the phase14-main deployer permission set and the roles and network of the MAIN root (Phase 14A).

Every expectation is hand-derived from the Phase 14 work order (decision 14-6 and mid-subphase decisions D1 and D2), not
from the Terraform that implements it:

  14-6  a scoped `phase14-main` set: service-scoped, region-locked to us-east-2, IAM limited to scholarchain-<env>-* roles
        with a permissions boundary, MFA, a 1-hour session, each document under 6,144 characters, spike-emr removed.
  D1    every aws_iam_role of the main root (identity: task, execution, neptune-loader, emr-ec2, emr-service, deployment;
        workflow: embedding-producer) carries a permissions boundary created by the deployer root; the EMR service role the
        EMR service boundary, every other role the runtime boundary.
  D2    the application subnets and the EMR node and service-access security groups carry
        for-use-with-amazon-emr-managed-policies = "true"; no other subnet or security group does.

  F2    (repair round 1, user-ordered narrowing) no IAM statement of the set grants key administration, key use or grants on
        a key (those live in the main-stack key policies, which name the deployer role); kms:TagResource is only a create-time
        helper; no security-group mutation without the project resource tag; no CreateTags that could tag a foreign group into
        scope; the VPC default security group is not managed by the main root.

The checks read a parsed `terraform show -json` offline plan (real AWS provider, fake credentials, closed proxy; see
infra_support.py) and return a list of problem strings; an empty list means the invariant holds. Each check is exercised by a
real-tree test and by at least one mutation of a scratch copy in test_phase14_main.py.
"""
import fnmatch
import json
import re

from infra_support import after, as_list, condition_pairs, managed_changes, policy_statements

ACCOUNT = "111122223333"
REGION = "us-east-2"
DEPLOYER_ROLE_NAME = "scholarchain-deployer"
BILLING_ROLE_NAME = "scholarchain-billing-deployer"
SIZE_LIMIT = 6144  # IAM managed-policy limit in characters, whitespace excluded
ATTACHMENT_LIMIT = 10  # default managed policies per role
EXPECTED_PERMISSION_SET_DOCUMENTS = 7  # decision 14-6 evidence: seven documents and seven attachments
REGION_EXEMPT_SERVICES = {"iam", "route53"}  # global services: no aws:RequestedRegion
OPERATOR_ARN = "arn:aws:iam::%s:user/example-operator" % ACCOUNT
EMR_TAG = "for-use-with-amazon-emr-managed-policies"

# IAM actions the deployer must never be ALLOWED on anything: they would let it widen its own or a role's authority.
NEVER_ALLOWED_IAM = (
    "iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary", "iam:UpdateAssumeRolePolicy",
    "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion",
    "iam:CreatePolicy", "iam:AttachRolePolicy", "iam:DetachRolePolicy", "iam:CreateUser", "iam:CreateAccessKey",
    "iam:AttachUserPolicy", "iam:PutUserPolicy", "iam:CreateLoginProfile", "iam:UpdateLoginProfile",
    "iam:AddUserToGroup", "iam:PutUserPermissionsBoundary", "iam:DeleteUserPermissionsBoundary",
)

# The 13 role instances of the main root (7 resource blocks): hand-derived from the work order and the four runtime services.
SERVICES = ("query-api", "graph-service", "semantic-service", "embedding-worker")


def expected_main_role_names(env):
    prefix = "scholarchain-%s-" % env
    names = {prefix + s + "-task" for s in SERVICES} | {prefix + s + "-execution" for s in SERVICES}
    names |= {prefix + n for n in ("neptune-loader", "emr-ec2", "emr-service", "deployment", "embedding-producer")}
    return names


# ---------------------------------------------------------------------------------------------------------------
# deployer plan accessors
# ---------------------------------------------------------------------------------------------------------------

def policy_resources(plan):
    """address -> (name, parsed document) of every aws_iam_policy the deployer root plans."""
    result = {}
    for address, rc in managed_changes(plan).items():
        if rc["type"] == "aws_iam_policy":
            a = rc["change"]["after"]
            result[address] = (a.get("name"), json.loads(a["policy"]))
    return result


def permission_set_documents(plan):
    return {a: v for a, v in policy_resources(plan).items() if a.startswith("aws_iam_policy.permission_set[")}


def boundary_documents(plan):
    return {a: v for a, v in policy_resources(plan).items() if a.startswith(("aws_iam_policy.main_boundary_"))}


def boundary_arns(plan):
    """(runtime ARN, EMR-service ARN) built from the names the deployer root gives the two boundary policies."""
    docs = boundary_documents(plan)
    runtime = [n for a, (n, _) in docs.items() if a.startswith("aws_iam_policy.main_boundary_runtime")]
    emr = [n for a, (n, _) in docs.items() if a.startswith("aws_iam_policy.main_boundary_emr")]
    if len(runtime) != 1 or len(emr) != 1:
        return None, None
    return "arn:aws:iam::%s:policy/%s" % (ACCOUNT, runtime[0]), "arn:aws:iam::%s:policy/%s" % (ACCOUNT, emr[0])


def statements(documents, effect):
    """[(address, statement)] of the given effect across {address: (name, document)}."""
    return [(address, st) for address, (_, doc) in documents.items() for st in policy_statements(doc) if st.get("Effect") == effect]


def services_of(statement):
    return {a.split(":")[0].lower() for a in as_list(statement.get("Action")) if ":" in a}


def covers(statement_actions, action):
    return any(fnmatch.fnmatchcase(action, a) for a in as_list(statement_actions))


def pairs_of(statement):
    return {(op, key): value for op, key, value in condition_pairs(statement)}


def sid(statement):
    return statement.get("Sid")


# ---------------------------------------------------------------------------------------------------------------
# deployer checks
# ---------------------------------------------------------------------------------------------------------------

def check_spike_absent(plan):
    """With the default set, nothing of spike-emr is planned: no spike policy, attachment, boundary or ARN."""
    problems = []
    for address, rc in managed_changes(plan).items():
        text = json.dumps(rc["change"]["after"], sort_keys=True)
        if "spike" in address.lower() or "spike" in text.lower():
            problems.append("%s mentions spike" % address)
    parts = permission_set_documents(plan)
    if len(parts) != EXPECTED_PERMISSION_SET_DOCUMENTS:
        problems.append("expected %d permission-set documents, found %d" % (EXPECTED_PERMISSION_SET_DOCUMENTS, len(parts)))
    for address, (name, _) in parts.items():
        if not address.startswith('aws_iam_policy.permission_set["phase14-main--'):
            problems.append("%s is not a phase14-main document" % address)
        if not str(name).startswith(DEPLOYER_ROLE_NAME + "-phase14-main--"):
            problems.append("%s is named %r" % (address, name))
    outputs = plan.get("planned_values", {}).get("outputs", {})
    if outputs.get("spike_permissions_boundary_arn", {}).get("value") is not None:
        problems.append("output spike_permissions_boundary_arn is not null")
    return problems


def check_document_sizes(plan):
    """Every policy (the seven permission-set documents and the two boundaries) is at most 6,144 characters as minified JSON."""
    problems = []
    docs = policy_resources(plan)
    if len(docs) != EXPECTED_PERMISSION_SET_DOCUMENTS + 2:
        problems.append("expected 9 managed policies (7 documents + 2 boundaries), found %d" % len(docs))
    for address, (_, doc) in docs.items():
        size = len(json.dumps(doc, separators=(",", ":")))
        if size > SIZE_LIMIT:
            problems.append("%s is %d characters (limit %d)" % (address, size, SIZE_LIMIT))
    return problems


def check_attachment_count(plan):
    """The deployer role has at most 10 managed-policy attachments (login is inline), one per permission-set document."""
    attachments = [a for a in managed_changes(plan) if a.startswith("aws_iam_role_policy_attachment.")]
    problems = []
    if len(attachments) > ATTACHMENT_LIMIT:
        problems.append("%d managed attachments (limit %d)" % (len(attachments), ATTACHMENT_LIMIT))
    if len(attachments) != len(permission_set_documents(plan)):
        problems.append("%d attachments for %d documents" % (len(attachments), len(permission_set_documents(plan))))
    return problems


def check_region_condition(plan):
    """Every Allow statement that names a service other than IAM or Route 53 carries StringEquals aws:RequestedRegion = us-east-2."""
    problems = []
    allows = statements(permission_set_documents(plan), "Allow")
    for address, st in allows:
        services = services_of(st)
        if services <= REGION_EXEMPT_SERVICES:
            continue
        value = pairs_of(st).get(("StringEquals", "aws:RequestedRegion"))
        if as_list(value) != [REGION]:
            problems.append("%s/%s (%s) lacks StringEquals aws:RequestedRegion = %s (has %r)" % (
                address, sid(st), sorted(services - REGION_EXEMPT_SERVICES), REGION, value))
    return problems


def check_region_exemption_is_only_iam_and_route53(plan):
    """Statements without the region condition name only IAM and Route 53 actions, and both services are in use."""
    problems = []
    unconditioned = set()
    seen = set()
    for address, st in statements(permission_set_documents(plan), "Allow"):
        seen |= services_of(st)
        if as_list(pairs_of(st).get(("StringEquals", "aws:RequestedRegion"))) != [REGION]:
            unconditioned |= services_of(st)
    if not unconditioned <= REGION_EXEMPT_SERVICES:
        problems.append("services exempt from the region condition: %s (only iam and route53 may be)" % sorted(unconditioned - REGION_EXEMPT_SERVICES))
    for service in sorted(REGION_EXEMPT_SERVICES - seen):
        problems.append("no Allow statement for %s (the exemption check would be vacuous)" % service)
    return problems


def check_no_wildcard_actions(plan):
    """No Allow statement (permission sets and boundaries) uses Action `*`, `*:*` or `<service>:*`, and none uses NotAction."""
    problems = []
    docs = dict(permission_set_documents(plan))
    docs.update(boundary_documents(plan))
    if len(docs) != EXPECTED_PERMISSION_SET_DOCUMENTS + 2:
        problems.append("expected 9 policies to scan, found %d" % len(docs))
    for address, st in statements(docs, "Allow"):
        if "NotAction" in st or "NotResource" in st:
            problems.append("%s/%s uses NotAction or NotResource in an Allow" % (address, sid(st)))
        for action in as_list(st.get("Action")):
            if action in ("*", "*:*") or re.fullmatch(r"[A-Za-z0-9-]+:\*", action):
                problems.append("%s/%s allows %s" % (address, sid(st), action))
    return problems


def check_iam_scope(plan, env="course"):
    """IAM Allow statements name only scholarchain-<env>-* roles, instance profiles and policies (plus exact AWS service-linked
    roles), never the deployer or billing role, never `*`, and never an action that widens authority."""
    problems = []
    prefix_re = re.compile(r"^arn:aws:iam::%s:(role|instance-profile|policy)/scholarchain-%s-[A-Za-z0-9*_+=,.@-]+$" % (ACCOUNT, re.escape(env)))
    slr_re = re.compile(r"^arn:aws:iam::%s:role/aws-service-role/[a-z0-9.-]+\.amazonaws\.com/AWSServiceRole[A-Za-z0-9_]+$" % ACCOUNT)
    forbidden = ["arn:aws:iam::%s:role/%s" % (ACCOUNT, n) for n in (DEPLOYER_ROLE_NAME, BILLING_ROLE_NAME)]
    forbidden += ["arn:aws:iam::%s:user/example-operator" % ACCOUNT]
    seen = False
    for address, st in statements(permission_set_documents(plan), "Allow"):
        actions = as_list(st.get("Action"))
        for action in NEVER_ALLOWED_IAM:
            if covers(actions, action):
                problems.append("%s/%s allows %s" % (address, sid(st), action))
        if "iam" not in services_of(st):
            continue
        seen = True
        if set(actions) == {"iam:CreateServiceLinkedRole"}:
            if ("StringEquals", "iam:AWSServiceName") not in pairs_of(st):
                problems.append("%s/%s: CreateServiceLinkedRole without iam:AWSServiceName" % (address, sid(st)))
            for resource in as_list(st.get("Resource")):
                if not slr_re.match(resource):
                    problems.append("%s/%s: service-linked role resource %r is not an exact AWS service role ARN" % (address, sid(st), resource))
            continue
        for resource in as_list(st.get("Resource")):
            if not prefix_re.match(resource):
                problems.append("%s/%s: IAM resource %r is not a scholarchain-%s-* role, instance profile or policy" % (address, sid(st), resource, env))
            for protected in forbidden:
                if fnmatch.fnmatchcase(protected, resource):
                    problems.append("%s/%s: IAM resource %r also matches %s" % (address, sid(st), resource, protected))
    if not seen:
        problems.append("no IAM Allow statement found (the check would be vacuous)")
    return problems


def check_create_role_requires_boundary(plan):
    """iam:CreateRole requires iam:PermissionsBoundary equal to ONE of the two boundary ARNs (a string, not a list or pattern):
    the EMR service role only with the EMR boundary, every other role only with the runtime boundary. PutRolePolicy and
    DeleteRolePolicy are likewise only on roles that carry one of the two boundaries."""
    runtime, emr = boundary_arns(plan)
    if runtime is None:
        return ["the two boundary policies are missing from the plan"]
    problems = []
    creates = 0
    for address, st in statements(permission_set_documents(plan), "Allow"):
        actions = as_list(st.get("Action"))
        if covers(actions, "iam:CreateRole"):
            creates += 1
            value = pairs_of(st).get(("StringEquals", "iam:PermissionsBoundary"))
            if not isinstance(value, str) or value not in (runtime, emr):
                problems.append("%s/%s: iam:CreateRole condition iam:PermissionsBoundary is %r, expected one of the two boundary ARNs" % (address, sid(st), value))
                continue
            resources = as_list(st.get("Resource"))
            emr_role = any(r.endswith("-emr-service") for r in resources)
            if emr_role and (value != emr or not all(r.endswith("-emr-service") for r in resources)):
                problems.append("%s/%s: the EMR service role must be created only with the EMR boundary" % (address, sid(st)))
            if not emr_role and value != runtime:
                problems.append("%s/%s: a runtime role must be created only with the runtime boundary" % (address, sid(st)))
        if covers(actions, "iam:PutRolePolicy") or covers(actions, "iam:DeleteRolePolicy"):
            value = pairs_of(st).get(("StringEquals", "iam:PermissionsBoundary"))
            if sorted(as_list(value)) != sorted([runtime, emr]):
                problems.append("%s/%s: role-policy changes are not limited to roles carrying the two boundaries (%r)" % (address, sid(st), value))
    if creates < 2:
        problems.append("expected an iam:CreateRole statement per boundary, found %d (the check would be vacuous)" % creates)
    return problems


def check_deny_statements(plan, env="course", role_names=None):
    """Boundary tampering and secret reads are explicitly denied, with no Condition that could switch the Deny off."""
    runtime, emr = boundary_arns(plan)
    if runtime is None:
        return ["the two boundary policies are missing from the plan"]
    problems = []
    denies = statements(permission_set_documents(plan), "Deny")
    role_arns = ["arn:aws:iam::%s:role/%s" % (ACCOUNT, n) for n in sorted(role_names or expected_main_role_names(env))]

    def deny_covering(action, resources_ok):
        for address, st in denies:
            if covers(st.get("Action"), action) and not st.get("Condition") and resources_ok(as_list(st.get("Resource"))):
                return True
        return False

    def matches_all(targets):
        return lambda resources: all(any(fnmatch.fnmatchcase(t, r) for r in resources) for t in targets)

    for action in ("iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary"):
        if not deny_covering(action, matches_all(role_arns)):
            problems.append("no unconditional Deny of %s on every main role" % action)
    for action in ("iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy"):
        if not deny_covering(action, matches_all([runtime, emr])):
            problems.append("no unconditional Deny of %s on both boundary policies" % action)
    if not deny_covering("secretsmanager:GetSecretValue", lambda resources: "*" in resources):
        problems.append("no unconditional Deny of secretsmanager:GetSecretValue on *")
    return problems


def check_pass_role_names_the_service(plan, env="course"):
    """Every Allow iam:PassRole is on named scholarchain-<env> roles and carries StringEquals iam:PassedToService with concrete services."""
    problems = []
    found = 0
    for address, st in statements(permission_set_documents(plan), "Allow"):
        if not covers(st.get("Action"), "iam:PassRole"):
            continue
        found += 1
        services = as_list(pairs_of(st).get(("StringEquals", "iam:PassedToService")))
        if not services or not all(re.fullmatch(r"[a-z0-9-]+\.amazonaws\.com", x) for x in services):
            problems.append("%s/%s: iam:PassRole without a concrete iam:PassedToService (%r)" % (address, sid(st), services))
        for resource in as_list(st.get("Resource")):
            if not resource.startswith("arn:aws:iam::%s:role/scholarchain-%s-" % (ACCOUNT, env)):
                problems.append("%s/%s: iam:PassRole on %r" % (address, sid(st), resource))
    if found < 3:
        problems.append("expected several iam:PassRole statements, found %d (the check would be vacuous)" % found)
    return problems


def check_create_role_covers_main_roles(plan, main_roles):
    """Cross-check with the MAIN root: for each real main role there is an iam:CreateRole Allow whose resource pattern matches
    its ARN and whose boundary condition equals the boundary that role carries; no statement for it demands another boundary."""
    problems = []
    for name, boundary in sorted(main_roles.items()):
        arn = "arn:aws:iam::%s:role/%s" % (ACCOUNT, name)
        matching = [(a, st) for a, st in statements(permission_set_documents(plan), "Allow")
                    if covers(st.get("Action"), "iam:CreateRole") and any(fnmatch.fnmatchcase(arn, r) for r in as_list(st.get("Resource")))]
        if not matching:
            problems.append("no iam:CreateRole Allow matches %s" % name)
        for a, st in matching:
            value = pairs_of(st).get(("StringEquals", "iam:PermissionsBoundary"))
            if value != boundary:
                problems.append("%s/%s allows creating %s with boundary %r, but the main root gives it %r" % (a, sid(st), name, value, boundary))
    return problems


def check_trust_and_session(plan):
    """The deployer trust names exactly the operator, requires MFA, and sessions last at most one hour (3600)."""
    problems = []
    role = after(plan, "aws_iam_role.deployer")
    if role.get("max_session_duration") != 3600:
        problems.append("max_session_duration is %r, expected 3600" % role.get("max_session_duration"))
    trust = json.loads(role["assume_role_policy"])
    stmts = policy_statements(trust)
    if len(stmts) != 1:
        problems.append("the trust policy has %d statements, expected exactly one" % len(stmts))
        return problems
    st = stmts[0]
    if st.get("Effect") != "Allow" or as_list(st.get("Action")) != ["sts:AssumeRole"]:
        problems.append("trust statement is not Allow sts:AssumeRole")
    if st.get("Principal") != {"AWS": OPERATOR_ARN}:
        problems.append("trust principal is %r, expected exactly the operator" % (st.get("Principal"),))
    if pairs_of(st).get(("Bool", "aws:MultiFactorAuthPresent")) != "true":
        problems.append("trust does not require aws:MultiFactorAuthPresent = true")
    return problems


# F2 ------------------------------------------------------------------------------------------------------------------
# Hand-derived from the review finding: tags confer nothing on a key, and a foreign security group tagged into scope gains
# nothing. KMS actions that administer a key, use it, or grant access to it (the key policy carries these for the main-stack keys).
KMS_ADMIN_USE_GRANT = (
    "kms:PutKeyPolicy", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:DisableKey", "kms:EnableKey",
    "kms:DisableKeyRotation", "kms:EnableKeyRotation", "kms:UntagResource", "kms:UpdateKeyDescription",
    "kms:UpdatePrimaryRegion", "kms:ReplicateKey", "kms:ImportKeyMaterial", "kms:DeleteImportedKeyMaterial",
    "kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:GenerateDataKeyWithoutPlaintext",
    "kms:GenerateDataKeyPair", "kms:GenerateDataKeyPairWithoutPlaintext", "kms:GenerateMac", "kms:VerifyMac",
    "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:Sign", "kms:Verify", "kms:DeriveSharedSecret",
    "kms:CreateGrant", "kms:ListGrants", "kms:ListRetirableGrants", "kms:RevokeGrant", "kms:RetireGrant",
    "kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias",  # these two also need the key: only on alias ARNs here
)
KMS_ALIAS_ACTIONS = {"kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias"}
SG_MUTATIONS = (
    "ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress",
    "ec2:RevokeSecurityGroupEgress", "ec2:DeleteSecurityGroup", "ec2:ModifySecurityGroupRules",
)
PROJECT = "scholarchain"


def check_no_kms_administration_use_or_grants_in_iam(plan, env="course"):
    """No Allow statement grants key administration, use or grants on key/* or `*` (alias actions only on alias ARNs).
    kms:CreateKey needs the project request tags; kms:TagResource is on key/* only with the project and environment request
    tags and a literal aws:TagKeys list."""
    problems = []
    creates = tags = 0
    for address, st in statements(permission_set_documents(plan), "Allow"):
        actions = [a for a in as_list(st.get("Action")) if a.lower().startswith("kms:") or a == "*" or a.endswith(":*")]
        if not actions:
            continue
        resources = as_list(st.get("Resource"))
        on_key = [r for r in resources if r == "*" or ":key/" in r]
        for forbidden in KMS_ADMIN_USE_GRANT:
            if not covers(actions, forbidden):
                continue
            if forbidden in KMS_ALIAS_ACTIONS and not on_key:
                continue  # alias create/update/delete on alias ARNs of the main stack is fine
            problems.append("%s/%s grants %s on %s" % (address, sid(st), forbidden, resources))
        pairs = pairs_of(st)
        if "kms:CreateKey" in actions:
            creates += 1
            for tag in ("project", "environment"):
                if not isinstance(pairs.get(("StringEquals", "aws:RequestTag/" + tag)), str):
                    problems.append("%s/%s: kms:CreateKey lacks the %s request tag" % (address, sid(st), tag))
        if "kms:TagResource" in actions:
            tags += 1
            if any(not r.endswith(":key/*") or r == "*" for r in resources):
                problems.append("%s/%s: kms:TagResource on %s (only key/* of this region and account)" % (address, sid(st), resources))
            for tag in ("project", "environment"):
                if not isinstance(pairs.get(("StringEquals", "aws:RequestTag/" + tag)), str):
                    problems.append("%s/%s: kms:TagResource lacks the %s request tag" % (address, sid(st), tag))
            keys = as_list(pairs.get(("ForAllValues:StringEquals", "aws:TagKeys")))
            if not keys or any("*" in k or "?" in k for k in keys):
                problems.append("%s/%s: kms:TagResource lacks a literal aws:TagKeys list (%r)" % (address, sid(st), keys))
        for resource in on_key:
            if resource == "*" and not set(actions) <= {"kms:CreateKey", "kms:ListAliases"}:
                problems.append("%s/%s: KMS actions %s on *" % (address, sid(st), sorted(set(actions) - {"kms:CreateKey", "kms:ListAliases"})))
    if creates < 1 or tags < 1:
        problems.append("expected kms:CreateKey and kms:TagResource statements (the check would be vacuous): %d, %d" % (creates, tags))
    return problems


def check_security_group_mutations_need_the_project_resource_tag(plan):
    """Authorize*, Revoke*, DeleteSecurityGroup and ModifySecurityGroupRules reach a security group (or its rules) only
    with StringEquals aws:ResourceTag/project = scholarchain, never on `*`. Authorize on the rule ARN, which does not exist
    before the call, may use the project request tag instead."""
    problems = []
    seen = set()
    for address, st in statements(permission_set_documents(plan), "Allow"):
        actions = as_list(st.get("Action"))
        hit = [a for a in SG_MUTATIONS if covers(actions, a)]
        if not hit:
            continue
        seen |= set(hit)
        pairs = pairs_of(st)
        resource_tag = pairs.get(("StringEquals", "aws:ResourceTag/project")) == PROJECT
        request_tag = pairs.get(("StringEquals", "aws:RequestTag/project")) == PROJECT
        for resource in as_list(st.get("Resource")):
            if resource == "*":
                problems.append("%s/%s: %s on *" % (address, sid(st), hit))
            elif ":security-group-rule/" in resource:
                authorize_only = all(a.startswith("ec2:Authorize") for a in hit)
                if not (resource_tag or (authorize_only and request_tag)):
                    problems.append("%s/%s: %s on security-group-rule without the project tag" % (address, sid(st), hit))
            elif ":security-group/" in resource and not resource_tag:
                problems.append("%s/%s: %s on security-group/* without aws:ResourceTag/project" % (address, sid(st), hit))
    for needed in ("ec2:DeleteSecurityGroup", "ec2:RevokeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupIngress", "ec2:ModifySecurityGroupRules"):
        if needed not in seen:
            problems.append("no statement allows %s (the check would be vacuous)" % needed)
    return problems


def check_security_group_tagging_cannot_adopt(plan):
    """ec2:CreateTags that can reach a security group needs ec2:CreateAction (tagging inside a create call) or the project
    resource tag (an in-scope group); a request tag alone would let a foreign group be tagged into scope. ec2:DeleteTags needs
    the resource tag. Neither is ever granted on `*`."""
    problems = []
    creates = 0
    for address, st in statements(permission_set_documents(plan), "Allow"):
        actions = as_list(st.get("Action"))
        for action in ("ec2:CreateTags", "ec2:DeleteTags"):
            if not covers(actions, action):
                continue
            resources = as_list(st.get("Resource"))
            if "*" in resources:
                problems.append("%s/%s: %s on *" % (address, sid(st), action))
            if not any(":security-group/" in r for r in resources):
                continue
            pairs = pairs_of(st)
            resource_tag = pairs.get(("StringEquals", "aws:ResourceTag/project")) == PROJECT
            create_action = bool(as_list(pairs.get(("StringEquals", "ec2:CreateAction"))))
            if action == "ec2:CreateTags":
                creates += 1
                if not (create_action or resource_tag):
                    problems.append("%s/%s: ec2:CreateTags on security-group/* with neither ec2:CreateAction nor aws:ResourceTag/project" % (address, sid(st)))
            elif not resource_tag:
                problems.append("%s/%s: ec2:DeleteTags on security-group/* without aws:ResourceTag/project" % (address, sid(st)))
    if creates < 2:
        problems.append("expected CreateTags statements on security-group/*, found %d (the check would be vacuous)" % creates)
    return problems


DEPLOYER_CHECKS = {
    "spike_absent": check_spike_absent,
    "document_sizes": check_document_sizes,
    "attachment_count": check_attachment_count,
    "region_condition": check_region_condition,
    "region_exemption_only_iam_route53": check_region_exemption_is_only_iam_and_route53,
    "no_wildcard_actions": check_no_wildcard_actions,
    "iam_scope": check_iam_scope,
    "create_role_requires_boundary": check_create_role_requires_boundary,
    "deny_statements": check_deny_statements,
    "pass_role_names_the_service": check_pass_role_names_the_service,
    "trust_and_session": check_trust_and_session,
    "no_kms_administration_in_iam": check_no_kms_administration_use_or_grants_in_iam,
    "security_group_mutations_need_project_tag": check_security_group_mutations_need_the_project_resource_tag,
    "security_group_tagging_cannot_adopt": check_security_group_tagging_cannot_adopt,
}


ENV_AWARE = {"iam_scope", "deny_statements", "pass_role_names_the_service"}


def failing_deployer_checks(plan, env="course"):
    failing = {}
    for name, fn in DEPLOYER_CHECKS.items():
        problems = fn(plan, env=env) if name in ENV_AWARE else fn(plan)
        if problems:
            failing[name] = problems
    return failing


# ---------------------------------------------------------------------------------------------------------------
# main-root checks
# ---------------------------------------------------------------------------------------------------------------

def main_roles(main_plan):
    """name -> permissions_boundary for every aws_iam_role the main root plans."""
    roles = {}
    for address, rc in managed_changes(main_plan).items():
        if rc["type"] == "aws_iam_role":
            a = rc["change"]["after"]
            roles[a["name"]] = a.get("permissions_boundary")
    return roles


def check_main_roles_carry_the_deployer_boundaries(main_plan, deployer_plan, env="course"):
    """D1: all 13 role instances exist, each carries a boundary ARN of the form arn:aws:iam::<account>:policy/scholarchain-<env>-...-boundary
    that equals the deployer root's boundary; the EMR service role the EMR boundary, every other role the runtime boundary."""
    runtime, emr = boundary_arns(deployer_plan)
    if runtime is None:
        return ["the deployer plan has no pair of boundary policies"]
    problems = []
    shape = re.compile(r"^arn:aws:iam::%s:policy/scholarchain-%s-[a-z0-9-]+-boundary$" % (ACCOUNT, re.escape(env)))
    for arn in (runtime, emr):
        if not shape.match(arn):
            problems.append("deployer boundary %s does not follow the scholarchain-%s-...-boundary shape" % (arn, env))
    if runtime == emr:
        problems.append("the two boundaries are the same policy")
    roles = main_roles(main_plan)
    expected = expected_main_role_names(env)
    for name in sorted(expected - set(roles)):
        problems.append("expected main role %s is not planned" % name)
    for name, boundary in sorted(roles.items()):
        if not isinstance(boundary, str) or not shape.match(boundary):
            problems.append("role %s carries permissions_boundary %r" % (name, boundary))
            continue
        want = emr if name == "scholarchain-%s-emr-service" % env else runtime
        if boundary != want:
            problems.append("role %s carries %s, expected %s" % (name, boundary, want))
    return problems


def tags_of(change_after):
    return change_after.get("tags") or {}, change_after.get("tags_all") or {}


def check_emr_managed_policy_tag(main_plan):
    """D2: the application subnets, security_group.role["emr"] and security_group.emr_service_access carry the tag = "true"
    (in tags and tags_all); every other subnet and security group does not."""
    problems = []
    must = lambda address: (  # noqa: E731
        address.startswith("module.network.aws_subnet.application[")
        or address in ('module.network.aws_security_group.role["emr"]', "module.network.aws_security_group.emr_service_access"))
    tagged = 0
    other = {"subnet": 0, "sg": 0}
    for address, rc in managed_changes(main_plan).items():
        if rc["type"] not in ("aws_subnet", "aws_security_group"):
            continue
        a = rc["change"]["after"]
        tags, tags_all = tags_of(a)
        if must(address):
            tagged += 1
            for label, source in (("tags", tags), ("tags_all", tags_all)):
                if source.get(EMR_TAG) != "true":
                    problems.append("%s %s[%s] is %r, expected \"true\"" % (address, label, EMR_TAG, source.get(EMR_TAG)))
        else:
            other["subnet" if rc["type"] == "aws_subnet" else "sg"] += 1
            for label, source in (("tags", tags), ("tags_all", tags_all)):
                if EMR_TAG in source:
                    problems.append("%s must not carry %s (%s)" % (address, EMR_TAG, label))
    if tagged != 4:
        problems.append("expected 4 tagged resources (2 application subnets, emr group, emr service-access group), found %d" % tagged)
    if other["subnet"] < 4 or other["sg"] < 2:
        problems.append("too few untagged subnets or groups to be meaningful: %s" % other)
    return problems


def check_no_default_security_group(main_plan):
    """F2 narrowing: the main root does not manage the VPC default security group (as in the Phase 12D spike)."""
    return ["%s is planned" % a for a, rc in managed_changes(main_plan).items() if rc["type"] == "aws_default_security_group"]


def failing_main_checks(main_plan, deployer_plan, env="course"):
    checks = {
        "main_roles_boundaries": lambda: check_main_roles_carry_the_deployer_boundaries(main_plan, deployer_plan, env),
        "emr_managed_policy_tag": lambda: check_emr_managed_policy_tag(main_plan),
        "no_default_security_group": lambda: check_no_default_security_group(main_plan),
        "create_role_covers_main_roles": lambda: check_create_role_covers_main_roles(deployer_plan, main_roles(main_plan)),
    }
    return {name: v for name, fn in checks.items() if (v := fn())}
