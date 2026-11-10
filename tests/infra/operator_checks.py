"""Named invariants for the Phase 14B/14C operator roles and the runtime permissions boundary (replan W5a), hand-derived from the
user's decisions in docs/agent-runs/phase-14/prompt.md ("14C decisions" 2 and "Answers" 1), not from the Terraform that
implements them:

  O1  the roles are OFF by default: no operator role, policy or login policy is planned and the output is null;
  O2  when enabled there are exactly three roles (loader, reader, cleanup), named scholarchain-<env>-operator-<kind>;
  O3  trust: only the one human operator principal, sts:AssumeRole, with aws:MultiFactorAuthPresent = true; no wildcard principal;
  O4  maximum session 14400 s (4 h) on each operator role (the deployer role stays at 3600);
  O5  each role carries the same-device `aws login` policy (sign-in actions only, the localhost public client of this account and
      region, condition signin:OAuthClientId = arn:aws:signin:::devtools/same-device), identical to the deployer's apart from the Sid;
  O6  no operator or deployer policy anywhere mentions aws-marketplace (the Haiku subscription is a human step, no role holds it);
  O7  no Allow statement of an operator policy has a wildcard action (`*`, `svc:*`, `*:*`) or a bare `*` resource, and no IAM
      action other than iam:PassRole (so a role cannot widen its own authority);
  O8  data-plane only: the services used are limited to those the 14C load needs (s3, dynamodb, s3vectors, bedrock, neptune-db, kms,
      plus ecs/ssm/ssmmessages/iam:PassRole for the tunnel and the signin pair); bedrock is InvokeModel on the Titan text embeddings
      v2 foundation model only; S3 object access never covers a whole bucket; DynamoDB never covers `table/*`;
  O9  the runtime permissions boundary allows exactly the four ssmmessages ECS Exec actions (on the only resource form they have)
      and NO neptune-db load or write action.

Each check takes the parsed `terraform show -json` plan of the deployer root (infra_support.ROOTS["deployer14ops"] or ["deployer14"])
and returns a list of problem strings; an empty list means the invariant holds.
"""
import json

from infra_support import after, as_list, managed_changes, policy_statements

ACCOUNT = "111122223333"
REGION = "us-east-2"
ENV = "course"
OPERATOR = "arn:aws:iam::%s:user/example-operator" % ACCOUNT
KINDS = ("cleanup", "loader", "pipeline", "reader")  # the fourth role (pipeline) was added by the G5/G6 gap work
LOGIN_ACTIONS = {"signin:AuthorizeOAuth2Access", "signin:CreateOAuth2Token"}
LOGIN_RESOURCE = "arn:aws:signin:%s:%s:oauth2/public-client/localhost" % (REGION, ACCOUNT)
SAME_DEVICE = "arn:aws:signin:::devtools/same-device"
ALLOWED_SERVICES = {"s3", "dynamodb", "s3vectors", "bedrock", "neptune-db", "kms", "ecs", "ssm", "ssmmessages", "iam", "signin",
                    "elasticmapreduce"}
TITAN = "arn:aws:bedrock:%s::foundation-model/amazon.titan-embed-text-v2:0" % REGION
ECS_EXEC_ACTIONS = {"ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel",
                    "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"}
NEPTUNE_LOAD_WRITE = ("StartLoaderJob", "GetLoaderJobStatus", "ListLoaderJobs", "CancelLoaderJob", "WriteDataViaQuery",
                      "DeleteDataViaQuery", "ResetDatabase")
NEPTUNE_LOAD_WRITE_WORDS = ("Loader", "Write", "Delete", "Reset", "Statistics")


ROLE_PREFIXES = ("aws_iam_role.operator[", "aws_iam_role.operator_pipeline[")
POLICY_PREFIXES = ("aws_iam_role_policy.operator[", "aws_iam_role_policy.operator_pipeline[")
LOGIN_PREFIXES = ("aws_iam_role_policy.operator_login[", "aws_iam_role_policy.operator_pipeline_login[")


