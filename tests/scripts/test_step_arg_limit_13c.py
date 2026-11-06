"""Independent tests of the Phase 13C repair-1 step form (finding C1): every EMR step's HadoopJarStepConfig.Args string must stay
within EMR's 10,280 character limit, and the installed step programs are sha256-pinned on the node.

Expectations come from the AWS API reference limit (10,280 characters per Args string), the plan and the review finding C1, not from
the implementation: the lengths are MEASURED here from the arguments the dry run prints (one word per line, joined with
backslash-newline, so shlex gives the exact Args list EMR would receive) and compared with the script's own STEP-ARG-LENGTHS markers.

  a  a dry run at maximum-length realistic values stays within the limit for every step
  c  boundary: one argument exactly at the limit is accepted; one character over is refused (exit 3, STEP-ARG-TOO-LONG) before any
     cloud call, and with --execute the ledger is unchanged and the approval stays unconsumed
  d  mutation: with the length check neutralised in a SCRATCH copy of pipeline.py the boundary test fails (evidence file written
     when SC_MUTATION_EVIDENCE names a path)
  e  the on-node launcher: a tampered runner or Python program gives STEP-FAIL with nothing run
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sc_support as S
import test_pipeline_bodies as B

LIMIT = 10280
REAL_PIPELINE = S.REPO / "scripts" / "lib" / "pipeline.py"
TOO_LONG = re.compile(r"STEP-ARG-TOO-LONG: step (\S+) argument (\d+) \((\w+)\) has (\d+) characters, over the limit of (\d+)")


def measured(run):
    """step -> list of argument lengths measured from the printed command."""
    return {name: [len(a) for a in S.step_args(run, name)] for name in S.STEP_NAMES}


def marker_lengths(run):
    out = {}
    for line in run.grep(r"^STEP-ARG-LENGTHS: "):
        m = re.match(r"STEP-ARG-LENGTHS: (\S+) limit=(\d+) count=(\d+) max=(\d+) total=(\d+) lengths=([\d,]+)$", line)
        assert m, line
        out[m.group(1)] = dict(limit=int(m.group(2)), count=int(m.group(3)), max=int(m.group(4)), total=int(m.group(5)),
                               lengths=[int(x) for x in m.group(6).split(",")])
    return out


def long_values(fx):
    """Maximum-length realistic values: 63-character bucket, ~900-character keys (S3 allows 1024 bytes), 64-character run id,
    32-character cluster id suffix, 128-character dataset tokens."""
    bucket = "b" * 63

    def ref(n, suffix=""):
        return "s3://%s/%s%s" % (bucket, "k" * n, suffix)
    tokens = {k: {"snapshot": "s" * 128, "retrieval": "r" * 128} for k in S.DATASETS}
    (fx.repo / "inputs/datasets.json").write_text(json.dumps(tokens))
    fx.commit_all()
    return dict(run_id="bp-" + "a" * 61, cluster_id="j-" + "A" * 32, input_prefix=ref(900), output_prefix=ref(900),
                hadoop_submit_jar=ref(900, ".jar"), hadoop_libjars=ref(900, ".jar"), er_jar=ref(900), er_policy=ref(900),
                er_config=ref(900), spark_config_template=ref(900))


class MaximumLengthValues(unittest.TestCase):
    def test_every_step_argument_of_a_maximum_length_dry_run_is_within_the_limit_and_the_markers_agree(self):
        fx = S.Fixture(self)
        values = long_values(fx)
        run = fx.dry(**values)
        self.assertEqual((run.rc, run.status), (0, "DRY-RUN"), run.describe())
        mine = measured(run)
        markers = marker_lengths(run)
        self.assertEqual(sorted(mine), sorted(S.STEP_NAMES))
        self.assertEqual(sorted(markers), sorted(S.STEP_NAMES))
        for name in S.STEP_NAMES:
            with self.subTest(step=name):
                self.assertLessEqual(max(mine[name]), LIMIT, "%s has an Args string over the EMR limit" % name)
                self.assertEqual(markers[name]["limit"], LIMIT)
                self.assertEqual(markers[name]["lengths"], mine[name], "the script's lengths differ from my measurement")
                self.assertEqual(markers[name]["count"], len(mine[name]))
                self.assertEqual(markers[name]["max"], max(mine[name]))
                self.assertEqual(markers[name]["total"], sum(mine[name]))
        # the long values really are in the arguments (the test is not vacuous)
        self.assertGreater(max(max(v) for v in mine.values()), 900)
        self.assertIn("STEP: arg-limit", run.out)
        self.assertIn("STEP-ARG-LIMIT:", run.out)

    def test_the_args_shape_is_launcher_then_pinned_runner_hash_then_step_then_key_value_words(self):
        fx = S.Fixture(self)
        run = fx.dry()
        runner_sha = S.sha256_file(fx.stepbin / "sc-step.sh")
        for name in S.STEP_NAMES:
            with self.subTest(step=name):
                args = S.step_args(run, name)
                self.assertEqual(args[:2], ["bash", "-c"])
                self.assertEqual(args[3], "sc-step")
                self.assertEqual(args[4], runner_sha, "the launcher is told the sha256 of the repository's runner")
                self.assertEqual(args[5], name)
                for word in args[6:]:
                    self.assertRegex(word, r"^[A-Z][A-Z0-9_]*=", "every parameter is a KEY=VALUE word")
                keys = [w.split("=", 1)[0] for w in args[6:] if not w.startswith("SPARK_CONF=")]
                self.assertEqual(len(keys), len(set(keys)), "a parameter key appears twice")

    def test_the_marker_step_does_not_look_like_a_submitted_step(self):
        fx = S.Fixture(self)
        run = fx.dry()
        self.assertIn("arg-limit", run.steps())
        self.assertEqual([s for s in run.steps() if s.startswith("step-")], ["step-" + n for n in S.STEP_NAMES])
        self.assertLess(run.steps().index("plan"), run.steps().index("arg-limit"))
        self.assertLess(run.steps().index("arg-limit"), run.steps().index("g6-gate"))


# ---- boundary ----------------------------------------------------------------------------------------------------------------

def launcher_length(fx, bin_dir):
    env = {"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_BIN_DIR=bin_dir))}
    run = fx.dry(extra_env=env)
    assert run.rc == 0, run.describe()
    return len(S.step_args(run, "stage-in")[2])


def dir_for_launcher(fx, length):
    """A step bin directory that makes the launcher exactly `length` characters (the directory appears once in it)."""
    probe = "/" + "a" * 40
    base = launcher_length(fx, probe)
    wanted = len(probe) + (length - base)
    return "/" + "a" * (wanted - 1)


def scenario_boundary_launcher(test, patch=None):
    fx = S.Fixture(test, patch=patch)
    at_limit = dir_for_launcher(fx, LIMIT)
    ok = fx.dry(extra_env={"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_BIN_DIR=at_limit))})
    test.assertEqual((ok.rc, ok.status), (0, "DRY-RUN"), "a launcher of exactly %d characters must be accepted\n%s" % (LIMIT, ok.describe()))
    test.assertEqual(max(len(a) for a in S.step_args(ok, "spark-job")), LIMIT)
    over_dir = at_limit + "a"
    fx.log.write_text("")
    over = fx.dry(extra_env={"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_BIN_DIR=over_dir))})
    test.assertEqual((over.rc, over.status), (3, "REFUSED"), "one character over the limit must be refused\n" + over.describe())
    test.assertIn("step=arg-limit", over.result)
    m = TOO_LONG.search(over.text)
    test.assertIsNotNone(m, over.text[-600:])
    test.assertEqual((m.group(2), m.group(3), int(m.group(4)), int(m.group(5))), ("2", "launcher", LIMIT + 1, LIMIT))
    test.assertEqual(over.calls, [], "no fake binary (aws, ...) may run before the refusal")
    return fx


def scenario_boundary_parameter(test, patch=None):
    """The same boundary on a KEY=VALUE word: an artifact reference (dataset tokens are capped at 128 characters by the script, an
    S3 reference is not, so a reference is the realistic way to reach the limit)."""
    fx = S.Fixture(test, patch=patch)
    head = "s3://%s/" % ("b" * 63)
    word = "ER_CONFIG_REF="

    def dry(n):
        return fx.dry(er_config=head + "k" * n)
    n_ok = LIMIT - len(word) - len(head)
    ok = dry(n_ok)
    test.assertEqual((ok.rc, ok.status), (0, "DRY-RUN"), ok.describe())
    test.assertEqual(max(len(a) for a in S.step_args(ok, "entity-resolution")), LIMIT)
    over = dry(n_ok + 1)
    test.assertEqual((over.rc, over.status), (3, "REFUSED"), over.describe())
    m = TOO_LONG.search(over.text)
    test.assertIsNotNone(m, over.text[-600:])
    test.assertEqual((m.group(1), m.group(3), int(m.group(4))), ("entity-resolution", "ER_CONFIG_REF", LIMIT + 1))
    test.assertEqual(over.calls, [])


class Boundary(unittest.TestCase):
    def test_a_launcher_of_exactly_the_limit_is_accepted_and_one_over_is_refused_before_any_cloud_call(self):
        scenario_boundary_launcher(self)

    def test_a_parameter_of_exactly_the_limit_is_accepted_and_one_over_is_refused(self):
        scenario_boundary_parameter(self)

    def test_with_execute_a_refused_plan_leaves_the_ledger_unchanged_and_the_approval_unconsumed(self):
        fx = S.Fixture(self)
        args, env = fx.exec_ready()  # a valid approval record and receipt, derived from a valid dry run
        before = fx.ledger_path.read_bytes()
        approval_sha = S.sha256_file(fx.aux / "approval.md")
        approval_before = (fx.aux / "approval.md").read_bytes()
        too_long = dir_for_launcher(fx, LIMIT) + "a"
        env = dict(env, SCHOLARCHAIN_CONFIG_FILE=str(fx.test_config(PIPELINE_POLL_SECONDS="0", PIPELINE_STEP_BIN_DIR=too_long)))
        fx.log.write_text("")
        run = fx.run("run-bounded-pipeline.sh", args, env)
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertIn("step=arg-limit", run.result)
        self.assertIn("STEP-ARG-TOO-LONG", run.text)
        self.assertEqual(run.calls, [], "no aws, hadoop or yarn call may happen")
        self.assertEqual(fx.ledger_path.read_bytes(), before, "the ledger must be unchanged")
        self.assertEqual(fx.reservations(), [])
        self.assertEqual((fx.aux / "approval.md").read_bytes(), approval_before)
        self.assertNotIn(approval_sha, fx.ledger_path.read_text(), "the approval record must not be consumed")
        self.assertFalse((fx.repo / "target" / "pipeline-runs").exists(), "no run directory or manifest may be written")

    def test_a_pinned_limit_outside_1000_to_10280_is_refused(self):
        fx = S.Fixture(self)
        for value in ("999", "10281", "0", "20000"):
            with self.subTest(limit=value):
                env = {"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_ARG_MAX_CHARS=value))}
                run = fx.dry(extra_env=env)
                self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
                self.assertEqual(run.calls, [])
        env = {"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_ARG_MAX_CHARS="1000"))}
        lowered = fx.dry(extra_env=env)
        self.assertEqual(lowered.rc, 0, lowered.describe())
        self.assertEqual(marker_lengths(lowered)["stage-in"]["limit"], 1000, "the limit may be lowered")

    def test_a_lowered_limit_refuses_a_step_that_would_pass_the_default(self):
        fx = S.Fixture(self)
        values = long_values(fx)  # its longest argument is about 1,050 characters, far under 10,280
        default = fx.dry(**values)
        self.assertEqual(default.rc, 0, default.describe())
        self.assertGreater(max(max(v) for v in measured(default).values()), 1000)
        env = {"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_ARG_MAX_CHARS="1000"))}
        run = fx.dry(extra_env=env, **values)
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertIn("STEP-ARG-TOO-LONG", run.text)
        self.assertEqual(run.calls, [])

    def test_the_run_configuration_hash_covers_the_step_bin_directory_and_the_program_hashes(self):
        fx = S.Fixture(self)
        base = fx.run_config_sha(fx.dry())
        moved = fx.dry(extra_env={"SCHOLARCHAIN_CONFIG_FILE": str(fx.test_config(PIPELINE_STEP_BIN_DIR="/opt/other/bin"))})
        self.assertNotEqual(base, fx.run_config_sha(moved), "the node directory of the step programs is part of the approved configuration")
        edited = S.Fixture(self, patch=lambda scripts: (scripts / "emr" / "sc-ceiling-check.py").write_text(
            (scripts / "emr" / "sc-ceiling-check.py").read_text() + "\n# edited\n"))
        self.assertNotEqual(base, edited.run_config_sha(edited.dry()), "the program hashes are part of the approved configuration")

    def test_a_step_program_that_differs_from_the_terraform_pin_refuses_the_plan(self):
        fx = S.Fixture(self)
        manifest = fx.repo / "infra/terraform/emr-step-programs.json"
        pinned = json.loads(manifest.read_text())
        pinned["programs"]["sc-step.sh"] = "0" * 64
        manifest.write_text(json.dumps(pinned))
        fx.commit_all()
        run = fx.dry()
        self.assertEqual((run.rc, run.status), (3, "REFUSED"), run.describe())
        self.assertIn("STEP-PROGRAM-DRIFT", run.text)
        self.assertEqual(run.calls, [])


# ---- mutation proof (d) ------------------------------------------------------------------------------------------------------

def sha(data):
    return hashlib.sha256(data).hexdigest()


class MutationProof(unittest.TestCase):
    CHECK = "        if len(arg) > limit:"

    def test_neutralising_the_length_check_in_a_scratch_copy_makes_the_boundary_tests_fail_and_restoring_it_passes(self):
        original = REAL_PIPELINE.read_bytes()
        real_before = sha(original)
        text = original.decode()
        self.assertEqual(text.count(self.CHECK), 1, "mutation anchor moved: update the mutation")
        mutated = text.replace(self.CHECK, "        if False:", 1).encode()
        self.assertNotEqual(sha(mutated), real_before)
        scratch_dir = Path(tempfile.mkdtemp(prefix="sc-argmut-"))
        self.addCleanup(shutil.rmtree, str(scratch_dir), True)
        scratch = scratch_dir / "pipeline.py"
        lines = ["pipeline.py (real tree) sha256 before: %s" % real_before]

        def writer(data):
            return lambda scripts: (scripts / "lib" / "pipeline.py").write_bytes(data)

        scratch.write_bytes(original)
        scratch.write_bytes(mutated)
        lines.append("scratch copy mutated (check `%s` replaced by `if False:`) sha256: %s" % (self.CHECK.strip(), sha(scratch.read_bytes())))
        outcomes = {}
        for label, scenario in (("launcher boundary", scenario_boundary_launcher), ("parameter boundary", scenario_boundary_parameter)):
            with self.assertRaises(AssertionError) as caught:
                scenario(self, patch=writer(scratch.read_bytes()))
            outcomes[label] = str(caught.exception).splitlines()[0][:140]
            lines.append("MUTATED   %-19s -> test FAILS as required: %s" % (label, outcomes[label]))
        scratch.write_bytes(original)
        identical = scratch.read_bytes() == original and sha(scratch.read_bytes()) == real_before
        lines.append("restored byte-identical: %s (sha256 %s)" % (identical, sha(scratch.read_bytes())))
        self.assertTrue(identical)
        scenario_boundary_launcher(self, patch=writer(scratch.read_bytes()))
        scenario_boundary_parameter(self, patch=writer(scratch.read_bytes()))
        lines.append("RESTORED  launcher boundary / parameter boundary -> both PASS")
        real_after = sha(REAL_PIPELINE.read_bytes())
        lines.append("pipeline.py (real tree) sha256 after:  %s  unchanged: %s" % (real_after, real_after == real_before))
        self.assertEqual(real_after, real_before, "the real tree must never be modified")
        target = os.environ.get("SC_MUTATION_EVIDENCE")
        if target:
            Path(target).write_text("\n".join(lines) + "\n")


# ---- (e) the on-node launcher -----------------------------------------------------------------------------------------------

def run_step(h, name, extra_args=(), drop_prefixes=(), **env):
    """Run the dry run's Args for `name` directly (argv list) on the fake node, optionally editing the parameters."""
    args = [a for a in S.step_args(h.dry, name) if not a.startswith(tuple(drop_prefixes))] + list(extra_args)
    h.fx.log.write_text("")
    done = subprocess.run(args, env=h.body_env(**env), cwd=str(h.fx.repo), capture_output=True, text=True, timeout=120)
    return done, h.fx.calls()


