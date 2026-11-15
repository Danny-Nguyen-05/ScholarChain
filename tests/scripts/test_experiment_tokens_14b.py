"""scripts/run-experiment.sh run-time tokens (replan G-MAIN), written independently by the test-engineer from the requirement:

  Bucket names embed the AWS account ID, so a COMMITTED manifest holds only the tokens ${SCHOLARCHAIN_ARTIFACTS_BUCKET} (also _LOGS_,
  _RAW_, _REPORTS_) and ${SCHOLARCHAIN_RUN_PREFIX}. The script resolves them from the environment BEFORE the schema check and refuses
  (exit 3, nothing runs): an unknown token, an unclosed `${`, a bare `$NAME`, an empty or unset variable for a token in use, a value of
  the wrong shape, buckets of different accounts, and a raw 12-digit account ID anywhere in the committed manifest. It records the
  committed and the rendered sha256 and shows the account as <acct>. The approval keeps binding the COMMITTED bytes.

The account ID is synthetic; nothing is run against a real account.
"""
import json
import re
import unittest

import sc_support as S

ACCOUNT = "111122223333"
OTHER = "4444" + "5555" + "6666"
RUN = "run-20261115"
ART = "scholarchain-course-%s-artifacts" % ACCOUNT
LOGS = "scholarchain-course-%s-logs" % ACCOUNT
PATH = "experiments/tokens.json"
ENV = {"SCHOLARCHAIN_ARTIFACTS_BUCKET": ART, "SCHOLARCHAIN_LOGS_BUCKET": LOGS, "SCHOLARCHAIN_RUN_PREFIX": RUN}
A = "${SCHOLARCHAIN_ARTIFACTS_BUCKET}"
R = "${SCHOLARCHAIN_RUN_PREFIX}"


def doc():
    base = "s3://%s/emr/%s" % (A, R)
    return {
        "schema": "scholarchain.experiment-manifest.v1", "id": "tokens-smoke", "description": "fixture for the token tests",
        "budget": {"max_usd": 3, "max_runtime_minutes": 60, "max_capacity": 2, "region": "us-east-2"},
        "teardown": {"mode": "auto-termination", "max_idle_timeout_seconds": 900},
        "pipeline": {
            "instance_type": "m5.xlarge", "core_count": 1, "max_task_count": 0,
            "input_prefix": base + "/input/size-25", "output_prefix": "s3://%s/pipeline/%s/15a/size-25" % (A, R),
            "hadoop_submit_jar": base + "/jars/hadoop-submit.jar", "hadoop_libjars": base + "/jars/hadoop-bundle.jar",
            "hadoop_config": "inputs/prep.json", "er_jar": base + "/jars/entity-resolution.jar", "er_policy": base + "/config/er-policy.json",
            "er_config": base + "/config/er-config.json", "spark_config_template": base + "/config/spark-config-template.json",
            "datasets_manifest": "inputs/datasets.json", "artifact_sha256": {name: S.HEX64 for name in S.ARTIFACT_NAMES},
        },
        "metrics": {"locations": ["s3://%s/pipeline/%s/15a/size-25/metrics/" % (A, R)]},
    }


class Base(unittest.TestCase):
    def committed(self, mutate=None):
        fx = S.Fixture(self)
        d = doc()
        if mutate:
            mutate(d)
        S.Fixture.write_json(fx.repo / PATH, d)
        fx.commit_all("add the token manifest")
        return fx

    def run_exp(self, fx, env=None, unset=(), extra=()):
        merged = {k: v for k, v in (ENV if env is None else env).items() if k not in unset}
        args = ["--manifest", str(fx.repo / PATH), "--cluster-id", "j-TESTCLUSTER"] + list(extra)
        fx.log.write_text("") if fx.log.exists() else None
        return fx.run("run-experiment.sh", args, merged)

    def refused(self, run):
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertEqual(run.calls, [], "nothing may run for an unresolvable manifest")
        self.assertFalse(run.grep(r"^pipeline\| "), "the pipeline must not run")
        return run

    def committed_sha(self, fx):
        return S.sha256_file(fx.repo / PATH)


