"""Self-contained support for the independent Phase 13B script tests (test-engineer, tests/scripts/**).

Nothing here imports or reuses scripts/tests. The fixtures are:

  * a temporary git repository holding a copy of scripts/** (the scripts locate their repository through
    SCHOLARCHAIN_REPO_ROOT and their own directory), a prep config, a datasets manifest and a .gitignore;
  * a temporary bin directory placed FIRST on PATH with python3 fake binaries (aws, hadoop, yarn, spark-submit,
    terraform, docker, sbt, timeout, sha256sum, java) that append their argv to one JSON-lines log and answer from
    a scenario file. A fake that is never called leaves the log empty, which is how "no cloud call" is asserted.

Expectations in the tests are hand-derived from scripts/README.md, each script's --help, plan section 7 and 9 and the
user's Step 0 answers. The scripts' own logic is never re-implemented here.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC_SCRIPTS = REPO / "scripts"
PY = sys.executable

HEX64 = "a" * 64
ACCOUNT = "731904628150"  # a made-up 12-digit canary account id (never a real account)
CANARY_SECRET = "canary-secret-access-key-7f3a91c2"
CANARY_TOKEN = "canary-session-token-55d0be44"
CANARY_SMOKE_KEY = "canary-smoke-api-key-91ac07e5"

SECRET_ENV = {
    "AWS_SECRET_ACCESS_KEY": CANARY_SECRET,
    "AWS_SESSION_TOKEN": CANARY_TOKEN,
    "SCHOLARCHAIN_SMOKE_API_KEY": CANARY_SMOKE_KEY,
}
CANARIES = [CANARY_SECRET, CANARY_TOKEN, CANARY_SMOKE_KEY, ACCOUNT]

CEILINGS = {
    "maxLocalSampleRecords": 12000,  # pipeline-specific exception (USD 25 replan); the Phase 4 smoke keeps 1000
    "reducerCount": 8,
    "maxCandidateBlockSize": 256,
    "maxCandidatePairsPerBlock": 4096,
    "maxAuthorTeamSize": 64,
    "maxRecordBytes": 8388608,
    "maxXmlEntityExpansion": 8388608,
}
SAFE_PREP = {
    "maxLocalSampleRecords": 100,
    "reducerCount": 2,
    "maxCandidateBlockSize": 64,
    "maxCandidatePairsPerBlock": 1024,
    "maxAuthorTeamSize": 16,
    "maxRecordBytes": 1048576,
    "maxXmlEntityExpansion": 1048576,
}
DATASETS = {
    "dblp": {"snapshot": "dblp-2026-01", "retrieval": "2026-01-02"},
    "openalex": {"snapshot": "oa-2026-01", "retrieval": "2026-01-03"},
    "crossref": {"snapshot": "cr-2026-01", "retrieval": "2026-01-04"},
    "orcid": {"snapshot": "or-2026-01", "retrieval": "2026-01-05"},
}
# 60-minute maximum runtime = 3600 s, weights 5/20/20/5/40/10 (scripts/config/release.conf): hand-derived per-step seconds
STEP_SECONDS = {"stage-in": 180, "hadoop-prep": 720, "entity-resolution": 720, "spark-class-origin": 180, "spark-job": 1440, "copy-out": 360}
STEP_NAMES = ["stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out"]
ARTIFACT_NAMES = [
    "hadoop-submit-jar", "hadoop-libjars", "er-jar", "job-jar", "er-policy", "er-config", "spark-config-template",
]

# ---------------------------------------------------------------------------------------------------------------
# Fake binaries
# ---------------------------------------------------------------------------------------------------------------

FAKE_TEMPLATE = r'''#!__PY__
import hashlib, json, os, signal, subprocess, sys, time
TOOL = __TOOL__
ARGV = sys.argv[1:]
LOG = os.environ.get("SC_FAKE_LOG")
if LOG:
    with open(LOG, "a") as handle:
        handle.write(json.dumps({"tool": TOOL, "argv": ARGV, "cwd": os.getcwd()}) + "\n")
SCEN = {}
if os.environ.get("SC_FAKE_SCENARIO") and os.path.exists(os.environ["SC_FAKE_SCENARIO"]):
    with open(os.environ["SC_FAKE_SCENARIO"]) as handle:
        SCEN = json.load(handle)


def state_path():
    return os.environ.get("SC_FAKE_STATE") or os.path.join(os.path.dirname(LOG or "/tmp/x"), "fake-state.json")


def load_state():
    try:
        with open(state_path()) as handle:
            return json.load(handle)
    except Exception:
        return {"steps": {}, "counter": 0}


def save_state(state):
    with open(state_path(), "w") as handle:
        json.dump(state, handle)


def override(key):
    spec = (SCEN.get("verbs") or {}).get(key)
    if spec is None:
        return False
    sys.stdout.write(spec.get("stdout", ""))
    sys.stderr.write(spec.get("stderr", ""))
    sys.exit(spec.get("rc", 0))


def aws():
    key = " ".join(ARGV[:2])
    if os.environ.get("SC_FAKE_AWS_FAIL_ALL"):
        sys.stderr.write("fake aws: refusing every call\n")
        sys.exit(99)
    override(key)
    if os.environ.get("SC_FAKE_AWS_HANG") == key:
        # B1 tests: a copy that never returns (a stalled transfer). It records its pid so a test can prove it was killed.
        pidfile = os.environ.get("SC_FAKE_HANG_PIDFILE")
        if pidfile:
            with open(pidfile, "a") as handle:
                handle.write("%d\n" % os.getpid())
        if os.environ.get("SC_FAKE_HANG_IGNORE_TERM"):
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        time.sleep(600)
        sys.exit(0)
    if key == "sts get-caller-identity":
        print(SCEN.get("account", "__ACCOUNT__"))
    elif key == "emr describe-cluster":
        print(json.dumps(SCEN.get("describe_cluster", {"Cluster": {"Id": SCEN.get("cluster_id", "j-TESTCLUSTER"), "Status": {"State": "WAITING"}}})))
    elif key == "emr get-auto-termination-policy":
        print(json.dumps(SCEN.get("policy", {"AutoTerminationPolicy": {"IdleTimeout": 900}})))
    elif key == "emr list-instance-groups":
        print(json.dumps(SCEN.get("groups", {"InstanceGroups": [
            {"InstanceGroupType": "MASTER", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1},
            {"InstanceGroupType": "CORE", "InstanceType": "m5.xlarge", "RequestedInstanceCount": 1, "RunningInstanceCount": 1}]})))
    elif key == "emr add-steps":
        steps = json.loads(ARGV[ARGV.index("--steps") + 1])
        state = load_state()
        state["counter"] += 1
        step_id = "s-FAKE%04d" % state["counter"]
        state["steps"][step_id] = {"name": steps[0]["Name"], "polls": 0}
        save_state(state)
        print(step_id)
    elif key == "emr describe-step":
        step_id = ARGV[ARGV.index("--step-id") + 1]
        state = load_state()
        entry = state["steps"].get(step_id, {"name": "", "polls": 0})
        entry["polls"] += 1
        state["steps"][step_id] = entry
        save_state(state)
        name = entry["name"]
        seq = None
        for suffix, value in (SCEN.get("step_states") or {}).items():
            if name.endswith("-" + suffix):
                seq = value
        if seq is None:
            seq = ["COMPLETED"]
        if isinstance(seq, str):
            seq = [seq]
        print(seq[min(entry["polls"] - 1, len(seq) - 1)])
    elif key == "emr cancel-steps":
        print("{}")
    elif key == "s3 ls":
        print("Total Objects: 4\n   Total Size: %s" % SCEN.get("s3_total_size", 1024))
    elif ARGV[:1] == ["s3"]:
        pass
    else:
        sys.stderr.write("fake aws: unexpected verb %r\n" % key)
        sys.exit(97)


def terraform():
    if ARGV[:2] == ["version", "-json"]:
        print(json.dumps({"terraform_version": SCEN.get("terraform_version", "1.13.5")}))
        return
    sys.stderr.write("fake terraform: no other command is simulated\n")
    sys.exit(98)


def hadoop():
    if ARGV[:2] == ["fs", "-copyToLocal"]:
        src, dest = ARGV[2], ARGV[3]
        base = os.path.basename(src)
        root = os.environ.get("SC_FAKE_S3DIR", "")
        candidate = os.path.join(root, base)
        if not os.path.isfile(candidate):
            sys.stderr.write("fake hadoop: no fixture for %s\n" % src)
            sys.exit(1)
        with open(candidate, "rb") as source, open(dest, "wb") as target:
            target.write(source.read())
        return
    if ARGV[:1] == ["jar"]:
        sys.exit(int(os.environ.get("SC_FAKE_HADOOP_JAR_RC", "0")))
    sys.exit(0)


def yarn():
    if ARGV[:2] == ["application", "-list"]:
        tag = ARGV[ARGV.index("-appTags") + 1] if "-appTags" in ARGV else None
        if tag is not None and tag == os.environ.get("SC_FAKE_YARN_TAG"):
            print("Total number of applications (application-types: [], states: [RUNNING] and tags: [%s]):2" % tag)
            print("                Application-Id\tApplication-Name")
            for app in filter(None, os.environ.get("SC_FAKE_YARN_APPS", "").split(",")):
                print("%s\tscholarchain\tSPARK\tuser\tdefault\tRUNNING" % app)
        else:
            print("Total number of applications (application-types: [], states: [RUNNING] and tags: []):0")
        return
    sys.exit(0)


def timeout():
    args = list(ARGV)
    kill_after = None
    while args and args[0].startswith("-"):
        flag = args.pop(0)
        if flag.startswith("--kill-after="):
            kill_after = flag.split("=", 1)[1]
        elif flag in ("-k", "--kill-after") and args:
            kill_after = args.pop(0)
        elif flag == "-s" and args:
            args.pop(0)
    if len(args) < 2:
        sys.exit(125)
    duration = args.pop(0)
    # The step-level wrapper (finding B1, installed form of C1) is `timeout --kill-after=N SECONDS bash <bin>/sc-step.sh __body STEP ...`.
    outer = len(args) >= 3 and args[0] == "bash" and args[1].endswith("/sc-step.sh") and args[2] == "__body"
    mode = os.environ.get("SC_FAKE_OUTER_TIMEOUT_MODE" if outer else "SC_FAKE_TIMEOUT_MODE", "pass")
    if mode.startswith("exit:"):
        sys.exit(int(mode.split(":", 1)[1]))
    if mode == "real":
        # Enforce a short real deadline with GNU timeout semantics: the command runs in timeout's OWN process group (timeout
        # is the group leader, the child inherits the group, there is no new session), the deadline sends TERM to that group,
        # then KILL to the group after the grace period only if the direct child is still running, and exits 124. So a
        # grandchild that ignores TERM survives once the direct child is gone, exactly as with coreutils. TERM or INT
        # received are forwarded to the group. SC_FAKE_TIMEOUT_REAL_SECONDS replaces the (minutes-long) real duration; the
        # recorded argv still carries the true one.
        limit = float(os.environ.get("SC_FAKE_TIMEOUT_REAL_SECONDS", duration))
        grace = float(os.environ.get("SC_FAKE_TIMEOUT_REAL_KILL_AFTER", kill_after or "1"))
        try:
            os.setpgid(0, 0)
        except OSError:
            pass
        group = os.getpgrp()
        child = subprocess.Popen(args)
        state = {"cleanup": False}

        def forward(signum, frame):
            if state["cleanup"]:
                return
            state["cleanup"] = True
            os.killpg(group, signum)

        signal.signal(signal.SIGTERM, forward)
        signal.signal(signal.SIGINT, forward)

        def status(rc):
            return 128 - rc if rc < 0 else rc

        try:
            sys.exit(status(child.wait(timeout=limit)))
        except subprocess.TimeoutExpired:
            state["cleanup"] = True
            os.killpg(group, signal.SIGTERM)
            try:
                child.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                os.killpg(group, signal.SIGKILL)  # also ends this process, as GNU timeout does
            sys.exit(124)  # GNU timeout reports 124 when the command was stopped after the deadline
    sys.exit(subprocess.call(args))


def sha256sum():
    if ARGV[:3] == ["-c", "--status", "-"]:
        ok = True
        for line in sys.stdin.read().splitlines():
            want, _, path = line.partition("  ")
            try:
                with open(path, "rb") as handle:
                    got = hashlib.sha256(handle.read()).hexdigest()
            except OSError:
                ok = False
                continue
            ok = ok and got == want
        sys.exit(0 if ok else 1)
    for path in ARGV:
        with open(path, "rb") as handle:
            print("%s  %s" % (hashlib.sha256(handle.read()).hexdigest(), path))


def java():
    if "-version" in ARGV:
        sys.stderr.write('openjdk version "%s" 2026-01-20\n' % os.environ.get("SC_FAKE_JAVA_VERSION", "17.0.12"))
        return
    sys.exit(int(os.environ.get("SC_FAKE_JAVA_RC", "0")))


def generic():
    sys.exit(int(os.environ.get("SC_FAKE_GENERIC_RC", "0")))


{"aws": aws, "terraform": terraform, "hadoop": hadoop, "yarn": yarn, "timeout": timeout,
 "sha256sum": sha256sum, "java": java}.get(TOOL, generic)()
'''


def write_fake(path, tool, account=ACCOUNT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    source = FAKE_TEMPLATE.replace("__PY__", PY).replace("__TOOL__", repr(tool)).replace("__ACCOUNT__", account)
    path.write_text(source)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


# ---------------------------------------------------------------------------------------------------------------
# Result of one script run
# ---------------------------------------------------------------------------------------------------------------

class Run:
    def __init__(self, completed, calls):
        self.rc = completed.returncode
        self.out = completed.stdout
        self.err = completed.stderr
        self.calls = calls

    @property
    def text(self):
        return self.out + "\n" + self.err

    def lines(self):
        return self.out.splitlines()

    def steps(self):
        return [line[len("STEP: "):] for line in self.lines() if line.startswith("STEP: ")]

    def results(self):
        return [line for line in self.lines() if line.startswith("RESULT:")]

    @property
    def result(self):
        found = self.results()
        return found[0] if found else ""

    @property
    def status(self):
        parts = self.result.split()
        return parts[1] if len(parts) > 1 else ""

    def tool_calls(self, tool):
        return [c for c in self.calls if c["tool"] == tool]

    def aws_verbs(self):
        return [" ".join(c["argv"][:2]) for c in self.tool_calls("aws")]

    def grep(self, pattern):
        return [line for line in self.out.splitlines() if re.search(pattern, line)]

    def describe(self):
        return "rc=%s steps=%s result=%r\nSTDOUT(tail)=%s\nSTDERR(tail)=%s" % (
            self.rc, self.steps()[-6:], self.result, "\n".join(self.out.splitlines()[-12:]), "\n".join(self.err.splitlines()[-6:]))


# ---------------------------------------------------------------------------------------------------------------
# Fixture: temp git repo + fakes
# ---------------------------------------------------------------------------------------------------------------

def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


class Fixture:
    def __init__(self, test, infra=False, patch=None):
        self.test = test
        self.root = Path(tempfile.mkdtemp(prefix="sc13b-")).resolve()
        test.addCleanup(shutil.rmtree, str(self.root), True)
        self.repo = self.root / "repo"
        self.aux = self.root / "aux"
        self.bin = self.root / "bin"
        self.home = self.root / "home"
        self.tmp = self.root / "tmp"
        for d in (self.repo, self.aux, self.bin, self.home, self.tmp):
            d.mkdir()
        self.log = self.aux / "fake-calls.jsonl"
        self.scenario_path = self.aux / "scenario.json"
        self.state_path = self.aux / "fake-state.json"
        self.s3dir = self.aux / "fake-s3"
        self.s3dir.mkdir()
        self.scenario = {}
        for tool in ("aws", "hadoop", "yarn", "spark-submit", "terraform", "docker", "sbt", "timeout", "sha256sum", "java"):
            write_fake(self.bin / tool, tool)
        shutil.copytree(
            SRC_SCRIPTS, self.repo / "scripts",
            ignore=shutil.ignore_patterns("tests", "phase12d-spike", "billing", "__pycache__", "*.pyc"),
        )
        if patch is not None:
            patch(self.repo / "scripts")  # mutation cases: edit the fixture's COPY of the scripts, never the repository
        # C1: the Terraform-side pin of the installed step programs must exist in the fixture repository (the plan refuses with
        # STEP-PROGRAM-DRIFT otherwise), and the fake NODE installs scripts/emr/sc-* into a step bin directory.
        manifest = self.repo / "infra/terraform/emr-step-programs.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "infra/terraform/emr-step-programs.json", manifest)
        if patch is not None:
            # a mutation case may edit a step program: re-pin the manifest to the fixture's (mutated) copies so the plan still
            # builds and the mutation is judged by behaviour, not by STEP-PROGRAM-DRIFT
            pinned = json.loads(manifest.read_text())
            actual = {p.name: sha256_file(p) for p in sorted((self.repo / "scripts" / "emr").glob("sc-*"))}
            if pinned["programs"] != actual:
                pinned["programs"] = actual
                manifest.write_text(json.dumps(pinned, indent=2, sort_keys=True) + "\n")
        self.stepbin = self.aux / "stepbin"
        self.install_step_programs()
        self.write(self.repo / ".gitignore", "target/\n__pycache__/\n*.pyc\n")
        self.write(self.repo / "docs" / "agent-runs" / "README.md", "fixture placeholder so the default archive destination root exists\n")
        self.write_json(self.repo / "inputs" / "prep.json", SAFE_PREP)
        self.write_json(self.repo / "inputs" / "datasets.json", DATASETS)
        if infra:
            tf_src = REPO / "infra" / "terraform"
            (self.repo / "infra/terraform/environments").mkdir(parents=True)
            (self.repo / "infra/terraform/modules/runtime").mkdir(parents=True)
            shutil.copy(tf_src / "environments" / "course.tfvars", self.repo / "infra/terraform/environments/course.tfvars")
            shutil.copy(tf_src / "modules/runtime/compute.tf", self.repo / "infra/terraform/modules/runtime/compute.tf")
            self.write(self.repo / "infra/terraform/versions.tf", "terraform {}\n")
        self.git("init", "-q", ".")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fixture base")
        self.write_scenario({})

    def install_step_programs(self):
        """The fake primary node: the bootstrap installs scripts/emr/sc-* (the fixture's copy) into the step bin directory."""
        self.stepbin.mkdir(parents=True, exist_ok=True)
        for src in sorted((self.repo / "scripts" / "emr").glob("sc-*")):
            target = self.stepbin / src.name
            shutil.copyfile(src, target)
            target.chmod(0o755)

    # ----- files -----
    @staticmethod
    def write(path, text):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    @staticmethod
    def write_json(path, obj):
        return Fixture.write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")

    def write_scenario(self, scenario):
        self.scenario = scenario
        self.write_json(self.scenario_path, scenario)

    def update_scenario(self, **kw):
        self.scenario.update(kw)
        self.write_json(self.scenario_path, self.scenario)

    # ----- git -----
    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid", "HOME": str(self.home)})
        done = subprocess.run(["git", "-C", str(self.repo)] + list(args), env=env, capture_output=True, text=True)
        if done.returncode != 0:
            raise AssertionError("git %s failed: %s" % (args, done.stderr))
        return done.stdout.strip()

    def head(self):
        return self.git("rev-parse", "HEAD")

    def commit_all(self, message="more"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    # ----- environment and process -----
    def env(self, extra=None, secrets=False):
        env = {
            "PATH": "%s:%s" % (self.bin, os.environ.get("PATH", "/usr/bin:/bin")),
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
            "SCHOLARCHAIN_REPO_ROOT": str(self.repo),
            "SC_FAKE_LOG": str(self.log),
            "SC_FAKE_SCENARIO": str(self.scenario_path),
            "SC_FAKE_STATE": str(self.state_path),
            "SC_FAKE_S3DIR": str(self.s3dir),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if secrets:
            env.update(SECRET_ENV)
        if extra:
            env.update(extra)
        return env

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines() if line.strip()]

    def run(self, script, args=(), extra_env=None, secrets=False, cwd=None, timeout=180, stdin=None):
        path = self.repo / "scripts" / script
        done = subprocess.run(
            [str(path)] + [str(a) for a in args], env=self.env(extra_env, secrets), cwd=str(cwd or self.repo),
            capture_output=True, text=True, timeout=timeout, input=stdin,
        )
        return Run(done, self.calls())

    # ----- test-only configuration (documented mechanisms) -----
    def test_config(self, **overrides):
        """A full copy of the repository config with KEY=value lines appended (later lines win), used only through the
        documented test-only SCHOLARCHAIN_CONFIG_FILE."""
        text = (self.repo / "scripts/config/release.conf").read_text()
        overrides = dict({"PIPELINE_STEP_BIN_DIR": str(self.stepbin)}, **overrides)  # the fake node's step bin directory
        text += "\n" + "\n".join("%s=%s" % (k, v) for k, v in overrides.items()) + "\n"
        return self.write(self.aux / "test-release.conf", text)

    def pricing_file(self, confirmed=True, drop=()):
        text = (self.repo / "scripts/config/emr-pricing.conf").read_text()
        lines = []
        for line in text.splitlines():
            if line.startswith("EMR_PRICING_CONFIRMED_BY_HUMAN="):
                line = "EMR_PRICING_CONFIRMED_BY_HUMAN=%s" % ("true" if confirmed else "false")
            if any(line.startswith(d + "=") for d in drop):
                continue
            lines.append(line)
        return self.write(self.aux / "test-pricing.conf", "\n".join(lines) + "\n")

    def exec_env(self, confirmed=True, poll="0", **config):
        """Environment for a pipeline --execute run against fakes: test config + test pricing + a profile."""
        cfg = {"PIPELINE_POLL_SECONDS": poll}
        cfg.update(config)
        return {
            "SCHOLARCHAIN_CONFIG_FILE": str(self.test_config(**cfg)),
            "SCHOLARCHAIN_PRICING_FILE": str(self.pricing_file(confirmed)),
            "AWS_PROFILE": "test-profile",
        }

    # ----- pipeline helpers -----
    def pipeline_args(self, **ov):
        a = {
            "--cluster-id": "j-TESTCLUSTER", "--region": "us-east-2", "--instance-type": "m5.xlarge", "--core-count": "1",
            "--max-runtime-minutes": "60", "--budget-usd": "3", "--input-prefix": "s3://inbucket/data/in",
            "--output-prefix": "s3://outbucket/data/out", "--hadoop-submit-jar": "s3://abucket/hadoop-submit.jar",
            "--hadoop-libjars": "s3://abucket/hadoop-libs.jar", "--hadoop-config": str(self.repo / "inputs/prep.json"),
            "--er-jar": "s3://abucket/er.jar", "--er-policy": "s3://abucket/policy.json", "--er-config": "s3://abucket/er-config.json",
            "--spark-config-template": "s3://abucket/spark-template.json", "--datasets-manifest": str(self.repo / "inputs/datasets.json"),
            "--run-id": "bp-test-run-1",
        }
        drop = set()
        for k, v in ov.items():
            key = "--" + k.replace("_", "-")
            if v is None:
                drop.add(key)
            else:
                a[key] = str(v)
        argv = []
        for k, v in a.items():
            if k in drop:
                continue
            argv += [k, v]
        return argv

    def artifact_args(self, skip=(), **hashes):
        argv = []
        for name in ARTIFACT_NAMES:
            if name in skip:
                continue
            argv += ["--artifact-sha256", "%s=%s" % (name, hashes.get(name, HEX64))]
        return argv

    def full_args(self, skip_artifacts=(), extra=(), artifact_hashes=None, **ov):
        return self.pipeline_args(**ov) + self.artifact_args(skip=skip_artifacts, **(artifact_hashes or {})) + list(extra)

    def dry(self, extra_env=None, secrets=False, **kw):
        return self.run("run-bounded-pipeline.sh", self.full_args(**kw), extra_env, secrets)

    def run_config_sha(self, run):
        for line in run.lines():
            if line.startswith("RUN-CONFIG-SHA256: "):
                return line.split(": ", 1)[1].strip()
        raise AssertionError("no RUN-CONFIG-SHA256 line in the dry run\n" + run.describe())

    # ----- approval, receipts, ledger -----
    @staticmethod
    def account_hash(account=ACCOUNT):
        return hashlib.sha256(account.encode()).hexdigest()

    def write_prespend(self, name="prespend.json", **mods):
        snapshot = mods.pop("snapshot_dt", now_utc() - datetime.timedelta(hours=1))
        body = {
            "schema": "scholarchain.prespend-receipt.v1", "monitoring_confirmed_active": True,
            "cost_snapshot_utc": utc(snapshot), "reported_spend_usd": 1.5,
            "anthropic_spend_to_date_usd": 0.25, "voyage_spend_to_date_usd": 0.0,
            "unreported_usage_allowance_usd": 1.0, "reserves_usd": 2.0,
            # Repair round 3 ceiling arithmetic, hand-derived: 25 - (1.5 + 0.25 + 0.0) - 1.0 - 2.0 = 20.25 (the most a receipt may state).
            "remaining_headroom_usd": 20.25,
        }
        for k, v in mods.items():
            if v is Ellipsis:
                body.pop(k, None)
            else:
                body[k] = v
        path = self.aux / name
        self.write_json(path, body)
        return path

    def approval_values(self, dry_run, action="run-bounded-pipeline", prespend=None, budget="3", capacity="2", runtime="60",
                        cluster="j-TESTCLUSTER", region="us-east-2", manifest_sha=None):
        values = [
            ("APPROVED_ACTION", action),
            ("APPROVED_COMMIT", self.head()),
            ("APPROVED_ACCOUNT_SHA256", self.account_hash()),
            ("APPROVED_REGION", region),
            ("APPROVED_CLUSTER_ID", cluster),
            ("APPROVED_RUN_CONFIG_SHA256", self.run_config_sha(dry_run)),
            ("APPROVED_BUDGET_USD", budget),
            ("APPROVED_MAX_CAPACITY", capacity),
            ("APPROVED_MAX_RUNTIME_MINUTES", runtime),
            ("APPROVED_TEARDOWN", "auto-termination"),
            ("APPROVED_PRESPEND_SHA256", sha256_file(prespend) if prespend else HEX64),
        ]
        if manifest_sha:
            values.append(("APPROVED_MANIFEST_SHA256", manifest_sha))
        return values

    def write_approval(self, values, name="approval.md", override=None, drop=(), extra_lines=(), duplicate=(), raw_transform=None):
        override = override or {}
        lines = ["# Human approval record (test fixture)", "Prose lines like this one are ignored.", ""]
        for key, value in values:
            if key in drop:
                continue
            lines.append("%s=%s" % (key, override.get(key, value)))
            if key in duplicate:
                lines.append("%s=%s" % (key, override.get(key, value)))
        lines += list(extra_lines)
        text = "\n".join(lines) + "\n"
        if raw_transform:
            text = raw_transform(text)
        path = self.aux / name
        path.write_text(text)
        return path

    # ----- the run ledger (13C finding B2): outside the repository, under HOME, created only by --init-ledger -----
    LEDGER_REL = ".scholarchain/emr-ledger/runs.jsonl"

    @property
    def ledger_path(self):
        return self.home / self.LEDGER_REL

    def write_ledger(self, estimates=(), approvals=None, init=True):
        """Write an INITIALISED ledger directly (a hand-made fixture, independent of --init-ledger): the init record
        scripts/lib/budget.py documents (event, initialized_by, initialized_utc) then one reserve record per estimate.
        approvals optionally gives the approval_record_sha256 of each reserve record."""
        path = self.ledger_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as handle:
            if init:
                handle.write(json.dumps({"event": "init", "initialized_by": "fixture", "initialized_utc": "2026-11-01T00:00:00Z"}) + "\n")
            for i, est in enumerate(estimates):
                entry = {"event": "reserve", "run_id": "old-%d" % i, "action": "run-bounded-pipeline", "estimate_usd": est,
                         "run_config_sha256": HEX64, "reserved_utc": "2026-11-01T00:00:00Z"}
                if approvals:
                    entry["approval_record_sha256"] = approvals[i]
                handle.write(json.dumps(entry) + "\n")
        return path

    def ledger_records(self):
        if not self.ledger_path.exists():
            return []
        return [json.loads(line) for line in self.ledger_path.read_text().splitlines() if line.strip()]

    def reservations(self):
        """The reserve records in the ledger (an absent ledger has none)."""
        return [r for r in self.ledger_records() if r.get("event") == "reserve"]

    def exec_ready(self, approval_over=None, approval_drop=(), prespend_mods=None, pipeline_over=None, env_over=None, config=None,
                   duplicate=(), extra_lines=(), raw_transform=None, action="run-bounded-pipeline", ledger=True, serial=None,
                   approval_name="approval.md", **approval_kw):
        """Builds everything a green --execute needs, with optional single-point sabotage. Returns (args, env).

        ledger=True initialises the run ledger first when none exists (a green run needs one; B2). ledger=False leaves
        it absent. Approvals are single-use (B4): a second record for the same fixture needs a different text, so pass
        a distinct serial (a prose line the parser ignores) and approval_name."""
        if ledger and not self.ledger_path.exists():
            self.write_ledger([])
        if serial is not None:
            extra_lines = tuple(extra_lines) + ("Record serial: %s" % serial,)
        pre = self.write_prespend(**(prespend_mods or {}))
        env = self.exec_env(**(config or {}))
        if env_over:
            env.update(env_over)
        dry = self.dry(extra_env=env, **(pipeline_over or {}))
        assert dry.rc == 0, "the dry run used to derive the approval record failed\n" + dry.describe()
        values = self.approval_values(dry, action=action, prespend=pre, **approval_kw)
        approval = self.write_approval(values, name=approval_name, override=approval_over, drop=approval_drop, duplicate=duplicate,
                                       extra_lines=extra_lines, raw_transform=raw_transform)
        args = self.full_args(**(pipeline_over or {})) + ["--approval", str(approval), "--prespend", str(pre), "--execute"]
        return args, env

    def execute(self, **kw):
        secrets = kw.pop("secrets", False)
        args, env = self.exec_ready(**kw)
        self.log.write_text("")  # the dry run used for the approval record is not under test
        return self.run("run-bounded-pipeline.sh", args, env, secrets=secrets)

    # ----- retained files -----
    def tree_text(self, base):
        out = {}
        base = Path(base)
        if not base.exists():
            return out
        for p in sorted(base.rglob("*")):
            if p.is_file() and not p.is_symlink():
                try:
                    out[str(p.relative_to(base))] = p.read_text(errors="replace")
                except OSError:
                    pass
        return out


def last_step(run):
    steps = run.steps()
    return steps[-1] if steps else ""


def extract_body(run, name):
    text = run.out
    begin = "STEP-BODY-BEGIN: %s\n" % name
    end = "\nSTEP-BODY-END: %s" % name
    i = text.index(begin) + len(begin)
    j = text.index(end, i)
    return text[i:j] + "\n"


def step_args(run, name):
    """The EMR step's HadoopJarStepConfig.Args reconstructed from the dry run's printed command (one word per line, joined with
    backslash-newline): the exact argument list EMR would receive."""
    import shlex
    return shlex.split(extract_body(run, name).replace("\\\n", " "))


def step_params(args):
    """KEY -> [values] of the KEY=VALUE words after the step name (args[6:])."""
    out = {}
    for word in args[6:]:
        key, _, value = word.partition("=")
        out.setdefault(key, []).append(value)
    return out


def installed_program(fx, name):
    """Text of a step program on the fixture's fake node."""
    return (fx.stepbin / name).read_text()


def count_calls(calls, tool, first=None, second=None):
    n = 0
    for c in calls:
        if c["tool"] != tool:
            continue
        if first is not None and c["argv"][:1] != [first]:
            continue
        if second is not None and c["argv"][1:2] != [second]:
            continue
        n += 1
    return n
