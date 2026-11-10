"""Replan G-MAIN (gap G3/G4): the bounded runtime artifact pointer in the main root, tested from the requirement.

Requirement (docs/agent-runs/phase-14/prompt.md, 14C decision 4 and the G-MAIN gap work): the bounded runtime artifact that
RuntimeArtifactMain writes under rag `runtime-artifacts/<run>/versions/...` is made known to the services by four root variables
runtime_artifact_bucket / _key / _sha256 / _source_run_id (the services refuse a partial pointer):
  * key, sha256 and source run id are all set or all null; setting them needs the verified aws-mode runtime
    (runtime_enabled and runtime_composition_verified);
  * the bucket is optional; when set it must equal the project's rag bucket and needs the pointer;
  * the pointer reaches ONLY the query-api container (SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY / _SHA256 / _SOURCE_RUN_ID, plus _BUCKET when
    given); with no pointer no such variable exists anywhere;
  * the query-api role can read objects under rag `runtime-artifacts/` and list that prefix; `rag_prefixes` includes it.

Evidence: real offline plans of the main root (guards), a mock-provider apply of a scratch wrapper around modules/runtime (container
environments) and modules/identity (the rendered query-api policy). Nothing is applied; no AWS call.
"""
import fnmatch
import json
import re
import unittest

import main_root_shape as M
import runtime_shape_checks as R
from infra_support import REPO

RAG = "scholarchain-course-111122223333-rag"
KEY = "runtime-artifacts/run-20261115/versions/run-1/runtime-subset-abc.json"
SHA = "a" * 64
SRC = "run:00112233-4455-4677-8899-aabbccddeeff"
POINTER = {"runtime_artifact_key": KEY, "runtime_artifact_sha256": SHA, "runtime_artifact_source_run_id": SRC}
ENV_KEYS = ("SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY", "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256", "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID",
            "SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET")


def refused_text(done):
    return re.sub(r"\s+", " ", done.stdout + done.stderr)


class RootGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mp = M.MainPlans()
        cls.addClassCleanup(cls.mp.close)

    def accepted(self, **vars_):
        done = self.mp.attempt(**vars_)
        self.assertEqual(done.returncode, 0, refused_text(done)[-1200:])

    def refused(self, **vars_):
        done = self.mp.attempt(**vars_)
        self.assertNotEqual(done.returncode, 0, "the plan must be refused for %s" % sorted(vars_))
        return refused_text(done)

    def test_no_pointer_is_the_default_and_plans(self):
        self.accepted()
        self.accepted(**M.RUNTIME_VARS)

    def test_the_full_pointer_with_a_verified_runtime_plans(self):
        self.accepted(**M.RUNTIME_VARS, **POINTER)

    def test_the_pointer_is_all_or_none(self):
        names = list(POINTER)
        for i in range(len(names)):
            only = {names[i]: POINTER[names[i]]}
            with self.subTest(only=names[i]):
                self.assertRegex(self.refused(**M.RUNTIME_VARS, **only), r"(?i)together or not at all|partial")
            without = {n: POINTER[n] for n in names if n != names[i]}
            with self.subTest(without=names[i]):
                self.refused(**M.RUNTIME_VARS, **without)

    def test_the_pointer_needs_the_enabled_verified_runtime(self):
        self.refused(**POINTER)  # no runtime at all
        for override in ({"runtime_enabled": False}, {"runtime_composition_verified": False}):
            with self.subTest(override=override):
                self.refused(**dict(M.RUNTIME_VARS, **override), **POINTER)

    def test_the_bucket_must_be_the_rag_bucket_and_needs_the_pointer(self):
        self.accepted(**M.RUNTIME_VARS, **POINTER, runtime_artifact_bucket=RAG)
        for other in ("scholarchain-course-111122223333-graph", "scholarchain-course-111122223333-artifacts", "some-other-bucket", RAG + "-x"):
            with self.subTest(bucket=other):
                self.assertRegex(self.refused(**M.RUNTIME_VARS, **POINTER, runtime_artifact_bucket=other), r"(?i)rag bucket")
        self.refused(**M.RUNTIME_VARS, runtime_artifact_bucket=RAG)  # a bucket alone is not a pointer
        self.refused(runtime_artifact_bucket=RAG)

    def test_the_key_sha_and_run_id_formats_are_enforced(self):
        bad_keys = ("runtime-artifacts/run-20261115/versions/", "other/run-20261115/versions/v/f.json", "runtime-artifacts/Run-1/versions/v/f.json",
                    "runtime-artifacts/run-20261115/versions/../x.json", "runtime-artifacts/run-20261115/versions/./x.json",
                    "runtime-artifacts/run-20261115/versions/a b.json", "/runtime-artifacts/run-20261115/versions/v/f.json",
                    "runtime-artifacts/run-20261115/versions/" + "a" * 900)
        for key in bad_keys:
            with self.subTest(key=key[:70]):
                self.refused(**M.RUNTIME_VARS, **dict(POINTER, runtime_artifact_key=key))
        for sha in ("A" * 64, "a" * 63, "a" * 65, "g" * 64, ""):
            with self.subTest(sha=sha[:10]):
                self.refused(**M.RUNTIME_VARS, **dict(POINTER, runtime_artifact_sha256=sha))
        for run_id in ("", "-bad", "has space", "x" * 129):
            with self.subTest(run_id=run_id[:10]):
                self.refused(**M.RUNTIME_VARS, **dict(POINTER, runtime_artifact_source_run_id=run_id))

    def test_the_root_passes_each_variable_to_the_runtime_module_unchanged(self):
        plan = self.mp.plan(**M.RUNTIME_VARS, **POINTER, runtime_artifact_bucket=RAG)
        expressions = plan["configuration"]["root_module"]["module_calls"]["runtime"]["expressions"]
        for name in ("runtime_artifact_bucket", "runtime_artifact_key", "runtime_artifact_sha256", "runtime_artifact_source_run_id"):
            self.assertEqual(expressions[name]["references"][0], "var." + name, name)

    def test_the_identity_module_receives_runtime_artifacts_among_the_rag_prefixes(self):
        # The plan JSON lists only the variable references of a mixed list expression, so the literal element is read from the source.
        text = (REPO / "infra/terraform/main.tf").read_text()
        match = re.search(r'module "identity" \{.*?\n\}', text, re.S)
        self.assertRegex(match.group(0), r'rag_prefixes\s*=\s*\[[^\]]*"runtime-artifacts"[^\]]*\]')


