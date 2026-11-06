"""Subphase 13C repair round 1, finding C1: EMR accepts at most 10,280 characters per string in a step's
HadoopJarStepConfig.Args, so the static program text is installed (sha256-pinned bootstrap artifacts) and each step is a short
launcher plus KEY=VALUE parameters.

Covered here, with fake binaries only (no cloud call, no network):
  * maximum-length realistic values (63-character buckets, ~900-character prefixes and references, a 64-character run id, a
    32-character cluster id, 128-character dataset tokens): every step argument is printed, checked and far below the limit;
  * an oversized argument is refused with exit 3, the STEP: arg-limit marker and the offending step and length BEFORE any fake
    aws, hadoop or yarn call, the ledger reservation and the approval; the boundary (exactly 10,280 passes, 10,281 fails);
  * the pinned limit can be lowered but never raised and ignores the environment;
  * on-node sha256 verification of the installed runner and of every installed Python program fails closed and runs nothing;
  * the runner's parameter allow-list (unknown, duplicate, missing key; inherited environment; values never evaluated);
  * the Terraform-side manifest equals the files and the pinned directory.
Expectations are hand-derived: the limit is the AWS API reference value, 10,280.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

from helpers import REAL_REPO, SCRIPTS_DIR
from pipeline_helpers import JOB_SHA, PIPELINE_FIXTURES, RUN, PipelineFixture, read

LIMIT = 10280
STEPS = ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out")
BUCKET63 = "b" * 63
LONG_KEY = "/".join("x" * 63 for _ in range(14))  # 14 segments of 63 characters: 895 characters
RUN64 = "bp-" + "a" * 61
CLUSTER_MAX = "j-" + "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6"  # 2 + 32 characters
TOKEN128 = "s" * 128
EMR_DIR = os.path.join(SCRIPTS_DIR, "emr")


def sha_file(name):
    with open(os.path.join(EMR_DIR, name), "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def ref(name, key=LONG_KEY):
    return "s3://%s/%s/%s" % (BUCKET63, key, name)


class MaximumValues(PipelineFixture):
    """A pipeline argument list at the longest realistic values."""

    def max_overrides(self):
        datasets = os.path.join(self.inputs, "datasets-max.json")
        with open(datasets, "w", encoding="utf-8") as handle:
            json.dump({s: {"snapshot": TOKEN128, "retrieval": TOKEN128} for s in ("dblp", "openalex", "crossref", "orcid")}, handle)
        return {
            "--cluster-id": CLUSTER_MAX,
            "--run-id": RUN64,
            "--input-prefix": "s3://%s/%s" % (BUCKET63, LONG_KEY),
            "--output-prefix": "s3://%s/%s" % (BUCKET63, LONG_KEY),
            "--hadoop-submit-jar": ref("hadoop-submit.jar"),
            "--hadoop-libjars": ref("hadoop-bundle.jar"),
            "--er-jar": ref("er.jar"),
            "--er-policy": ref("er-policy.json"),
            "--er-config": ref("er-config.json"),
            "--spark-config-template": ref("spark-template.json"),
            "--datasets-manifest": datasets,
        }

    def parse_lengths(self, stdout):
        found = {}
        for line in stdout.splitlines():
            if line.startswith("STEP-ARG-LENGTHS: "):
                m = re.match(r"STEP-ARG-LENGTHS: (\S+) limit=(\d+) count=(\d+) max=(\d+) total=(\d+) lengths=([\d,]+)$", line)
                self.assertIsNotNone(m, line)
                found[m.group(1)] = dict(limit=int(m.group(2)), count=int(m.group(3)), max=int(m.group(4)), total=int(m.group(5)), lengths=[int(n) for n in m.group(6).split(",")])
        return found


class MaximumLengthTests(MaximumValues):
    def test_every_step_argument_is_far_below_the_emr_limit_at_maximum_realistic_values(self):
        result = self.dry(**self.max_overrides())
        self.assertEqual(result.rc, 0, result.out)
        lengths = self.parse_lengths(result.stdout)
        self.assertEqual(sorted(lengths), sorted(STEPS))
        self.assertIn("STEP: arg-limit", result.stdout.splitlines())
        self.assertEqual(len(RUN64), 64)
        for name in STEPS:
            argv = self.step_argv(name, **self.max_overrides())
            printed = lengths[name]
            self.assertEqual([len(a) for a in argv], printed["lengths"], "the printed lengths are the lengths of the arguments EMR would receive")
            self.assertEqual(printed["limit"], LIMIT)
            self.assertEqual(printed["count"], len(argv))
            self.assertEqual(printed["total"], sum(printed["lengths"]))
            for index, length in enumerate(printed["lengths"]):
                print("max-values step=%-19s arg[%2d] length=%5d  %s" % (name, index, length, argv[index][:44].replace("\n", " ")))
                self.assertLessEqual(length, LIMIT, "%s arg %d" % (name, index))
                self.assertLess(length, LIMIT // 5, "%s arg %d must keep a margin of at least 80 percent below the limit" % (name, index))
            self.assertLess(printed["max"], 1500, name)
            self.assertEqual(argv[:2], ["bash", "-c"])
        # the longest argument anywhere is an S3 reference or prefix (about 1,000 characters), not the 293-character static launcher
        longest = len("OUTPUT_PREFIX=") + len("s3://%s/%s" % (BUCKET63, LONG_KEY)) + 1 + len(RUN64)
        self.assertEqual(max(v["max"] for v in lengths.values()), longest)
        self.assertEqual(self.parse_lengths(result.stdout)["copy-out"]["max"], longest)

    def test_retained_dry_run_prints_every_argument_length(self):
        """The dry run at maximum-length realistic values prints, for every step, each argument's length and the total. When
        SC_ARG_LENGTH_EVIDENCE names a file, the marker lines and the per-argument table are written there (the retained 13C
        repair-round-1 evidence); the assertions run either way."""
        result = self.dry(**self.max_overrides())
        self.assertEqual(result.rc, 0, result.out)
        keep = ("STEP:", "PLAN: run-id", "PLAN: step-", "PLAN: artifact-sha256", "STEP-ARG-LENGTHS:", "STEP-ARG-LIMIT:", "STEP-TIMEOUT:", "RUN-CONFIG-SHA256:", "G6-STATUS:", "RESULT:")
        lines = ["# 13C repair round 1, finding C1: dry run at maximum-length realistic values (63-character bucket, 895-character prefix and",
                 "# references, 64-character run id, 32-character cluster id suffix, 128-character dataset tokens). Fake binaries, no cloud call.",
                 "# produced by: SC_ARG_LENGTH_EVIDENCE=<file> python3 -m unittest test_c1_step_args.MaximumLengthTests.test_retained_dry_run_prints_every_argument_length",
                 "# (cd scripts/tests). Lines kept from the dry run stdout: " + ", ".join(keep), ""]
        lines += [l for l in result.stdout.splitlines() if l.startswith(keep)]
        lines += ["", "# per-argument lengths (KEY and length only; the EMR limit is %d characters per argument)" % LIMIT]
        grand = 0
        for name in STEPS:
            argv = self.step_argv(name, **self.max_overrides())
            total = sum(len(a) for a in argv)
            grand += total
            lines.append("step %s: %d arguments, longest %d, total %d" % (name, len(argv), max(len(a) for a in argv), total))
            for index, arg in enumerate(argv):
                label = arg.split("=", 1)[0] if re.match(r"^[A-Z][A-Z0-9_]*=", arg) else ("launcher" if arg.startswith("set -euo") else arg)
                lines.append("  arg[%2d] %-26s %6d" % (index, label, len(arg)))
            self.assertLess(max(len(a) for a in argv), LIMIT // 5)
        lines.append("all six steps: total %d characters over %d arguments" % (grand, sum(len(self.step_argv(n, **self.max_overrides())) for n in STEPS)))
        for name in STEPS:
            self.assertIn("STEP-ARG-LENGTHS: %s limit=%d" % (name, LIMIT), result.stdout)
        target = os.environ.get("SC_ARG_LENGTH_EVIDENCE")
        if target:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

    def test_the_submitted_json_arguments_at_maximum_values_match_the_printed_lengths(self):
        args = self.ready(record_override={"APPROVED_CLUSTER_ID": CLUSTER_MAX}, **self.max_overrides())
        self.assertEqual(self.execute(args).rc, 0)
        for index, step in enumerate(self.submitted_steps()):
            self.assertTrue(all(len(a) < LIMIT // 5 for a in step["HadoopJarStep"]["Args"]), STEPS[index])

    def test_the_launcher_and_the_dry_run_state_the_limit(self):
        out = self.dry().stdout
        self.assertIn("STEP-ARG-LIMIT: no step argument exceeds %d characters" % LIMIT, out)
        for name in STEPS:
            self.assertRegex(out, r"STEP-ARG-LENGTHS: %s limit=%d count=\d+ max=\d+ total=\d+ lengths=" % (name, LIMIT))


class OversizeRefusalTests(MaximumValues):
    def oversize(self, extra=0):
        """An --er-jar reference whose ER_JAR_REF argument has exactly LIMIT + extra characters."""
        need = LIMIT + extra - len("ER_JAR_REF=")
        key = "k" * (need - len("s3://%s/" % BUCKET63))
        value = "s3://%s/%s" % (BUCKET63, key)
        self.assertEqual(len("ER_JAR_REF=" + value), LIMIT + extra)
        return value

    def test_an_oversized_argument_is_refused_with_exit_3_before_any_cloud_call(self):
        result = self.dry(**{"--er-jar": self.oversize(1)})
        self.assertEqual(result.rc, 3, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: REFUSED step=arg-limit"), result.result_line())
        self.assertIn("STEP: arg-limit", result.stdout.splitlines())
        self.assertIn("STEP-ARG-TOO-LONG: step entity-resolution argument", result.out)
        self.assertIn("(ER_JAR_REF) has %d characters, over the limit of %d" % (LIMIT + 1, LIMIT), result.out)
        self.assertEqual(self.calls(), [], "no fake aws, hadoop, yarn or spark call was made")
        self.assertNotIn("emr add-steps", result.stdout)
        self.assertNotIn("STEP-BODY-BEGIN", result.stdout)

    def test_the_boundary_exactly_at_the_limit_passes_and_one_over_is_refused(self):
        at = self.dry(**{"--er-jar": self.oversize(0)})
        self.assertEqual(at.rc, 0, at.out)
        self.assertEqual(self.parse_lengths(at.stdout)["entity-resolution"]["max"], LIMIT)
        over = self.dry(**{"--er-jar": self.oversize(1)})
        self.assertEqual(over.rc, 3, over.out)

    def test_every_step_is_checked_not_only_the_first(self):
        for flag, step, key in (
            ("--input-prefix", "stage-in", "INPUT_PREFIX"),
            ("--hadoop-submit-jar", "hadoop-prep", "SUBMIT_JAR_REF"),
            ("--spark-config-template", "spark-job", "TEMPLATE_REF"),
            ("--output-prefix", "copy-out", "OUTPUT_PREFIX"),
        ):
            with self.subTest(step):
                result = self.dry(**{flag: "s3://%s/%s" % (BUCKET63, "k" * 10300)})
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("STEP-ARG-TOO-LONG: step %s argument" % step, result.out)
                self.assertIn("(%s)" % key, result.out)
                self.assertEqual(self.calls(), [])

    def test_execute_refuses_before_the_ledger_the_approval_and_any_aws_call(self):
        args = self.ready()
        i = args.index("--er-jar")
        args[i + 1] = self.oversize(5)
        result = self.execute(args)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("STEP-ARG-TOO-LONG: step entity-resolution argument", result.out)
        self.assertEqual(self.calls(), [], "not even the account check ran")
        with open(self.ledger_path(), encoding="utf-8") as handle:
            self.assertEqual(len(handle.readlines()), 1, "the ledger holds only its init record: no slot was reserved")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "pipeline-runs")))
        self.assertEqual(self.submitted_steps(), [])
        # the approval record is still unused: the same record works once the argument is short again
        args[i + 1] = "s3://fixture-bucket/art/er.jar"
        self.assertEqual(self.execute(args).rc, 0)

    def test_the_pinned_limit_can_be_lowered_but_not_raised(self):
        self.use_config(PIPELINE_STEP_ARG_MAX_CHARS="2000")
        lowered = self.dry(**{"--er-jar": "s3://%s/%s" % (BUCKET63, "k" * 2000)})
        self.assertEqual(lowered.rc, 3, lowered.out)
        self.assertIn("over the limit of 2000", lowered.out)
        self.use_config(PIPELINE_STEP_ARG_MAX_CHARS="10281")
        raised = self.dry()
        self.assertEqual(raised.rc, 3, raised.out)
        self.assertIn("PIPELINE_STEP_ARG_MAX_CHARS 10281 must be from 1000 to 10280", raised.out)
        self.assertEqual(self.calls(), [])

    def test_the_limit_ignores_the_environment(self):
        result = self.run_pipeline(PIPELINE_STEP_ARG_MAX_CHARS="1000")
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("PIPELINE_STEP_ARG_MAX_CHARS", result.out.split("CONFIG-IGNORED", 1)[1].splitlines()[0])
        self.assertIn("limit=%d" % LIMIT, self.value_of(result, "STEP-ARG-LENGTHS: stage-in "))
        conf = read(os.path.join(SCRIPTS_DIR, "config", "release.conf"))
        self.assertRegex(conf, r"(?m)^PIPELINE_STEP_ARG_MAX_CHARS=10280$")
        common = read(os.path.join(SCRIPTS_DIR, "lib", "common.sh"))
        self.assertIn(" PIPELINE_STEP_ARG_MAX_CHARS ", common)
        self.assertIn(" PIPELINE_STEP_BIN_DIR ", common)


class InstalledProgramTests(PipelineFixture):
    """The launcher and the runner verify the installed files on the node and fail closed."""

    def setUp(self):
        super().setUp()
        self.node_config()
        self.run_root = os.path.join(self.mnt, "runs", RUN)
        self.marker = os.path.join(self.tmp, "TAMPER-RAN")

    def tamper(self, program, extra):
        path = os.path.join(self.stepbin, program)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(extra)

    def test_the_step_carries_the_sha256_of_the_repository_runner(self):
        argv = self.step_argv("stage-in")
        self.assertEqual(argv[3:6], ["sc-step", sha_file("sc-step.sh"), "stage-in"])
        self.assertIn("f=%s/sc-step.sh" % self.stepbin, argv[2])
        summary = self.dry().stdout
        for name in ("sc-step.sh", "sc-ceiling-check.py", "sc-class-origin-verify.py", "sc-render-spark-config.py"):
            self.assertIn("PLAN: step-program-sha256 %s: %s" % (name, sha_file(name)), summary)
        self.assertIn("PLAN: step-bin-dir: %s" % self.stepbin, summary)

    def test_a_tampered_runner_is_refused_by_the_launcher_and_nothing_runs(self):
        body = self.step_body("stage-in")
        self.tamper("sc-step.sh", "\ntouch %s\n" % self.marker)
        result = self.run_body(body, {"FAKE_S3_TOTAL": "1024"})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("STEP-FAIL sc-step: sha256 mismatch for %s/sc-step.sh: the installed step runner is not the approved one" % self.stepbin, result.stderr)
        self.assertFalse(os.path.exists(self.marker), "the tampered runner must not run at all")
        self.assertEqual(self.aws_calls(), [])
        self.assertEqual(self.node_calls(), [])

    def test_a_missing_runner_is_refused_too(self):
        body = self.step_body("stage-in")
        os.remove(os.path.join(self.stepbin, "sc-step.sh"))
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.aws_calls(), [])

    def stage_spark_job(self):
        """A completed Hadoop run, the ER output directory and a PASSING class-origin result, so the spark-job step gets as far
        as the program under test."""
        run = os.path.join(self.run_root, "hadoop", "run-1")
        os.makedirs(run)
        open(os.path.join(run, "_SCHOLARCHAIN_COMPLETE"), "w").close()
        os.makedirs(os.path.join(self.run_root, "er", "run"))
        os.makedirs(os.path.join(self.run_root, "results"))
        with open(os.path.join(PIPELINE_FIXTURES, "probe-ok.json"), encoding="utf-8") as handle:
            document = json.load(handle)
        jars = os.path.join(self.runtime, "jars") + "/"
        for report in [document["driver"]] + document["taskProcesses"]:
            for lib in report["libraries"]:
                if lib["component"] == "scala3-library":
                    lib["origin"] = self.jobjar
                    lib["codeSourceSha256"] = JOB_SHA
                else:
                    lib["origin"] = jars + os.path.basename(lib["origin"])
        with open(os.path.join(self.run_root, "results", "class-origin.json"), "w", encoding="utf-8") as handle:
            json.dump(document, handle)

    def test_a_tampered_python_program_is_refused_before_it_runs(self):
        cases = (
            ("hadoop-prep", "sc-ceiling-check.py", "hadoop jar"),
            ("spark-class-origin", "sc-class-origin-verify.py", None),
            ("spark-job", "sc-render-spark-config.py", "spark-submit"),
            ("spark-job", "sc-class-origin-verify.py", "spark-submit"),
        )
        for step, program, forbidden in cases:
            with self.subTest(step=step, program=program):
                shutil.rmtree(self.run_root, ignore_errors=True)
                os.makedirs(os.path.join(self.run_root, "inputs"))
                body = self.step_body(step, **self.local_artifacts())
                if step == "spark-job":
                    self.stage_spark_job()
                original = read(os.path.join(self.stepbin, program))
                self.tamper(program, "\nimport pathlib\npathlib.Path(%r).touch()\n" % self.marker)
                open(self.nodelog, "w").close()
                result = self.run_body(body)
                with open(os.path.join(self.stepbin, program), "w", encoding="utf-8") as handle:
                    handle.write(original)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("sha256 mismatch for the installed step program %s" % program, result.stderr)
                self.assertFalse(os.path.exists(self.marker), "the tampered program must not run")
                if forbidden:
                    self.assertEqual([c for c in self.node_calls() if c.startswith(forbidden)], [])

    def test_untampered_programs_let_the_same_staged_spark_job_run(self):
        """The control for the tamper test: with the genuine programs the staged spark-job step reaches spark-submit."""
        os.makedirs(os.path.join(self.run_root, "inputs"))
        body = self.step_body("spark-job", **self.local_artifacts())
        self.stage_spark_job()
        result = self.run_body(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len([c for c in self.node_calls() if c.startswith("spark-submit ")]), 1)

    def local_artifacts(self):
        refs = {}
        for name in ("hadoop-submit", "hadoop-bundle", "er"):
            path = os.path.join(self.inputs, name + ".jar")
            with open(path, "wb") as handle:
                handle.write(("bytes-of-" + name).encode())
            refs[name] = path
        for name in ("er-policy", "er-config"):
            path = os.path.join(self.inputs, name + ".json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{}\n")
            refs[name] = path
        template = os.path.join(self.inputs, "spark-template.json")
        with open(os.path.join(SCRIPTS_DIR, "tests", "fixtures", "pipeline", "spark-template.json"), encoding="utf-8") as src, open(template, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        return {
            "--hadoop-submit-jar": refs["hadoop-submit"], "--hadoop-libjars": refs["hadoop-bundle"], "--er-jar": refs["er"],
            "--er-policy": refs["er-policy"], "--er-config": refs["er-config"], "--spark-config-template": template,
            "drop": ("--artifact-sha256:hadoop-submit-jar", "--artifact-sha256:hadoop-libjars", "--artifact-sha256:er-jar", "--artifact-sha256:er-policy", "--artifact-sha256:er-config", "--artifact-sha256:spark-config-template"),
        }

    def test_a_missing_python_program_fails_closed(self):
        os.makedirs(os.path.join(self.run_root, "inputs"))
        body = self.step_body("hadoop-prep", **self.local_artifacts())
        os.remove(os.path.join(self.stepbin, "sc-ceiling-check.py"))
        result = self.run_body(body)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("the installed step program sc-ceiling-check.py is missing", result.stderr)
        self.assertEqual([c for c in self.node_calls() if c.startswith("hadoop jar")], [])


class RunnerParameterTests(PipelineFixture):
    """sc-step.sh parses KEY=VALUE words against a per-step allow-list and never evaluates a value."""

    def setUp(self):
        super().setUp()
        self.node_config()
        self.runner = os.path.join(self.stepbin, "sc-step.sh")
        self.run_root = os.path.join(self.mnt, "runs", RUN)

    def argv_params(self):
        """The runner's own arguments for stage-in: everything after the launcher words (bash -c LAUNCHER sc-step SHA)."""
        return self.step_argv("stage-in")[5:]

    def run_runner(self, args, env=None, mode="__body"):
        e = dict(self.body_env_cache)
        e.update(env or {})
        return subprocess.run(["bash", self.runner] + ([mode] if mode else []) + args, env=e, capture_output=True, text=True, timeout=60, cwd=self.tmp)

    def test_the_runner_runs_a_step_from_its_parameters(self):
        result = self.run_runner(self.argv_params(), {"FAKE_S3_TOTAL": "1024"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_an_unknown_key_a_duplicate_and_a_missing_key_are_refused(self):
        params = self.argv_params()
        for label, mutated, needle in (
            ("unknown", params + ["EVIL=1"], "parameter EVIL is not accepted by this step"),
            ("other step's key", params + ["ER_XMX=3g"], "parameter ER_XMX is not accepted by this step"),
            ("duplicate", params + ["REGION=us-east-1"], "parameter REGION was given twice"),
            ("missing", [p for p in params if not p.startswith("INPUT_PREFIX=")], "missing parameter INPUT_PREFIX"),
            ("not key=value", params + ["justaword"], "a parameter is not KEY=VALUE"),
            ("lower case key", params + ["region=x"], "a parameter is not KEY=VALUE"),
        ):
            with self.subTest(label):
                result = self.run_runner(mutated, {"FAKE_S3_TOTAL": "1024"})
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn(needle, result.stderr)
                self.assertEqual(self.aws_calls(), [], "no command ran")

    def test_an_inherited_environment_variable_never_stands_in_for_a_missing_parameter(self):
        params = [p for p in self.argv_params() if not p.startswith("INPUT_PREFIX=")]
        result = self.run_runner(params, {"INPUT_PREFIX": "s3://env-bucket/x/", "FAKE_S3_TOTAL": "1024"})
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing parameter INPUT_PREFIX", result.stderr)

    def test_a_value_is_never_evaluated(self):
        canary = os.path.join(self.tmp, "EVAL-CANARY")
        value = "s3://fixture-bucket/in$(touch %s)`touch %s`;touch %s/" % (canary, canary, canary)
        params = [("INPUT_PREFIX=" + value) if p.startswith("INPUT_PREFIX=") else p for p in self.argv_params()]
        result = self.run_runner(params, {"FAKE_S3_TOTAL": "1024"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(os.path.exists(canary), "a parameter value must never be executed")
        self.assertTrue(any(value in c for c in self.aws_calls()), "the literal text reached aws as one argument")

    def test_an_unknown_step_name_and_a_bad_timeout_are_refused(self):
        bad = self.run_runner(["no-such-step", "STEP_SECONDS=1"])
        self.assertEqual(bad.returncode, 1)
        self.assertIn("unknown step name", bad.stderr)
        params = ["STEP_SECONDS=soon" if p.startswith("STEP_SECONDS=") else p for p in self.argv_params()]
        result = self.run_runner(params)
        self.assertEqual(result.returncode, 1)
        self.assertIn("STEP_SECONDS and KILL_AFTER must be whole numbers", result.stderr)


class ManifestTests(unittest.TestCase):
    PIPELINE_PY = os.path.join(SCRIPTS_DIR, "lib", "pipeline.py")

    def module(self):
        spec = importlib.util.spec_from_file_location("pipeline_under_test", self.PIPELINE_PY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_the_committed_manifest_equals_the_files_and_the_pinned_directory(self):
        manifest_path = os.path.join(REAL_REPO, "infra", "terraform", "emr-step-programs.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        names = ("sc-step.sh", "sc-ceiling-check.py", "sc-class-origin-verify.py", "sc-render-spark-config.py")
        self.assertEqual(sorted(manifest["programs"]), sorted(names))
        for name in names:
            self.assertEqual(manifest["programs"][name], sha_file(name), name)
        conf = read(os.path.join(SCRIPTS_DIR, "config", "release.conf"))
        pinned = re.search(r"(?m)^PIPELINE_STEP_BIN_DIR=(.*)$", conf).group(1)
        self.assertEqual(manifest["bin_dir"], pinned)
        self.assertIn('STEP_BIN="${SC_STEP_BIN:-%s}"' % pinned, read(os.path.join(EMR_DIR, "bootstrap.sh")))
        result = subprocess.run([sys.executable, "-I", self.PIPELINE_PY, "step-manifest", "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_drifted_manifest_is_refused_with_step_program_drift(self):
        module = self.module()
        shas = module.program_shas()
        module.check_step_manifest(shas)  # the committed manifest matches
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            for label, content in (
                ("wrong hash", json.dumps({"bin_dir": "/x", "programs": dict(shas, **{"sc-step.sh": "0" * 64})})),
                ("missing program", json.dumps({"bin_dir": "/x", "programs": {k: v for k, v in shas.items() if k != "sc-step.sh"}})),
                ("not json", "{"),
            ):
                with self.subTest(label):
                    path = os.path.join(tmp, "m.json")
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    module.STEP_MANIFEST = path
                    with self.assertRaises(module.Refused) as caught:
                        module.check_step_manifest(shas)
                    self.assertIn("STEP-PROGRAM-DRIFT", str(caught.exception))
            module.STEP_MANIFEST = os.path.join(tmp, "absent.json")
            with self.assertRaises(module.Refused):
                module.check_step_manifest(shas)

    def test_the_python_programs_are_the_files_the_plan_builder_and_verifier_run(self):
        module = self.module()
        self.assertEqual(module.program_text("sc-class-origin-verify.py"), read(os.path.join(EMR_DIR, "sc-class-origin-verify.py")))
        for name in ("sc-ceiling-check.py", "sc-class-origin-verify.py", "sc-render-spark-config.py"):
            compile(read(os.path.join(EMR_DIR, name)), name, "exec")
        for old in ("CEILING_PY", "CLASS_ORIGIN_PY", "RENDER_PY", "wrap_body", "BODIES"):
            self.assertFalse(hasattr(module, old), "%s was replaced by the installed programs" % old)

    def test_the_bootstrap_installs_step_programs_from_the_pinned_directory(self):
        text = read(os.path.join(EMR_DIR, "bootstrap.sh"))
        self.assertIn('"${RUNTIME_DEST}"/* | "${STEP_BIN}"/*) ;;', text)
        self.assertIn('"${STEP_BIN}"/*) sudo chmod 755 "${ART_DEST[$i]}" ;;', text)


if __name__ == "__main__":
    unittest.main()
