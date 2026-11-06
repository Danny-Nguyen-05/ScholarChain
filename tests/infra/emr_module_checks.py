"""Named invariants of the main EMR module (infra/terraform/modules/emr) after the 13C port, derived by hand from decision 12-10
(docs/agent-runs/phase-12/evidence/12d-spike-closeout/decision-12-10.md), the Phase 13 plan (Subphase 13C tasks 1 and 4, the
Phase 12 handoff, the Step 0 answers in docs/agent-runs/phase-13/prompt.md) and the reviewed pins in scripts/config/*.conf.

The checks take the plan JSON and/or mock state JSON of an EmrModuleTree (infra_support.py). The Spark settings expectation
is the independently parsed scripts/config/spark-12-10.conf; the G6 task-node bound is computed here from emr-pricing.conf
and release.conf (Decimal arithmetic), not copied from the module's validation messages.
"""
import base64
import decimal
import hashlib
import json
import re
from decimal import Decimal as D

from infra_support import REPO, after, as_list, managed_changes, policy_statements

PREFIX = "module.emr."
SPARK_CONF = REPO / "scripts/config/spark-12-10.conf"
PRICING_CONF = REPO / "scripts/config/emr-pricing.conf"
RELEASE_CONF = REPO / "scripts/config/release.conf"

# Default config: 11 managed resources, no task group, no managed scaling policy (G3), one EFS staging stack (G1 option ii).
EXPECTED_DEFAULT = frozenset(PREFIX + a for a in (
    "aws_emr_security_configuration.encrypted[0]", "aws_emr_cluster.pipeline[0]", "aws_efs_file_system.staging[0]",
    "aws_efs_backup_policy.staging[0]", "aws_security_group.efs[0]", "aws_vpc_security_group_ingress_rule.efs_from_emr[0]",
    "aws_vpc_security_group_egress_rule.emr_to_efs[0]", "aws_efs_mount_target.staging[0]", "aws_efs_access_point.staging[0]",
    "aws_efs_file_system_policy.staging[0]", "aws_iam_role_policy.node[0]",
))
EMR_SG = "sg-0123456789abcdef0"


def _cluster(plan):
    return after(plan, PREFIX + "aws_emr_cluster.pipeline[0]")


# ---------------------------------------------------------------------------------------------------------------
# independent parsing of the pinned inputs
# ---------------------------------------------------------------------------------------------------------------

