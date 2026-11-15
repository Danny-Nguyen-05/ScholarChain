"""Phase 14B repair round 3 (Anthropic API for synthesis, Voyage AI for embeddings), the infrastructure side, written independently by the
test-engineer from the shared contract in docs/agent-runs/phase-14/prompt.md ("Repair round 3 work order") and the instructor ruling, not
from the Terraform sources. Nothing is applied and no AWS, Anthropic or Voyage call is made: plans use the real AWS provider with fake
credentials and a closed proxy; module checks use mock_provider applies (infra_support, runtime_shape_checks). All identifiers are
synthetic.

Expectations, each hand-derived from the contract:
  * a provider API key never enters Terraform: no secret version, no secret string or binary, no data source that reads a secret, no
    variable or output that could carry a key, and no key-shaped token anywhere in the repository text; a sentinel key placed in the
    process environment never reaches a plan;
  * two empty Secrets Manager containers scholarchain-<env>/anthropic-api-key and scholarchain-<env>/voyage-api-key, each created ONLY when
    its provider (synthesis anthropic, embedding voyage) is selected, with recovery window 0 and the AWS-managed key;
  * the execution role of a service may read only the ARN pattern of the secret that service needs (query-api: Anthropic; semantic-service
    and embedding-worker: Voyage; graph-service: none), never a wildcard and never the other provider's secret;
  * no Marketplace action on any role; Bedrock invoke grants only when a provider is bedrock (task roles, runtime boundary, operator loader);
  * ECS injects the keys through `secrets` (never `environment`), and only in the aws service mode.
"""
import fnmatch
import json
import os
import re
import subprocess
import unittest

import hcl_text
import main_root_shape as M
import phase14_checks as P
import runtime_shape_checks as R
from infra_support import REPO, TfTree, managed_changes, policy_statements

TF_ROOT = REPO / "infra" / "terraform"
ACCOUNT = M.ACCT
REGION = M.REGION
SENTINEL_ANTHROPIC = "sk-" + "ant-" + "SENTINEL" + "x9Qz" * 8
SENTINEL_VOYAGE = "pa-" + "SENTINEL" + "k7Lm" * 10
ANTHROPIC_NAME = "scholarchain-course/anthropic-api-key"
VOYAGE_NAME = "scholarchain-course/voyage-api-key"
ANTHROPIC_PATTERN = "arn:aws:secretsmanager:%s:%s:secret:%s-??????" % (REGION, ACCOUNT, ANTHROPIC_NAME)
VOYAGE_PATTERN = "arn:aws:secretsmanager:%s:%s:secret:%s-??????" % (REGION, ACCOUNT, VOYAGE_NAME)
ANTHROPIC_REAL = "arn:aws:secretsmanager:%s:%s:secret:%s-AbC123" % (REGION, ACCOUNT, ANTHROPIC_NAME)
VOYAGE_REAL = "arn:aws:secretsmanager:%s:%s:secret:%s-XyZ789" % (REGION, ACCOUNT, VOYAGE_NAME)
OWN = {"query-api": ANTHROPIC_PATTERN, "semantic-service": VOYAGE_PATTERN, "embedding-worker": VOYAGE_PATTERN}
BEDROCK_BOTH = {"synthesis_provider": "bedrock", "embedding_provider": "bedrock", "synthesis_model_id": "anthropic.claude-synthetic-test-v1:0"}


def terraform_files(*suffixes):
    out = []
    for dirpath, dirnames, filenames in os.walk(TF_ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".terraform", "__pycache__")]
        for name in filenames:
            if name.endswith(suffixes):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def code_of(path):
    text = open(path, encoding="utf-8").read()
    return hcl_text.strip_comments(text) if path.endswith((".tf", ".hcl")) else text


def allows(policy, action, resource):
    """IAM matching for the two wildcards used here (`*` and `?`), over Allow statements only."""
    for st in policy_statements(policy):
        if st.get("Effect") != "Allow":
            continue
        actions = st["Action"] if isinstance(st["Action"], list) else [st["Action"]]
        resources = st["Resource"] if isinstance(st["Resource"], list) else [st["Resource"]]
        if any(fnmatch.fnmatchcase(action, a) for a in actions) and any(fnmatch.fnmatchcase(resource, r) for r in resources):
            return True
    return False