def kind_of(name):
    """loader / reader / cleanup / pipeline from a role or inline-policy name scholarchain-<env>-operator-<kind>[-suffix]."""
    return name.split("-operator-")[1].split("-")[0]


def role_changes(plan, prefix=None):
    """address -> planned role attributes of every operator role (the three for_each roles and the pipeline role)."""
    prefixes = (prefix,) if prefix else ROLE_PREFIXES
    return {a: rc["change"]["after"] for a, rc in managed_changes(plan).items() if a.startswith(prefixes)}


def operator_policies(plan):
    """address -> (role kind, parsed document) of the data/tunnel documents of every operator role."""
    out = {}
    for a, rc in managed_changes(plan).items():
        if a.startswith(POLICY_PREFIXES):
            out[a] = (kind_of(rc["change"]["after"]["name"]), json.loads(rc["change"]["after"]["policy"]))
    return out


def policies_of(plan, kind):
    return [doc for _, (k, doc) in operator_policies(plan).items() if k == kind]


def login_policies(plan):
    return {a: json.loads(rc["change"]["after"]["policy"]) for a, rc in managed_changes(plan).items() if a.startswith(LOGIN_PREFIXES)}


def allow_statements(document):
    return [s for s in policy_statements(document) if s.get("Effect") == "Allow"]


def check_off_by_default(plan):
    problems = []
    for a in managed_changes(plan):
        if "operator" in a:
            problems.append("O1 %s is planned although operator_roles_enabled is false" % a)
    outputs = plan.get("planned_values", {}).get("outputs", {})
    if outputs.get("operator_role_arns", {}).get("value") is not None:
        problems.append("O1 operator_role_arns is not null by default")
    return problems


def check_three_roles(plan):
    """O2 (kept under its old name): exactly the four named operator roles."""
    roles = role_changes(plan)
    problems = []
    names = sorted(r["name"] for r in roles.values())
    expected = sorted("scholarchain-%s-operator-%s" % (ENV, k) for k in KINDS)
    if names != expected:
        problems.append("O2 the operator roles are %s, expected %s" % (names, expected))
    return problems


def check_trust(plan):
    problems = []
    for a, r in role_changes(plan).items():
        doc = json.loads(r["assume_role_policy"])
        sts = policy_statements(doc)
        if len(sts) != 1:
            problems.append("O3 %s has %d trust statements, expected 1" % (a, len(sts)))
            continue
        st = sts[0]
        if st.get("Effect") != "Allow" or as_list(st.get("Action")) != ["sts:AssumeRole"]:
            problems.append("O3 %s trust is not Allow sts:AssumeRole" % a)
        if st.get("Principal") != {"AWS": OPERATOR}:
            problems.append("O3 %s trust principal is not exactly the operator" % a)
        if st.get("Condition") != {"Bool": {"aws:MultiFactorAuthPresent": "true"}}:
            problems.append("O3 %s trust does not require MFA (exactly aws:MultiFactorAuthPresent = true)" % a)
    return problems


def check_session(plan):
    return ["O4 %s max_session_duration is %r, expected 14400" % (a, r.get("max_session_duration"))
            for a, r in role_changes(plan).items() if r.get("max_session_duration") != 14400]


