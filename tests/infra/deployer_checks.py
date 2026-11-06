"""Named invariants of the deployer root (infra/terraform/deployer): tag-condition values (item 20), request-tag
conditions on the actions that have no resource type (item 10) and the login policy attachment (item 21).

Expectations are hand-derived from the deployer README, the Phase 12D review findings and the AWS Service
Authorization Reference notes recorded in the review. Properties are written to survive the 13C IAM fixes: the
infra-engineer may add stricter conditions and statements, never weaker ones.
"""
import json

from infra_support import after, as_list, condition_pairs, managed_changes, policy_statements, state_resources

REGION = "us-east-2"
DEPLOYER_ROLE_NAME = "scholarchain-deployer"
STACK_TAG = "scholarchain:stack"
EMR_TAG = "for-use-with-amazon-emr-managed-policies"
KNOWN_TAG_VALUES = {STACK_TAG: "spike-emr", EMR_TAG: "true"}

# Actions with no IAM resource type: only request tags (and the region) can scope them. action -> required
# (condition key, exact value) pairs under StringEquals.
REQUEST_SCOPED_ACTIONS = {
    "kms:CreateKey": [("aws:RequestTag/" + STACK_TAG, "spike-emr"), ("aws:RequestedRegion", REGION)],
    "elasticmapreduce:RunJobFlow": [
        ("aws:RequestTag/" + STACK_TAG, "spike-emr"),
        ("aws:RequestTag/" + EMR_TAG, "true"),
        ("aws:RequestedRegion", REGION),
    ],
}


def policy_documents(plan):
    """[(address, parsed document)] for every policy whose JSON is known at plan time (permission sets, boundary, login)."""
    docs = []
    for address in managed_changes(plan):
        a = after(plan, address)
        policy = a.get("policy")
        if isinstance(policy, str) and policy.lstrip().startswith("{"):
            docs.append((address, json.loads(policy)))
    return docs


def check_tag_condition_values(plan):
    """Item 20: every aws:RequestTag/* and aws:ResourceTag/* condition names a known tag, uses StringEquals and has
    the exact string value ("spike-emr" for the stack tag, "true" for the EMR tag), not merely the key."""
    problems = []
    counts = {STACK_TAG: 0, EMR_TAG: 0}
    for address, doc in policy_documents(plan):
        for st in policy_statements(doc):
            for operator, key, value in condition_pairs(st):
                lowered = key.lower()
                if not (lowered.startswith("aws:requesttag/") or lowered.startswith("aws:resourcetag/")):
                    continue
                tag = key.split("/", 1)[1]
                sid = st.get("Sid")
                if tag not in KNOWN_TAG_VALUES:
                    problems.append("%s/%s uses unknown tag condition %s" % (address, sid, key))
                    continue
                counts[tag] += 1
                if operator != "StringEquals":
                    problems.append("%s/%s tag condition %s uses operator %s, expected StringEquals" % (address, sid, key, operator))
                if not isinstance(value, str) or value != KNOWN_TAG_VALUES[tag]:
                    problems.append("%s/%s tag condition %s has value %r, expected exactly %r" % (address, sid, key, value, KNOWN_TAG_VALUES[tag]))
    if counts[STACK_TAG] < 15 or counts[EMR_TAG] < 5:
        problems.append("tag-condition coverage too low to be meaningful: %s (expected >=15 stack and >=5 EMR)" % counts)
    return problems


def check_request_tag_only_actions_conditioned(plan):
    """Item 10: kms:CreateKey and elasticmapreduce:RunJobFlow (no resource type) are allowed only under their exact
    request-tag and region conditions; a condition-stripped or weakened statement is rejected."""
    problems = []
    seen = {action: 0 for action in REQUEST_SCOPED_ACTIONS}
    for address, doc in policy_documents(plan):
        for st in policy_statements(doc):
            if st.get("Effect") != "Allow":
                continue
            actions = as_list(st.get("Action"))
            for action, required in REQUEST_SCOPED_ACTIONS.items():
                if action not in actions and not any(a.endswith("*") and action.startswith(a[:-1]) for a in actions):
                    continue
                seen[action] += 1
                pairs = {(op, key): value for op, key, value in condition_pairs(st)}
                for key, value in required:
                    if pairs.get(("StringEquals", key)) != value:
                        problems.append("%s/%s allows %s without StringEquals %s = %r" % (address, st.get("Sid"), action, key, value))
    for action, count in seen.items():
        if count == 0:
            problems.append("no Allow statement for %s found (the check would be vacuous)" % action)
    return problems


