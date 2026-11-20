"""Subphase 13C: 13B reviewer findings B1 to B4 for run-bounded-pipeline.sh, each tested at its boundary.

B1  every step body runs on the node under `timeout --kill-after` of its timeout_seconds (stage-in, copy-out and the
    localize copies included); a hung aws or hadoop copy is killed at the step timeout; the printed text is accurate.
B2  the ledger lives under HOME, outside the repository; an absent ledger refuses --execute until the human runs
    --init-ledger, which records who and when and refuses when a ledger exists.
B3  the estimate adds the auto-termination idle tail; the idle cap is 900 s.
B4  an approval record is single-use: the ledger stores its sha256 and refuses any later run with the same record.

Expectations are hand-derived; nothing here calls AWS (fake aws, hadoop, yarn and a faithful timeout shim).
"""
import json
import os
import re
import shutil
import signal
import subprocess
import time
import unittest

from helpers import SCRIPTS_DIR, sha256_bytes, write_exec
from pipeline_helpers import REAL_TIMEOUT_PY, RUN, PipelineFixture

STEPS = ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def bodies(stdout):
    found = {}
    for name in STEPS:
        found[name] = stdout.split("STEP-BODY-BEGIN: %s\n" % name, 1)[1].split("STEP-BODY-END: %s\n" % name, 1)[0]
    return found


class B1WrapperTests(PipelineFixture):
    def test_every_printed_step_body_runs_under_timeout_kill_after_of_its_own_timeout(self):
        result = self.dry()
        self.assertEqual(result.rc, 0, result.out)
        seconds = dict(re.findall(r"STEP-TIMEOUT: (\S+) (\d+)s", result.stdout))
        self.assertEqual(sorted(seconds), sorted(STEPS))
        # Finding C1: the printed step is a launcher plus KEY=VALUE parameters; the on-node timeout is in the installed runner.
        runner = read(os.path.join(SCRIPTS_DIR, "emr", "sc-step.sh"))
        self.assertIn('timeout --kill-after="${KILL_AFTER}" "${STEP_SECONDS}" bash "${SELF}" __body "${STEP_NAME}"', runner)
        for name, body in bodies(result.stdout).items():
            with self.subTest(name):
                self.assertIn("STEP_SECONDS=%s " % seconds[name], body)
                self.assertIn("KILL_AFTER=60 ", body)
                self.assertTrue(body.startswith("bash \\\n  -c \\\n  'set -euo pipefail; f="), body[:80])
        # hand-derived from 90 minutes (5400 s) and the pinned weights 5/20/20/5/40/10 percent
        self.assertEqual({k: int(v) for k, v in seconds.items()}, {"stage-in": 270, "hadoop-prep": 1080, "entity-resolution": 1080, "spark-class-origin": 270, "spark-job": 2160, "copy-out": 540})

    def test_the_printed_text_says_the_whole_body_is_bounded(self):
        out = self.dry().stdout
        for name in STEPS:
            self.assertRegex(out, r"STEP-TIMEOUT: %s \d+s \(the whole step body, including every copy, runs on the node under timeout --kill-after=60s in its own process group, which is sent TERM and then KILL after the grace on timeout or cancel; YARN applications are also killed by tag when it fires\)" % name)
        self.assertNotIn("the body runs under timeout;", out)

    def test_the_step_json_carries_the_wrapped_body(self):
        out = self.dry().stdout
        for name, body in bodies(out).items():
            self.assertIn("STEP_SECONDS", body, name)
        self.assertEqual(len(re.findall(r"aws emr add-steps", out)), 6)