def actions_of(policy):
    return {a for st in policy_statements(policy) for a in (st["Action"] if isinstance(st["Action"], list) else [st["Action"]])}


class KeysNeverEnterTerraform(unittest.TestCase):
    """Static and repository-wide guards (no terraform run)."""

    def test_no_secret_version_secret_string_or_secret_reading_data_source_in_any_terraform_code(self):
        forbidden = ("aws_secretsmanager_secret_version", "secret_string", "secret_binary", 'data "aws_secretsmanager')
        found = []
        # Configuration only: the *.tftest.hcl files legitimately NAME these tokens in assertions that they are absent.
        for path in terraform_files(".tf", ".tftpl"):
            text = code_of(path)
            found += ["%s: %s" % (os.path.relpath(path, REPO), token) for token in forbidden if token in text]
        self.assertEqual(found, [], "a key value must never be written or read by Terraform")

    def test_no_variable_or_output_can_carry_a_provider_key(self):
        pattern = re.compile(r"(?i)api_?key|secret_?string|secret_?value|key_?value|anthropic_?key|voyage_?key|bearer|password")
        found = []
        for path in terraform_files(".tf"):
            text = code_of(path)
            for kind in ("variable", "output"):
                for m in re.finditer(r'^[ \t]*%s[ \t]+"([^"]+)"' % kind, text, re.M):
                    if pattern.search(m.group(1)):
                        found.append("%s %s in %s" % (kind, m.group(1), os.path.relpath(path, REPO)))
        self.assertEqual(found, [])

    def test_no_marketplace_action_in_any_terraform_code_or_boundary_template(self):
        found = [os.path.relpath(p, REPO) for p in terraform_files(".tf", ".tftpl") if "marketplace" in code_of(p).lower()]
        self.assertEqual(found, [], "no role of any root may hold an aws-marketplace permission")

    def test_no_key_shaped_token_anywhere_in_the_repository_text(self):
        """Anthropic keys start sk-ant- and Voyage keys start pa-; a long token after either prefix is a leaked key (this file builds its
        sentinels from pieces so it holds no such literal). Evidence and docs are included; build output and .git are not."""
        listing = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=str(REPO), capture_output=True, check=True).stdout
        anthropic = re.compile(r"(?<![A-Za-z0-9_-])sk-ant-[A-Za-z0-9_-]{20,}")
        voyage = re.compile(r"(?<![A-Za-z0-9_-])pa-[A-Za-z0-9_-]{30,}")
        placeholder = re.compile(r"(?i)synthetic|placeholder|fake|sentinel|example|dummy|canary|leaky|secret-value")
        findings = []
        for raw in listing.split(b"\0"):
            if not raw:
                continue
            path = raw.decode("utf-8", "replace")
            full = REPO / path
            if not full.is_file() or full.stat().st_size > 2_000_000 or "/target/" in "/" + path:
                continue
            try:
                text = full.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(text.splitlines(), 1):
                tokens = [m.group(0) for m in anthropic.finditer(line)] + [m.group(0) for m in voyage.finditer(line)]
                # A token that says so (synthetic, placeholder, fake, sentinel, example, dummy, leaky) is a test double, never a real key.
                if any(not placeholder.search(t) for t in tokens):
                    findings.append("%s:%d" % (path, number))  # path and line only: the match is never printed
        self.assertEqual(findings, [])


