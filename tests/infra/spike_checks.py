"""Named invariants of the isolated EMR spike root (infra/terraform/spikes/emr-spark-isolated).

Each check takes the offline PLAN JSON and/or the mock STATE JSON of a root copy and returns a list of violation
strings (empty = holds). The expectations below are hand-derived from the spike README ("Exact shape", "Resources"),
the Phase 12D review findings (items 6, 7, 12) and the Phase 13 plan; they do not read the Terraform sources.

Properties are written to stay true after the Phase 13C infra fixes (items 2, 5, 14, 16, 17, EMR port): the spike
root may gain stricter conditions, but its resource inventory, rules, volumes, tags and S3/KMS/EFS reach are fixed.
"""
import fnmatch

from infra_support import (after, as_list, condition_pairs, config_refs, managed_changes, policy_statements,
                           state_resources)

ACCOUNT = "111122223333"
REGION = "us-east-2"
BUCKET_ARN = "arn:aws:s3:::scholarchain-spike-emr-%s-%s" % (ACCOUNT, REGION)
KEY_ARN = "arn:aws:kms:us-east-2:%s:key/11111111-2222-3333-4444-555555555555" % ACCOUNT
FS_ARN = "arn:aws:elasticfilesystem:us-east-2:%s:file-system/fs-0123456789abcdef0" % ACCOUNT
AP_ARN = "arn:aws:elasticfilesystem:us-east-2:%s:access-point/fsap-0123456789abcdef0" % ACCOUNT
CLUSTER_ARNS = "arn:aws:elasticmapreduce:us-east-2:%s:cluster/*" % ACCOUNT

REQUIRED_TAGS = {
    "course": "CS441",
    "project": "ScholarChain",
    "environment": "spike",
    "owner": "example-owner",
    "expiration": "2026-11-04",
    "scholarchain:stack": "spike-emr",
    "for-use-with-amazon-emr-managed-policies": "true",
}

# The complete, hand-listed inventory (README "Resources"): 55 managed resources, no module, no data source.
EXPECTED_ADDRESSES = frozenset(
    [
        # network
        "aws_vpc.spike", "aws_internet_gateway.spike", "aws_subnet.public", "aws_subnet.private", "aws_eip.nat",
        "aws_nat_gateway.spike", "aws_route_table.public", "aws_route_table.private",
        "aws_route_table_association.public", "aws_route_table_association.private", "aws_vpc_endpoint.s3",
        # security groups and rules
        "aws_security_group.primary", "aws_security_group.core", "aws_security_group.service_access",
        "aws_security_group.efs",
        "aws_vpc_security_group_ingress_rule.primary_self", "aws_vpc_security_group_ingress_rule.primary_from_core",
        "aws_vpc_security_group_ingress_rule.primary_from_service_access",
        "aws_vpc_security_group_ingress_rule.core_self", "aws_vpc_security_group_ingress_rule.core_from_primary",
        "aws_vpc_security_group_ingress_rule.core_from_service_access",
        "aws_vpc_security_group_ingress_rule.service_access_from_primary",
        "aws_vpc_security_group_ingress_rule.efs_from_primary", "aws_vpc_security_group_ingress_rule.efs_from_core",
        "aws_vpc_security_group_egress_rule.primary_all", "aws_vpc_security_group_egress_rule.core_all",
        "aws_vpc_security_group_egress_rule.service_access_to_primary",
        "aws_vpc_security_group_egress_rule.service_access_to_core",
        # kms (one key, one alias)
        "aws_kms_key.spike", "aws_kms_alias.spike",
        # iam
        "aws_iam_role.service", "aws_iam_role.instance", "aws_iam_role_policy_attachment.service_emr_v2",
        "aws_iam_role_policy.service_pass_instance_role", "aws_iam_role_policy.instance",
        "aws_iam_instance_profile.instance",
        # s3: one bucket, its four controls, seven staged objects
        "aws_s3_bucket.spike", "aws_s3_bucket_public_access_block.spike", "aws_s3_bucket_ownership_controls.spike",
        "aws_s3_bucket_server_side_encryption_configuration.spike", "aws_s3_bucket_policy.spike",
        "aws_s3_object.runtime", "aws_s3_object.inputs", "aws_s3_object.bootstrap", "aws_s3_object.run_step",
        "aws_s3_object.collect_results", "aws_s3_object.g1_config", "aws_s3_object.spark_defaults",
        # efs
        "aws_efs_file_system.spike", "aws_efs_backup_policy.spike", "aws_efs_mount_target.private",
        "aws_efs_access_point.spike", "aws_efs_file_system_policy.spike",
        # emr
        "aws_emr_security_configuration.spike", "aws_emr_cluster.spike",
    ]
)