class ContainerEnvironment(unittest.TestCase):
    """modules/runtime in a mock apply: which container gets which variable."""

    def containers(self, **over):
        values = dict(R.RUNTIME_VALUES, composition_verified=True)
        tree = R.ModuleTree("runtime", values, over, snapshot="runtime_module_snapshot.tftest.hcl")
        try:
            state = tree.state_json()
        finally:
            tree.close()
        resources = {r["address"][len("module.m."):]: r["values"] for r in state["root_module"]["child_modules"][0]["resources"]}
        out = {}
        for service in R.SERVICES:
            definition = json.loads(resources['aws_ecs_task_definition.service["%s"]' % service]["container_definitions"])[0]
            out[service] = {e["name"]: e["value"] for e in definition["environment"]}
        return out

    def test_without_a_pointer_no_container_has_any_runtime_artifact_variable(self):
        envs = self.containers()
        for service, env in envs.items():
            self.assertEqual(env.get("SCHOLARCHAIN_SERVICE_MODE"), "aws", service)
            self.assertFalse([k for k in env if k.startswith("SCHOLARCHAIN_RUNTIME_ARTIFACT")], service)

    def test_the_pointer_reaches_query_api_only(self):
        envs = self.containers(runtime_artifact_key=KEY, runtime_artifact_sha256=SHA, runtime_artifact_source_run_id=SRC)
        query = envs["query-api"]
        self.assertEqual(query["SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY"], KEY)
        self.assertEqual(query["SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256"], SHA)
        self.assertEqual(query["SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID"], SRC)
        self.assertNotIn("SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET", query, "an unset bucket leaves the services' default (the rag bucket)")
        for service in ("graph-service", "semantic-service", "embedding-worker"):
            self.assertFalse([k for k in envs[service] if k.startswith("SCHOLARCHAIN_RUNTIME_ARTIFACT")], service)

    def test_a_given_bucket_is_added_to_query_api_only(self):
        envs = self.containers(runtime_artifact_key=KEY, runtime_artifact_sha256=SHA, runtime_artifact_source_run_id=SRC, runtime_artifact_bucket=RAG)
        self.assertEqual(envs["query-api"]["SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET"], RAG)
        for service in ("graph-service", "semantic-service", "embedding-worker"):
            self.assertNotIn("SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET", envs[service])

    def test_a_partial_pointer_gives_no_variable_at_all(self):
        for over in ({"runtime_artifact_key": KEY}, {"runtime_artifact_key": KEY, "runtime_artifact_sha256": SHA},
                     {"runtime_artifact_sha256": SHA, "runtime_artifact_source_run_id": SRC}, {"runtime_artifact_bucket": RAG}):
            with self.subTest(over=sorted(over)):
                envs = self.containers(**over)
                for service, env in envs.items():
                    self.assertFalse([k for k in env if k.startswith("SCHOLARCHAIN_RUNTIME_ARTIFACT")], "%s %s" % (service, sorted(env)))

    def test_without_the_composition_acknowledgment_the_tasks_get_no_aws_variables_at_all(self):
        tree = R.ModuleTree("runtime", dict(R.RUNTIME_VALUES, composition_verified=False),
                            {"runtime_artifact_key": KEY, "runtime_artifact_sha256": SHA, "runtime_artifact_source_run_id": SRC},
                            snapshot="runtime_module_snapshot.tftest.hcl")
        try:
            state = tree.state_json()
        finally:
            tree.close()
        for r in state["root_module"]["child_modules"][0]["resources"]:
            if r["address"].startswith("module.m.aws_ecs_task_definition.service["):
                env = {e["name"]: e["value"] for e in json.loads(r["values"]["container_definitions"])[0]["environment"]}
                self.assertEqual(env["SCHOLARCHAIN_SERVICE_MODE"], "unconfigured")
                self.assertFalse([k for k in env if k.startswith("SCHOLARCHAIN_RUNTIME_ARTIFACT")])