class RootPlans(unittest.TestCase):
    """The main root planned offline with each provider combination (real provider, fake credentials, closed proxy)."""

    @classmethod
    def setUpClass(cls):
        saved = {k: os.environ.get(k) for k in ("SCHOLARCHAIN_ANTHROPIC_API_KEY", "SCHOLARCHAIN_VOYAGE_API_KEY")}
        os.environ["SCHOLARCHAIN_ANTHROPIC_API_KEY"] = SENTINEL_ANTHROPIC
        os.environ["SCHOLARCHAIN_VOYAGE_API_KEY"] = SENTINEL_VOYAGE
        cls.mp = M.MainPlans()
        cls.addClassCleanup(cls.mp.close)

        def restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        cls.addClassCleanup(restore)
        cls.default = cls.mp.plan()
        cls.bedrock = cls.mp.plan(**BEDROCK_BOTH)
        cls.anthropic_only = cls.mp.plan(embedding_provider="bedrock")
        cls.voyage_only = cls.mp.plan(synthesis_provider="bedrock", synthesis_model_id="anthropic.claude-synthetic-test-v1:0")

    @staticmethod
    def secret_names(plan):
        return {a: rc["change"]["after"]["name"] for a, rc in M.resources(plan, "aws_secretsmanager_secret").items()}

    @staticmethod
    def controls(plan):
        return plan["planned_values"]["outputs"]["provider_controls"]["value"]

    def test_defaults_plan_both_containers_with_the_hand_derived_names(self):
        names = self.secret_names(self.default)
        self.assertEqual(sorted(names.values()), [ANTHROPIC_NAME, VOYAGE_NAME])
        self.assertEqual(len(names), 2)

    def test_each_container_is_empty_force_deleted_and_uses_the_aws_managed_key(self):
        for address, rc in M.resources(self.default, "aws_secretsmanager_secret").items():
            after = rc["change"]["after"]
            with self.subTest(address=address):
                self.assertEqual(after["recovery_window_in_days"], 0, "force delete without a recovery window")
                self.assertIsNone(after.get("kms_key_id"), "the AWS-managed key aws/secretsmanager: no customer key")
                self.assertEqual(after["tags"]["project"], "scholarchain")
                self.assertNotIn("secret_string", after)
                self.assertNotIn("policy", {k for k, v in after.items() if v})

    def test_no_plan_creates_a_secret_version_or_reads_a_secret(self):
        for label, plan in (("default", self.default), ("bedrock", self.bedrock), ("anthropic-only", self.anthropic_only), ("voyage-only", self.voyage_only)):
            with self.subTest(plan=label):
                self.assertEqual([a for a, rc in managed_changes_all(plan) if rc["type"] in ("aws_secretsmanager_secret_version", "aws_secretsmanager_secret_rotation", "aws_secretsmanager_secret_policy")], [])
                self.assertEqual([rc["address"] for rc in plan.get("resource_changes", []) if rc.get("mode") == "data"], [])
                self.assertNotIn("secret_string", json.dumps(plan))

    def test_a_sentinel_key_in_the_environment_never_reaches_a_plan(self):
        for label, plan in (("default", self.default), ("bedrock", self.bedrock), ("anthropic-only", self.anthropic_only), ("voyage-only", self.voyage_only)):
            text = json.dumps(plan)
            with self.subTest(plan=label):
                self.assertNotIn(SENTINEL_ANTHROPIC, text)
                self.assertNotIn(SENTINEL_VOYAGE, text)
                self.assertNotIn("SENTINEL", text)

    def test_a_refused_plan_does_not_echo_a_sentinel_either(self):
        done = self.mp.attempt(synthesis_model_id="anthropic.claude-synthetic-test-v1:0")  # anthropic provider (default) fixes the model
        text = done.stdout + done.stderr
        self.assertNotEqual(done.returncode, 0, text[-800:])
        self.assertNotIn("SENTINEL", text)

    def test_with_both_bedrock_providers_no_secret_exists_and_no_pattern_is_passed(self):
        self.assertEqual(self.secret_names(self.bedrock), {})
        controls = self.controls(self.bedrock)
        self.assertEqual(controls["secrets"], {})
        self.assertEqual(controls["iam_arn_patterns"], {"query-api": [], "graph-service": [], "semantic-service": [], "embedding-worker": []})

    def test_synthesis_anthropic_with_embedding_bedrock_creates_only_the_anthropic_secret(self):
        self.assertEqual(sorted(self.secret_names(self.anthropic_only).values()), [ANTHROPIC_NAME])
        patterns = self.controls(self.anthropic_only)["iam_arn_patterns"]
        self.assertEqual(patterns, {"query-api": [ANTHROPIC_PATTERN], "graph-service": [], "semantic-service": [], "embedding-worker": []})

    def test_synthesis_bedrock_with_embedding_voyage_creates_only_the_voyage_secret(self):
        self.assertEqual(sorted(self.secret_names(self.voyage_only).values()), [VOYAGE_NAME])
        patterns = self.controls(self.voyage_only)["iam_arn_patterns"]
        self.assertEqual(patterns, {"query-api": [], "graph-service": [], "semantic-service": [VOYAGE_PATTERN], "embedding-worker": [VOYAGE_PATTERN]})

    def test_the_default_patterns_name_only_each_services_own_secret(self):
        patterns = self.controls(self.default)["iam_arn_patterns"]
        self.assertEqual(patterns, {"query-api": [ANTHROPIC_PATTERN], "graph-service": [], "semantic-service": [VOYAGE_PATTERN], "embedding-worker": [VOYAGE_PATTERN]})
        for service, listed in patterns.items():
            for pattern in listed:
                self.assertNotIn("*", pattern.replace("??????", ""), service)

    def test_the_bedrock_identifiers_exist_only_for_a_bedrock_purpose(self):
        d, b, a, v = (self.controls(p) for p in (self.default, self.bedrock, self.anthropic_only, self.voyage_only))
        self.assertEqual((d["bedrock_synthesis_model"], d["bedrock_embedding_model"]), (None, None))
        self.assertEqual((d["synthesis_model"], d["embedding_model"], d["embedding_model_version"], d["vector_dimension"]), ("claude-haiku-5-5", "voyage-4-lite", "voyage-4-lite", 256))
        self.assertEqual((b["bedrock_synthesis_model"], b["bedrock_embedding_model"]), ("anthropic.claude-synthetic-test-v1:0", "amazon.titan-embed-text-v2:0"))
        self.assertEqual((a["bedrock_synthesis_model"], a["bedrock_embedding_model"]), (None, "amazon.titan-embed-text-v2:0"))
        self.assertEqual((v["bedrock_synthesis_model"], v["bedrock_embedding_model"]), ("anthropic.claude-synthetic-test-v1:0", None))

    def test_the_provider_is_refused_when_it_is_unknown_or_the_bedrock_inputs_contradict_it(self):
        cases = {
            "unknown synthesis provider": dict(synthesis_provider="openai"),
            "unknown embedding provider": dict(embedding_provider="cohere"),
            "anthropic with a bedrock model id": dict(synthesis_model_id="anthropic.claude-synthetic-test-v1:0"),
            "voyage with another version tag": dict(embedding_model_version="titan-v2"),
            "voyage with another dimension": dict(vector_dimension=1024),
        }
        for label, variables in cases.items():
            with self.subTest(case=label):
                done = self.mp.attempt(**variables)
                self.assertNotEqual(done.returncode, 0, "%s was accepted:\n%s" % (label, (done.stdout + done.stderr)[-600:]))