# Resources that have no tags argument (so no tags_all): everything else must expose tags_all.
NON_TAGGABLE = frozenset(
    [
        "aws_route_table_association.public", "aws_route_table_association.private", "aws_kms_alias.spike",
        "aws_s3_bucket_public_access_block.spike", "aws_s3_bucket_ownership_controls.spike",
        "aws_s3_bucket_server_side_encryption_configuration.spike", "aws_s3_bucket_policy.spike",
        "aws_iam_role_policy_attachment.service_emr_v2", "aws_iam_role_policy.service_pass_instance_role",
        "aws_iam_role_policy.instance", "aws_efs_backup_policy.spike", "aws_efs_mount_target.private",
        "aws_efs_file_system_policy.spike", "aws_emr_security_configuration.spike",
    ]
)
EXPECTED_TAGGABLE = EXPECTED_ADDRESSES - NON_TAGGABLE

# Families that must not exist in this root (item 6: added SNS/SQS; item 12: the default SG; plus ingress paths
# that bypass the reviewed rule resources, SSH key pairs, instances and load balancers).
FORBIDDEN_PREFIXES = (
    "aws_sns_", "aws_sqs_", "aws_default_", "aws_security_group_rule", "aws_network_acl", "aws_key_pair",
    "aws_instance", "aws_launch_", "aws_autoscaling", "aws_emr_managed_scaling", "aws_emr_instance_", "aws_lb",
    "aws_lambda", "aws_cloudwatch", "aws_iam_user", "aws_iam_access_key", "aws_iam_policy", "aws_kms_grant",
    "aws_kms_external_key", "aws_kms_replica", "aws_secretsmanager", "aws_ssm_",
)

# (owner group, protocol, from, to, referenced group): README security-group rule tables.
EXPECTED_INGRESS = {
    "primary_self": ("primary", "-1", None, None, "primary"),
    "primary_from_core": ("primary", "-1", None, None, "core"),
    "primary_from_service_access": ("primary", "tcp", 8443, 8443, "service_access"),
    "core_self": ("core", "-1", None, None, "core"),
    "core_from_primary": ("core", "-1", None, None, "primary"),
    "core_from_service_access": ("core", "tcp", 8443, 8443, "service_access"),
    "service_access_from_primary": ("service_access", "tcp", 9443, 9443, "primary"),
    "efs_from_primary": ("efs", "tcp", 2049, 2049, "primary"),
    "efs_from_core": ("efs", "tcp", 2049, 2049, "core"),
}
# name -> (owner group, protocol, from, to, referenced group or None, cidr or None)
EXPECTED_EGRESS = {
    "primary_all": ("primary", "-1", None, None, None, "0.0.0.0/0"),
    "core_all": ("core", "-1", None, None, None, "0.0.0.0/0"),
    "service_access_to_primary": ("service_access", "tcp", 8443, 8443, "primary", None),
    "service_access_to_core": ("service_access", "tcp", 8443, 8443, "core", None),
}

# action -> exact resource set the instance profile policy may grant (README "IAM").
EXPECTED_INSTANCE_ACTIONS = {
    "s3:GetObject": {BUCKET_ARN + "/staging/*"},
    "s3:PutObject": {BUCKET_ARN + "/results/*", BUCKET_ARN + "/emr-logs/*"},
    "s3:AbortMultipartUpload": {BUCKET_ARN + "/results/*", BUCKET_ARN + "/emr-logs/*"},
    "s3:ListBucket": {BUCKET_ARN},
    "kms:Decrypt": {KEY_ARN}, "kms:Encrypt": {KEY_ARN}, "kms:GenerateDataKey": {KEY_ARN},
    "kms:ReEncryptFrom": {KEY_ARN}, "kms:ReEncryptTo": {KEY_ARN}, "kms:DescribeKey": {KEY_ARN},
    "elasticmapreduce:GetAutoTerminationPolicy": {CLUSTER_ARNS},
    "elasticmapreduce:PutAutoTerminationPolicy": {CLUSTER_ARNS},
    "elasticmapreduce:RemoveAutoTerminationPolicy": {CLUSTER_ARNS},
    "elasticfilesystem:ClientMount": {FS_ARN}, "elasticfilesystem:ClientWrite": {FS_ARN},
}