class Resolution(Base):
    def test_both_tokens_resolve_and_the_dry_run_passes_with_the_account_redacted(self):
        fx = self.committed()
        run = self.run_exp(fx)
        self.assertEqual((run.rc, run.status), (0, "DRY-RUN"), run.describe())
        self.assertIn("manifest-tokens", run.steps())
        self.assertLess(run.steps().index("manifest-tokens"), run.steps().index("manifest-schema"), "tokens resolve before the schema check")
        self.assertIn("EXPERIMENT-TOKEN: SCHOLARCHAIN_ARTIFACTS_BUCKET scholarchain-course-<acct>-artifacts", run.out)
        self.assertIn("EXPERIMENT-TOKEN: SCHOLARCHAIN_RUN_PREFIX " + RUN, run.out)
        self.assertNotIn(ACCOUNT, run.out + run.err, "the account never appears in the output")
        self.assertFalse([l for l in run.lines() if "${SCHOLARCHAIN" in l], "no unresolved token reaches the pipeline")

    def test_the_committed_manifest_in_git_holds_no_account_id(self):
        fx = self.committed()
        self.assertNotRegex((fx.repo / PATH).read_text(), r"[0-9]{12}")
        self.assertIn(A, (fx.repo / PATH).read_text())

    def test_the_committed_and_the_rendered_sha256_are_reported_and_differ(self):
        fx = self.committed()
        run = self.run_exp(fx)
        line = run.grep(r"^EXPERIMENT-MANIFEST-SHA256: ")[0]
        committed, rendered = re.fullmatch(r"EXPERIMENT-MANIFEST-SHA256: committed=([0-9a-f]{64}) rendered=([0-9a-f]{64})", line).groups()
        self.assertEqual(committed, self.committed_sha(fx))
        self.assertNotEqual(rendered, committed)
        self.assertIn("EXPERIMENT-APPROVAL-LINE: APPROVED_MANIFEST_SHA256=" + committed, run.out, "the approval binds the COMMITTED bytes")
        self.assertIn("Rendered manifest sha256: " + rendered, run.out)

    def test_the_rendered_hash_follows_the_resolved_values_not_the_committed_bytes(self):
        fx = self.committed()
        first = self.run_exp(fx).grep(r"^EXPERIMENT-MANIFEST-SHA256: ")[0]
        same = self.run_exp(fx).grep(r"^EXPERIMENT-MANIFEST-SHA256: ")[0]
        other = self.run_exp(fx, env=dict(ENV, SCHOLARCHAIN_RUN_PREFIX="run-20261116")).grep(r"^EXPERIMENT-MANIFEST-SHA256: ")[0]
        self.assertEqual(first, same)
        self.assertEqual(first.split("committed=")[1].split()[0], other.split("committed=")[1].split()[0])
        self.assertNotEqual(first.split("rendered=")[1], other.split("rendered=")[1])

    def test_a_logs_token_resolves_with_the_same_account(self):
        fx = self.committed(lambda d: d["metrics"]["locations"].append("s3://${SCHOLARCHAIN_LOGS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/"))
        run = self.run_exp(fx)
        self.assertEqual(run.rc, 0, run.describe())
        self.assertIn("EXPERIMENT-TOKEN: SCHOLARCHAIN_LOGS_BUCKET scholarchain-course-<acct>-logs", run.out)
        self.assertIn("EXPERIMENT-METRIC-LOCATION: s3://scholarchain-course-<acct>-logs/emr/%s/" % RUN, run.out)

    def test_unused_token_variables_are_ignored_and_a_tokenless_manifest_is_unchanged(self):
        fx = S.Fixture(self)
        plain = doc()
        for k, v in list(plain["pipeline"].items()):
            if isinstance(v, str):
                plain["pipeline"][k] = v.replace(A, "plainbucket").replace(R, "run-x")
        plain["metrics"]["locations"] = ["s3://plainbucket/m/"]
        S.Fixture.write_json(fx.repo / PATH, plain)
        fx.commit_all("plain")
        run = self.run_exp(fx, env={})
        self.assertEqual(run.rc, 0, run.describe())
        self.assertNotIn("EXPERIMENT-TOKEN:", run.out)
        line = run.grep(r"^EXPERIMENT-MANIFEST-SHA256: ")[0]
        committed, rendered = re.findall(r"=([0-9a-f]{64})", line)
        self.assertEqual(committed, rendered, "no token, no change")