def check_wildcard_resource_allows_are_conditioned(plan):
    """Item 10 (general form): an Allow whose Resource includes a bare "*" must carry a non-empty Condition."""
    problems = []
    for address, doc in policy_documents(plan):
        for st in policy_statements(doc):
            if st.get("Effect") == "Allow" and "*" in as_list(st.get("Resource")) and not st.get("Condition"):
                problems.append("%s/%s allows %s on Resource * with no Condition" % (address, st.get("Sid"), as_list(st.get("Action"))))
    return problems


def check_attachments_target_deployer_role(plan):
    """Every managed-policy attachment targets the deployer role by name (plan-time known), and only that role exists."""
    problems = []
    roles = [a for a in managed_changes(plan) if a.startswith("aws_iam_role.")]
    if roles != ["aws_iam_role.deployer"]:
        problems.append("the root must declare exactly one role, aws_iam_role.deployer; found %s" % roles)
    for address in managed_changes(plan):
        if address.startswith("aws_iam_role_policy_attachment."):
            role = after(plan, address).get("role")
            if role != DEPLOYER_ROLE_NAME:
                problems.append("%s attaches to %r, expected %r" % (address, role, DEPLOYER_ROLE_NAME))
    return problems


PLAN_CHECKS = {
    "tag_condition_values": check_tag_condition_values,
    "request_tag_only_actions": check_request_tag_only_actions_conditioned,
    "wildcard_resource_allows_are_conditioned": check_wildcard_resource_allows_are_conditioned,
    "attachments_target_deployer_role": check_attachments_target_deployer_role,
}


def check_login_policy_attachment(state):
    """Item 21: the always-attached login inline policy targets the deployer role (id or name), nothing else."""
    resources = state_resources(state)
    problems = []
    logins = [a for a in resources if a.startswith("aws_iam_role_policy.login")]
    if logins != ["aws_iam_role_policy.login"]:
        problems.append("expected exactly one aws_iam_role_policy.login, found %s" % logins)
        return problems
    deployer = resources.get("aws_iam_role.deployer")
    if deployer is None:
        return problems + ["aws_iam_role.deployer missing from the mock state"]
    role = resources["aws_iam_role_policy.login"].get("role")
    if role not in (deployer.get("id"), deployer.get("name")):
        problems.append("login policy role is %r, expected the deployer role (id %r or name %r)" % (role, deployer.get("id"), deployer.get("name")))
    if deployer.get("name") != DEPLOYER_ROLE_NAME:
        problems.append("deployer role name is %r, expected %r" % (deployer.get("name"), DEPLOYER_ROLE_NAME))
    return problems


STATE_CHECKS = {"login_attachment": check_login_policy_attachment}


def failing_plan_checks(plan):
    return {name: v for name, fn in PLAN_CHECKS.items() if (v := fn(plan))}


def failing_state_checks(state):
    return {name: v for name, fn in STATE_CHECKS.items() if (v := fn(state))}


# ---------------------------------------------------------------------------------------------------------------
# Phase 13C IAM items (hand-derived from the 12D carried findings 2, 14, 16, 17 and the Phase 13 plan)
# ---------------------------------------------------------------------------------------------------------------
import fnmatch