def _name(address):
    return address.split(".", 1)[1]


# ---------------------------------------------------------------------------------------------------------------
# plan checks
# ---------------------------------------------------------------------------------------------------------------

def check_inventory(plan):
    """Exact resource inventory (item 6: absence of extra resources). No module call, no data source, one provider."""
    got = set(managed_changes(plan))
    problems = []
    if got - EXPECTED_ADDRESSES:
        problems.append("unexpected resources: %s" % sorted(got - EXPECTED_ADDRESSES))
    if EXPECTED_ADDRESSES - got:
        problems.append("missing resources: %s" % sorted(EXPECTED_ADDRESSES - got))
    if len(got) != len(EXPECTED_ADDRESSES):
        problems.append("resource count %d != %d" % (len(got), len(EXPECTED_ADDRESSES)))
    root = plan["configuration"]["root_module"]
    if root.get("module_calls"):
        problems.append("module calls present: %s" % sorted(root["module_calls"]))
    data = [r["address"] for r in root.get("resources", []) if r.get("mode") == "data"]
    if data:
        problems.append("data sources present: %s" % data)
    providers = sorted(plan["configuration"].get("provider_config", {}))
    if providers != ["aws"]:
        problems.append("provider set is %s, expected ['aws']" % providers)
    return problems


def check_forbidden_families(plan):
    """Item 6 and 12: no SNS/SQS, no default security group, no side-door ingress or compute families."""
    bad = [a for a in managed_changes(plan) if a.split(".")[0].startswith(FORBIDDEN_PREFIXES)]
    return ["forbidden resource family present: %s" % sorted(bad)] if bad else []


def check_default_security_group_absent(plan):
    """Item 12: aws_default_security_group is not managed in this root (the README disclosure)."""
    bad = [a for a in managed_changes(plan) if a.startswith("aws_default_security_group.")]
    return ["aws_default_security_group is managed: %s" % bad] if bad else []


def check_single_kms_key(plan):
    """Item 6: exactly one CMK and one alias."""
    types = [a.split(".")[0] for a in managed_changes(plan)]
    problems = []
    if types.count("aws_kms_key") != 1:
        problems.append("aws_kms_key count is %d, expected exactly 1" % types.count("aws_kms_key"))
    if types.count("aws_kms_alias") != 1:
        problems.append("aws_kms_alias count is %d, expected exactly 1" % types.count("aws_kms_alias"))
    return problems


def _group(refs):
    for ref in refs:
        if ref.startswith("aws_security_group.") and ref.endswith(".id"):
            return ref.split(".")[1]
    return None