class Refusals(Base):
    def assert_token_refusal(self, fx, **kw):
        run = self.refused(self.run_exp(fx, **kw))
        self.assertIn("step=manifest-tokens", run.result, run.describe())
        return run

    def test_an_unknown_token_is_refused(self):
        for token in ("${SCHOLARCHAIN_SECRET}", "${SCHOLARCHAIN_ARTIFACTS_BUCKET_X}", "${HOME}", "${scholarchain_run_prefix}", "${ }", "${}"):
            with self.subTest(token=token):
                fx = self.committed(lambda d, t=token: d["pipeline"].__setitem__("er_policy", "s3://%s/p.json" % t))
                self.assert_token_refusal(fx)

    def test_an_unclosed_token_is_refused(self):
        fx = self.committed(lambda d: d["pipeline"].__setitem__("er_policy", "s3://" + A + "/emr/${SCHOLARCHAIN_RUN_PREFIX/p.json"))
        self.assert_token_refusal(fx)

    def test_a_bare_dollar_name_is_refused(self):
        for bare in ("$SCHOLARCHAIN_RUN_PREFIX", "$SCHOLARCHAIN_ARTIFACTS_BUCKET", "$HOME"):
            with self.subTest(bare=bare):
                fx = self.committed(lambda d, b=bare: d["pipeline"].__setitem__("er_policy", "s3://" + A + "/emr/" + b + "/p.json"))
                self.assert_token_refusal(fx)

    def test_an_empty_or_unset_variable_for_a_token_in_use_is_refused(self):
        fx = self.committed()
        for name in ("SCHOLARCHAIN_ARTIFACTS_BUCKET", "SCHOLARCHAIN_RUN_PREFIX"):
            with self.subTest(name=name, state="unset"):
                self.assert_token_refusal(fx, unset=(name,))
            with self.subTest(name=name, state="empty"):
                self.assert_token_refusal(fx, env=dict(ENV, **{name: ""}))
            with self.subTest(name=name, state="blank"):
                self.assert_token_refusal(fx, env=dict(ENV, **{name: "   "}))

    def test_values_of_the_wrong_shape_are_refused(self):
        fx = self.committed()
        bad_buckets = ("scholarchain-course-abc-artifacts", "other-%s-artifacts" % ACCOUNT, "scholarchain-course-%s-logs" % ACCOUNT,
                       "Scholarchain-course-%s-artifacts" % ACCOUNT, "scholarchain-course-%s-artifacts-x" % ACCOUNT,
                       "scholarchain-course-1234567890123-artifacts", "s3://" + ART, ART + "/")
        for bucket in bad_buckets:
            with self.subTest(bucket=bucket):
                self.assert_token_refusal(fx, env=dict(ENV, SCHOLARCHAIN_ARTIFACTS_BUCKET=bucket))
        for prefix in ("Run-20261115", "run-", "x/../y", "run-20261115/", "run_1", "run-" + "a" * 40, "20261115"):
            with self.subTest(prefix=prefix):
                self.assert_token_refusal(fx, env=dict(ENV, SCHOLARCHAIN_RUN_PREFIX=prefix))

    def test_buckets_of_different_stacks_are_refused(self):
        fx = self.committed(lambda d: d["metrics"]["locations"].append("s3://${SCHOLARCHAIN_LOGS_BUCKET}/emr/"))
        for logs in ("scholarchain-course-%s-logs" % OTHER, "scholarchain-other-%s-logs" % ACCOUNT):
            with self.subTest(logs=logs.replace(OTHER, "<other>")):
                run = self.assert_token_refusal(fx, env=dict(ENV, SCHOLARCHAIN_LOGS_BUCKET=logs))
                self.assertNotIn(OTHER, run.out + run.err, "even a refused foreign account is not echoed")

    def test_a_raw_twelve_digit_account_id_in_the_committed_manifest_is_refused(self):
        spots = {
            "pipeline value": lambda d: d["pipeline"].__setitem__("er_policy", "s3://scholarchain-course-%s-artifacts/p.json" % ACCOUNT),
            "metric location": lambda d: d["metrics"]["locations"].append("s3://scholarchain-course-%s-logs/" % ACCOUNT),
            "description": lambda d: d.__setitem__("description", "run in account %s" % ACCOUNT),
            "an arn in the id": lambda d: d.__setitem__("id", "arn-%s" % ACCOUNT),
        }
        for label, mutate in spots.items():
            with self.subTest(spot=label):
                fx = self.committed(mutate)
                run = self.refused(self.run_exp(fx))
                self.assertIn("step=manifest-tokens", run.result, run.describe())
                self.assertNotIn(ACCOUNT, run.out + run.err)

    def test_a_literal_account_id_is_refused_even_when_the_tokens_would_resolve(self):
        fx = self.committed(lambda d: d["pipeline"].__setitem__("input_prefix", "s3://scholarchain-course-%s-artifacts/emr/%s/input/size-25" % (OTHER, RUN)))
        run = self.refused(self.run_exp(fx))
        self.assertNotIn(OTHER, run.out + run.err)

    def test_a_manifest_that_is_not_committed_is_still_refused_before_tokens(self):
        fx = self.committed()
        (fx.repo / PATH).write_text((fx.repo / PATH).read_text().replace("tokens-smoke", "changed"))
        run = self.run_exp(fx)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertIn("step=manifest-committed", run.result)
        self.assertNotIn("manifest-tokens", run.steps())