NOTHING_RUN = ("aws", "hadoop", "yarn", "spark-submit", "java")


class OnNodeLauncher(unittest.TestCase):
    def assert_nothing_ran(self, calls, allowed=()):
        ran = [c["tool"] for c in calls if c["tool"] in NOTHING_RUN and c["tool"] not in allowed]
        self.assertEqual(ran, [], "something ran after a failed integrity check: %s" % ran)
        self.assertEqual([c for c in calls if c["tool"] == "timeout"], [], "the timeout wrapper must not start")

    def test_a_tampered_runner_fails_the_launcher_and_nothing_runs(self):
        for step in ("stage-in", "spark-job"):
            with self.subTest(step=step):
                h = B.Harness(self)
                with open(h.fx.stepbin / "sc-step.sh", "a") as handle:
                    handle.write("\necho tampered >&2\n")
                done, calls = run_step(h, step)
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn("STEP-FAIL sc-step: sha256 mismatch for", done.stderr)
                self.assertIn("the installed step runner is not the approved one", done.stderr)
                self.assertNotIn("tampered", done.stderr + done.stdout, "the tampered runner must never execute")
                self.assert_nothing_ran(calls)

    def test_a_missing_runner_fails_the_launcher_and_nothing_runs(self):
        h = B.Harness(self)
        (h.fx.stepbin / "sc-step.sh").unlink()
        done, calls = run_step(h, "copy-out")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("STEP-FAIL sc-step", done.stderr)
        self.assert_nothing_ran(calls)

    def test_a_runner_installed_from_a_different_version_is_refused(self):
        h = B.Harness(self)
        text = (h.fx.stepbin / "sc-step.sh").read_text()
        (h.fx.stepbin / "sc-step.sh").write_text(text.replace("STEP-LOG", "STEP-NOTE"))
        done, calls = run_step(h, "stage-in")
        self.assertEqual(done.returncode, 1)
        self.assertIn("not the approved one", done.stderr)
        self.assert_nothing_ran(calls)

    def test_a_tampered_ceiling_program_stops_hadoop_prep_before_the_hadoop_client(self):
        h = B.Harness(self)
        with open(h.fx.stepbin / "sc-ceiling-check.py", "a") as handle:
            handle.write("\nprint('tampered')\n")
        done, calls = run_step(h, "hadoop-prep")
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("STEP-FAIL hadoop-prep: sha256 mismatch for the installed step program sc-ceiling-check.py", done.stderr)
        self.assertNotIn("tampered", done.stdout)
        self.assertEqual([a for a in B.argv_of(calls, "hadoop") if a[:1] == ["jar"]], [], "the hadoop client must not start")
        self.assertEqual(B.inner_timeouts(calls), [])

    def test_a_tampered_renderer_or_verifier_stops_the_spark_job_before_spark_submit(self):
        for program in ("sc-render-spark-config.py", "sc-class-origin-verify.py"):
            with self.subTest(program=program):
                h = B.Harness(self)
                h.stage_for_spark_job()
                with open(h.fx.stepbin / program, "a") as handle:
                    handle.write("\nprint('tampered')\n")
                done, calls = run_step(h, "spark-job")
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertIn("STEP-FAIL spark-job: sha256 mismatch for the installed step program %s" % program, done.stderr)
                self.assertEqual(B.argv_of(calls, "spark-submit"), [], "the Spark job must not start")
                self.assertEqual(B.inner_timeouts(calls), [])

    def test_a_missing_python_program_is_reported_by_name(self):
        h = B.Harness(self)
        (h.fx.stepbin / "sc-ceiling-check.py").unlink()
        done, calls = run_step(h, "hadoop-prep")
        self.assertEqual(done.returncode, 1)
        self.assertIn("the installed step program sc-ceiling-check.py is missing", done.stderr)
        self.assertEqual([a for a in B.argv_of(calls, "hadoop") if a[:1] == ["jar"]], [])

    def test_parameters_outside_the_allow_list_given_twice_or_missing_fail_closed(self):
        h = B.Harness(self)
        done, calls = run_step(h, "stage-in", extra_args=["EVIL=1"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("parameter EVIL is not accepted by this step", done.stderr)
        self.assert_nothing_ran(calls)
        done, calls = run_step(h, "stage-in", extra_args=["REGION=us-west-2"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("parameter REGION was given twice", done.stderr)
        self.assert_nothing_ran(calls)
        done, calls = run_step(h, "stage-in", drop_prefixes=["REGION="])
        self.assertEqual(done.returncode, 1)
        self.assertIn("missing parameter REGION", done.stderr)
        self.assert_nothing_ran(calls)
        # a parameter of another step is not accepted either
        done, calls = run_step(h, "stage-in", extra_args=["OUTPUT_PREFIX=s3://x/y"])
        self.assertIn("parameter OUTPUT_PREFIX is not accepted by this step", done.stderr)

    def test_an_inherited_environment_variable_cannot_stand_in_for_a_missing_parameter(self):
        h = B.Harness(self)
        done, calls = run_step(h, "stage-in", drop_prefixes=["REGION="], REGION="us-east-2")
        self.assertEqual(done.returncode, 1)
        self.assertIn("missing parameter REGION", done.stderr)
        self.assert_nothing_ran(calls)

    def test_a_parameter_value_is_never_evaluated(self):
        h = B.Harness(self)
        marker = h.fx.aux / "evaluated"
        done, calls = run_step(h, "stage-in", drop_prefixes=["REGION="], extra_args=["REGION=$(touch %s)" % marker])
        self.assertFalse(marker.exists(), "a parameter value was executed")


if __name__ == "__main__":
    unittest.main()