def check_security_group_rules(plan):
    """Item 6: no CIDR ingress, no SSH, exact rule tables; no inline or legacy rule side doors."""
    problems = []
    changes = managed_changes(plan)
    for address in changes:
        kind = address.split(".")[0]
        if kind == "aws_security_group":
            a = after(plan, address)
            if as_list(a.get("ingress")) or as_list(a.get("egress")):
                problems.append("%s declares inline rules (ingress/egress must be empty)" % address)
        if kind == "aws_security_group_rule":
            problems.append("%s is a legacy rule resource (not allowed)" % address)
    ingress = {_name(a): a for a in changes if a.startswith("aws_vpc_security_group_ingress_rule.")}
    egress = {_name(a): a for a in changes if a.startswith("aws_vpc_security_group_egress_rule.")}
    if set(ingress) != set(EXPECTED_INGRESS):
        problems.append("ingress rule set differs: unexpected=%s missing=%s" % (
            sorted(set(ingress) - set(EXPECTED_INGRESS)), sorted(set(EXPECTED_INGRESS) - set(ingress))))
    if set(egress) != set(EXPECTED_EGRESS):
        problems.append("egress rule set differs: unexpected=%s missing=%s" % (
            sorted(set(egress) - set(EXPECTED_EGRESS)), sorted(set(EXPECTED_EGRESS) - set(egress))))
    for name, address in ingress.items():
        a = after(plan, address)
        if a.get("cidr_ipv4") or a.get("cidr_ipv6") or a.get("prefix_list_id"):
            problems.append("%s opens ingress to a CIDR or prefix list" % address)
        lo, hi = a.get("from_port"), a.get("to_port")
        if (lo is not None and hi is not None and lo <= 22 <= hi) or (a.get("ip_protocol") in ("-1", "all") and (a.get("cidr_ipv4") or a.get("cidr_ipv6"))):
            problems.append("%s covers port 22" % address)
        if name in EXPECTED_INGRESS:
            group, proto, from_port, to_port, ref = EXPECTED_INGRESS[name]
            if (a.get("ip_protocol"), a.get("from_port"), a.get("to_port")) != (proto, from_port, to_port):
                problems.append("%s protocol/ports are %s/%s/%s, expected %s/%s/%s" % (
                    address, a.get("ip_protocol"), a.get("from_port"), a.get("to_port"), proto, from_port, to_port))
            if _group(config_refs(plan, address, "security_group_id")) != group or _group(config_refs(plan, address, "referenced_security_group_id")) != ref:
                problems.append("%s attaches to the wrong group or references the wrong source group" % address)
    for name, address in egress.items():
        a = after(plan, address)
        if name in EXPECTED_EGRESS:
            group, proto, from_port, to_port, ref, cidr = EXPECTED_EGRESS[name]
            if (a.get("ip_protocol"), a.get("from_port"), a.get("to_port"), a.get("cidr_ipv4")) != (proto, from_port, to_port, cidr):
                problems.append("%s egress shape differs from the reviewed table" % address)
            if _group(config_refs(plan, address, "security_group_id")) != group or _group(config_refs(plan, address, "referenced_security_group_id")) != ref:
                problems.append("%s egress attaches to or references the wrong group" % address)
    return problems


def check_ebs_pinned(plan):
    """Item 6: gp3 data volumes pin size, IOPS and throughput (README: 32 GiB, 3000 IOPS, 125 MiB/s); root 32 GiB."""
    cluster = after(plan, "aws_emr_cluster.spike")
    problems = []
    if cluster.get("ebs_root_volume_size") != 32:
        problems.append("ebs_root_volume_size is %r, expected 32" % cluster.get("ebs_root_volume_size"))
    for group_name in ("master_instance_group", "core_instance_group"):
        groups = as_list(cluster.get(group_name))
        if len(groups) != 1:
            problems.append("%s count is %d" % (group_name, len(groups)))
            continue
        configs = as_list(groups[0].get("ebs_config"))
        if len(configs) != 1:
            problems.append("%s must have exactly one ebs_config, found %d" % (group_name, len(configs)))
            continue
        c = configs[0]
        want = {"type": "gp3", "size": 32, "iops": 3000, "throughput": 125, "volumes_per_instance": 1}
        got = {k: c.get(k) for k in want}
        if got != want:
            problems.append("%s ebs_config is %s, expected exactly %s (IOPS/throughput must be pinned)" % (group_name, got, want))
    return problems


def check_tags_all(plan):
    """Item 7: EVERY taggable resource's provider-computed tags_all carries all seven required tags, exact values."""
    problems = []
    changes = managed_changes(plan)
    exposing = set()
    for address in changes:
        a = after(plan, address)
        if "tags_all" in a and isinstance(a["tags_all"], dict):
            exposing.add(address)
            for key, value in REQUIRED_TAGS.items():
                if a["tags_all"].get(key) != value:
                    problems.append("%s tags_all[%s] is %r, expected %r" % (address, key, a["tags_all"].get(key), value))
    absent = EXPECTED_TAGGABLE - exposing
    if absent:
        problems.append("taggable resources without tags_all in the plan (coverage gap): %s" % sorted(absent))
    return problems


PLAN_CHECKS = {
    "inventory": check_inventory,
    "forbidden_families": check_forbidden_families,
    "default_security_group_absent": check_default_security_group_absent,
    "single_kms_key": check_single_kms_key,
    "security_group_rules": check_security_group_rules,
    "ebs_pinned": check_ebs_pinned,
    "tags_all": check_tags_all,
}


# ---------------------------------------------------------------------------------------------------------------
# state (mock apply) checks
# ---------------------------------------------------------------------------------------------------------------

def _all_policy_documents(state):
    """(address, document) for every IAM-style policy JSON in the mock state (role/bucket/EFS/KMS policies)."""
    docs = []
    for address, values in state_resources(state).items():
        policy = values.get("policy")
        if isinstance(policy, str) and policy.lstrip().startswith("{") and '"Statement"' in policy:
            docs.append((address, policy))
    return docs


