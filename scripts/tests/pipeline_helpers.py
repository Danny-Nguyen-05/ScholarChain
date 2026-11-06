"""Shared fixtures for the Subphase 13B tests (pipeline, experiment, budget): a temp git repository that holds the pinned
config files, local input files, a pre-spend receipt and an approval record. Fake aws/yarn/hadoop/spark-submit/timeout
binaries only; no network, no credentials, no cloud call. Expectations are hand-derived in the tests."""
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess

from helpers import FAKE_ACCOUNT, REGION, SCRIPTS_DIR, Fixture, account_hash, sha256_bytes, write_exec

CLUSTER = "j-ABC123DEF456"
RUN = "bp-test-0001"
FIXTURES = os.path.join(SCRIPTS_DIR, "tests", "fixtures")
PIPELINE_FIXTURES = os.path.join(FIXTURES, "pipeline")
JOB_SHA = hashlib.sha256(b"job-jar-bytes").hexdigest()
ARTIFACT_NAMES = ("hadoop-submit-jar", "hadoop-libjars", "er-jar", "er-policy", "er-config", "spark-config-template")


REAL_TIMEOUT_PY = r'''import os, signal, subprocess, sys, time
# `timeout --kill-after=K SECS CMD...` in its WORST realistic form: it signals only its direct child (no process-group
# signalling) and exits 124 on a timeout (137 when it had to KILL). A grandchild that ignores TERM survives it, which is what
# the step wrapper's own process-group kill must cope with.
args = sys.argv[1:]
kill_after = 0.0
if args and args[0].startswith("--kill-after="):
    kill_after = float(args.pop(0).split("=", 1)[1])
secs = float(args.pop(0))
proc = subprocess.Popen(args)


def forward(signum, _frame):
    try:
        proc.send_signal(signum)
    except ProcessLookupError:
        pass


for name in ("SIGTERM", "SIGINT", "SIGHUP", "SIGQUIT"):
    signal.signal(getattr(signal, name), forward)
deadline = time.time() + secs
while proc.poll() is None and time.time() < deadline:
    time.sleep(0.05)
if proc.poll() is not None:
    sys.exit(proc.returncode)
proc.send_signal(signal.SIGTERM)
end = time.time() + kill_after
while proc.poll() is None and time.time() < end:
    time.sleep(0.05)
if proc.poll() is None:
    proc.kill()
    proc.wait()
    sys.exit(137)
sys.exit(124)
'''