def parse_spark_conf(text):
    """key -> value of a `key value` per line file; blank lines and # comments ignored."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(" ")
        out[key] = value.strip()
    return out


def conf_values(path, pattern):
    return dict(re.findall(pattern, path.read_text(), re.M))


def g6_bounds():
    """(max task nodes, rate per instance-hour, billed hours at the maximum runtime, per-run cap) from the reviewed files.

    estimate = instances x (EC2 + EMR uplift) x (max runtime minutes x 60 + idle seconds) / 3600; the largest cluster that
    stays within the per-run cap, minus the primary and the one core node, is the most task nodes the module may allow."""
    release = conf_values(RELEASE_CONF, r"^([A-Z_0-9]+)=(\S+)\s*$")
    rates = conf_values(PRICING_CONF, r"^(EMR_RATE_[A-Z0-9_]+)=(\S+)\s*$")
    cap = D(release["EMR_MAX_RUN_USD"])
    hours = (D(release["PIPELINE_MAX_RUNTIME_MINUTES"]) * 60 + D(release["PIPELINE_MAX_IDLE_TIMEOUT_SECONDS"])) / 3600
    per_instance = {}
    for key, value in rates.items():
        m = re.match(r"EMR_RATE_EC2_(.+)$", key)
        if m:
            per_instance[m.group(1)] = D(value) + D(rates["EMR_RATE_EMR_" + m.group(1)])
    return cap, hours, per_instance


def max_instances(rate, hours, cap):
    return int((cap / (rate * hours)).to_integral_value(rounding=decimal.ROUND_FLOOR))


# ---------------------------------------------------------------------------------------------------------------
# plan checks (default configuration)
# ---------------------------------------------------------------------------------------------------------------

def check_inventory(plan):
    got = set(managed_changes(plan))
    problems = []
    if got - EXPECTED_DEFAULT:
        problems.append("unexpected resources: %s" % sorted(got - EXPECTED_DEFAULT))
    if EXPECTED_DEFAULT - got:
        problems.append("missing resources: %s" % sorted(EXPECTED_DEFAULT - got))
    return problems


def check_cluster_is_decision_12_10(plan):
    """EMR emr-7.8.0 with applications ["Hadoop"] only; no key pair; auto-termination set; one primary and one core."""
    c = _cluster(plan)
    problems = []
    if c.get("applications") != ["Hadoop"]:
        problems.append("applications are %r, expected exactly ['Hadoop'] (decision 12-10)" % c.get("applications"))
    if c.get("release_label") != "emr-7.8.0":
        problems.append("release_label is %r, expected emr-7.8.0" % c.get("release_label"))
    if c.get("termination_protection") is not False:
        problems.append("termination_protection must be off")
    attrs = as_list(c.get("ec2_attributes"))
    if attrs and attrs[0].get("key_name"):
        problems.append("the cluster must have no EC2 key pair")
    policies = as_list(c.get("auto_termination_policy"))
    if len(policies) != 1 or not (60 <= policies[0].get("idle_timeout", 0) <= 900):
        problems.append("auto_termination_policy idle_timeout must be set and at most 900 s, got %r" % policies)
    for group in ("master_instance_group", "core_instance_group"):
        g = as_list(c.get(group))
        if len(g) != 1 or g[0].get("instance_count") != 1 or g[0].get("instance_type") != "m5.xlarge":
            problems.append("%s must be one m5.xlarge" % group)
    return problems


def check_security_configuration(plan):
    """13C TLS decision: in-transit encryption OFF (disclosed), at-rest encryption ON with SSE-KMS and EBS/local-disk KMS."""
    conf = json.loads(after(plan, PREFIX + "aws_emr_security_configuration.encrypted[0]")["configuration"])["EncryptionConfiguration"]
    problems = []
    if conf.get("EnableInTransitEncryption") is not False:
        problems.append("in-transit encryption must be disabled (13C decision); got %r" % conf.get("EnableInTransitEncryption"))
    if conf.get("EnableAtRestEncryption") is not True:
        problems.append("at-rest encryption must be enabled")
    rest = conf.get("AtRestEncryptionConfiguration", {})
    if rest.get("S3EncryptionConfiguration", {}).get("EncryptionMode") != "SSE-KMS":
        problems.append("S3 encryption must be SSE-KMS")
    local = rest.get("LocalDiskEncryptionConfiguration", {})
    if local.get("EnableEbsEncryption") is not True or local.get("EncryptionKeyProviderType") != "AwsKms":
        problems.append("local-disk and EBS encryption must use AwsKms with EBS encryption enabled")
    if "TLSCertificateConfiguration" in json.dumps(conf):
        problems.append("no TLS certificate configuration may remain when in-transit encryption is off")
    return problems


def check_g3_defaults(plan):
    """G3: zero task nodes and no managed scaling by default."""
    got = managed_changes(plan)
    problems = []
    if any(a.startswith(PREFIX + "aws_emr_instance_group.task") for a in got):
        problems.append("a task instance group exists by default")
    if any(a.startswith(PREFIX + "aws_emr_managed_scaling_policy") for a in got):
        problems.append("a managed scaling policy exists by default")
    return problems


def check_ebs_pinned(plan):
    """gp3 32 GiB, 3000 IOPS, 125 MiB/s, one volume per instance on the primary and core groups (no provisioned surcharge)."""
    c = _cluster(plan)
    problems = []
    want = {"type": "gp3", "size": 32, "iops": 3000, "throughput": 125, "volumes_per_instance": 1}
    for group in ("master_instance_group", "core_instance_group"):
        g = as_list(c.get(group))
        configs = as_list(g[0].get("ebs_config")) if g else []
        if len(configs) != 1 or {k: configs[0].get(k) for k in want} != want:
            problems.append("%s ebs_config differs from %s: %r" % (group, want, configs))
    if c.get("ebs_root_volume_size") != 32:
        problems.append("ebs_root_volume_size must be 32")
    return problems


def check_efs_is_nfs_from_the_emr_group_only(plan):
    """G1 option (ii): one ingress rule on the EFS group, TCP 2049 from the EMR security group only; no CIDR, prefix list or
    other source anywhere in the module; no inline rules; a matching egress rule from the EMR group to the EFS group only."""
    changes = managed_changes(plan)
    problems = []
    ingress = [a for a in changes if "aws_vpc_security_group_ingress_rule" in a or "aws_security_group_rule" in a]
    if ingress != [PREFIX + "aws_vpc_security_group_ingress_rule.efs_from_emr[0]"]:
        problems.append("the module must declare exactly the one efs_from_emr ingress rule, found %s" % ingress)
    for address in ingress:
        a = after(plan, address)
        if (a.get("ip_protocol"), a.get("from_port"), a.get("to_port")) != ("tcp", 2049, 2049):
            problems.append("%s is not TCP 2049" % address)
        if a.get("referenced_security_group_id") != EMR_SG:
            problems.append("%s must reference the EMR node security group, got %r" % (address, a.get("referenced_security_group_id")))
        if a.get("cidr_ipv4") or a.get("cidr_ipv6") or a.get("prefix_list_id"):
            problems.append("%s opens NFS to a CIDR or prefix list" % address)
    for address in changes:
        if address.startswith(PREFIX + "aws_vpc_security_group_egress_rule."):
            a = after(plan, address)
            if (a.get("ip_protocol"), a.get("from_port"), a.get("to_port")) != ("tcp", 2049, 2049) or a.get("cidr_ipv4") or a.get("cidr_ipv6"):
                problems.append("%s must be a TCP 2049 rule to the EFS group, not a CIDR" % address)
        if address.startswith(PREFIX + "aws_security_group.efs"):
            a = after(plan, address)
            if as_list(a.get("ingress")) or as_list(a.get("egress")):
                problems.append("the EFS security group declares inline rules")
    if "0.0.0.0/0" in json.dumps([after(plan, a) for a in changes]):
        problems.append("0.0.0.0/0 appears in a module resource")
    return problems


def check_stack_tag_on_the_cluster(plan):
    """Carried item 17: the stack tag (and the EMR managed-policies tag) is on the cluster so it propagates to nodes and ENIs."""
    tags = _cluster(plan).get("tags") or {}
    problems = []
    if tags.get("scholarchain:stack") != "main-emr":
        problems.append("cluster tag scholarchain:stack is %r, expected 'main-emr'" % tags.get("scholarchain:stack"))
    if tags.get("for-use-with-amazon-emr-managed-policies") != "true":
        problems.append("cluster tag for-use-with-amazon-emr-managed-policies must be 'true'")
    return problems


PLAN_CHECKS = {
    "inventory": check_inventory,
    "cluster_decision_12_10": check_cluster_is_decision_12_10,
    "security_configuration": check_security_configuration,
    "g3_defaults": check_g3_defaults,
    "ebs_pinned": check_ebs_pinned,
    "efs_nfs_from_emr_only": check_efs_is_nfs_from_the_emr_group_only,
    "stack_tag": check_stack_tag_on_the_cluster,
}


# ---------------------------------------------------------------------------------------------------------------
# state checks (mock apply)
# ---------------------------------------------------------------------------------------------------------------

def module_resources(state):
    """address (without the module prefix) -> values for the single child module `emr`."""
    out = {}
    for child in state["root_module"].get("child_modules", []):
        for r in child.get("resources", []):
            out[r["address"]] = r["values"]
    return out


def rendered_spark_defaults(state):
    """The spark-defaults text Terraform hands the bootstrap, decoded from --spark-defaults-b64 of the cluster's bootstrap args,
    plus the sha256 argument."""
    args = module_resources(state)[PREFIX + "aws_emr_cluster.pipeline[0]"]["bootstrap_action"][0]["args"]
    pairs = {args[i]: args[i + 1] for i in range(0, len(args) - 1) if args[i].startswith("--")}
    text = base64.b64decode(pairs["--spark-defaults-b64"]).decode()
    return text, pairs.get("--spark-defaults-sha256"), pairs


def check_spark_settings_equal_the_reviewed_conf(state):
    """The cluster's rendered Spark settings equal scripts/config/spark-12-10.conf exactly (independently parsed), the sha256
    argument is the hash of the rendered text, no JAVA_HOME key is baked in (the bootstrap resolves Java 17 per node), the
    codec list holds no LZO, and G2 shuffle tracking is on."""
    text, sha_arg, _ = rendered_spark_defaults(state)
    got = parse_spark_conf(text)
    want = parse_spark_conf(SPARK_CONF.read_text())
    problems = []
    if got != want:
        problems.append("rendered settings differ from spark-12-10.conf: only-in-module=%s only-in-conf=%s changed=%s" % (
            sorted(set(got) - set(want)), sorted(set(want) - set(got)), sorted(k for k in got if k in want and got[k] != want[k])))
    if sha_arg != hashlib.sha256(text.encode()).hexdigest():
        problems.append("--spark-defaults-sha256 is not the sha256 of the rendered text")
    if "JAVA_HOME" in text:
        problems.append("a JAVA_HOME key is baked into the rendered defaults")
    if "lzo" in got.get("spark.hadoop.io.compression.codecs", "").lower():
        problems.append("the codec list names an LZO codec")
    if got.get("spark.dynamicAllocation.shuffleTracking.enabled") != "true":
        problems.append("shuffle tracking (G2) is not enabled")
    return problems


def check_bootstrap_arguments(state):
    """The bootstrap receives pinned hashes and S3 URIs (G5): runtime hash 789a96..., the job jar and self hashes from tfvars."""
    _, _, pairs = rendered_spark_defaults(state)
    problems = []
    if pairs.get("--runtime-sha256") != "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5":
        problems.append("--runtime-sha256 is not the pinned runtime archive hash")
    for flag, value in (("--self-sha256", "a" * 64), ("--job-jar-sha256", "b" * 64)):
        if pairs.get(flag) != value:
            problems.append("%s is %r, expected the tfvars value" % (flag, pairs.get(flag)))
    for flag in ("--runtime-uri", "--job-jar-uri"):
        if not (pairs.get(flag) or "").startswith("s3://"):
            problems.append("%s is not an S3 URI" % flag)
    return problems


def check_node_policy(state):
    """The instance-role inline policy: EFS client only through this access point; auto-termination only on clusters carrying
    the stack tag; nothing else."""
    values = module_resources(state)[PREFIX + "aws_iam_role_policy.node[0]"]
    statements = policy_statements(values["policy"])
    problems = []
    actions = sorted(a for st in statements for a in as_list(st["Action"]))
    want = sorted(["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite", "elasticmapreduce:GetAutoTerminationPolicy",
                   "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy"])
    if actions != want:
        problems.append("node policy actions are %s, expected %s" % (actions, want))
    for st in statements:
        if "elasticfilesystem:ClientMount" in as_list(st["Action"]):
            if st.get("Condition", {}).get("StringEquals", {}).get("elasticfilesystem:AccessPointArn") != "arn:aws:elasticfilesystem:us-east-2:111122223333:access-point/fsap-0123456789abcdef0":
                problems.append("EFS client access is not tied to the access point")
        else:
            if st.get("Condition", {}).get("StringEquals", {}).get("aws:ResourceTag/scholarchain:stack") != "main-emr":
                problems.append("auto-termination actions are not tied to the stack tag")
        if "*" in as_list(st["Resource"]):
            problems.append("a node policy statement has Resource *")
    return problems


def check_efs_policy_and_mount_target(state):
    """The file system is encrypted, the mount target sits behind exactly the EFS security group, and the file system policy
    denies non-TLS and allows only the instance role, only through the access point."""
    res = module_resources(state)
    problems = []
    fs = res[PREFIX + "aws_efs_file_system.staging[0]"]
    if fs.get("encrypted") is not True:
        problems.append("the staging file system is not encrypted")
    mount = res[PREFIX + "aws_efs_mount_target.staging[0]"]
    if as_list(mount.get("security_groups")) != [res[PREFIX + "aws_security_group.efs[0]"]["id"]]:
        problems.append("the mount target must sit behind exactly the EFS security group")
    statements = policy_statements(res[PREFIX + "aws_efs_file_system_policy.staging[0]"]["policy"])
    deny = [st for st in statements if st["Effect"] == "Deny"]
    allow = [st for st in statements if st["Effect"] == "Allow"]
    if len(deny) != 1 or deny[0].get("Condition", {}).get("Bool", {}).get("aws:SecureTransport") != "false":
        problems.append("the file system policy must deny non-TLS access")
    if len(allow) != 1 or allow[0]["Principal"] != {"AWS": "arn:aws:iam::111122223333:role/emr-ec2"} or \
            allow[0].get("Condition", {}).get("StringEquals", {}).get("elasticfilesystem:AccessPointArn") != "arn:aws:elasticfilesystem:us-east-2:111122223333:access-point/fsap-0123456789abcdef0":
        problems.append("the file system policy must allow only the instance role through the access point")
    return problems


STATE_CHECKS = {
    "spark_settings_equal_conf": check_spark_settings_equal_the_reviewed_conf,
    "bootstrap_arguments": check_bootstrap_arguments,
    "node_policy": check_node_policy,
    "efs_policy_and_mount": check_efs_policy_and_mount_target,
}


def failing_plan_checks(plan):
    return {name: v for name, fn in PLAN_CHECKS.items() if (v := fn(plan))}


def failing_state_checks(state):
    return {name: v for name, fn in STATE_CHECKS.items() if (v := fn(state))}