class Execute(Base):
    def test_the_experiment_record_binds_both_hashes_and_shows_the_account_as_acct(self):
        fx = self.committed()
        pre = fx.write_prespend()
        env = dict(fx.exec_env(), **ENV)
        if not fx.ledger_path.exists():
            fx.write_ledger([])
        dry = self.run_exp(fx, env=env)
        self.assertEqual(dry.rc, 0, dry.describe())
        run_cfg = next(l.split(": ", 1)[1].strip() for l in dry.lines() if l.startswith("pipeline| RUN-CONFIG-SHA256: "))
        values = [("APPROVED_ACTION", "run-experiment"), ("APPROVED_COMMIT", fx.head()), ("APPROVED_ACCOUNT_SHA256", fx.account_hash()),
                  ("APPROVED_REGION", "us-east-2"), ("APPROVED_CLUSTER_ID", "j-TESTCLUSTER"), ("APPROVED_RUN_CONFIG_SHA256", run_cfg),
                  ("APPROVED_BUDGET_USD", "3"), ("APPROVED_MAX_CAPACITY", "2"), ("APPROVED_MAX_RUNTIME_MINUTES", "60"),
                  ("APPROVED_TEARDOWN", "auto-termination"), ("APPROVED_PRESPEND_SHA256", S.sha256_file(pre)),
                  ("APPROVED_MANIFEST_SHA256", self.committed_sha(fx))]
        approval = fx.write_approval(values)
        fx.log.write_text("")
        run = self.run_exp(fx, env=env, extra=["--approval", str(approval), "--prespend", str(pre), "--execute"])
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        line = dry.grep(r"^EXPERIMENT-MANIFEST-SHA256: ")[0]
        committed, rendered = re.findall(r"=([0-9a-f]{64})", line)
        dirs = list((fx.repo / "target/experiment-runs").iterdir())
        self.assertEqual(len(dirs), 1)
        for name in ("experiment-record.json", "experiment-result.json"):
            text = (dirs[0] / name).read_text()
            json.loads(text)
            self.assertIn(committed, text, name)
            self.assertIn(rendered, text, name)
            self.assertIn("<acct>", text, name)
            self.assertNotIn(ACCOUNT, text, name)
        self.assertNotIn(ACCOUNT, run.out + run.err)
        for canary in S.CANARIES:
            self.assertNotIn(canary, run.text)

    def test_an_approval_for_other_committed_bytes_still_refuses_even_if_the_rendered_values_are_the_same(self):
        fx = self.committed()
        pre = fx.write_prespend()
        env = dict(fx.exec_env(), **ENV)
        fx.write_ledger([])
        dry = self.run_exp(fx, env=env)
        run_cfg = next(l.split(": ", 1)[1].strip() for l in dry.lines() if l.startswith("pipeline| RUN-CONFIG-SHA256: "))
        values = [("APPROVED_ACTION", "run-experiment"), ("APPROVED_COMMIT", fx.head()), ("APPROVED_ACCOUNT_SHA256", fx.account_hash()),
                  ("APPROVED_REGION", "us-east-2"), ("APPROVED_CLUSTER_ID", "j-TESTCLUSTER"), ("APPROVED_RUN_CONFIG_SHA256", run_cfg),
                  ("APPROVED_BUDGET_USD", "3"), ("APPROVED_MAX_CAPACITY", "2"), ("APPROVED_MAX_RUNTIME_MINUTES", "60"),
                  ("APPROVED_TEARDOWN", "auto-termination"), ("APPROVED_PRESPEND_SHA256", S.sha256_file(pre)),
                  ("APPROVED_MANIFEST_SHA256", "0" * 64)]
        approval = fx.write_approval(values)
        fx.log.write_text("")
        run = self.run_exp(fx, env=env, extra=["--approval", str(approval), "--prespend", str(pre), "--execute"])
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(S.count_calls(run.calls, "aws", "emr", "add-steps"), 0)


if __name__ == "__main__":
    unittest.main()