def sha_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def artifact_sha(name):
    return sha_text("fixture-" + name)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class PipelineFixture(Fixture):
    """A repo with scripts/config/spark-12-10.conf and emr-pricing.conf committed, local input files outside the repo."""

    def build_repo(self):
        super().build_repo()
        for rel in ("scripts/config/spark-12-10.conf", "scripts/config/emr-pricing.conf"):
            os.makedirs(os.path.dirname(os.path.join(self.repo, rel)), exist_ok=True)
            shutil.copy(os.path.join(SCRIPTS_DIR, "config", os.path.basename(rel)), os.path.join(self.repo, rel))
        self.commit("pipeline config")

    def setUp(self):
        super().setUp()
        self.inputs = os.path.join(self.tmp, "inputs")
        os.makedirs(self.inputs)
        for name in ("prep-config.json", "datasets.json"):
            shutil.copy(os.path.join(PIPELINE_FIXTURES, name), os.path.join(self.inputs, name))
        self.prep_config = os.path.join(self.inputs, "prep-config.json")
        self.datasets = os.path.join(self.inputs, "datasets.json")
        # 13C finding B2: an absent ledger refuses --execute, so the fixture starts with the initialised, empty ledger the
        # human would have created with --init-ledger (tests of the absent case remove it).
        self.write_ledger([])

    # ---- pricing -------------------------------------------------------------------------------------------------
    def set_pricing(self, confirmed=True, drop=(), **replace):
        """Rewrite the committed pricing file (a clean tree is kept by committing it)."""
        path = os.path.join(self.repo, "scripts/config/emr-pricing.conf")
        lines = []
        for line in read(os.path.join(SCRIPTS_DIR, "config", "emr-pricing.conf")).splitlines():
            key = line.split("=", 1)[0]
            if key in drop:
                continue
            if key == "EMR_PRICING_CONFIRMED_BY_HUMAN":
                line = "EMR_PRICING_CONFIRMED_BY_HUMAN=%s" % ("true" if confirmed else "false")
            if key in replace:
                line = "%s=%s" % (key, replace[key])
            lines.append(line)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        if subprocess.run(["git", "-C", self.repo, "status", "--porcelain=v1", "--", "scripts/config/emr-pricing.conf"], capture_output=True, text=True).stdout.strip():
            self.commit("pricing")

    # ---- pipeline command line -----------------------------------------------------------------------------------
    def pipeline_args(self, **over):
        values = {
            "--cluster-id": CLUSTER,
            "--region": REGION,
            "--instance-type": "m5.xlarge",
            "--core-count": "1",
            "--max-task-count": "1",
            "--max-runtime-minutes": "90",
            "--budget-usd": "2.50",
            "--input-prefix": "s3://fixture-bucket/inputs",
            "--output-prefix": "s3://fixture-bucket/outputs",
            "--hadoop-submit-jar": "s3://fixture-bucket/art/hadoop-submit.jar",
            "--hadoop-libjars": "s3://fixture-bucket/art/hadoop-bundle.jar",
            "--hadoop-config": self.prep_config,
            "--er-jar": "s3://fixture-bucket/art/er.jar",
            "--er-policy": "s3://fixture-bucket/art/er-policy.json",
            "--er-config": "s3://fixture-bucket/art/er-config.json",
            "--spark-config-template": "s3://fixture-bucket/art/spark-template.json",
            "--datasets-manifest": self.datasets,
            "--run-id": RUN,
        }
        drop = over.pop("drop", ())
        values.update(over)
        args = []
        for flag, value in values.items():
            if flag not in drop:
                args += [flag, str(value)]
        for name in ARTIFACT_NAMES:
            if "--artifact-sha256:" + name not in drop:
                args += ["--artifact-sha256", "%s=%s" % (name, artifact_sha(name))]
        if "--artifact-sha256:job-jar" not in drop:
            args += ["--artifact-sha256", "job-jar=%s" % JOB_SHA]
        return args

    def run_pipeline(self, *extra, args=None, **env):
        return self.run_script("run-bounded-pipeline.sh", *((args if args is not None else self.pipeline_args()) + list(extra)), **env)

    def dry(self, **over):
        return self.run_pipeline(args=self.pipeline_args(**over))

    @staticmethod
    def value_of(result, prefix):
        for line in result.stdout.splitlines():
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        raise AssertionError("no %r line in: %s" % (prefix, result.stdout[-600:]))

    def run_config_sha(self, **over):
        return self.value_of(self.dry(**over), "RUN-CONFIG-SHA256: ")

    # ---- the approval record and pre-spend receipt -----------------------------------------------------------------
    def approval_lines(self, run_config_sha, prespend_sha, **override):
        values = {
            "APPROVED_ACTION": "run-bounded-pipeline",
            "APPROVED_COMMIT": self.head(),
            "APPROVED_ACCOUNT_SHA256": account_hash(),
            "APPROVED_REGION": REGION,
            "APPROVED_CLUSTER_ID": CLUSTER,
            "APPROVED_RUN_CONFIG_SHA256": run_config_sha,
            "APPROVED_BUDGET_USD": "2.50",
            "APPROVED_MAX_CAPACITY": "3",
            "APPROVED_MAX_RUNTIME_MINUTES": "90",
            "APPROVED_TEARDOWN": "auto-termination",
            "APPROVED_PRESPEND_SHA256": prespend_sha,
        }
        values.update(override)
        return values

    def write_record(self, values, name="gate.md", raw_extra=""):
        path = os.path.join(self.repo, "target", "approvals", name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        lines = ["# Synthetic approval record for tests", "Prose mentioning APPROVED_COMMIT=ignored-mid-line stays ignored."]
        lines += ["%s=%s" % (k, v) for k, v in values.items() if v is not None]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n" + raw_extra)
        return path

    def ready(self, pricing_confirmed=True, record_override=None, prespend_override=None, serial=None, **over):
        """Pricing confirmed, receipt written, approval record matching the dry run. Returns the execute argument list."""
        self.set_pricing(confirmed=pricing_confirmed)
        run_sha = self.run_config_sha(**over)
        prespend_path, prespend_sha = self.write_prespend(**(prespend_override or {}))
        # An approval record is single-use (finding B4): a test that executes twice gives each record its own serial line
        # (text that is not an APPROVED_* line is ignored by the parser, so it only changes the file's sha256).
        record = self.write_record(self.approval_lines(run_sha, prespend_sha, **(record_override or {})), raw_extra=("Approval serial: %s\n" % serial) if serial is not None else "")
        self.prespend_path = prespend_path
        self.record_path = record
        self.prespend_sha = prespend_sha
        return self.pipeline_args(**over) + ["--approval", record, "--prespend", prespend_path, "--profile", "approved-profile", "--execute"]

    def execute(self, args, **env):
        return self.run_script("run-bounded-pipeline.sh", *args, **env)

    # ---- fake aws call log helpers ------------------------------------------------------------------------------------
    def aws_calls(self):
        return [args for name, args in self.calls("aws")]

    def emr_ops(self):
        ops = []
        for args in self.aws_calls():
            words = args.split()
            if words[:1] == ["emr"]:
                ops.append(words[1])
        return ops

    def submitted_steps(self):
        path = self.log + ".steps"
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as handle:
            return [json.loads(line)[0] for line in handle if line.strip()]

    def ledger_path(self):
        """13C finding B2: the ledger lives under HOME (the fixture sets HOME to its temp dir), outside the repository."""
        return os.path.join(self.tmp, ".scholarchain", "emr-ledger", "runs.jsonl")

    def write_ledger(self, estimates, approvals=None, init=True):
        """An initialised ledger holding one reservation per estimate (each with a distinct earlier approval sha256)."""
        path = self.ledger_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            if init:
                handle.write(json.dumps({"event": "init", "initialized_by": "fixture", "initialized_utc": "2026-11-01T00:00:00Z"}) + "\n")
            for index, value in enumerate(estimates):
                approval = (approvals or {}).get(index, hashlib.sha256(("earlier-approval-%d" % index).encode()).hexdigest())
                handle.write(json.dumps({"event": "reserve", "run_id": "earlier-%d" % index, "action": "run-bounded-pipeline", "estimate_usd": value, "run_config_sha256": "0" * 64, "approval_record_sha256": approval, "reserved_utc": "2026-11-01T00:00:00Z"}) + "\n")

    def tree_clean(self):
        return subprocess.run(["git", "-C", self.repo, "status", "--porcelain=v1", "--untracked-files=all"], capture_output=True, text=True).stdout.strip() == ""

    # ---- cluster-side step bodies run locally with fake binaries --------------------------------------------------------
    def body_env(self):
        """A fake EMR master under the test tmp dir: mount, runtime, Java 17 home file and the fake commands the bodies call."""
        base = os.path.join(self.tmp, "node")
        self.node = base
        self.mnt = os.path.join(base, "mnt")
        self.runtime = os.path.join(base, "runtime")
        self.nodebin = os.path.join(base, "bin")
        self.nodelog = os.path.join(base, "node.log")
        self.javahome = os.path.join(base, "jvm", "java-17")
        self.javafile = os.path.join(base, "java-home")
        self.jobjar = os.path.join(self.runtime, "application", "scholarchain-job.jar")
        self.procmounts = os.path.join(base, "mounts")
        # Finding C1: the bootstrap installs the step runner and its Python programs (sha256-pinned --artifact files) here; the
        # EMR step's launcher runs the installed runner from the pinned PIPELINE_STEP_BIN_DIR (node_config points it here).
        self.stepbin = os.path.join(base, "step-bin")
        os.makedirs(self.stepbin, exist_ok=True)
        for program in sorted(os.listdir(os.path.join(SCRIPTS_DIR, "emr"))):
            if program.startswith("sc-"):
                shutil.copy2(os.path.join(SCRIPTS_DIR, "emr", program), os.path.join(self.stepbin, program))
        for directory in (self.mnt, os.path.join(self.runtime, "application"), os.path.join(self.runtime, "bin"), os.path.join(self.runtime, "jars"), self.nodebin, os.path.join(self.javahome, "bin")):
            os.makedirs(directory, exist_ok=True)
        with open(self.jobjar, "wb") as handle:
            handle.write(b"job-jar-bytes")
        with open(self.procmounts, "w", encoding="utf-8") as handle:
            handle.write("fs-fake:/ %s efs rw 0 0\n" % self.mnt)
        with open(self.javafile, "w", encoding="utf-8") as handle:
            handle.write(self.javahome + "\n")
        with open(self.nodelog, "w", encoding="utf-8"):
            pass
        write_exec(os.path.join(self.javahome, "bin", "java"), '#!/bin/bash\necho "java $*" >> "%s"\necho \'openjdk version "17.0.21" 2026-01-01\' >&2\nexit 0\n' % self.nodelog)
        write_exec(
            os.path.join(self.runtime, "bin", "spark-submit"),
            '#!/bin/bash\necho "spark-submit $*" >> "%s"\nif [ -n "${FAKE_PROBE_SRC:-}" ]; then n=$#; out="${@:$((n-1)):1}"; cp "$FAKE_PROBE_SRC" "$out"; fi\nexit 0\n' % self.nodelog,
        )
        # GNU timeout shim: FAKE_TIMEOUT_RC=124 simulates the cap firing; otherwise it runs the command.
        # 13C (finding B1): the step wrapper runs the body as `timeout ... bash FILE`; that call always runs the body, and
        # FAKE_TIMEOUT_RC applies to the inner client call (hadoop jar, spark-submit, java), as before.
        write_exec(os.path.join(self.nodebin, "timeout"), '#!/bin/bash\necho "timeout $*" >> "%s"\nshift 2\nif [ "$1" = "bash" ]; then exec "$@"; fi\nif [ -n "${FAKE_TIMEOUT_RC:-}" ]; then exit "$FAKE_TIMEOUT_RC"; fi\nexec "$@"\n' % self.nodelog)
        # A faithful `timeout --kill-after=K SECS CMD...` (GNU semantics: own process group, TERM at SECS, KILL after K,
        # exit 124) for the B1 hang tests; the node bin dir shadows it with the logging shim above unless FAKE_REAL_TIMEOUT=1.
        write_exec(os.path.join(self.nodebin, "timeout-real"), '#!/usr/bin/env python3\n' + REAL_TIMEOUT_PY)
        write_exec(
            os.path.join(self.nodebin, "yarn"),
            '#!/bin/bash\necho "yarn $*" >> "%s"\nif [ -n "${FAKE_YARN_APP:-}" ] && [ "$1 $2" = "application -list" ]; then\n'
            '  echo "Total number of applications:1"\n  echo "application_1700000000000_0007  scholarchain  SPARK  user  default  RUNNING"\nfi\nexit 0\n' % self.nodelog,
        )
        write_exec(os.path.join(self.nodebin, "hadoop"), '#!/bin/bash\necho "hadoop $*" >> "%s"\nif [ -n "${FAKE_HADOOP_HANG:-}" ] && [ "$1 $2" = "fs -copyToLocal" ]; then exec sleep 600; fi\nexit 0\n' % self.nodelog)
        # sha256sum is not on stock macOS: a python shim for `sha256sum -c --status -` and `sha256sum FILE`.
        write_exec(
            os.path.join(self.nodebin, "sha256sum"),
            '#!/usr/bin/env python3\nimport hashlib, sys\nargs = sys.argv[1:]\n'
            'def digest(path):\n    return hashlib.sha256(open(path, "rb").read()).hexdigest()\n'
            'if args[:1] == ["-c"]:\n    bad = 0\n    for line in sys.stdin:\n        want, _, path = line.rstrip("\\n").partition("  ")\n'
            '        try:\n            ok = digest(path) == want\n        except OSError:\n            ok = False\n        bad += 0 if ok else 1\n    sys.exit(1 if bad else 0)\n'
            'for path in args:\n    print(digest(path) + "  " + path)\n',
        )
        return {
            "PATH": self.nodebin + ":" + self.runtime + "/bin:" + os.path.dirname(__import__("sys").executable) + ":" + self.bin + ":/usr/bin:/bin:/usr/sbin:/sbin",
            "SC_PROC_MOUNTS": self.procmounts,
            "HOME": self.tmp,
            "TMPDIR": self.tmp,
            "LC_ALL": "C",
            "FAKE_LOG": self.log,
        }

    def node_calls(self):
        with open(self.nodelog, encoding="utf-8") as handle:
            return [line.rstrip("\n") for line in handle]

    def node_config(self, **extra):
        """A test-only release.conf whose node paths point into the fake master (SCHOLARCHAIN_CONFIG_FILE)."""
        self.body_env_cache = self.body_env()
        values = {
            "PIPELINE_EFS_MOUNT": self.mnt,
            "PIPELINE_RUNTIME_DIR": self.runtime,
            "PIPELINE_JOB_JAR_PATH": self.jobjar,
            "PIPELINE_JAVA_HOME_FILE": self.javafile,
            "PIPELINE_STEP_BIN_DIR": self.stepbin,
        }
        values.update(extra)
        return self.use_config(**values)

    def step_body(self, name, **over):
        """The cluster body of one step exactly as the dry run prints it (between its STEP-BODY markers)."""
        result = self.run_pipeline(args=self.pipeline_args(**over))
        assert result.rc == 0, result.out
        begin = "STEP-BODY-BEGIN: %s\n" % name
        end = "STEP-BODY-END: %s\n" % name
        return result.stdout.split(begin, 1)[1].split(end, 1)[0]

    def step_argv(self, name, **over):
        """The EMR step's HadoopJarStepConfig.Args list for one step, parsed from the printed command (shell words)."""
        return shlex.split(self.step_body(name, **over).replace("\\\n", " "))

    def step_text(self, name, **over):
        """Everything that decides what a step does: the printed command (launcher and parameters) plus the text of the
        installed step programs it runs. Used where a test asserts program text rather than behaviour."""
        text = self.step_body(name, **over)
        for program in sorted(os.listdir(os.path.join(SCRIPTS_DIR, "emr"))):
            if program.startswith("sc-"):
                text += "\n" + read(os.path.join(SCRIPTS_DIR, "emr", program))
        return text

    def run_body(self, body, extra_env=None):
        env = dict(self.body_env_cache)
        env.update(extra_env or {})
        return subprocess.run(["bash", "-c", body], env=env, capture_output=True, text=True, timeout=120, cwd=self.tmp)