ACCOUNT = "111122223333"
BOUNDARY_ADDRESS = "aws_iam_policy.spike_boundary[0]"
BOUNDARY_ARN = "arn:aws:iam::%s:policy/scholarchain-spike-emr-boundary" % ACCOUNT
SPIKE_ROLE_ARNS = {
    "arn:aws:iam::%s:role/scholarchain-spike-emr-service" % ACCOUNT,
    "arn:aws:iam::%s:role/scholarchain-spike-emr-instance" % ACCOUNT,
}
# The keys of the spike root's provider default_tags plus Name (spike README "Provider default_tags").
SPIKE_KMS_TAG_KEYS = {
    "course", "project", "environment", "owner", "expiration", "scholarchain:stack",
    "for-use-with-amazon-emr-managed-policies", "Name",
}
# Existing-resource mutations a spike role (the boundary) may hold only for the spike's OWN stack (item 17).
EXISTING_RESOURCE_MUTATIONS = (
    "ec2:TerminateInstances", "ec2:ModifyInstanceAttribute", "ec2:DeleteNetworkInterface", "ec2:DeleteTags",
    "ec2:DeleteLaunchTemplate", "ec2:DeleteLaunchTemplateVersions", "ec2:ModifyLaunchTemplate",
)
ENI_ACTIONS = ("ec2:DeleteNetworkInterface", "ec2:ModifyNetworkInterfaceAttribute", "ec2:CreateNetworkInterface")


def _doc(plan, address):
    for addr, doc in policy_documents(plan):
        if addr == address:
            return doc
    return None


def _covers(actions, name):
    """True when an Action list (possibly with wildcards) covers the named action."""
    return any(fnmatch.fnmatchcase(name, a) for a in as_list(actions))


def _equals(statement):
    return {(op, key): value for op, key, value in condition_pairs(statement)}


def check_item17_boundary_mutations_need_the_stack_tag(plan):
    """Item 17: in the permissions boundary, terminating or modifying instances, deleting or tagging-away ENIs and tags,
    or deleting launch templates is allowed only on resources carrying BOTH the EMR managed-policies tag and the stack
    tag (the EMR tag alone is on every EMR cluster in the account), in the spike region."""
    boundary = _doc(plan, BOUNDARY_ADDRESS)
    if boundary is None:
        return ["the spike permissions boundary policy is missing from the plan"]
    problems, seen = [], set()
    for st in policy_statements(boundary):
        if st.get("Effect") != "Allow":
            continue
        for action in EXISTING_RESOURCE_MUTATIONS:
            if not _covers(st.get("Action"), action):
                continue
            seen.add(action)
            pairs = _equals(st)
            for key, value in (("aws:ResourceTag/" + STACK_TAG, "spike-emr"), ("aws:ResourceTag/" + EMR_TAG, "true"), ("aws:RequestedRegion", REGION)):
                if pairs.get(("StringEquals", key)) != value:
                    problems.append("boundary %s allows %s without StringEquals %s = %r" % (st.get("Sid"), action, key, value))
    for action in ("ec2:TerminateInstances", "ec2:ModifyInstanceAttribute", "ec2:DeleteNetworkInterface", "ec2:DeleteTags"):
        if action not in seen:
            problems.append("no boundary statement allows %s (the check would be vacuous)" % action)
    return problems


def check_item2_eni_actions_are_region_scoped(plan):
    """Item 2: every statement that creates, deletes or modifies network interfaces names only us-east-2 ARNs of this
    account and carries StringEquals aws:RequestedRegion = us-east-2."""
    problems, seen = [], set()
    prefix = "arn:aws:ec2:%s:%s:" % (REGION, ACCOUNT)
    for address, doc in policy_documents(plan):
        for st in policy_statements(doc):
            if st.get("Effect") != "Allow":
                continue
            for action in ENI_ACTIONS:
                if not _covers(st.get("Action"), action):
                    continue
                seen.add(action)
                for resource in as_list(st.get("Resource")):
                    if not resource.startswith(prefix):
                        problems.append("%s/%s: %s on %r is not scoped to %s" % (address, st.get("Sid"), action, resource, prefix))
                if _equals(st).get(("StringEquals", "aws:RequestedRegion")) != REGION:
                    problems.append("%s/%s: %s lacks the aws:RequestedRegion condition" % (address, st.get("Sid"), action))
    for action in ENI_ACTIONS:
        if action not in seen:
            problems.append("no statement allows %s (the check would be vacuous)" % action)
    return problems


