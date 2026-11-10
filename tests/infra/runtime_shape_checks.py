"""Support for the Phase 14B replan "cost shape" tests (test-engineer, tests/infra/**).

Requirement under test (user decisions of 2026-11-08, replan under the USD 25 course cap; docs/agent-runs/phase-14/prompt.md
"Subphase 14B - replan", deliverable "shape reductions"):
  * `container_insights_enabled = false` -> the ECS cluster setting `containerInsights` is "disabled" and the embedding-worker
    backlog target-tracking policy (which divides by the paid ECS/ContainerInsights RunningTaskCount metric) is NOT created,
    while the three HTTP CPU target-tracking policies remain and track the predefined, free `ECSServiceAverageCPUUtilization`
    metric (namespace AWS/ECS). With it true (the committed default) the cluster setting is "enabled" and the backlog policy exists.
  * `dashboard_enabled = false` -> no CloudWatch dashboard; the alarms and log groups stay.
  * `service_capacity` accepts the smallest Fargate shape 256/1024 for all four services and refuses 256/512 and 256/4096; the
    COMMITTED defaults are unchanged (512 CPU / 1024 MiB, min 1, max 2; the worker max 4).

How: a SCRATCH root that calls a scratch COPY of the real module (modules/runtime or modules/observability) with synthetic
inputs and is planned offline with the real provider (no network; same harness as the EMR module wrapper in infra_support.py),
and a providerless scratch root that holds the real `variable` blocks extracted from the root's variable file (so the real
validation expressions and defaults are evaluated by Terraform itself). Nothing is read from or written to the repository.
"""
import json
import re
import shutil
import tempfile
from pathlib import Path

import hcl_text
from infra_support import (COPY_IGNORE, OFFLINE_PROVIDER_OVERRIDE, REPO, TfTree, require_toolchain, run, tf_env, TF_BIN,
                           managed_changes, after)

SERVICES = ("query-api", "graph-service", "semantic-service", "embedding-worker")
HTTP_SERVICES = ("query-api", "graph-service", "semantic-service")
ACCT = "111122223333"  # synthetic
ROOT_VARIABLE_FILES = ("phase12b-variables.tf", "variables.tf")

WRAPPER_VERSIONS = '''terraform {
  required_version = "= 1.13.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.44.0"
    }
  }
}
'''

TAGS = {"course": "CS441", "project": "ScholarChain", "environment": "course", "owner": "example-owner"}


def capacity(cpu=256, memory=1024, workers_max=2):
    return {s: {"cpu": cpu, "memory": memory, "min": 1, "max": (workers_max if s == "embedding-worker" else 2)} for s in SERVICES}


# Synthetic inputs by variable name. A required variable that is not listed here is filled from its declared type, so a variable that a
# later change adds does not break the wrapper; the specific values below are the ones whose KEYS the module indexes.
RUNTIME_VALUES = {
    "name_prefix": "scholarchain-course",
    "kms_key_arn": "arn:aws:kms:us-east-2:%s:key/11111111-2222-3333-4444-555555555555" % ACCT,
    "cleanup_mode": False, "tags": TAGS, "enabled": True, "composition_verified": False, "image_revision": "rev1",
    "aws_region": "us-east-2", "vpc_id": "vpc-0123456789abcdef0",
    "application_subnets": ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"],
    "public_subnets": ["subnet-0123456789abcdef2", "subnet-0123456789abcdef3"],
    "security_groups": dict({s: "sg-0123456789abcde%d" % i for i, s in enumerate(SERVICES)}, alb="sg-0123456789abcdf0"),
    "task_roles": {s: "arn:aws:iam::%s:role/scholarchain-course-%s-task" % (ACCT, s) for s in SERVICES},
    "execution_roles": {s: "arn:aws:iam::%s:role/scholarchain-course-%s-exec" % (ACCT, s) for s in SERVICES},
    "service_secret_bindings": {},
    "capacity": capacity(512, 1024, 4), "cpu_target": 60, "container_insights_enabled": True, "backlog_target": 10, "service_port": 8080,
    "certificate_arn": "arn:aws:acm:us-east-2:%s:certificate/11111111-2222-3333-4444-555555555555" % ACCT,
    "queue_name": "scholarchain-course-embedding", "queue_url": "https://sqs.us-east-2.amazonaws.com/%s/q" % ACCT,
    "dlq_url": "https://sqs.us-east-2.amazonaws.com/%s/dlq" % ACCT,
    "table_names": {t: "scholarchain-course-" + t for t in (
        "RunLedger", "EntityLinkCache", "QuerySession", "EvidenceBundle", "ArtifactRegistry", "ResearcherMetricCache")},
    "neptune_endpoint": "https://graph.cluster-ro-example.us-east-2.neptune.amazonaws.com:8182",
    "vector_bucket": "scholarchain-course-vectors",
    "log_groups": {s: "/scholarchain-course/" + s for s in SERVICES},
    "rag_bucket": "scholarchain-course-%s-rag" % ACCT, "graph_bucket": "scholarchain-course-%s-graph" % ACCT,
    "embedding_model_id": "amazon.titan-embed-text-v2:0", "vector_dimension": 256, "vector_metric": "cosine",
    "query_session_index": "session-index", "queue_visibility_seconds": 120, "queue_wait_seconds": 10,
    "semantic_index": "researcher-profile-v1", "embedding_text_prefix": "embedding-text", "evidence_index_prefix": "evidence",
    "audit_prefix": "audit",
}
OBSERVABILITY_VALUES = {
    "name_prefix": "scholarchain-course", "aws_region": "us-east-2", "retention_days": 14, "notification_arns": [],
    "application_namespace": "ScholarChain", "api_error_percent": 5, "latency_seconds": 2, "queue_age_seconds": 300,
    "queue_name": "scholarchain-course-embedding", "table_names": RUNTIME_VALUES["table_names"], "neptune_identifier": None,
    "emr_cluster_id": None, "tags": TAGS, "workflow_arn": None,
}