def check_login_policy(plan):
    problems = []
    logins = {}
    for a, rc in managed_changes(plan).items():
        if a.startswith(LOGIN_PREFIXES):
            logins[a] = (kind_of(rc["change"]["after"]["name"]), json.loads(rc["change"]["after"]["policy"]))
    kinds = sorted(k for k, _ in logins.values())
    if kinds != list(KINDS):
        problems.append("O5 login policies exist for %s, expected %s" % (kinds, list(KINDS)))
    deployer = [rc["change"]["after"]["policy"] for a, rc in managed_changes(plan).items() if a == "aws_iam_role_policy.login"]
    deployer_statement = json.loads(deployer[0])["Statement"][0] if deployer else None
    for a, (_, doc) in logins.items():
        sts = policy_statements(doc)
        if len(sts) != 1:
            problems.append("O5 %s has %d statements" % (a, len(sts)))
            continue
        st = sts[0]
        if st.get("Effect") != "Allow" or set(as_list(st.get("Action"))) != LOGIN_ACTIONS:
            problems.append("O5 %s actions are not exactly the two sign-in actions" % a)
        if as_list(st.get("Resource")) != [LOGIN_RESOURCE]:
            problems.append("O5 %s resource is not the localhost public client of this account and region" % a)
        if st.get("Condition") != {"StringEquals": {"signin:OAuthClientId": SAME_DEVICE}}:
            problems.append("O5 %s is missing the same-device client condition" % a)
        if deployer_statement is not None:
            same = {k: v for k, v in st.items() if k != "Sid"} == {k: v for k, v in deployer_statement.items() if k != "Sid"}
            if not same:
                problems.append("O5 %s differs from the deployer's login policy beyond the Sid" % a)
    return problems


def _all_policy_texts(plan):
    for a, rc in managed_changes(plan).items():
        after_ = rc["change"]["after"]
        for key in ("policy", "assume_role_policy"):
            if isinstance(after_.get(key), str):
                yield a, after_[key]


def check_no_marketplace(plan):
    return ["O6 %s mentions aws-marketplace" % a for a, text in _all_policy_texts(plan) if "aws-marketplace" in text.lower()]


def check_no_wildcards(plan):
    problems = []
    for a, (_, doc) in operator_policies(plan).items():
        for st in allow_statements(doc):
            for action in as_list(st.get("Action")):
                if "*" in action or "?" in action:
                    problems.append("O7 %s grants wildcard action %s" % (a, action))
                if action.startswith("iam:") and action != "iam:PassRole":
                    problems.append("O7 %s grants %s" % (a, action))
            for resource in as_list(st.get("Resource")):
                if resource in ("*", "arn:aws:*", "arn:*"):
                    problems.append("O7 %s (%s) has a bare wildcard resource" % (a, st.get("Sid")))
    return problems


def check_data_plane_scope(plan):
    problems = []
    for a, (kind, doc) in operator_policies(plan).items():
        for st in allow_statements(doc):
            actions, resources = as_list(st.get("Action")), as_list(st.get("Resource"))
            for action in actions:
                if action.split(":")[0].lower() not in ALLOWED_SERVICES:
                    problems.append("O8 %s uses service %s" % (a, action))
            if any(x.startswith("bedrock:") for x in actions) and (set(actions) != {"bedrock:InvokeModel"} or resources != [TITAN]):
                problems.append("O8 %s bedrock access is not InvokeModel on the Titan v2 foundation model alone" % a)
            if any(x.startswith("s3:") and x not in ("s3:ListBucket", "s3:ListBucketVersions") for x in actions):
                for r in resources:
                    bucket, _, key = (r.split(":::", 1)[1] if r.startswith("arn:aws:s3:::") else "").partition("/")
                    if not bucket or key in ("", "*"):
                        problems.append("O8 %s S3 object access covers a whole bucket or a malformed resource (%s)" % (a, st.get("Sid")))
            if any(x.startswith("dynamodb:") for x in actions):
                for r in resources:
                    if r.endswith(":table/*") or "table/*" in r:
                        problems.append("O8 %s DynamoDB access covers every table (%s)" % (a, st.get("Sid")))
    return problems


def runtime_boundary(plan):
    docs = {a: json.loads(rc["change"]["after"]["policy"]) for a, rc in managed_changes(plan).items()
            if a.startswith("aws_iam_policy.main_boundary_runtime")}
    return docs


