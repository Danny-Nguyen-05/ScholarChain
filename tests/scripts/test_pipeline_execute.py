"""Independent --execute-path tests for scripts/run-bounded-pipeline.sh against fake aws (Subphase 13B, test-engineer).

The execute path is exercised only with fake binaries on PATH and the documented test-only SCHOLARCHAIN_CONFIG_FILE /
SCHOLARCHAIN_PRICING_FILE (confirmed pricing) / SCHOLARCHAIN_TEST_DEADLINE_SECONDS mechanisms; no network, no account.
Expectations: scripts/README.md "Bounded pipeline" (steps stop at the first non-COMPLETED step, exit 4 for a failed or
cancelled step, 5 for an aws failure, 124 for the hard runtime cap, a reservation counts for good, the run manifest and
result are written exclusively and git-ignored, never an infrastructure call).
"""
import json
import re
import unittest

import sc_support as S

BANNED_VERB = re.compile(r"^(create|run|terminate|modify|put|delete|set|update|remove|resize|register|deregister)")


class PipelineExecute(unittest.TestCase):
    def fx(self):
        return S.Fixture(self)

    # ----- green path -----
    def test_green_run_submits_six_steps_in_order_then_passes(self):
        fx = self.fx()
        r = fx.execute(secrets=True)
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        self.assertEqual(len(r.results()), 1)
        self.assertTrue(r.lines()[-1].startswith("RESULT: PASS"))
        added = [c for c in r.calls if c["tool"] == "aws" and c["argv"][:2] == ["emr", "add-steps"]]
        self.assertEqual(len(added), 6)
        names = []
        for c in added:
            steps = json.loads(c["argv"][c["argv"].index("--steps") + 1])
            self.assertEqual(len(steps), 1)
            jar = steps[0]["HadoopJarStep"]
            self.assertEqual(jar["Jar"], "command-runner.jar")
            self.assertEqual(jar["Args"][:2], ["bash", "-c"])
            names.append(steps[0]["Name"])
            self.assertIn("--cluster-id", c["argv"])
            self.assertEqual(c["argv"][c["argv"].index("--cluster-id") + 1], "j-TESTCLUSTER")
        self.assertEqual(names, ["ScholarChain-bp-test-run-1-" + n for n in S.STEP_NAMES])
        self.assertEqual([s for s in r.steps() if s.startswith("step-")], ["step-" + n for n in S.STEP_NAMES])
        self.assertEqual(len(r.grep(r"^STEP-RESULT: .* COMPLETED$")), 6)

    def test_verification_precedes_any_submission_and_nothing_infrastructural_is_called(self):
        fx = self.fx()
        r = fx.execute()
        verbs = r.aws_verbs()
        self.assertEqual(verbs[:4], ["sts get-caller-identity", "emr describe-cluster", "emr get-auto-termination-policy", "emr list-instance-groups"])
        self.assertEqual(verbs.index("emr add-steps"), 4)
        for verb in verbs:
            service, _, action = verb.partition(" ")
            if verb == "emr add-steps" or verb == "emr cancel-steps":
                continue
            self.assertIsNone(BANNED_VERB.match(action), "mutating/infrastructure aws verb called: " + verb)
        self.assertEqual(r.tool_calls("terraform"), [])
        self.assertEqual(r.tool_calls("docker"), [])
        self.assertTrue(set(verbs) <= {"sts get-caller-identity", "emr describe-cluster", "emr get-auto-termination-policy",
                                       "emr list-instance-groups", "emr add-steps", "emr describe-step", "emr cancel-steps"}, verbs)

    def test_every_aws_call_is_bounded_by_a_timeout_in_the_printed_command(self):
        fx = self.fx()
        r = fx.execute()
        cmds = r.grep(r"^CMD: ")
        self.assertTrue(cmds)
        for line in cmds:
            self.assertRegex(line, r"^CMD: timeout=\d+s ")

    def test_ledger_manifest_and_result_are_written_and_hold_the_required_provenance(self):
        fx = self.fx()
        r = fx.execute(secrets=True)
        self.assertEqual(r.rc, 0, r.describe())
        ledger = (fx.repo / "target/emr-ledger/runs.jsonl").read_text().splitlines()
        self.assertEqual(len(ledger), 1)
        entry = json.loads(ledger[0])
        self.assertEqual(entry["run_id"], "bp-test-run-1")
        self.assertEqual(entry["estimate_usd"], "0.48")
        run_dir = fx.repo / "target/pipeline-runs/bp-test-run-1"
        manifest = json.loads((run_dir / "run-manifest.json").read_text())
        result = json.loads((run_dir / "run-result.json").read_text())
        text = json.dumps(manifest)
        for expected in (fx.head(), "bp-test-run-1", "j-TESTCLUSTER", "us-east-2", "s3://outbucket/data/out", "dblp-2026-01",
                         "or-2026-01", "auto-termination", S.Fixture.account_hash()):
            self.assertIn(expected, text, "run manifest lacks %r" % expected)
        self.assertIn("COMPLETED", json.dumps(result))
        # the manifest and result directory must stay out of git (ignored)
        self.assertEqual(fx.git("status", "--porcelain"), "")

    def test_no_canary_secret_or_raw_account_id_in_output_or_retained_files(self):
        fx = self.fx()
        r = fx.execute(secrets=True)
        self.assertEqual(r.rc, 0, r.describe())
        retained = fx.tree_text(fx.repo / "target")
        self.assertTrue(retained)
        for canary in S.CANARIES:
            self.assertNotIn(canary, r.out)
            self.assertNotIn(canary, r.err)
            for name, text in retained.items():
                self.assertNotIn(canary, text, "canary leaked into retained file %s" % name)

    def test_aws_failure_output_is_redacted_before_it_is_shown(self):
        fx = self.fx()
        noisy = "boom %s %s %s\n" % (S.CANARY_SECRET, S.CANARY_TOKEN, S.ACCOUNT)
        fx.update_scenario(verbs={"emr describe-cluster": {"rc": 1, "stderr": noisy}})
        r = fx.execute(secrets=True)
        self.assertNotEqual(r.rc, 0, r.describe())
        self.assertIn("boom", r.text, "the failing command's output should be shown (redacted), not swallowed")
        for canary in (S.CANARY_SECRET, S.CANARY_TOKEN, S.ACCOUNT):
            self.assertNotIn(canary, r.out)
            self.assertNotIn(canary, r.err)

    def test_api_key_named_variables_are_redacted_from_shown_aws_output_by_every_script(self):
        """Resolved finding O4. scripts/README.md: values of environment variables whose names contain SECRET, TOKEN,
        PASSWORD, ACCESS_KEY, API_KEY, CREDENTIAL or PRIVATE_VARS, or that end in _KEY, are hidden by every script (so
        SCHOLARCHAIN_SMOKE_API_KEY is hidden outside smoke-test.sh too). A failing aws call that echoes such values must
        therefore show <redacted>, never the values."""
        other = "canary-signing-key-3e8d5a17"
        fx = self.fx()
        fx.update_scenario(verbs={"emr describe-cluster": {"rc": 1, "stderr": "boom %s %s\n" % (S.CANARY_SMOKE_KEY, other)}})
        r = fx.execute(secrets=True, env_over={"MY_SERVICE_SIGNING_KEY": other})
        self.assertNotEqual(r.rc, 0, r.describe())
        self.assertIn("boom", r.text, "the failing command's output should be shown (redacted), not swallowed")
        self.assertIn("<redacted>", r.text)
        for value in (S.CANARY_SMOKE_KEY, other):
            self.assertNotIn(value, r.out)
            self.assertNotIn(value, r.err)
        for name, text in fx.tree_text(fx.repo / "target").items():
            for value in (S.CANARY_SMOKE_KEY, other):
                self.assertNotIn(value, text, "leak in retained file %s" % name)

    def test_second_run_with_the_same_run_id_never_overwrites_the_first_manifest(self):
        fx = self.fx()
        first = fx.execute()
        self.assertEqual(first.rc, 0, first.describe())
        path = fx.repo / "target/pipeline-runs/bp-test-run-1/run-manifest.json"
        before = path.read_bytes()
        args, env = fx.exec_ready()
        fx.log.write_text("")
        again = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertNotEqual(again.rc, 0, again.describe())
        self.assertEqual(path.read_bytes(), before, "the run manifest of an earlier run was overwritten")
        self.assertEqual(S.count_calls(again.calls, "aws", "emr", "add-steps"), 0)

    # ----- failures -----
    def failing_step(self, state, step="hadoop-prep"):
        fx = self.fx()
        fx.update_scenario(step_states={step: state})
        r = fx.execute()
        return fx, r

    def test_failed_cancelled_or_interrupted_step_stops_the_run_with_exit_4(self):
        for state in ("FAILED", "CANCELLED", "INTERRUPTED"):
            with self.subTest(state=state):
                fx, r = self.failing_step(state)
                self.assertEqual((r.rc, r.status), (4, "FAIL"), r.describe())
                self.assertEqual(len(r.results()), 1)
                self.assertEqual(S.last_step(r), "step-hadoop-prep")
                self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 2, "no step after the failed one may be submitted")
                self.assertTrue(r.grep(r"^STEP-RESULT: hadoop-prep s-FAKE0002 %s" % state))
                result = (fx.repo / "target/pipeline-runs/bp-test-run-1/run-result.json").read_text()
                self.assertIn(state, result)
                self.assertTrue((fx.repo / "target/emr-ledger/runs.jsonl").read_text().strip(), "a failed run still counts against the ledger")

    def test_unknown_step_state_fails_closed_and_asks_emr_to_cancel(self):
        fx, r = self.failing_step("EXPLODED", step="stage-in")
        self.assertEqual(r.rc, 4, r.describe())
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "cancel-steps"), 1)
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 1)

    def test_add_steps_failure_is_an_aws_failure_exit_5(self):
        fx = self.fx()
        fx.update_scenario(verbs={"emr add-steps": {"rc": 255, "stderr": "ValidationException\n"}})
        r = fx.execute()
        self.assertEqual((r.rc, r.status), (5, "FAIL"), r.describe())
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 1)

    def test_describe_step_failure_cancels_the_step_and_exits_5(self):
        fx = self.fx()
        fx.update_scenario(verbs={"emr describe-step": {"rc": 255, "stderr": "Throttling\n"}})
        r = fx.execute()
        self.assertEqual((r.rc, r.status), (5, "FAIL"), r.describe())
        cancels = [c for c in r.calls if c["argv"][:2] == ["emr", "cancel-steps"]]
        self.assertEqual(len(cancels), 1)
        self.assertIn("SEND_INTERRUPT", cancels[0]["argv"])
        self.assertIn("s-FAKE0001", cancels[0]["argv"])

    def test_hard_runtime_cap_cancels_the_running_step_and_exits_124(self):
        fx = self.fx()
        fx.update_scenario(step_states={"stage-in": "RUNNING"})
        args, env = fx.exec_ready(config={"PIPELINE_POLL_SECONDS": "1"}, env_over={"SCHOLARCHAIN_TEST_DEADLINE_SECONDS": "1"})
        fx.log.write_text("")
        r = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((r.rc, r.status), (124, "FAIL"), r.describe())
        self.assertIn("DEADLINE-OVERRIDE", r.out)
        self.assertIn("TIMED OUT", r.result)
        cancels = [c for c in r.calls if c["argv"][:2] == ["emr", "cancel-steps"]]
        self.assertEqual(len(cancels), 1, "the running EMR step must be asked to stop when the cap passes")
        self.assertIn("SEND_INTERRUPT", cancels[0]["argv"])
        self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 1, "no further step after the cap")
        self.assertIn("TIMED-OUT", (fx.repo / "target/pipeline-runs/bp-test-run-1/run-result.json").read_text())

    def test_test_deadline_is_ignored_without_the_test_config(self):
        fx = self.fx()
        # the repository config is in force: the run is refused at the G6 gate (pricing unconfirmed), never run
        args, _ = fx.exec_ready()
        fx.log.write_text("")
        r = fx.run("run-bounded-pipeline.sh", args, {"AWS_PROFILE": "p", "SCHOLARCHAIN_TEST_DEADLINE_SECONDS": "1"})
        self.assertEqual(r.rc, 3, r.describe())
        self.assertEqual(r.calls, [])


if __name__ == "__main__":
    unittest.main()