def _matches_get_object(action):
    """True when an Action pattern (possibly with wildcards) covers s3:GetObject."""
    return fnmatch.fnmatchcase("s3:GetObject", action)


def check_s3_get_object_scope(state):
    """Item 6: in EVERY policy document, any Allow that can GetObject names only bucket/staging/*."""
    problems = []
    for address, doc in _all_policy_documents(state):
        for st in policy_statements(doc):
            if st.get("Effect") != "Allow":
                continue
            if any(_matches_get_object(a) for a in as_list(st.get("Action"))):
                resources = set(as_list(st.get("Resource")))
                if resources != {BUCKET_ARN + "/staging/*"}:
                    problems.append("%s grants s3:GetObject on %s, expected exactly {%s/staging/*}" % (address, sorted(resources), BUCKET_ARN))
    return problems


def check_instance_policy_exact(state):
    """Item 6: the instance profile policy grants exactly the reviewed action -> resource table, nothing more."""
    problems = []
    values = state_resources(state).get("aws_iam_role_policy.instance")
    if values is None:
        return ["aws_iam_role_policy.instance missing from the mock state"]
    granted = {}
    for st in policy_statements(values["policy"]):
        if st.get("Effect") != "Allow":
            problems.append("instance policy has a non-Allow statement %r" % st.get("Sid"))
            continue
        for action in as_list(st.get("Action")):
            granted.setdefault(action, set()).update(as_list(st.get("Resource")))
    if set(granted) != set(EXPECTED_INSTANCE_ACTIONS):
        problems.append("instance policy actions differ: extra=%s missing=%s" % (
            sorted(set(granted) - set(EXPECTED_INSTANCE_ACTIONS)), sorted(set(EXPECTED_INSTANCE_ACTIONS) - set(granted))))
    for action, want in EXPECTED_INSTANCE_ACTIONS.items():
        if action in granted and granted[action] != want:
            problems.append("instance policy %s resources are %s, expected exactly %s" % (action, sorted(granted[action]), sorted(want)))
    # Conditions that keep the reach narrow must survive (stricter is fine, absent is not).
    for st in policy_statements(values["policy"]):
        actions = set(as_list(st.get("Action")))
        pairs = condition_pairs(st)
        if "s3:ListBucket" in actions and not any(k == "s3:prefix" and set(as_list(v)) == {"staging/*", "results/*", "emr-logs/*"} for _, k, v in pairs):
            problems.append("ListBucket lost its exact s3:prefix condition")
        if "elasticmapreduce:PutAutoTerminationPolicy" in actions and not any(k == "aws:ResourceTag/scholarchain:stack" and v == "spike-emr" for _, k, v in pairs):
            problems.append("auto-termination statement lost the stack resource-tag condition")
        if "elasticfilesystem:ClientMount" in actions and not any(k == "elasticfilesystem:AccessPointArn" and v == AP_ARN for _, k, v in pairs):
            problems.append("EFS statement lost the access-point condition")
    return problems


def check_no_wildcard_statements(state):
    """Item 6 (defence in depth): no Allow statement in any policy names a bare '*' action or '*' resource."""
    problems = []
    for address, doc in _all_policy_documents(state):
        if address.startswith("aws_kms_key"):
            continue  # a key policy's Resource "*" means "this key" (README)
        for st in policy_statements(doc):
            if st.get("Effect") != "Allow":
                continue
            if "*" in as_list(st.get("Action")) or "*" in as_list(st.get("Resource")):
                problems.append("%s has an Allow with a bare * action or resource" % address)
    return problems


STATE_CHECKS = {
    "s3_get_object_scope": check_s3_get_object_scope,
    "instance_policy_exact": check_instance_policy_exact,
    "no_wildcard_statements": check_no_wildcard_statements,
}


def failing_plan_checks(plan):
    return {name: v for name, fn in PLAN_CHECKS.items() if (v := fn(plan))}


def failing_state_checks(state):
    return {name: v for name, fn in STATE_CHECKS.items() if (v := fn(state))}


# ---------------------------------------------------------------------------------------------------------------
# Phase 13C items 5 and 16 on the spike root (plan view; the key policy and the trust policies are known at plan time)
# ---------------------------------------------------------------------------------------------------------------
import json

