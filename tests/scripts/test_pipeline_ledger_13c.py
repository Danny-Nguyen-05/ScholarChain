"""Independent tests of the 13C run-ledger and cost-estimate behaviour of scripts/run-bounded-pipeline.sh
(test-engineer; human decisions in docs/agent-runs/phase-13/prompt.md "Subphase 13C" Step 0 answers 2 to 4).

  B2  the ledger is ~/.scholarchain/emr-ledger/runs.jsonl (HOME-based; a temp HOME here), created only by
      `run-bounded-pipeline.sh --init-ledger`, which refuses when it exists; an ABSENT or uninitialised ledger refuses
      --execute before any cloud call.
  B3  estimate = instances x hourly rate x (maximum runtime + idle timeout), idle cap 900 s (boundary values are in
      test_pipeline_refusals.py, PipelineG6Refusals; every number there is derived by hand from emr-pricing.conf).
  B4  an approval record is single-use: the reservation stores its sha256 and a reused record is refused, even after
      a failed run.

Each property has a MUTATION case: the fixture's COPY of the scripts is patched to remove the guard and the same scenario
must then fail (the repository scripts are never edited).
"""
import json
import os
import unittest

import sc_support as S


def last(run):
    return S.last_step(run)


class LedgerInit(unittest.TestCase):
    def test_init_ledger_creates_the_ledger_under_home_outside_the_repository_and_makes_no_cloud_call(self):
        fx = S.Fixture(self)
        self.assertFalse(fx.ledger_path.exists())
        r = fx.run("run-bounded-pipeline.sh", ["--init-ledger"])
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        self.assertEqual(r.calls, [], "--init-ledger is a local file creation: no aws, hadoop or terraform call")
        self.assertEqual(str(fx.ledger_path), str(fx.home / ".scholarchain/emr-ledger/runs.jsonl"))
        self.assertFalse(str(fx.ledger_path).startswith(str(fx.repo)))
        records = fx.ledger_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["event"], "init")
        self.assertTrue(records[0]["initialized_by"])
        self.assertRegex(records[0]["initialized_utc"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(fx.git("status", "--porcelain"), "", "nothing in the repository may change")
        self.assertEqual(os.stat(fx.ledger_path).st_mode & 0o022, 0, "the ledger must not be group or world writable")

    def test_init_ledger_refuses_an_existing_ledger_and_leaves_it_byte_identical(self):
        fx = S.Fixture(self)
        self.assertEqual(fx.run("run-bounded-pipeline.sh", ["--init-ledger"]).rc, 0)
        fx.write_ledger(["0.60", "0.60"])  # a ledger that already holds spend records
        before = fx.ledger_path.read_bytes()
        r = fx.run("run-bounded-pipeline.sh", ["--init-ledger"])
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertIn("already exists", r.text)
        self.assertEqual(fx.ledger_path.read_bytes(), before, "a script must never reset the spend record")
        self.assertEqual(r.calls, [])

    def test_init_ledger_takes_no_other_argument(self):
        fx = S.Fixture(self)
        r = fx.run("run-bounded-pipeline.sh", ["--init-ledger", "--cluster-id", "j-TESTCLUSTER"])
        self.assertEqual(r.rc, 2, r.describe())
        r = fx.run("run-bounded-pipeline.sh", ["--init-ledger", "--execute"])
        self.assertEqual(r.rc, 2, r.describe())
        self.assertFalse(fx.ledger_path.exists())

    def test_a_ledger_path_outside_the_scholarchain_home_directory_is_a_usage_error(self):
        fx = S.Fixture(self)
        for bad in ("target/emr-ledger/runs.jsonl", "/tmp/runs.jsonl", "~/elsewhere/runs.jsonl"):
            with self.subTest(path=bad):
                env = {"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(EMR_LEDGER_PATH=bad))}
                r = fx.run("run-bounded-pipeline.sh", ["--init-ledger"], env)
                self.assertEqual(r.rc, 2, r.describe())
                self.assertFalse((fx.repo / "target").exists())

    def test_a_ledger_created_by_init_ledger_is_accepted_by_a_green_execute(self):
        fx = S.Fixture(self)
        self.assertEqual(fx.run("run-bounded-pipeline.sh", ["--init-ledger"]).rc, 0)
        r = fx.execute()  # exec_ready leaves an existing ledger alone
        self.assertEqual((r.rc, r.status), (0, "PASS"), r.describe())
        self.assertEqual([x["event"] for x in fx.ledger_records()], ["init", "reserve"])

    def test_the_ledger_is_never_inside_the_repository_even_when_home_is_the_repository(self):
        fx = S.Fixture(self)
        r = fx.run("run-bounded-pipeline.sh", ["--init-ledger"], {"HOME": str(fx.repo)})
        self.assertEqual(r.rc, 3, r.describe())
        self.assertIn("outside the repository", r.text)
        self.assertFalse((fx.repo / ".scholarchain").exists())


def scenario_absent_ledger_refuses_execute(test, patch=None):
    fx = S.Fixture(test, patch=patch)
    r = fx.execute(ledger=False)
    test.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
    test.assertEqual(last(r), "g6-gate", r.describe())
    test.assertIn("--init-ledger", r.text)
    test.assertEqual(r.calls, [], "no fake binary (aws, hadoop, yarn, ...) may run before the refusal")
    test.assertFalse(fx.ledger_path.exists(), "an absent ledger must not be created by --execute")
    test.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 0)


class AbsentLedger(unittest.TestCase):
    def test_an_absent_ledger_refuses_execute_before_any_cloud_call(self):
        scenario_absent_ledger_refuses_execute(self)

    def test_the_dry_run_reports_the_missing_ledger_but_still_passes(self):
        fx = S.Fixture(self)
        r = fx.dry()
        self.assertEqual((r.rc, r.status), (0, "DRY-RUN"), r.describe())
        self.assertIn("G6-STATUS: --execute would be refused", r.out)
        self.assertIn("--init-ledger", r.text)
        self.assertFalse(fx.ledger_path.exists(), "a dry run never creates the ledger")

    def test_a_ledger_that_is_not_initialised_is_never_read_as_empty(self):
        fx = S.Fixture(self)
        for label, writer in (("empty file", lambda: fx.write_ledger([], init=False)),
                              ("reserve records without the init record", lambda: fx.write_ledger(["0.10"], init=False)),
                              ("garbage", lambda: (fx.ledger_path.parent.mkdir(parents=True, exist_ok=True), fx.ledger_path.write_text("nope\n")))):
            with self.subTest(case=label):
                writer()
                r = fx.execute(ledger=False)
                self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
                self.assertEqual(last(r), "g6-gate", r.describe())
                self.assertEqual(r.calls, [])
                self.assertEqual(S.count_calls(r.calls, "aws", "emr", "add-steps"), 0)

    def test_a_ledger_that_is_a_symlink_is_refused(self):
        fx = S.Fixture(self)
        target = fx.aux / "elsewhere.jsonl"
        fx.write_ledger([])
        target.write_text(fx.ledger_path.read_text())
        fx.ledger_path.unlink()
        fx.ledger_path.symlink_to(target)
        r = fx.execute(ledger=False)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(r.calls, [])

    def test_mutation_reading_an_absent_ledger_as_zero_runs_is_caught(self):
        def patch(scripts):
            path = scripts / "lib" / "budget.py"
            text = path.read_text()
            old = '        raise LedgerAbsent("the run ledger %s does not exist; the human creates it once with run-bounded-pipeline.sh --init-ledger" % path)'
            self.assertIn(old, text, "mutation anchor moved: update the mutation")
            new = "        return 0, D(0), set()"
            path.write_text(text.replace(old, new, 1))
        with self.assertRaises(AssertionError):
            scenario_absent_ledger_refuses_execute(self, patch=patch)


def scenario_reused_approval_is_refused_even_after_a_failed_run(test, patch=None, failed=True):
    fx = S.Fixture(test, patch=patch)
    if failed:
        fx.update_scenario(step_states={"hadoop-prep": "FAILED"})
    args, env = fx.exec_ready()
    fx.log.write_text("")
    first = fx.run("run-bounded-pipeline.sh", args, env)
    if failed:
        test.assertEqual((first.rc, first.status), (4, "FAIL"), first.describe())
    else:
        test.assertEqual((first.rc, first.status), (0, "PASS"), first.describe())
    reserved = fx.reservations()
    test.assertEqual(len(reserved), 1)
    approval_sha = S.sha256_file(fx.aux / "approval.md")
    test.assertEqual(reserved[0]["approval_record_sha256"], approval_sha)
    # the very same record again (also with the failed step now healthy): refused, nothing submitted, nothing reserved
    fx.update_scenario(step_states={})
    fx.log.write_text("")
    again = fx.run("run-bounded-pipeline.sh", args, env)
    test.assertEqual((again.rc, again.status), (3, "REFUSED"), again.describe())
    test.assertIn("single-use", again.text)
    test.assertIn(approval_sha, again.text)
    test.assertEqual(again.calls, [], "the reused record must be refused before any aws call")
    test.assertEqual(len(fx.reservations()), 1, "a refused reuse must not reserve a second slot")
    return fx


class ApprovalSingleUse(unittest.TestCase):
    def test_a_reused_approval_is_refused_after_a_failed_run(self):
        scenario_reused_approval_is_refused_even_after_a_failed_run(self, failed=True)

    def test_a_reused_approval_is_refused_after_a_successful_run(self):
        scenario_reused_approval_is_refused_even_after_a_failed_run(self, failed=False)

    def test_a_prose_only_change_makes_a_new_record_that_is_accepted_for_a_new_run(self):
        """The hash is of the whole record text: a prose-only change makes a new record that is accepted."""
        fx = S.Fixture(self)
        args, env = fx.exec_ready()
        fx.log.write_text("")
        self.assertEqual(fx.run("run-bounded-pipeline.sh", args, env).rc, 0)
        first_sha = S.sha256_file(fx.aux / "approval.md")
        # a second approval, same configuration, one extra prose line, a NEW run id (the run id is part of the record)
        args2, env2 = fx.exec_ready(pipeline_over={"run_id": "bp-test-run-2"}, serial=2, approval_name="approval-2.md")
        self.assertNotEqual(S.sha256_file(fx.aux / "approval-2.md"), first_sha)
        fx.log.write_text("")
        r2 = fx.run("run-bounded-pipeline.sh", args2, env2)
        self.assertEqual((r2.rc, r2.status), (0, "PASS"), r2.describe())
        self.assertEqual([x["approval_record_sha256"] for x in fx.reservations()], [first_sha, S.sha256_file(fx.aux / "approval-2.md")])

    def test_a_ledger_entry_with_this_records_hash_refuses_the_run_before_any_aws_call(self):
        fx = S.Fixture(self)
        args, env = fx.exec_ready(ledger=False)
        sha = S.sha256_file(fx.aux / "approval.md")
        fx.write_ledger(["0.10"], approvals=[sha])
        fx.log.write_text("")
        r = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertIn("single-use", r.text)
        self.assertEqual(r.calls, [])
        self.assertEqual(len(fx.reservations()), 1)

    def test_a_malformed_approval_hash_in_the_ledger_is_never_ignored(self):
        fx = S.Fixture(self)
        args, env = fx.exec_ready()
        records = fx.ledger_records()
        records.append({"event": "reserve", "run_id": "old", "action": "run-bounded-pipeline", "estimate_usd": "0.10",
                        "run_config_sha256": S.HEX64, "approval_record_sha256": "not-a-hash", "reserved_utc": "2026-11-01T00:00:00Z"})
        fx.ledger_path.write_text("".join(json.dumps(x) + "\n" for x in records))
        fx.log.write_text("")
        r = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((r.rc, r.status), (3, "REFUSED"), r.describe())
        self.assertEqual(r.calls, [])

    def test_mutation_without_the_single_use_check_the_reused_approval_is_not_refused_as_such(self):
        def patch(scripts):
            path = scripts / "lib" / "budget.py"
            text = path.read_text()
            old = "    if approval_sha is not None and approval_sha in approvals:"
            self.assertIn(old, text, "mutation anchor moved: update the mutation")
            path.write_text(text.replace(old, "    if False:", 1))
        for failed in (True, False):
            with self.subTest(failed=failed):
                with self.assertRaises(AssertionError):
                    scenario_reused_approval_is_refused_even_after_a_failed_run(self, patch=patch, failed=failed)


def scenario_estimate_includes_the_idle_tail(test, patch=None):
    fx = S.Fixture(test, patch=patch)
    # 2 x 0.240 x (3600 + 900) / 3600 = 0.60 (hand-derived from emr-pricing.conf and the 900 s idle cap)
    test.assertIn("ESTIMATE-USD: 0.60", fx.dry().out)
    # 4 x 0.240 x (10320 + 900) / 3600 = 2.992 -> 3.00; 173 minutes -> 3.008 -> 3.01 is over the 3 USD cap
    test.assertIn("ESTIMATE-USD: 3.00", fx.dry(core_count=3, max_runtime_minutes=172).out)
    over = fx.dry(core_count=3, max_runtime_minutes=173)
    test.assertEqual((over.rc, over.status), (3, "REFUSED"), over.describe())


class IdleTailInTheEstimate(unittest.TestCase):
    def test_the_estimate_counts_the_idle_tail(self):
        scenario_estimate_includes_the_idle_tail(self)

    def test_mutation_dropping_the_idle_tail_is_caught(self):
        def patch(scripts):
            path = scripts / "lib" / "budget.py"
            text = path.read_text()
            old = "billed_seconds = args.minutes * 60 + args.idle_seconds"
            self.assertIn(old, text, "mutation anchor moved: update the mutation")
            path.write_text(text.replace(old, "billed_seconds = args.minutes * 60", 1))
        with self.assertRaises(AssertionError):
            scenario_estimate_includes_the_idle_tail(self, patch=patch)

    def test_the_idle_cap_is_900_seconds(self):
        fx = S.Fixture(self)
        self.assertEqual(fx.run("run-bounded-pipeline.sh", fx.full_args(max_idle_seconds=901)).rc, 2)
        self.assertEqual(fx.run("run-bounded-pipeline.sh", fx.full_args(max_idle_seconds=59)).rc, 2)
        self.assertEqual(fx.run("run-bounded-pipeline.sh", fx.full_args(max_idle_seconds=900)).rc, 0)
        self.assertEqual(fx.run("run-bounded-pipeline.sh", fx.full_args(max_idle_seconds=60)).rc, 0)
        fx.update_scenario(policy={"AutoTerminationPolicy": {"IdleTimeout": 901}})
        r = fx.execute()
        self.assertEqual((r.rc, last(r)), (4, "cluster-check"), r.describe())


if __name__ == "__main__":
    unittest.main()