class B1HangTests(PipelineFixture):
    """A hung copy is killed at the step timeout. The faithful timeout shim kills the step's process group like GNU timeout."""

    def setUp(self):
        super().setUp()
        self.node_config()
        self.run_root = os.path.join(self.mnt, "runs", RUN)
        self.realbin = os.path.join(self.tmp, "realbin")
        os.makedirs(self.realbin)
        write_exec(os.path.join(self.realbin, "timeout"), "#!/usr/bin/env python3\n" + REAL_TIMEOUT_PY)

    def short(self, body, seconds=2, kill_after=1):
        body = re.sub(r"STEP_SECONDS=\d+", "STEP_SECONDS=%d" % seconds, body, count=1)
        return re.sub(r"KILL_AFTER=\d+", "KILL_AFTER=%d" % kill_after, body, count=1)

    def run_real(self, body, extra_env=None, signal_after=None, ready_file=None):
        env = dict(self.body_env_cache)
        env["PATH"] = self.realbin + ":" + env["PATH"]
        env.update(extra_env or {})
        started = time.time()
        proc = subprocess.Popen(["bash", "-c", body], env=env, cwd=self.tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        if signal_after is not None:
            if ready_file is not None:
                # signal only once the stuck copy has started (the launcher and runner start-up time varies under load)
                deadline = time.time() + 30
                while time.time() < deadline and not (os.path.exists(ready_file) and open(ready_file, encoding="utf-8").read().strip()):
                    time.sleep(0.05)
            time.sleep(signal_after)
            os.kill(proc.pid, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            for kill in (lambda: os.killpg(proc.pid, signal.SIGKILL), proc.kill):
                try:
                    kill()
                except (ProcessLookupError, PermissionError):
                    pass
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                pass  # an orphaned child still holds the pipe; the failure below is what matters
            self.fail("the step was NOT killed by its on-node timeout (the hung copy ran past 60 s)")
        return proc.returncode, out, err, time.time() - started

    def test_a_hanging_aws_s3_cp_in_stage_in_is_killed_at_the_step_timeout(self):
        body = self.short(self.step_body("stage-in"))
        rc, out, err, elapsed = self.run_real(body, {"FAKE_AWS_HANG": "cp", "FAKE_S3_TOTAL": "1024"})
        self.assertEqual(rc, 124, out + err)
        self.assertIn("STEP-FAIL stage-in: exceeded the 2s step timeout (exit 124)", err)
        self.assertLess(elapsed, 30)
        self.assertTrue(any(a.startswith("s3 cp") for a in self.aws_calls()), "the copy had started")

    def test_a_hanging_aws_s3_cp_in_copy_out_is_killed_at_the_step_timeout(self):
        for part in ("hadoop", "er", "spark", "results", "config"):
            os.makedirs(os.path.join(self.run_root, part))
            with open(os.path.join(self.run_root, part, "f.txt"), "w", encoding="utf-8") as handle:
                handle.write(part)
        body = self.short(self.step_body("copy-out"))
        rc, out, err, elapsed = self.run_real(body, {"FAKE_AWS_HANG": "cp"})
        self.assertEqual(rc, 124, out + err)
        self.assertIn("STEP-FAIL copy-out: exceeded the 2s step timeout (exit 124)", err)
        self.assertLess(elapsed, 30)

    def test_a_hanging_hadoop_fs_copy_in_the_localize_function_is_killed_at_the_step_timeout(self):
        os.makedirs(os.path.join(self.run_root, "inputs"))
        body = self.short(self.step_body("hadoop-prep"))  # the default references are s3:// URIs, localized with hadoop fs -copyToLocal
        rc, out, err, elapsed = self.run_real(body, {"FAKE_HADOOP_HANG": "1"})
        # hadoop-prep is a YARN step: its TERM trap waits for the foreground copy, so with a timeout that signals only its
        # direct child the body may need the KILL (137) instead of ending on the TERM (124).
        self.assertIn(rc, (124, 137), out + err)
        self.assertRegex(err, r"STEP-FAIL hadoop-prep: exceeded the 2s step timeout \(exit (124|137)\)")
        self.assertTrue(any(c.startswith("hadoop fs -copyToLocal") for c in self.node_calls()), "the localize copy had started")
        self.assertLess(elapsed, 30)

    def test_a_step_that_finishes_inside_its_timeout_keeps_its_own_exit_status(self):
        body = self.short(self.step_body("stage-in"), seconds=30, kill_after=5)
        rc, out, err, _ = self.run_real(body, {"FAKE_S3_TOTAL": "1024"})
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("exceeded", err)
        shutil.rmtree(self.run_root)
        body = self.short(self.step_body("stage-in"), seconds=30, kill_after=5)
        rc, out, err, _ = self.run_real(body, {"FAKE_S3_TOTAL": "999999999999"})
        self.assertEqual(rc, 1, "a failing body's status passes through the wrapper")
        self.assertIn("exceeds the", err)

    def test_a_term_sent_to_the_wrapper_is_forwarded_to_the_timed_body(self):
        body = self.short(self.step_body("stage-in"), seconds=300, kill_after=5)
        rc, out, err, elapsed = self.run_real(body, {"FAKE_AWS_HANG": "cp"}, signal_after=1.5)
        self.assertNotEqual(rc, 0, out + err)
        self.assertLess(elapsed, 30, "an EMR cancel (TERM) ends the step instead of waiting for the hung copy")

    def alive(self, pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def read_pid(self, path):
        for _ in range(50):
            if os.path.exists(path) and open(path, encoding="utf-8").read().strip():
                return int(open(path, encoding="utf-8").read().strip())
            time.sleep(0.1)
        self.fail("the stuck copy never started")

    def wait_dead(self, pid, seconds=5):
        end = time.time() + seconds
        while time.time() < end:
            if not self.alive(pid):
                return True
            time.sleep(0.1)
        return False

    def test_a_term_ignoring_grandchild_is_dead_after_the_step_timeout(self):
        # The stuck `aws s3 cp` ignores SIGTERM and the timeout shim signals only its direct child (the worst case), so only
        # the wrapper's process-group kill can end it.
        pidfile = os.path.join(self.tmp, "stuck.pid")
        body = self.short(self.step_body("stage-in"))
        rc, out, err, elapsed = self.run_real(body, {"FAKE_AWS_HANG": "cp", "FAKE_AWS_IGNORE_TERM": "1", "FAKE_AWS_PIDFILE": pidfile, "FAKE_S3_TOTAL": "1024"})
        pid = self.read_pid(pidfile)
        self.addCleanup(lambda: self.alive(pid) and os.kill(pid, signal.SIGKILL))
        self.assertEqual(rc, 124, out + err)
        self.assertTrue(self.wait_dead(pid), "a TERM-ignoring grandchild survived the timed-out step")
        self.assertIn("STEP-FAIL stage-in: exceeded the 2s step timeout (exit 124)", err)
        self.assertIn("STEP-WARN stage-in: processes of the step process group", err)
        self.assertLess(elapsed, 30)

    def test_a_term_ignoring_grandchild_is_dead_after_a_cancel(self):
        pidfile = os.path.join(self.tmp, "stuck2.pid")
        body = self.short(self.step_body("stage-in"), seconds=300, kill_after=1)
        rc, out, err, elapsed = self.run_real(body, {"FAKE_AWS_HANG": "cp", "FAKE_AWS_IGNORE_TERM": "1", "FAKE_AWS_PIDFILE": pidfile, "FAKE_S3_TOTAL": "1024"}, signal_after=0.5, ready_file=pidfile)
        pid = self.read_pid(pidfile)
        self.addCleanup(lambda: self.alive(pid) and os.kill(pid, signal.SIGKILL))
        self.assertNotEqual(rc, 0, out + err)
        self.assertTrue(self.wait_dead(pid), "a TERM-ignoring grandchild survived the cancelled step")
        self.assertLess(elapsed, 30)

    def test_a_step_that_ends_cleanly_leaves_no_warning_and_no_job_control_noise(self):
        body = self.short(self.step_body("stage-in"), seconds=30, kill_after=5)
        rc, out, err, _ = self.run_real(body, {"FAKE_S3_TOTAL": "1024"})
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("STEP-WARN", err)
        self.assertNotRegex(err, r"\[\d+\][+-]?\s+(Done|Exit|Terminated)")

    def test_the_wrapper_leaves_no_temp_file(self):  # finding C1: the installed runner needs no private body file any more
        before = set(os.listdir(self.tmp))
        body = self.short(self.step_body("stage-in"), seconds=30, kill_after=5)
        self.run_real(body, {"FAKE_S3_TOTAL": "1024"})
        self.assertEqual([n for n in set(os.listdir(self.tmp)) - before if n.startswith("scholarchain-step.")], [])


class CopyOutPartialRunTests(PipelineFixture):
    """Follow-up defect 1: the copy-out manifest lists only the parts that exist, like the size and copy loops."""

    def setUp(self):
        super().setUp()
        self.node_config()
        self.run_root = os.path.join(self.mnt, "runs", RUN)

    def make_parts(self, parts):
        for part in parts:
            os.makedirs(os.path.join(self.run_root, part, "sub"))
            with open(os.path.join(self.run_root, part, "sub", "f.txt"), "w", encoding="utf-8") as handle:
                handle.write(part + "\n")

    def manifest_files(self):
        with open(os.path.join(self.run_root, "copyout-manifest.sha256"), encoding="utf-8") as handle:
            return sorted(line.rstrip("\n").split("  ", 1)[1] for line in handle if line.strip())

    def copied_parts(self):
        return sorted(a.split()[2].rstrip("/").split("/")[-1] for a in self.aws_calls() if a.startswith("s3 cp") and "--recursive" in a)

    def test_a_partial_run_with_missing_parts_copies_out_and_lists_only_the_present_parts(self):
        for present in (("results", "config"), ("spark",), ("hadoop", "er", "spark")):
            with self.subTest(present=present):
                shutil.rmtree(self.run_root, ignore_errors=True)
                open(self.log, "w").close()
                self.make_parts(present)
                body = self.step_body("copy-out")
                result = self.run_body(body)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.manifest_files(), sorted("%s/sub/f.txt" % part for part in present))
                self.assertEqual(self.copied_parts(), sorted(present))
                self.assertNotIn("STEP-FAIL", result.stderr)

    def test_a_run_with_every_part_missing_fails_with_a_marker(self):
        os.makedirs(self.run_root)
        result = self.run_body(self.step_body("copy-out"))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("STEP-FAIL copy-out: nothing to copy out", result.stderr)
        self.assertEqual([a for a in self.aws_calls() if a.startswith("s3 cp")], [])

    def test_a_real_find_error_still_fails_with_a_marker_and_copies_nothing(self):
        self.make_parts(("results", "config"))
        write_exec(os.path.join(self.nodebin, "find"), "#!/bin/bash\necho 'find: simulated failure' >&2\nexit 2\n")
        result = self.run_body(self.step_body("copy-out"))
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        # Phase 15 P23: the selective copy-out lists each part before sizing it, so a find failure now stops the step at the listing
        self.assertIn("STEP-FAIL copy-out: could not list %s/results" % self.run_root, result.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.run_root, "copyout-manifest.sha256")), "no manifest is written")
        self.assertEqual([a for a in self.aws_calls() if a.startswith("s3 cp")], [])