SERVICE_ROLE_ARN = "arn:aws:iam::%s:role/scholarchain-spike-emr-service" % ACCOUNT
INSTANCE_ROLE_ARN = "arn:aws:iam::%s:role/scholarchain-spike-emr-instance" % ACCOUNT
KEY_POLICY_SIDS = {
    "AccountRootAdministersAndDelegates", "DeployerAdministersKey", "DeployerUsesKeyOnlyViaS3AndEfs",
    "EmrServiceRoleEbsEncryption", "EmrServiceRoleCreateGrantForAwsResourcesOnly", "InstanceProfileDataKeyUse",
}


def _key_policy(plan):
    return json.loads(after(plan, "aws_kms_key.spike")["policy"])


def check_item5_service_role_create_grant_is_aws_resource_only(plan):
    """Item 5: the EMR service role's kms:CreateGrant exists in exactly one key-policy statement, as its only action,
    conditioned on Bool kms:GrantIsForAWSResource = "true" (a grant for an arbitrary grantee is refused); the instance
    role never gets CreateGrant; the key policy holds exactly the six reviewed statements."""
    problems = []
    statements = policy_statements(_key_policy(plan))
    sids = [st.get("Sid") for st in statements]
    if set(sids) != KEY_POLICY_SIDS or len(sids) != len(KEY_POLICY_SIDS):
        problems.append("key policy statements are %s, expected exactly %s" % (sorted(sids), sorted(KEY_POLICY_SIDS)))
    grants = [st for st in statements if as_list(st.get("Principal", {}).get("AWS")) == [SERVICE_ROLE_ARN] and "kms:CreateGrant" in as_list(st.get("Action"))]
    if len(grants) != 1:
        problems.append("expected exactly one service-role statement with kms:CreateGrant, found %d" % len(grants))
    for st in grants:
        if as_list(st.get("Action")) != ["kms:CreateGrant"]:
            problems.append("the CreateGrant statement must carry only kms:CreateGrant, found %s" % as_list(st.get("Action")))
        if st.get("Effect") != "Allow" or (st.get("Condition") or {}).get("Bool", {}).get("kms:GrantIsForAWSResource") != "true":
            problems.append("the service role's CreateGrant lacks Bool kms:GrantIsForAWSResource = \"true\"")
    for st in statements:
        if as_list(st.get("Principal", {}).get("AWS")) == [INSTANCE_ROLE_ARN] and "kms:CreateGrant" in as_list(st.get("Action")):
            problems.append("the instance role must not hold kms:CreateGrant")
    return problems


def check_item16_trust_policies_name_only_service_principals(plan):
    """Item 16 (what exists): the spike roles' own trust policies name only the EMR (service role) and EC2 (instance role)
    service principals, one statement each, sts:AssumeRole only, no AWS or federated principal, no wildcard principal."""
    problems = []
    want = {"aws_iam_role.service": "elasticmapreduce.amazonaws.com", "aws_iam_role.instance": "ec2.amazonaws.com"}
    for address, service in want.items():
        trust = json.loads(after(plan, address)["assume_role_policy"])
        statements = policy_statements(trust)
        if len(statements) != 1:
            problems.append("%s trust policy has %d statements, expected 1" % (address, len(statements)))
            continue
        st = statements[0]
        if st.get("Effect") != "Allow" or as_list(st.get("Action")) != ["sts:AssumeRole"]:
            problems.append("%s trust statement is not an Allow of sts:AssumeRole only" % address)
        if st.get("Principal") != {"Service": service}:
            problems.append("%s trust principal is %r, expected exactly {'Service': %r}" % (address, st.get("Principal"), service))
        if "*" in json.dumps(st.get("Principal")) or "*" in json.dumps(st.get("Action")):
            problems.append("%s trust policy names a wildcard principal or action" % address)
    service_trust = policy_statements(json.loads(after(plan, "aws_iam_role.service")["assume_role_policy"]))[0]
    if (service_trust.get("Condition") or {}).get("StringEquals", {}).get("aws:SourceAccount") != ACCOUNT:
        problems.append("the EMR service role trust lost its aws:SourceAccount condition")
    return problems


PLAN_CHECKS.update({
    "item5_service_role_create_grant": check_item5_service_role_create_grant_is_aws_resource_only,
    "item16_trust_service_principals_only": check_item16_trust_policies_name_only_service_principals,
})