def check_runtime_boundary(plan):
    problems = []
    docs = runtime_boundary(plan)
    if len(docs) != 1:
        return ["O9 expected one runtime boundary policy, found %d" % len(docs)]
    doc = next(iter(docs.values()))
    ssm = {a for st in allow_statements(doc) for a in as_list(st.get("Action")) if a.startswith("ssmmessages:")}
    if ssm != ECS_EXEC_ACTIONS:
        problems.append("O9 the runtime boundary allows ssmmessages actions %s, expected exactly %s" % (sorted(ssm), sorted(ECS_EXEC_ACTIONS)))
    for st in allow_statements(doc):
        for action in as_list(st.get("Action")):
            if action.startswith("neptune-db:"):
                name = action.split(":", 1)[1]
                if name in NEPTUNE_LOAD_WRITE or any(w in name for w in NEPTUNE_LOAD_WRITE_WORDS) or name == "*":
                    problems.append("O9 the runtime boundary allows %s" % action)
    return problems


# ---------------------------------------------------------------------------------------------------------------
# Pipeline role (G5/G6): hand-derived from the work order: the role that runs scripts/run-bounded-pipeline.sh --execute and the EMR
# artifact upload. Six EMR actions on the project cluster only (tag conditions), create-only uploads under emr/<run>/, read-only on
# pipeline/<run>/ and the EMR logs, KMS through S3 only, and nothing that could start, end or administer anything else.
# ---------------------------------------------------------------------------------------------------------------
RUN = "run-20261115"
ARTIFACTS = "arn:aws:s3:::scholarchain-%s-%s-artifacts" % (ENV, ACCOUNT)
LOGS = "arn:aws:s3:::scholarchain-%s-%s-logs" % (ENV, ACCOUNT)
RAG = "arn:aws:s3:::scholarchain-%s-%s-rag" % (ENV, ACCOUNT)
EMR_ACTIONS = {"elasticmapreduce:DescribeCluster", "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:ListInstanceGroups",
               "elasticmapreduce:AddJobFlowSteps", "elasticmapreduce:DescribeStep", "elasticmapreduce:CancelSteps"}
EMR_CLUSTERS = "arn:aws:elasticmapreduce:%s:%s:cluster/*" % (REGION, ACCOUNT)
EMR_TAGS = {"aws:ResourceTag/project": "scholarchain", "aws:ResourceTag/environment": ENV, "aws:ResourceTag/scholarchain:stack": "main-emr"}
REGION_CONDITION = {"aws:RequestedRegion": REGION}


def pipeline_statements(plan):
    return [s for doc in policies_of(plan, "pipeline") for s in policy_statements(doc)]


def _actions(statement):
    return as_list(statement.get("Action"))


def _resources(statement):
    return as_list(statement.get("Resource"))


def check_pipeline_role_basics(plan):
    """P1: the role exists once, with MFA trust and a 14,400 s session; the login policy is covered by check_login_policy."""
    problems = []
    roles = {a: r for a, r in role_changes(plan).items() if r["name"].endswith("-operator-pipeline")}
    if len(roles) != 1:
        return ["P1 expected exactly one operator-pipeline role, found %d" % len(roles)]
    role = next(iter(roles.values()))
    if role.get("max_session_duration") != 14400:
        problems.append("P1 the pipeline role session is %r, expected 14400" % role.get("max_session_duration"))
    trust = policy_statements(json.loads(role["assume_role_policy"]))
    if len(trust) != 1 or trust[0].get("Principal") != {"AWS": OPERATOR} or trust[0].get("Condition") != {"Bool": {"aws:MultiFactorAuthPresent": "true"}}:
        problems.append("P1 the pipeline role trust is not exactly the operator with MFA")
    if role.get("permissions_boundary"):
        problems.append("P1 operator roles carry no permissions boundary (they are human roles, not runtime roles)")
    return problems


def check_pipeline_emr(plan):
    """P2: EMR actions exactly the six, on cluster/* only, each statement with the region and the three cluster-tag conditions."""
    problems = []
    seen = set()
    for st in pipeline_statements(plan):
        emr = [a for a in _actions(st) if a.startswith("elasticmapreduce:")]
        if not emr:
            continue
        seen |= set(emr)
        if st["Effect"] != "Allow" or len(emr) != len(_actions(st)):
            problems.append("P2 an EMR statement mixes services or is not an Allow (%s)" % st.get("Sid"))
        if _resources(st) != [EMR_CLUSTERS]:
            problems.append("P2 %s resource is %s, expected only %s" % (st.get("Sid"), _resources(st), EMR_CLUSTERS))
        want = dict(REGION_CONDITION, **EMR_TAGS)
        if st.get("Condition") != {"StringEquals": want}:
            problems.append("P2 %s condition is not exactly the region plus the project/environment/stack tags" % st.get("Sid"))
    if seen != EMR_ACTIONS:
        problems.append("P2 EMR actions are %s, expected exactly %s" % (sorted(seen), sorted(EMR_ACTIONS)))
    return problems