def managed_changes_all(plan):
    return [(rc["address"], rc) for rc in plan.get("resource_changes", [])]


class ExecutionRolesReadOnlyTheirOwnSecret(unittest.TestCase):
    """modules/identity in a mock apply (the IAM policy documents embed the key ARN, which an offline plan leaves unknown)."""

    @classmethod
    def setUpClass(cls):
        cls.docs = cls.render({"provider_secret_arns": {s: [p] for s, p in OWN.items()} | {"graph-service": []}, "service_secret_arns": {},
                               "embedding_model_id": None, "synthesis_model_id": None})
        cls.with_bedrock = cls.render({"provider_secret_arns": {}, "service_secret_arns": {}})  # IDENTITY_VALUES carry both Bedrock model ids

    @staticmethod
    def render(overrides):
        values = dict(R.IDENTITY_VALUES)
        tree = R.ModuleTree("identity", values, overrides, snapshot="identity_module_snapshot.tftest.hcl")
        try:
            state = tree.state_json()
        finally:
            tree.close()
        return {r["address"][len("module.m."):]: json.loads(r["values"]["policy"])
                for r in state["root_module"]["child_modules"][0]["resources"] if r["type"] == "aws_iam_role_policy" and "policy" in r["values"]}

    def execution(self, service, docs=None):
        return (docs or self.docs)['aws_iam_role_policy.execution["%s"]' % service]

    def test_each_execution_role_may_read_its_own_secret_and_not_the_other(self):
        for service, own in OWN.items():
            other = VOYAGE_REAL if own == ANTHROPIC_PATTERN else ANTHROPIC_REAL
            mine = ANTHROPIC_REAL if own == ANTHROPIC_PATTERN else VOYAGE_REAL
            with self.subTest(service=service):
                self.assertTrue(allows(self.execution(service), "secretsmanager:GetSecretValue", mine))
                self.assertFalse(allows(self.execution(service), "secretsmanager:GetSecretValue", other))

    def test_the_graph_service_execution_role_reads_neither_provider_secret(self):
        for real in (ANTHROPIC_REAL, VOYAGE_REAL):
            self.assertFalse(allows(self.execution("graph-service"), "secretsmanager:GetSecretValue", real))
        self.assertEqual([a for a in actions_of(self.execution("graph-service")) if a.startswith("secretsmanager:")], [])

    def test_the_grant_is_the_exact_pattern_with_one_action_and_no_wildcard_resource(self):
        for service, own in OWN.items():
            statements = [st for st in policy_statements(self.execution(service)) if st.get("Sid") == "InjectProviderApiKey"]
            with self.subTest(service=service):
                self.assertEqual(len(statements), 1)
                self.assertEqual(statements[0]["Effect"], "Allow")
                self.assertEqual(statements[0]["Action"], ["secretsmanager:GetSecretValue"])
                self.assertEqual(statements[0]["Resource"], [own])

    def test_lookalike_names_and_other_secrets_are_not_readable(self):
        for service in OWN:
            for name in ("scholarchain-course/anthropic-api-key2", "scholarchain-course/voyage-api-key2", "scholarchain-other/anthropic-api-key",
                         "scholarchain-course/other"):
                arn = "arn:aws:secretsmanager:%s:%s:secret:%s-AbC123" % (REGION, ACCOUNT, name)
                with self.subTest(service=service, name=name):
                    self.assertFalse(allows(self.execution(service), "secretsmanager:GetSecretValue", arn))

    def test_no_kms_decrypt_and_no_secret_write_is_granted_for_the_provider_keys(self):
        for service in R.SERVICES:
            with self.subTest(service=service):
                acts = actions_of(self.execution(service))
                self.assertNotIn("kms:Decrypt", acts, "the containers use the AWS-managed key")
                self.assertEqual({a for a in acts if a.startswith("secretsmanager:")} - {"secretsmanager:GetSecretValue"}, set())

    def test_task_roles_hold_no_secrets_manager_permission(self):
        for service in R.SERVICES:
            policy = self.docs['aws_iam_role_policy.task["%s"]' % service]
            with self.subTest(service=service):
                self.assertEqual([a for a in actions_of(policy) if a.startswith("secretsmanager:")], [])

    def test_no_marketplace_action_on_any_role_in_either_configuration(self):
        for label, docs in (("no bedrock", self.docs), ("both bedrock", self.with_bedrock)):
            for address, policy in docs.items():
                with self.subTest(configuration=label, policy=address):
                    self.assertFalse([a for a in actions_of(policy) if "marketplace" in a.lower() or a in ("*", "*:*")])

    def test_without_a_bedrock_provider_no_role_may_invoke_bedrock(self):
        for address, policy in self.docs.items():
            with self.subTest(policy=address):
                self.assertEqual([a for a in actions_of(policy) if a.lower().startswith("bedrock:")], [])

    def test_with_bedrock_models_only_the_matching_service_may_invoke_only_invoke_model(self):
        for service in R.SERVICES:
            policy = self.with_bedrock['aws_iam_role_policy.task["%s"]' % service]
            bedrock_actions = {a for a in actions_of(policy) if a.lower().startswith("bedrock:")}
            with self.subTest(service=service):
                if service == "graph-service":
                    self.assertEqual(bedrock_actions, set())
                else:
                    self.assertEqual(bedrock_actions, {"bedrock:InvokeModel"})
        titan = "arn:aws:bedrock:us-east-2::foundation-model/amazon.titan-embed-text-v2:0"
        claude = "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-synthetic-test-v1:0"
        query, semantic = (self.with_bedrock['aws_iam_role_policy.task["%s"]' % s] for s in ("query-api", "semantic-service"))
        self.assertTrue(allows(query, "bedrock:InvokeModel", claude))
        self.assertFalse(allows(query, "bedrock:InvokeModel", titan))
        self.assertTrue(allows(semantic, "bedrock:InvokeModel", titan))
        self.assertFalse(allows(semantic, "bedrock:InvokeModel", claude))