def check_item14_kms_tag_resource_is_key_restricted(plan):
    """Item 14: kms:TagResource is allowed only on key ARNs of this region/account, with the stack request tag, the region,
    and a ForAllValues:StringEquals aws:TagKeys restriction to exactly the spike root's own tag keys."""
    problems, found = [], 0
    for address, doc in policy_documents(plan):
        for st in policy_statements(doc):
            if st.get("Effect") != "Allow" or not _covers(st.get("Action"), "kms:TagResource"):
                continue
            found += 1
            pairs = _equals(st)
            if set(as_list(st.get("Resource"))) != {"arn:aws:kms:%s:%s:key/*" % (REGION, ACCOUNT)}:
                problems.append("%s/%s: kms:TagResource resource is %s" % (address, st.get("Sid"), as_list(st.get("Resource"))))
            if pairs.get(("StringEquals", "aws:RequestTag/" + STACK_TAG)) != "spike-emr":
                problems.append("%s/%s: kms:TagResource lacks the stack request tag" % (address, st.get("Sid")))
            if pairs.get(("StringEquals", "aws:RequestedRegion")) != REGION:
                problems.append("%s/%s: kms:TagResource lacks the region condition" % (address, st.get("Sid")))
            keys = pairs.get(("ForAllValues:StringEquals", "aws:TagKeys"))
            if keys is None or set(as_list(keys)) != SPIKE_KMS_TAG_KEYS or "*" in "".join(as_list(keys)):
                problems.append("%s/%s: kms:TagResource is not limited to the spike tag keys (aws:TagKeys = %r)" % (address, st.get("Sid"), keys))
    if found != 1:
        problems.append("expected exactly one kms:TagResource Allow statement, found %d" % found)
    return problems


def check_item16_role_creation_and_trust_are_limited(plan):
    """Item 16 (a mitigation: IAM has no trust-document condition key): iam:CreateRole only for the two spike role ARNs, only
    with the boundary and the stack request tag; iam:UpdateAssumeRolePolicy denied on the spike roles and never allowed;
    the deployer can never assume a spike role."""
    problems, create = [], 0
    deny_update = deny_assume = False
    for address, doc in policy_documents(plan):
        for st in policy_statements(doc):
            effect = st.get("Effect")
            if effect == "Allow" and _covers(st.get("Action"), "iam:CreateRole"):
                create += 1
                if set(as_list(st.get("Resource"))) != SPIKE_ROLE_ARNS:
                    problems.append("%s/%s: iam:CreateRole resources are %s, expected exactly the two spike roles" % (address, st.get("Sid"), sorted(as_list(st.get("Resource")))))
                pairs = _equals(st)
                if pairs.get(("StringEquals", "iam:PermissionsBoundary")) != BOUNDARY_ARN:
                    problems.append("%s/%s: iam:CreateRole lacks the permissions boundary condition" % (address, st.get("Sid")))
                if pairs.get(("StringEquals", "aws:RequestTag/" + STACK_TAG)) != "spike-emr":
                    problems.append("%s/%s: iam:CreateRole lacks the stack request tag" % (address, st.get("Sid")))
            if effect == "Allow" and any(_covers(st.get("Action"), a) for a in ("iam:UpdateAssumeRolePolicy", "iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary")):
                problems.append("%s/%s allows changing a role's trust policy or boundary" % (address, st.get("Sid")))
            if effect == "Deny" and _covers(st.get("Action"), "iam:UpdateAssumeRolePolicy"):
                resources = " ".join(as_list(st.get("Resource")))
                if "role/scholarchain-spike-emr-" in resources:
                    deny_update = True
            if effect == "Deny" and _covers(st.get("Action"), "sts:AssumeRole") and "role/scholarchain-spike-emr-" in " ".join(as_list(st.get("Resource"))):
                deny_assume = True
    if create != 1:
        problems.append("expected exactly one iam:CreateRole Allow statement, found %d" % create)
    if not deny_update:
        problems.append("iam:UpdateAssumeRolePolicy is not denied on the spike roles")
    if not deny_assume:
        problems.append("sts:AssumeRole on the spike roles is not denied for the deployer")
    return problems


IAM_ITEM_CHECKS = {
    "item17_boundary_stack_tag": check_item17_boundary_mutations_need_the_stack_tag,
    "item2_eni_region_scope": check_item2_eni_actions_are_region_scoped,
    "item14_kms_tag_resource": check_item14_kms_tag_resource_is_key_restricted,
    "item16_role_creation_and_trust": check_item16_role_creation_and_trust_are_limited,
}
PLAN_CHECKS.update(IAM_ITEM_CHECKS)