FORBIDDEN_PIPELINE = ("elasticmapreduce:RunJobFlow", "elasticmapreduce:TerminateJobFlows", "elasticmapreduce:SetTerminationProtection",
                      "elasticmapreduce:ModifyCluster", "elasticmapreduce:PutAutoScalingPolicy", "elasticmapreduce:AddTags")


def check_pipeline_forbidden(plan):
    """P3: nothing that starts or ends a cluster, deletes objects, or touches IAM or STS."""
    problems = []
    for st in pipeline_statements(plan):
        for a in _actions(st):
            if a in FORBIDDEN_PIPELINE or a.startswith(("s3:Delete", "iam:", "sts:", "ec2:", "ecs:")) or a == "s3:PutBucketPolicy":
                problems.append("P3 the pipeline role grants %s (%s)" % (a, st.get("Sid")))
    return problems


def check_pipeline_s3(plan):
    """P4/P5: PutObject create-only under artifacts emr/<run>/ only; read-only on artifacts pipeline/<run>/ and logs emr/*; lists
    limited to those prefixes; no other bucket."""
    problems = []
    upload = "%s/emr/%s/*" % (ARTIFACTS, RUN)
    outputs, logs = "%s/pipeline/%s/*" % (ARTIFACTS, RUN), "%s/emr/*" % LOGS
    saw_header_rule = False
    for st in pipeline_statements(plan):
        actions = _actions(st)
        if not any(a.startswith("s3:") for a in actions):
            continue
        sid = st.get("Sid")
        for r in _resources(st):
            if not r.startswith((ARTIFACTS, LOGS)):
                problems.append("P4 %s reaches a bucket other than artifacts and logs: %s" % (sid, r))
        if "s3:PutObject" in actions:
            if _resources(st) != [upload] or actions != ["s3:PutObject"]:
                problems.append("P4 PutObject outside the create-only upload prefix or mixed with other actions (%s)" % sid)
            cond = st.get("Condition", {})
            if cond.get("Null") == {"s3:if-none-match": "false"}:
                saw_header_rule = True
            elif cond.get("Bool") != {"s3:ObjectCreationOperation": "false"}:
                problems.append("P4 PutObject statement %s is neither create-only (Null s3:if-none-match = false) nor the multipart-parts rule" % sid)
            if cond.get("StringEquals") != REGION_CONDITION:
                problems.append("P4 %s lacks the region condition" % sid)
        reads = [r for r in _resources(st) if r in (outputs, logs)]
        if reads and any(a not in ("s3:GetObject", "s3:GetObjectVersion") for a in actions):
            problems.append("P5 %s grants more than read on a read-only prefix: %s" % (sid, actions))
        if "s3:ListBucket" in actions:
            prefixes = as_list(st.get("Condition", {}).get("StringLike", {}).get("s3:prefix"))
            if not prefixes or any(not p.startswith(("emr", "pipeline")) for p in prefixes):
                problems.append("P5 %s lists without a prefix limit or outside emr/ and pipeline/" % sid)
        if any(a.startswith("s3:Put") and a != "s3:PutObject" for a in actions):
            problems.append("P4 %s grants %s" % (sid, actions))
    if not saw_header_rule:
        problems.append("P4 no PutObject statement requires If-None-Match (Null s3:if-none-match = false)")
    granted = {r for st in pipeline_statements(plan) for r in _resources(st)}
    for needed in (upload, outputs, logs):
        if needed not in granted:
            problems.append("P5 %s is not granted" % needed)
    return problems