class RuntimeInjection(unittest.TestCase):
    """modules/runtime in a mock apply: keys travel in `secrets`, only in the aws service mode, never in `environment`."""

    BINDINGS = {
        "query-api": {"SCHOLARCHAIN_ANTHROPIC_API_KEY": ANTHROPIC_REAL},
        "graph-service": {},
        "semantic-service": {"SCHOLARCHAIN_VOYAGE_API_KEY": VOYAGE_REAL},
        "embedding-worker": {"SCHOLARCHAIN_VOYAGE_API_KEY": VOYAGE_REAL},
    }

    def containers(self, verified, **over):
        values = dict(R.RUNTIME_VALUES, composition_verified=verified)
        over = dict({"provider_secret_bindings": self.BINDINGS, "synthesis_provider": "anthropic", "embedding_provider": "voyage",
                     "embedding_model_id": "voyage-4-lite", "embedding_model_version": "voyage-4-lite", "synthesis_model_id": "claude-haiku-5-5"}, **over)
        tree = R.ModuleTree("runtime", values, over, snapshot="runtime_module_snapshot.tftest.hcl")
        try:
            state = tree.state_json()
        finally:
            tree.close()
        resources = {r["address"][len("module.m."):]: r["values"] for r in state["root_module"]["child_modules"][0]["resources"]}
        out = {}
        for service in R.SERVICES:
            definition = json.loads(resources['aws_ecs_task_definition.service["%s"]' % service]["container_definitions"])[0]
            out[service] = ({e["name"]: e["value"] for e in definition["environment"]}, {s["name"]: s["valueFrom"] for s in definition.get("secrets", [])})
        return out

    def test_aws_mode_injects_each_key_into_its_own_services_only(self):
        got = self.containers(True)
        self.assertEqual(got["query-api"][1], {"SCHOLARCHAIN_ANTHROPIC_API_KEY": ANTHROPIC_REAL})
        self.assertEqual(got["semantic-service"][1], {"SCHOLARCHAIN_VOYAGE_API_KEY": VOYAGE_REAL})
        self.assertEqual(got["embedding-worker"][1], {"SCHOLARCHAIN_VOYAGE_API_KEY": VOYAGE_REAL})
        self.assertEqual(got["graph-service"][1], {})

    def test_no_environment_entry_carries_a_key_name_or_a_secret_arn(self):
        for service, (env, _secrets) in self.containers(True).items():
            with self.subTest(service=service):
                self.assertEqual([k for k in env if k.upper().endswith("API_KEY")], [])
                self.assertFalse([k for k, v in env.items() if "secretsmanager" in str(v)])

    def test_the_provider_choice_is_exported_to_the_services_that_use_it(self):
        got = self.containers(True)
        self.assertEqual(got["query-api"][0]["SCHOLARCHAIN_SYNTHESIS_PROVIDER"], "anthropic")
        self.assertEqual(got["query-api"][0]["SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL"], "claude-haiku-5-5")
        for service in ("query-api", "semantic-service", "embedding-worker"):
            env = got[service][0]
            self.assertEqual((env["SCHOLARCHAIN_EMBEDDING_PROVIDER"], env["SCHOLARCHAIN_MODELS_EMBEDDING_MODEL"], env["SCHOLARCHAIN_EMBEDDING_MODEL_VERSION"],
                              env["SCHOLARCHAIN_EMBEDDING_DIMENSION"]), ("voyage", "voyage-4-lite", "voyage-4-lite", "256"), service)

    def test_without_the_composition_acknowledgment_no_provider_secret_is_injected(self):
        for service, (env, secrets) in self.containers(False).items():
            with self.subTest(service=service):
                self.assertEqual(secrets, {}, "a task cannot start while its secret holds no value yet")
                self.assertEqual(env["SCHOLARCHAIN_SERVICE_MODE"], "unconfigured")

    def test_bedrock_providers_inject_no_provider_key(self):
        got = self.containers(True, provider_secret_bindings={s: {} for s in R.SERVICES}, synthesis_provider="bedrock", embedding_provider="bedrock",
                              embedding_model_id="amazon.titan-embed-text-v2:0", embedding_model_version="synthetic-pinned-version",
                              synthesis_model_id="anthropic.claude-synthetic-test-v1:0")
        for service, (env, secrets) in got.items():
            with self.subTest(service=service):
                self.assertEqual(secrets, {})
        self.assertEqual(got["query-api"][0]["SCHOLARCHAIN_SYNTHESIS_PROVIDER"], "bedrock")
        self.assertEqual(got["semantic-service"][0]["SCHOLARCHAIN_EMBEDDING_PROVIDER"], "bedrock")