def required_variables(variables_text):
    """{name: declared type text} for every variable block that has no `default` (comment-stripped, brace-matched)."""
    clean = hcl_text.strip_comments(variables_text)
    out = {}
    for m in re.finditer(r'^[ \t]*variable[ \t]+"([A-Za-z0-9_]+)"[ \t]*\{', clean, re.M):
        body = clean[m.end():hcl_text.matching_brace(clean, m.end() - 1)]
        depth_zero = _top_level(body)
        if not re.search(r"^[ \t]*default[ \t]*=", depth_zero, re.M):
            t = re.search(r"^[ \t]*type[ \t]*=[ \t]*(.+)$", depth_zero, re.M)
            out[m.group(1)] = t.group(1).strip() if t else "any"
    return out


def _top_level(body):
    """The body with every nested { ... } (validation blocks, object types) blanked, so `default` inside them is not seen."""
    out, depth = [], 0
    for ch in body:
        if ch == "{":
            depth += 1
            out.append(" ")
        elif ch == "}":
            depth -= 1
            out.append(" ")
        else:
            out.append(ch if depth == 0 or ch == "\n" else " ")
    return "".join(out)


def fallback_for(type_text):
    t = type_text.strip()
    if t.startswith("bool"):
        return False
    if t.startswith("number"):
        return 1
    if t.startswith(("map", "object")):
        return {}
    if t.startswith(("list", "set", "tuple")):
        return []
    return "synthetic"


def hcl_value(value):
    """An HCL expression that evaluates to `value` (JSON round trip through jsondecode; no interpolation is possible)."""
    text = json.dumps(value)
    assert "${" not in text and "%{" not in text
    return "jsondecode(%s)" % json.dumps(text)


class ModuleTree(TfTree):
    """A scratch ROOT that calls a scratch COPY of infra/terraform/modules/<module> with synthetic inputs (overridable per
    instance), planned offline with the real provider. Providers and the lock file come from the main root's terraform-gate init."""

    def __init__(self, module, values, overrides=None, snapshot=None):
        self.kind = "module-" + module
        self.module = module
        self.spec = {"rel": "wrapper", "extras": [], "vars": {}, "snapshot": snapshot}
        self.providers = require_toolchain("main")
        self.base = Path(tempfile.mkdtemp(prefix="sc-infra-shape-"))
        self.data_dir = self.base / "tfdata"
        self.data_dir.mkdir()
        self.root = self.base / "wrapper"
        self.root.mkdir()
        shutil.copytree(REPO / "infra/terraform/modules" / module, self.root / "modules" / module, ignore=COPY_IGNORE)
        shutil.copyfile(REPO / "infra/terraform/.terraform.lock.hcl", self.root / ".terraform.lock.hcl")
        required = required_variables((self.root / "modules" / module / "variables.tf").read_text())
        self.values = {name: values.get(name, fallback_for(kind)) for name, kind in required.items()}
        self.values.update({k: v for k, v in (overrides or {}).items()})
        self.unlisted = sorted(name for name in required if name not in values)  # filled from the type (reported, not hidden)
        lines = ['provider "aws" {', '  region = "us-east-2"', "}", "", 'module "m" {', '  source = "./modules/%s"' % module]
        lines += ["  %s = %s" % (k, hcl_value(v)) for k, v in sorted(self.values.items())]
        lines += ["}", ""]
        (self.root / "versions.tf").write_text(WRAPPER_VERSIONS)
        (self.root / "main.tf").write_text("\n".join(lines))
        (self.root / "zz_offline_override.tf").write_text(OFFLINE_PROVIDER_OVERRIDE)
        self._plan = None
        self._state = None
        self._initialised = False

    def planned(self):
        """address (without the leading `module.m.`) -> resource_change.change.after of the planned managed resources."""
        return {a[len("module.m."):]: rc["change"]["after"] for a, rc in managed_changes(self.plan_json()).items()}