def check_pipeline_kms(plan):
    """P6: KMS only through S3, with the project key alias, and only the two data-key actions."""
    problems = []
    seen = False
    for st in pipeline_statements(plan):
        kms = [a for a in _actions(st) if a.startswith("kms:")]
        if not kms:
            continue
        seen = True
        if set(kms) != set(_actions(st)) or not set(kms) <= {"kms:GenerateDataKey", "kms:Decrypt"}:
            problems.append("P6 KMS actions are %s" % _actions(st))
        cond = st.get("Condition", {})
        if cond.get("StringEquals", {}).get("kms:ViaService") != "s3.%s.amazonaws.com" % REGION:
            problems.append("P6 kms:ViaService is not exactly S3 (%s)" % cond.get("StringEquals", {}).get("kms:ViaService"))
        if cond.get("ForAnyValue:StringEquals", {}).get("kms:ResourceAliases") != "alias/scholarchain-%s-data" % ENV:
            problems.append("P6 the project key alias condition is missing")
    if not seen:
        problems.append("P6 no KMS statement (uploads to SSE-KMS buckets would fail)")
    return problems


def check_pipeline_services(plan):
    """P7: only elasticmapreduce, s3 and kms."""
    used = {a.split(":")[0] for st in pipeline_statements(plan) for a in _actions(st)}
    return ["P7 the pipeline role uses services %s" % sorted(used - {"elasticmapreduce", "s3", "kms"})] if used - {"elasticmapreduce", "s3", "kms"} else []


def check_loader_runtime_artifact(plan):
    """L1: the loader writes runtime artifacts to rag runtime-artifacts/<run>/ create-only, can read them back, and can never delete."""
    problems = []
    prefix = "%s/runtime-artifacts/%s/*" % (RAG, RUN)
    statements = [s for doc in policies_of(plan, "loader") for s in policy_statements(doc)]
    puts = [s for s in statements if "s3:PutObject" in _actions(s) and prefix in _resources(s)]
    if len(puts) != 1:
        problems.append("L1 expected exactly one PutObject statement on %s, found %d" % (prefix, len(puts)))
    else:
        st = puts[0]
        if _actions(st) != ["s3:PutObject"] or _resources(st) != [prefix]:
            problems.append("L1 the runtime-artifact write statement is not PutObject alone on that prefix")
        if st.get("Condition", {}).get("Null") != {"s3:if-none-match": "false"}:
            problems.append("L1 the runtime-artifact write is not create-only (Null s3:if-none-match = false)")
    if not [s for s in statements if "s3:GetObject" in _actions(s) and prefix in _resources(s)]:
        problems.append("L1 no read-back of the runtime artifacts")
    for st in statements:
        for a in _actions(st):
            if a.startswith("s3:Delete"):
                problems.append("L1 the loader grants %s (%s)" % (a, st.get("Sid")))
        if prefix in _resources(st) and st not in puts and any(a in ("s3:PutObject", "s3:AbortMultipartUpload") for a in _actions(st)):
            problems.append("L1 another statement writes or multiparts on the runtime-artifact prefix (%s)" % st.get("Sid"))
        if st.get("Effect") == "Allow" and "s3:PutObject" in _actions(st) and prefix not in _resources(st):
            if any(r.startswith(RAG + "/runtime-artifacts") for r in _resources(st)):
                problems.append("L1 an unconditional write reaches runtime-artifacts (%s)" % st.get("Sid"))
    return problems


ENABLED_CHECKS = (check_pipeline_role_basics, check_pipeline_emr, check_pipeline_forbidden, check_pipeline_s3, check_pipeline_kms,
                  check_pipeline_services, check_loader_runtime_artifact, check_three_roles, check_trust, check_session, check_login_policy, check_no_marketplace, check_no_wildcards,
                  check_data_plane_scope, check_runtime_boundary)


def failing(plan, checks=ENABLED_CHECKS):
    """The checks that report a problem: {check name: [problems]}."""
    return {c.__name__: p for c in checks for p in [c(plan)] if p}