class DeployerGrantsFollowTheProvider(unittest.TestCase):
    """The deployer root: the runtime permissions boundary and the operator-loader role grant Bedrock only for a Bedrock provider."""

    @classmethod
    def setUpClass(cls):
        cls.plans = {}
        for label, extra in (("default", {}), ("bedrock", {"main_synthesis_provider": "bedrock", "main_embedding_provider": "bedrock"})):
            tree = TfTree("deployer14ops")
            tree.spec = dict(tree.spec, vars=dict(tree.spec["vars"], **extra))
            try:
                cls.plans[label] = tree.plan_json()
            finally:
                tree.close()

    @staticmethod
    def every_policy(plan):
        docs = {}
        for address, rc in managed_changes(plan).items():
            after = rc["change"]["after"]
            if rc["type"] in ("aws_iam_policy", "aws_iam_role_policy") and isinstance(after.get("policy"), str):
                docs[address] = json.loads(after["policy"])
        return docs

    def test_no_marketplace_action_in_any_deployer_policy_or_boundary(self):
        for label, plan in self.plans.items():
            for address, doc in self.every_policy(plan).items():
                with self.subTest(configuration=label, policy=address):
                    self.assertFalse([a for a in actions_of(doc) if "marketplace" in a.lower()])

    def test_the_runtime_boundary_and_operator_roles_have_no_bedrock_action_with_the_primary_providers(self):
        docs = self.every_policy(self.plans["default"])
        boundary = {a: d for a, d in docs.items() if a.startswith("aws_iam_policy.main_boundary_runtime")}
        operator = {a: d for a, d in docs.items() if a.startswith("aws_iam_role_policy.operator")}
        self.assertTrue(boundary and operator)
        for address, doc in list(boundary.items()) + list(operator.items()):
            with self.subTest(policy=address):
                self.assertEqual([a for a in actions_of(doc) if a.lower().startswith("bedrock:")], [])

    def test_a_bedrock_provider_adds_the_bedrock_invoke_statements(self):
        docs = self.every_policy(self.plans["bedrock"])
        boundary = [d for a, d in docs.items() if a.startswith("aws_iam_policy.main_boundary_runtime")]
        self.assertEqual(len(boundary), 1)
        self.assertIn("bedrock:InvokeModel", actions_of(boundary[0]))
        titan = [st for d in docs.values() for st in policy_statements(d) if st.get("Sid") == "InvokeTitanTextEmbeddingsV2Only"]
        self.assertEqual(len(titan), 1, "exactly one Titan grant, on the loader role, and only with embedding_provider bedrock")
        self.assertEqual(titan[0]["Action"], ["bedrock:InvokeModel"])
        self.assertEqual(len(titan[0]["Resource"]), 1)
        self.assertTrue(titan[0]["Resource"][0].endswith("foundation-model/amazon.titan-embed-text-v2:0"))

    def test_the_default_plan_has_no_titan_grant_anywhere(self):
        titan = [st for d in self.every_policy(self.plans["default"]).values() for st in policy_statements(d) if st.get("Sid") == "InvokeTitanTextEmbeddingsV2Only"]
        self.assertEqual(titan, [])

    def test_no_deployer_permission_set_or_operator_role_can_read_or_write_a_secret_value(self):
        """The runtime BOUNDARY is a ceiling for the runtime roles (it names GetSecretValue for secret injection) and is excluded; the
        deployer's own permission sets and every operator role may neither read nor write a secret value."""
        for label, plan in self.plans.items():
            docs = {a: d for a, d in self.every_policy(plan).items() if not a.startswith("aws_iam_policy.main_boundary_")}
            self.assertTrue([a for a in docs if a.startswith("aws_iam_policy.permission_set[")] and [a for a in docs if a.startswith("aws_iam_role_policy.operator")])
            for address, doc in docs.items():
                for st in policy_statements(doc):
                    if st.get("Effect") == "Allow":
                        with self.subTest(configuration=label, policy=address, sid=st.get("Sid")):
                            self.assertFalse([a for a in (st["Action"] if isinstance(st["Action"], list) else [st["Action"]])
                                              if a in ("secretsmanager:GetSecretValue", "secretsmanager:PutSecretValue", "secretsmanager:*")])


if __name__ == "__main__":
    unittest.main()