class QueryApiRole(unittest.TestCase):
    """modules/identity in a mock apply: the rendered query-api policy."""

    @classmethod
    def setUpClass(cls):
        tree = R.ModuleTree("identity", R.IDENTITY_VALUES, snapshot="identity_module_snapshot.tftest.hcl")
        cls.addClassCleanup(tree.close)
        state = tree.state_json()
        cls.policies = {r["address"][len("module.m."):]: json.loads(r["values"]["policy"]) for r in state["root_module"]["child_modules"][0]["resources"]
                        if r["type"] == "aws_iam_role_policy" and "policy" in r["values"]}
        cls.query = cls.policies['aws_iam_role_policy.task["query-api"]']
        cls.object_arn = "arn:aws:s3:::%s/%s" % (RAG, KEY)

    def allows(self, policy, action, resource):
        for st in policy["Statement"]:
            if st["Effect"] != "Allow":
                continue
            actions = st["Action"] if isinstance(st["Action"], list) else [st["Action"]]
            resources = st["Resource"] if isinstance(st["Resource"], list) else [st["Resource"]]
            if action in actions and any(fnmatch.fnmatchcase(resource, r) for r in resources):
                return True
        return False

    def test_query_api_can_read_the_runtime_artifact_object(self):
        self.assertTrue(self.allows(self.query, "s3:GetObject", self.object_arn))
        self.assertTrue(self.allows(self.query, "s3:GetObjectVersion", self.object_arn))

    def test_query_api_can_list_the_runtime_artifacts_prefix_in_the_rag_bucket_only(self):
        lists = [st for st in self.query["Statement"] if "s3:ListBucket" in (st["Action"] if isinstance(st["Action"], list) else [st["Action"]])
                 and st.get("Condition", {}).get("StringLike")]
        self.assertTrue(lists)
        prefixes = {p for st in lists for p in st["Condition"]["StringLike"]["s3:prefix"]}
        self.assertLessEqual({"runtime-artifacts", "runtime-artifacts/*"}, prefixes)
        for st in lists:
            self.assertEqual(st["Resource"], ["arn:aws:s3:::%s" % RAG])

    def test_query_api_cannot_delete_or_overwrite_a_runtime_artifact(self):
        for action in ("s3:DeleteObject", "s3:DeleteObjectVersion", "s3:PutObjectAcl"):
            self.assertFalse(self.allows(self.query, action, self.object_arn), action)

    def test_only_query_api_and_the_worker_list_the_rag_prefixes(self):
        for service in ("graph-service", "semantic-service"):
            policy = self.policies['aws_iam_role_policy.task["%s"]' % service]
            self.assertFalse([st for st in policy["Statement"] if st.get("Condition", {}).get("StringLike", {}).get("s3:prefix")], service)

    def test_the_graph_service_cannot_read_the_rag_runtime_artifacts(self):
        graph = self.policies['aws_iam_role_policy.task["graph-service"]']
        self.assertFalse(self.allows(graph, "s3:GetObject", self.object_arn))


if __name__ == "__main__":
    unittest.main()