class B2LedgerTests(PipelineFixture):
    def test_an_absent_ledger_refuses_execute_before_any_aws_call(self):
        args = self.ready()
        os.remove(self.ledger_path())
        result = self.execute(args)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("does not exist", result.out)
        self.assertIn("--init-ledger", result.out)
        self.assertIn("never read as zero runs", result.out)
        self.assertEqual(self.calls(), [])
        self.assertFalse(os.path.exists(self.ledger_path()), "a refused run must not create the ledger")

    def test_the_dry_run_reports_that_an_absent_ledger_would_refuse_execute(self):
        os.remove(self.ledger_path())
        result = self.dry()
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("--execute would be REFUSED", result.out)
        self.assertIn("does not exist", result.out)
        self.assertIn("G6-STATUS: --execute would be refused", result.stdout)
        self.assertFalse(os.path.exists(self.ledger_path()))

    def test_init_ledger_creates_it_with_who_and_when_and_makes_no_cloud_call(self):
        os.remove(self.ledger_path())
        result = self.run_script("run-bounded-pipeline.sh", "--init-ledger")
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS"), result.result_line())
        self.assertIn("no cloud call was made", result.stdout)
        self.assertEqual(self.calls(), [])
        with open(self.ledger_path(), encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["event"], "init")
        self.assertEqual(lines[0]["initialized_by"], subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip())
        self.assertRegex(lines[0]["initialized_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(oct(os.stat(self.ledger_path()).st_mode & 0o777), "0o600")

    def test_init_ledger_refuses_when_a_ledger_exists_and_changes_nothing(self):
        with open(self.ledger_path(), "rb") as handle:
            before = handle.read()
        result = self.run_script("run-bounded-pipeline.sh", "--init-ledger")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("already exists", result.out)
        with open(self.ledger_path(), "rb") as handle:
            self.assertEqual(handle.read(), before)

    def test_init_ledger_takes_no_other_argument_and_no_execute(self):
        self.assertEqual(self.run_script("run-bounded-pipeline.sh", "--init-ledger", "--execute").rc, 2)
        self.assertEqual(self.run_script("run-bounded-pipeline.sh", "--init-ledger", "--cluster-id", "j-ABC123DEF456").rc, 2)

    def test_the_ledger_lives_under_home_outside_the_repository_and_a_pinned_path_ignores_the_environment(self):
        os.remove(self.ledger_path())
        result = self.run_script("run-bounded-pipeline.sh", "--init-ledger", EMR_LEDGER_PATH=os.path.join(self.repo, "target", "ledger.jsonl"))
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, ".scholarchain", "emr-ledger", "runs.jsonl")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "ledger.jsonl")))
        self.assertTrue(self.tree_clean())

    def test_a_ledger_configured_inside_the_repository_is_refused(self):
        os.remove(self.ledger_path())
        self.use_config(EMR_LEDGER_PATH="~/.scholarchain/../repo/ledger.jsonl")
        self.assertNotEqual(self.run_script("run-bounded-pipeline.sh", "--init-ledger").rc, 0)
        self.use_config(EMR_LEDGER_PATH="target/emr-ledger/runs.jsonl")
        result = self.run_script("run-bounded-pipeline.sh", "--init-ledger")
        self.assertEqual(result.rc, 2, result.out)
        self.assertIn("must be under ~/.scholarchain/", result.out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "emr-ledger")))

    def test_the_reservation_survives_removing_the_repository_target_directory(self):
        result = self.execute(self.ready())
        self.assertEqual(result.rc, 0, result.out)
        shutil.rmtree(os.path.join(self.repo, "target"), ignore_errors=True)  # what `sbt clean` does
        with open(self.ledger_path(), encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        self.assertEqual([entry["event"] for entry in lines], ["init", "reserve"])

    def test_a_deleted_ledger_refuses_instead_of_reopening_the_caps(self):
        args = self.ready()
        os.remove(self.ledger_path())
        self.assertEqual(self.execute(args).rc, 3)


class B3EstimateTests(PipelineFixture):
    def test_the_dry_run_estimate_includes_the_idle_tail(self):
        out = self.dry().stdout
        # 3 x 0.24 x (5400 s + 900 s idle) / 3600 = 1.26
        self.assertIn("ESTIMATE-USD: 1.26", out)
        self.assertIn('"idle_timeout_seconds": 900', out)
        self.assertIn('"billed_seconds": 6300', out)

    def test_a_tighter_idle_cap_lowers_the_estimate_and_a_looser_one_is_a_usage_error(self):
        # 3 x 0.24 x (5400 s + 300 s) / 3600 = 0.72 x 1.58333 = 1.14
        self.assertIn("ESTIMATE-USD: 1.14", self.dry_with_idle("300").stdout)
        self.assertEqual(self.dry_with_idle("901").rc, 2)
        self.assertEqual(self.dry_with_idle("3600").rc, 2)

    def dry_with_idle(self, seconds):
        return self.run_pipeline("--max-idle-seconds", seconds)

    def test_the_idle_cap_in_the_run_configuration_is_900(self):
        self.assertIn("at most 900 s", self.dry().stdout)


class B4SingleUseApprovalTests(PipelineFixture):
    def test_the_same_approval_record_cannot_start_a_second_run_even_after_a_failed_one(self):
        args = self.ready()
        first = self.execute(args, FAKE_EMR_STEP_STATE_2="FAILED")
        self.assertEqual(first.rc, 4, first.out)  # the first run failed after reserving
        calls_after_first = len(self.calls())
        second = self.execute(args)
        self.assertEqual(second.rc, 3, second.out)
        self.assertIn("this approval record", second.out)
        self.assertIn("already started a run", second.out)
        self.assertIn("single-use", second.out)
        self.assertEqual(len(self.calls()), calls_after_first, "the reuse is refused before any aws call")
        with open(self.ledger_path(), encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 2, "no second reservation")

    def test_a_new_record_with_the_same_content_but_a_serial_line_is_a_new_approval(self):
        first_args = self.ready(serial=1)
        self.assertEqual(self.execute(first_args).rc, 0)
        second_args = self.ready(serial=2, **{"--run-id": "bp-test-0002"})
        self.setUp_clean()
        self.assertEqual(self.execute(second_args).rc, 0)
        with open(self.ledger_path(), encoding="utf-8") as handle:
            reserves = [json.loads(line) for line in handle][1:]
        self.assertEqual(len({entry["approval_record_sha256"] for entry in reserves}), 2)

    def test_the_stored_hash_is_the_sha256_of_the_record_file(self):
        args = self.ready()
        self.assertEqual(self.execute(args).rc, 0)
        with open(self.ledger_path(), encoding="utf-8") as handle:
            reserve = [json.loads(line) for line in handle][1]
        with open(self.record_path, "rb") as handle:
            self.assertEqual(reserve["approval_record_sha256"], sha256_bytes(handle.read()))

    def setUp_clean(self):
        """Fresh fake call logs between sub-cases."""
        for path in (self.log, self.log + ".steps"):
            if os.path.exists(path):
                open(path, "w").close()


if __name__ == "__main__":
    unittest.main()