class VariablesTree:
    """A providerless scratch root that holds the real `variable` blocks (by name) of the main root's variable files, one output per
    variable, so Terraform itself evaluates the real defaults and validation expressions."""

    def __init__(self, names):
        self.base = Path(tempfile.mkdtemp(prefix="sc-infra-vars-"))
        self.data_dir = self.base / "tfdata"
        self.data_dir.mkdir()
        sources = {}
        for name in ROOT_VARIABLE_FILES:
            sources[name] = hcl_text.strip_comments((REPO / "infra/terraform" / name).read_text())
        parts = []
        for var in names:
            found = None
            for text in sources.values():
                m = re.search(r'^[ \t]*variable[ \t]+"%s"[ \t]*\{' % re.escape(var), text, re.M)
                if m:
                    found = text[m.start():hcl_text.matching_brace(text, m.end() - 1) + 1]
                    break
            if found is None:
                raise AssertionError("variable %r is not declared in the root's variable files (update the test)" % var)
            parts.append(found)
            parts.append('output "%s" {\n  value = var.%s\n}\n' % (var, var))
        (self.base / "main.tf").write_text("\n".join(parts))
        self.names = list(names)

    def close(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def plan(self, **values):
        """Run `terraform plan` with JSON var values; returns (returncode, stdout+stderr, outputs dict or None)."""
        args = []
        for k, v in values.items():
            args += ["-var", "%s=%s" % (k, json.dumps(v))]
        out = self.base / "p.tfplan"
        done = run([TF_BIN, "plan", "-no-color", "-input=false", "-out=" + str(out)] + args, self.base, tf_env(self.data_dir))
        text = done.stdout + done.stderr
        if done.returncode != 0:
            return done.returncode, text, None
        shown = run([TF_BIN, "show", "-json", str(out)], self.base, tf_env(self.data_dir))
        outputs = {k: v.get("value") for k, v in json.loads(shown.stdout).get("planned_values", {}).get("outputs", {}).items()}
        return 0, text, outputs


# ---- identity module wrapper (G-MAIN: the query-api role and the rag read prefixes) ----
BUCKETS = ("raw", "curated", "graph", "rag", "artifacts", "logs", "reports")
TABLES = ("RunLedger", "EntityLinkCache", "QuerySession", "EvidenceBundle", "ArtifactRegistry", "ResearcherMetricCache")
IDENTITY_VALUES = {
    "name_prefix": "scholarchain-course", "aws_region": "us-east-2", "aws_account_id": ACCT,
    "deployment_trusted_principal_arn": "arn:aws:iam::%s:role/example-architect" % ACCT, "kms_deletion_window_days": 7,
    "bucket_arns": {b: "arn:aws:s3:::scholarchain-course-%s-%s" % (ACCT, b) for b in BUCKETS},
    "table_arns": {t: "arn:aws:dynamodb:us-east-2:%s:table/scholarchain-course-%s" % (ACCT, t) for t in TABLES},
    "query_session_index_arn": "arn:aws:dynamodb:us-east-2:%s:table/scholarchain-course-QuerySession/index/x" % ACCT,
    "queue_arn": "arn:aws:sqs:us-east-2:%s:q" % ACCT, "dead_letter_queue_arn": "arn:aws:sqs:us-east-2:%s:dlq" % ACCT,
    "repository_arns": {s: "arn:aws:ecr:us-east-2:%s:repository/scholarchain-course/%s" % (ACCT, s) for s in SERVICES},
    "service_secret_arns": {s: ["arn:aws:secretsmanager:us-east-2:%s:secret:synthetic-%s-AbCdEf" % (ACCT, s)] for s in SERVICES},
    "tags": TAGS, "emr_output_prefixes": {}, "enable_emr": False, "emr_service_policy_json": None,
    "neptune_data_arn": "arn:aws:neptune-db:us-east-2:%s:cluster-ABCDEFGHIJ/*" % ACCT, "vector_index_arns": {},
    "embedding_model_id": "amazon.titan-embed-text-v2:0", "synthesis_model_id": "anthropic.claude-synthetic-test-v1:0",
    "rag_prefixes": ["evidence", "audit", "embedding-text", "runtime-artifacts"],
}
