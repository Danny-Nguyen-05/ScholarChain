#!/usr/bin/env python3
"""Phase 15 P6: local dry run of the EXACT Session 2 EMR step chain (stdlib; python3 -I). No AWS, Anthropic or Voyage call.

  python3 -I scripts/lib/p6_local_chain.py run --size S|L [--root target/phase15/p6] [--retain]
        [--workaround-hadoop-cli] [--er-xmx 12g] [--er-config FILE] [--hadoop-client-opts -Xmx4g] [--progress FILE]
  python3 -I scripts/lib/p6_local_chain.py seal --retention-dir DIR --render-report FILE

Workarounds (opt-in, each recorded in evidence/summary.json and the retention provenance; without them the chain stops where
the EMR chain would stop): --workaround-hadoop-cli (defects D1 and D2 of the hadoop-prep step: a non-v4 --run-id and a file://
--output-root) and --er-xmx (defect D3: the planned PIPELINE_ER_XMX heap runs out of memory; replaces the plan's ER_XMX).
--er-config FILE is a DIAGNOSTIC only (defect D4: the pinned ER config refuses the L input size); it cannot be combined with --retain.

`run` builds the real step plan with scripts/lib/pipeline.py (the same builder run-bounded-pipeline.sh uses) from the committed
15A experiment manifest (tokens resolved to a local placeholder bucket) and the pinned scripts/config/release.conf values, then
runs the six steps (stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job, copy-out) by calling the UNCHANGED
scripts/emr/sc-step.sh with each step's KEY=VALUE parameters, in order, stopping at the first failure. Only four node-local
values are replaced (MNT, RUNTIME_DIR, JOB_JAR, JAVA_HOME_FILE; plus ER_XMX with --er-xmx); every other parameter (step timeouts, sha256 pins, s3 refs,
Spark settings, ceilings) is the plan's. The node tools come from scripts/p6local/bin (see scripts/lib/p6_local.py for the
disclosed substitutions: LocalJobRunner instead of YARN for Hadoop, Spark local-cluster instead of YARN, a local directory
instead of S3). The Spark runtime is a fresh local copy of the pinned portable runtime archive (sha256 checked), with the
packaged job JAR installed where the bootstrap installs it.

Inputs (all local): the four packaged JARs (sbt packageEmr; target/emr-artifacts/emr-artifact-manifest.json), the Hadoop client
classpath (one line, `sbt "export hadoop/Compile/dependencyClasspath"`, in <root>/build/hadoop-dependency-classpath.raw.txt), the
input tree target/experiment-inputs/15a/size-100 (S) or size-l (L), the runtime archive RUNTIME_ARCHIVE_DEFAULT_PATH, JDK 17.

Outputs under <root> (git-ignored target/): work/<run-id>/ (the EFS and S3 stand-ins, logs, evidence/summary.json) and, with
--retain and only after every step exited 0, size-<S|L>/<spark-run-id>/ holding spark/ (the complete Spark export, the
directory passed as --export), SHA256SUMS (one line per file of spark/, relative paths 'spark/...', sorted; check with
`cd <dir> && shasum -a 256 -c SHA256SUMS`) and provenance.json. `seal` adds the render-only report of that export and checks that
its sourceRunId equals the run id, mode is render-only and embeddingCalls is 0.

Exit codes: 0 every step passed; 1 a step failed (evidence is still written); 2 usage; 3 refused before any step ran.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tarfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import p6_local  # noqa: E402

SIZES = {
    "S": {"manifest": "experiments/manifests/15a-emr-size-100.json", "input": "target/experiment-inputs/15a/size-100"},
    "L": {"manifest": "experiments/manifests/15a-emr-size-l.json", "input": "target/experiment-inputs/15a/size-l"},
}
NODE_LOCAL_KEYS = ("MNT", "RUNTIME_DIR", "JOB_JAR", "JAVA_HOME_FILE")
STEP_ORDER = ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out")
JAR_ROLES = {"hadoop-submit-jar": "hadoop-submit-jar", "hadoop-dependency-bundle": "hadoop-libjars",
             "entity-resolution-job-jar": "er-jar", "spark-job-jar": "job-jar"}
PLACEHOLDER_ENV = {"SCHOLARCHAIN_ARTIFACTS_BUCKET": "scholarchain-p6local-000000000000-artifacts", "SCHOLARCHAIN_RUN_PREFIX": "run-p6local"}
JAVA17 = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
LOADER_PART_CAP = 16 * 1024 * 1024


class Refused(Exception):
    pass


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_conf(path):
    """KEY=VALUE lines of a scripts/config file, read the way sc_load_config reads them (the file value, never the environment)."""
    values = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line[:1].isupper() and "=" in line:
                key, value = line.split("=", 1)
                if key.replace("_", "").isalnum():
                    values[key] = value
    return values


def py(args, env=None, check=True):
    result = subprocess.run([sys.executable, "-I"] + args, cwd=REPO, env=env, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise Refused("%s exited %d: %s%s" % (os.path.basename(args[0]), result.returncode, result.stdout[-2000:], result.stderr[-2000:]))
    return result


def build_plan(size, run_id, work, conf, pricing):
    """The step plan of the real builder for this experiment manifest; returns (plan, rendered manifest)."""
    env = dict(os.environ)
    env.update(PLACEHOLDER_ENV)
    rendered = os.path.join(work, "evidence", "rendered-manifest.json")
    py(["scripts/lib/experiment.py", "render", "--manifest", SIZES[size]["manifest"], "--out", rendered], env=env)
    lines = py(["scripts/lib/experiment.py", "args", "--manifest", rendered]).stdout.splitlines()
    pipe = list(lines)
    flags = dict(zip(lines[0::2], lines[1::2]))
    itype = flags["--instance-type"].upper().replace(".", "_")
    estimate = py(["scripts/lib/budget.py", "estimate", "--instance-type", flags["--instance-type"], "--primary-count", "1",
                   "--core-count", flags["--core-count"], "--task-count", flags["--max-task-count"], "--minutes", flags["--max-runtime-minutes"],
                   "--idle-seconds", flags["--max-idle-seconds"], "--ec2-rate", pricing.get("EMR_RATE_EC2_" + itype, ""),
                   "--emr-rate", pricing.get("EMR_RATE_EMR_" + itype, ""), "--max-run-usd", conf["EMR_MAX_RUN_USD"],
                   "--budget-usd", flags["--budget-usd"]]).stdout.strip()
    # run-bounded-pipeline.sh takes the idle bound from --max-idle-seconds; the plan builder takes it as --max-idle-timeout-seconds.
    pipe_args = []
    for flag, value in zip(pipe[0::2], pipe[1::2]):
        if flag != "--max-idle-seconds":
            pipe_args += [flag, value]
    plan_file = os.path.join(work, "evidence", "plan.json")
    ceilings = ("MAX_LOCAL_SAMPLE_RECORDS", "REDUCER_COUNT", "MAX_CANDIDATE_BLOCK_SIZE", "MAX_CANDIDATE_PAIRS_PER_BLOCK",
                "MAX_AUTHOR_TEAM_SIZE", "MAX_RECORD_BYTES", "MAX_XML_ENTITY_EXPANSION")
    args = ["scripts/lib/pipeline.py", "plan", "--out", plan_file, "--run-id", run_id, "--action", "run-experiment",
            "--cluster-id", "j-P6LOCALDRYRUN"] + pipe_args + [
        "--spark-conf-file", os.path.join(REPO, conf["PIPELINE_SPARK_CONF_FILE"]), "--efs-mount", conf["PIPELINE_EFS_MOUNT"],
        "--runtime-dir", conf["PIPELINE_RUNTIME_DIR"], "--job-jar-path", conf["PIPELINE_JOB_JAR_PATH"],
        "--java-home-file", conf["PIPELINE_JAVA_HOME_FILE"], "--er-xmx", conf["PIPELINE_ER_XMX"],
        "--expected-spark-version", conf["PIPELINE_EXPECTED_SPARK_VERSION"], "--expected-scala-version", conf["PIPELINE_EXPECTED_SCALA_VERSION"],
        "--step-weights", conf["PIPELINE_STEP_WEIGHTS"], "--runtime-archive-sha256", conf["RUNTIME_ARCHIVE_EXPECTED_SHA256"],
        "--estimate-json", estimate, "--max-capacity-cap", conf["PIPELINE_MAX_CAPACITY"], "--max-runtime-cap", conf["PIPELINE_MAX_RUNTIME_MINUTES"],
        "--max-input-bytes", conf["PIPELINE_MAX_INPUT_BYTES"], "--max-copyout-bytes", conf["PIPELINE_MAX_COPYOUT_BYTES"],
        "--max-idle-timeout-seconds", flags["--max-idle-seconds"], "--max-executors-per-node", conf["PIPELINE_MAX_EXECUTORS_PER_NODE"],
        "--kill-after-seconds", conf["PIPELINE_KILL_AFTER_SECONDS"], "--min-step-seconds", conf["PIPELINE_MIN_STEP_SECONDS"],
        "--step-bin-dir", conf["PIPELINE_STEP_BIN_DIR"], "--step-arg-max-chars", conf["PIPELINE_STEP_ARG_MAX_CHARS"]]
    for index, name in enumerate(ceilings):
        args += ["--ceiling-%d" % index, conf["PIPELINE_CEILING_" + name]]
    py(args)
    with open(plan_file, encoding="utf-8") as handle:
        plan = json.load(handle)
    with open(rendered, encoding="utf-8") as handle:
        return plan, json.load(handle)


def step_params(step, step_script_sha, overrides):
    """The KEY=VALUE parameters of one planned step, with only the node-local values replaced. Refuses a drifted runner pin."""
    args = step["args"]
    if args[:2] != ["bash", "-c"] or args[3] != "sc-step" or args[5] != step["name"]:
        raise Refused("step %s does not have the sc-step launcher form" % step["name"])
    if args[4] != step_script_sha:
        raise Refused("the plan pins sc-step.sh %s but scripts/emr/sc-step.sh is %s" % (args[4], step_script_sha))
    out, replaced = [], []
    for kv in args[6:]:
        key = kv.split("=", 1)[0]
        if key in overrides:
            out.append("%s=%s" % (key, overrides[key]))
            replaced.append(key)
        else:
            out.append(kv)
    return out, replaced


class DiskMonitor(threading.Thread):
    """Samples `du -sk` of named paths every interval seconds and keeps the peak of each and of the 'local' group sum."""

    def __init__(self, paths, local_group, interval=5):
        super().__init__(daemon=True)
        self.paths, self.local_group, self.interval = paths, local_group, interval
        self.stop_event = threading.Event()
        self.peaks = {name: 0 for name in paths}
        self.peak_local = 0
        self.samples = 0

    def sample(self):
        sizes = {}
        for name, path in self.paths.items():
            if os.path.exists(path):
                out = subprocess.run(["du", "-sk", path], capture_output=True, text=True).stdout.split()
                sizes[name] = int(out[0]) * 1024 if out else 0
            else:
                sizes[name] = 0
            self.peaks[name] = max(self.peaks[name], sizes[name])
        self.peak_local = max(self.peak_local, sum(sizes[n] for n in self.local_group))
        self.samples += 1

    def run(self):
        while not self.stop_event.is_set():
            self.sample()
            self.stop_event.wait(self.interval)

    def finish(self):
        self.stop_event.set()
        self.join()
        self.sample()
        return {"peakBytes": self.peaks, "peakLocalGroupBytes": self.peak_local, "localGroup": list(self.local_group),
                "samples": self.samples, "intervalSeconds": self.interval}


class ProcMonitor(threading.Thread):
    """Samples `ps` every interval seconds: the peak resident set of the java processes whose command line names the run's
    work directory (the step's JVMs: Hadoop client and LocalJobRunner, the ER JVM, the Spark driver and executors)."""

    def __init__(self, marker, interval=2):
        super().__init__(daemon=True)
        self.marker, self.interval = marker, interval
        self.stop_event = threading.Event()
        self.peak_single, self.peak_sum, self.max_processes, self.samples = 0, 0, 0, 0

    def sample(self):
        out = subprocess.run(["ps", "-axo", "rss=,command="], capture_output=True, text=True).stdout.splitlines()
        rss = []
        for line in out:
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[0].isdigit() and "java" in parts[1] and self.marker in parts[1]:
                rss.append(int(parts[0]) * 1024)
        self.peak_single = max([self.peak_single] + rss)
        self.peak_sum = max(self.peak_sum, sum(rss))
        self.max_processes = max(self.max_processes, len(rss))
        self.samples += 1

    def run(self):
        while not self.stop_event.is_set():
            self.sample()
            self.stop_event.wait(self.interval)

    def finish(self):
        self.stop_event.set()
        self.join()
        return {"peakSingleJvmRssBytes": self.peak_single, "peakSumJvmRssBytes": self.peak_sum, "maxJvms": self.max_processes,
                "samples": self.samples, "intervalSeconds": self.interval}


def prepare_runtime(conf, work, job_jar, job_sha):
    archive = os.path.join(REPO, conf["RUNTIME_ARCHIVE_DEFAULT_PATH"])
    if p6_local.sha256_file(archive) != conf["RUNTIME_ARCHIVE_EXPECTED_SHA256"]:
        raise Refused("the runtime archive does not have the pinned sha256")
    dest = os.path.join(work, "runtime")
    with tarfile.open(archive) as tar:
        tar.extractall(dest, filter="data")
    runtime = os.path.join(dest, "scholarchain-runtime")
    application = os.path.join(runtime, "application", "scholarchain-job.jar")
    shutil.copyfile(job_jar, application)  # as the bootstrap installs the uploaded job JAR over the archive's copy
    if p6_local.sha256_file(application) != job_sha:
        raise Refused("the installed job jar does not have the manifest sha256")
    real = os.path.join(runtime, "bin", "spark-submit")
    os.rename(real, real + ".real")
    os.symlink(os.path.join(REPO, "scripts", "p6local", "bin", "spark-submit"), real)
    return runtime, application


def stage_s3(rendered, s3_root, size, config_sources, artifacts):
    """Places every artifact, config and the input tree at the s3 key the rendered manifest names (the upload layout)."""
    pipeline = rendered["pipeline"]
    files = {
        "hadoop_submit_jar": artifacts["hadoop-submit-jar"], "hadoop_libjars": artifacts["hadoop-libjars"], "er_jar": artifacts["er-jar"],
        "hadoop_config": config_sources["hadoop-config"], "er_policy": config_sources["er-policy"], "er_config": config_sources["er-config"],
        "spark_config_template": config_sources["spark-config-template"],
    }
    for key, path in files.items():
        dest = p6_local.s3_local(s3_root, pipeline[key])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
    input_dest = p6_local.s3_local(s3_root, pipeline["input_prefix"].rstrip("/") + "/")
    shutil.copytree(os.path.join(REPO, SIZES[size]["input"]), input_dest)


def run_step(name, params, env, logs):
    out_path, err_path = os.path.join(logs, name + ".stdout.log"), os.path.join(logs, name + ".stderr.log")
    start, t0 = utc(), time.monotonic()
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        rc = subprocess.run(["bash", os.path.join(REPO, "scripts", "emr", "sc-step.sh"), name] + params,
                            cwd=env["P6_WORK"], env=env, stdout=out, stderr=err).returncode
    return {"step": name, "startUtc": start, "endUtc": utc(), "wallSeconds": round(time.monotonic() - t0, 2), "exitCode": rc,
            "stdout": os.path.relpath(out_path, REPO), "stderr": os.path.relpath(err_path, REPO)}


def grep_count(root, needle):
    count = 0
    for full in p6_local.walk_files(root, False) if os.path.isdir(root) else []:
        with open(full, "rb") as handle:
            count += handle.read().count(needle.encode("utf-8"))
    return count


def collect(run_root, logs, s3_root, rendered, run_id):
    """Per-step evidence read from the outputs (no recomputation): counters, rejects, ER summary, Spark counters, sidecar parts."""
    ev = {}
    hadoop_out = open(os.path.join(logs, "hadoop-prep.stdout.log"), encoding="utf-8").read() if os.path.exists(os.path.join(logs, "hadoop-prep.stdout.log")) else ""
    for line in hadoop_out.splitlines():
        for key in ("runId", "counters", "largestTeam", "largestPairExpansion", "largestBlock", "runDirectory"):
            if line.startswith(key + "="):
                ev.setdefault("hadoopStdout", {})[key] = line.split("=", 1)[1]
    counters = ev.get("hadoopStdout", {}).get("counters", "")
    ev["hadoopCounters"] = {k: int(v) for k, v in (item.split(":", 1) for item in counters.split(",") if ":" in item)}
    hadoop_dir = os.path.join(run_root, "hadoop")
    reject_dirs = []
    for current, dirs, _files in os.walk(hadoop_dir):
        if os.path.basename(current) == "reject" and os.sep + "export" + os.sep in current + os.sep:
            reject_dirs.append(current)
    ev["rejects"] = {
        "rejectDirectories": len(reject_dirs),
        "rejectFiles": sum(len(p6_local.walk_files(d, False)) for d in reject_dirs),
        "rejectBytes": sum(os.path.getsize(f) for d in reject_dirs for f in p6_local.walk_files(d, False)),
        "maxLocalSampleRecordsOccurrences": sum(grep_count(d, "maxLocalSampleRecords") for d in reject_dirs),
        "maxAuthorTeamSizeOccurrences": sum(grep_count(d, "maxAuthorTeamSize") for d in reject_dirs),
    }
    for name in ("counter-summary.json", "run-manifest.json"):
        for full in p6_local.walk_files(hadoop_dir, False) if os.path.isdir(hadoop_dir) else []:
            if os.path.basename(full) == name and "/export/" not in full and "/intermediate/" not in full:
                ev.setdefault("hadoopFiles", {})[name] = os.path.relpath(full, REPO)
    er_run = os.path.join(run_root, "er", "run")
    if os.path.isdir(er_run):
        ev["erTopLevelFiles"] = sorted(n for n in os.listdir(er_run) if os.path.isfile(os.path.join(er_run, n)))
        for name in ("resolution-manifest.json",):
            path = os.path.join(er_run, name)
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as handle:
                    doc = json.load(handle)
                ev["erManifestKeys"] = sorted(doc.keys()) if isinstance(doc, dict) else None
                ev["erManifest"] = {k: v for k, v in doc.items() if not isinstance(v, (list, dict))} if isinstance(doc, dict) else None
                for key in ("counts", "counters", "summary", "diagnostics"):
                    if isinstance(doc, dict) and isinstance(doc.get(key), dict):
                        ev["erManifest"][key] = doc[key]
    er_stdout = os.path.join(logs, "entity-resolution.stdout.log")
    if os.path.isfile(er_stdout):
        ev["erStdoutTail"] = open(er_stdout, encoding="utf-8", errors="replace").read().splitlines()[-15:]
    spark_root = os.path.join(run_root, "spark")
    exports = sorted(d for d in os.listdir(spark_root) if d.startswith("run:")) if os.path.isdir(spark_root) else []
    ev["sparkExports"] = exports
    if len(exports) == 1:
        export = os.path.join(spark_root, exports[0])
        ev["sparkRunId"] = exports[0]
        ev["sparkComplete"] = os.path.isfile(os.path.join(export, "_SCHOLARCHAIN_SPARK_COMPLETE"))
        path = os.path.join(export, "counters.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as handle:
                ev["sparkCounters"] = {row["name"]: row["value"] for row in json.load(handle) if row.get("context", {}).get("windowId") is None}
        sidecar = os.path.join(export, "neptune-opencypher-csv")
        parts = [(os.path.relpath(f, export), os.path.getsize(f)) for f in p6_local.walk_files(sidecar, False)] if os.path.isdir(sidecar) else []
        csv_parts = [p for p in parts if p[0].endswith(".csv")]
        ev["sidecar"] = {"files": len(parts), "csvParts": len(csv_parts), "maxPartBytes": max([b for _, b in csv_parts] or [0]),
                         "partsOverCap": [p for p in csv_parts if p[1] > LOADER_PART_CAP], "capBytes": LOADER_PART_CAP,
                         "totalBytes": sum(b for _, b in parts)}
        ev["exportBytes"] = sum(os.path.getsize(f) for f in p6_local.walk_files(export, False))
        ev["exportFiles"] = len(p6_local.walk_files(export, False))
    manifest = os.path.join(run_root, "copyout-manifest.sha256")
    out_prefix = rendered["pipeline"]["output_prefix"].rstrip("/") + "/" + run_id
    copied_root = p6_local.s3_local(s3_root, out_prefix + "/").rstrip("/")
    if os.path.isfile(manifest):
        listed = [line.split("  ", 1)[1] for line in open(manifest, encoding="utf-8").read().splitlines() if "  " in line]
        copied = sorted(os.path.relpath(f, copied_root) for f in p6_local.walk_files(copied_root, False))
        ev["copyOut"] = {
            "manifestFiles": len(listed),
            "selectedBytes": sum(os.path.getsize(os.path.join(run_root, rel)) for rel in listed),
            "copiedFilesExcludingManifest": len([c for c in copied if c != "copyout-manifest.sha256"]),
            "copiedSetEqualsManifest": sorted(listed) == sorted(c for c in copied if c != "copyout-manifest.sha256"),
            "copiedBytes": sum(os.path.getsize(f) for f in p6_local.walk_files(copied_root, False)),
            "ceilingBytes": None,
        }
    return ev


def run(args):
    if args.retain and args.er_config:
        raise Refused("--retain is refused with a diagnostic --er-config: a retained export must come from the pinned ER config")
    size = args.size
    root = os.path.abspath(args.root)
    conf = read_conf(os.path.join(REPO, "scripts", "config", "release.conf"))
    pricing = read_conf(os.path.join(REPO, conf["PIPELINE_PRICING_FILE"]))
    with open(os.path.join(REPO, "target", "emr-artifacts", "emr-artifact-manifest.json"), encoding="utf-8") as handle:
        built = {JAR_ROLES[a["role"]]: os.path.join(REPO, a["path"]) for a in json.load(handle)["artifacts"]}
    with open(os.path.join(REPO, "experiments", "inputs", "15a", "config-sources.json"), encoding="utf-8") as handle:
        config_sources = {k: os.path.join(REPO, v["path"]) for k, v in json.load(handle)["files"].items()}
    with open(os.path.join(root, "build", "hadoop-dependency-classpath.raw.txt"), encoding="utf-8") as handle:
        # one entry per line or the single colon-separated line that `sbt "export hadoop/Compile/dependencyClasspath"` prints
        entries = handle.read().replace(":", "\n").split()
        client_cp = ":".join(e for e in entries if e.endswith(".jar") and not os.path.abspath(e).startswith(REPO + os.sep))
    if not os.path.isfile(os.path.join(JAVA17, "bin", "java")):
        raise Refused("JDK 17 not found at %s" % JAVA17)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = "p6-%s-%s" % (size, stamp)
    work = os.path.join(root, "work", run_id)
    for sub in ("evidence", "logs", "s3", "mnt", "tmp", "spark-local", "bin"):
        os.makedirs(os.path.join(work, sub))
    chain_start = utc()
    plan, rendered = build_plan(size, run_id, work, conf, pricing)
    pins = rendered["pipeline"]["artifact_sha256"]
    for name in ("hadoop-submit-jar", "hadoop-libjars", "er-jar", "job-jar"):
        if p6_local.sha256_file(built[name]) != pins[name]:
            raise Refused("the built %s does not have the manifest sha256 %s" % (name, pins[name]))
    for name in ("hadoop-config", "er-policy", "er-config", "spark-config-template"):
        if p6_local.sha256_file(config_sources[name]) != pins[name]:
            raise Refused("%s does not have the manifest sha256" % name)
    runtime, job_jar = prepare_runtime(conf, work, built["job-jar"], pins["job-jar"])
    s3_root = os.path.join(work, "s3")
    stage_s3(rendered, s3_root, size, config_sources, built)
    mnt = os.path.join(work, "mnt")
    java_home_file = os.path.join(work, "java-home")
    with open(java_home_file, "w", encoding="utf-8") as handle:
        handle.write(JAVA17 + "\n")
    with open(os.path.join(work, "proc-mounts"), "w", encoding="utf-8") as handle:
        handle.write("p6-local-efs-stand-in %s nfs4 rw 0 0\n" % mnt)
    bindir = os.path.join(work, "bin")
    for tool in ("aws", "hadoop", "yarn", "timeout"):
        os.symlink(os.path.join(REPO, "scripts", "p6local", "bin", tool), os.path.join(bindir, tool))
    os.symlink(sys.executable, os.path.join(bindir, "python3"))
    env = {
        "PATH": "%s:/usr/bin:/bin:/usr/sbin:/sbin" % bindir, "HOME": os.environ.get("HOME", "/tmp"), "LANG": "C", "LC_ALL": "C",
        "TMPDIR": os.path.join(work, "tmp"), "SC_PROC_MOUNTS": os.path.join(work, "proc-mounts"), "P6_WORK": work,
        "P6_S3_ROOT": s3_root, "P6_SHIM_LOG": os.path.join(work, "logs", "shim-calls.jsonl"), "P6_JAVA_HOME": JAVA17,
        "P6_HADOOP_CLIENT_CLASSPATH": client_cp, "P6_HADOOP_CLIENT_OPTS": args.hadoop_client_opts,
        "P6_SPARK_LOCAL_DIRS": os.path.join(work, "spark-local"),
        "P6_WORKAROUND_HADOOP_CLI": "1" if args.workaround_hadoop_cli else "0",
        "AWS_CONFIG_FILE": "/dev/null", "AWS_SHARED_CREDENTIALS_FILE": "/dev/null", "AWS_EC2_METADATA_DISABLED": "true",
    }
    overrides = {"MNT": mnt, "RUNTIME_DIR": runtime, "JOB_JAR": job_jar, "JAVA_HOME_FILE": java_home_file}
    if args.er_xmx:
        overrides["ER_XMX"] = args.er_xmx
    if args.er_config:
        overrides["ER_CONFIG_REF"] = os.path.abspath(args.er_config)
        overrides["ER_CONFIG_SHA"] = p6_local.sha256_file(args.er_config)
    step_sha = p6_local.sha256_file(os.path.join(REPO, "scripts", "emr", "sc-step.sh"))
    run_root = os.path.join(mnt, "runs", run_id)
    results, disk = [], {}
    names = [s["name"] for s in plan["steps"]]
    if tuple(names) != STEP_ORDER:
        raise Refused("unexpected step order %s" % names)
    progress(args, "%s %s: chain start %s (work %s)" % (utc(), size, run_id, os.path.relpath(work, REPO)))
    for step in plan["steps"]:
        params, replaced = step_params(step, step_sha, overrides)
        monitor = None
        if step["name"] in ("spark-class-origin", "spark-job"):
            monitor = DiskMonitor({"sparkLocalDirs": os.path.join(work, "spark-local"), "executorWorkDirs": os.path.join(runtime, "work"),
                                   "checkpoint": os.path.join(run_root, "spark-checkpoint"), "sparkOutput": os.path.join(run_root, "spark")},
                                  ("sparkLocalDirs", "executorWorkDirs"))
            monitor.start()
        procs = ProcMonitor(work)
        procs.start()
        result = run_step(step["name"], params, env, os.path.join(work, "logs"))
        result["jvm"] = procs.finish()
        result["timeoutSeconds"] = step["timeout_seconds"]
        result["nodeLocalReplaced"] = replaced
        if monitor:
            disk[step["name"]] = monitor.finish()
        results.append(result)
        progress(args, "%s %s: step %s exit %d wall %.1f s (EMR timeout %s s)" % (utc(), size, step["name"], result["exitCode"], result["wallSeconds"], step["timeout_seconds"]))
        if result["exitCode"] != 0:
            break
    chain_end = utc()
    evidence = collect(run_root, os.path.join(work, "logs"), s3_root, rendered, run_id)
    if "copyOut" in evidence:
        evidence["copyOut"]["ceilingBytes"] = int(conf["PIPELINE_MAX_COPYOUT_BYTES"])
    ok = len(results) == len(STEP_ORDER) and all(r["exitCode"] == 0 for r in results)
    shim_calls = []
    if os.path.isfile(env["P6_SHIM_LOG"]):
        shim_calls = [json.loads(line) for line in open(env["P6_SHIM_LOG"], encoding="utf-8")]
    summary = {
        "schema": "scholarchain.p6-local-chain.v1", "size": size, "runId": run_id, "manifest": SIZES[size]["manifest"],
        "inputTree": SIZES[size]["input"], "inputTreeSha256": p6_local.tree_sha256(os.path.join(REPO, SIZES[size]["input"])),
        "chainStartUtc": chain_start, "chainEndUtc": chain_end, "allStepsPassed": ok, "steps": results, "disk": disk,
        "evidence": evidence, "git": git_state(), "pins": pins, "runtimeArchiveSha256": conf["RUNTIME_ARCHIVE_EXPECTED_SHA256"],
        "stepRunnerSha256": step_sha, "hadoopClientOpts": args.hadoop_client_opts,
        "erXmxOverride": args.er_xmx or None, "planErXmx": conf["PIPELINE_ER_XMX"],
        "erConfigOverride": ({"path": os.path.relpath(os.path.abspath(args.er_config), REPO), "sha256": overrides["ER_CONFIG_SHA"]}
                             if args.er_config else None),
        "workarounds": (["entity-resolution: DIAGNOSTIC ER config %s (sha256 %s) instead of the pinned er-config (defect D4: input.maxInputBytes refuses L)"
                         % (os.path.relpath(os.path.abspath(args.er_config), REPO), overrides["ER_CONFIG_SHA"])] if args.er_config else []) + (["entity-resolution: ER_XMX %s -> %s (defect D3: the planned heap runs out of memory)" % (conf["PIPELINE_ER_XMX"], args.er_xmx)]
                        if args.er_xmx else []) + (["hadoop: --run-id <pipeline run id> removed because HadoopPrepPipeline accepts only run:<uuid v4> (defect D1: the real EMR step fails at once)",
                         "hadoop: --output-root file://<dir> -> <dir> because FsPaths.runPath resolves file:/... as a relative path (defect D2: job J03 fails)"]
                        if args.workaround_hadoop_cli else []),
        "awsCallsServedLocally": sorted({" ".join(c["argv"][:2]) for c in shim_calls if c["tool"] == "aws"}),
        "substitutions": ["hadoop: --execution-mode cluster -> local (LocalJobRunner, no YARN)",
                          "spark-submit: --master yarn --deploy-mode cluster -> local-cluster[maxExecutors,executorCores,executorMemoryMiB] client mode",
                          "spark.authenticate: throwaway random secret via 0600 properties file (YARN generates one per application)",
                          "S3 -> local directory %s with awscli filter semantics" % os.path.relpath(s3_root, REPO),
                          "EFS mount -> local directory %s" % os.path.relpath(mnt, REPO),
                          "node-local parameters replaced: %s" % ", ".join(NODE_LOCAL_KEYS)],
    }
    with open(os.path.join(work, "evidence", "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    progress(args, "%s %s: chain end, all steps passed=%s, summary %s" % (utc(), size, ok, os.path.relpath(os.path.join(work, "evidence", "summary.json"), REPO)))
    if ok and args.retain:
        retain(root, size, run_root, evidence, summary, config_sources)
    print(json.dumps({"runId": run_id, "allStepsPassed": ok, "summary": os.path.relpath(os.path.join(work, "evidence", "summary.json"), REPO)}))
    return 0 if ok else 1


def git_state():
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    porcelain = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True).stdout
    relevant = subprocess.run(["git", "-C", REPO, "status", "--porcelain", "--untracked-files=all", "--", "modules/core", "modules/hadoop",
                               "modules/entity-resolution", "modules/spark", "experiments/inputs/15a", "experiments/manifests", "scripts/emr",
                               "scripts/config", "build.sbt", "project"], capture_output=True, text=True).stdout.splitlines()
    import hashlib
    return {"head": head, "workTreeClean": porcelain == "", "porcelainSha256": hashlib.sha256(porcelain.encode()).hexdigest(),
            "pipelineRelevantChangesVsHead": relevant}


def retain(root, size, run_root, evidence, summary, config_sources):
    spark_run = evidence.get("sparkRunId")
    if not spark_run or not evidence.get("sparkComplete"):
        raise Refused("no single complete Spark export to retain")
    dest = os.path.join(root, "size-%s" % size, spark_run)
    if os.path.exists(dest):
        raise Refused("%s already exists: a retention directory is never overwritten" % dest)
    os.makedirs(dest)
    shutil.copytree(os.path.join(run_root, "spark", spark_run), os.path.join(dest, "spark"), symlinks=True)
    sums = p6_local.sha256sums(os.path.join(dest, "spark"), prefix="spark/")
    if sums != p6_local.sha256sums(os.path.join(run_root, "spark", spark_run), prefix="spark/"):
        raise Refused("the retained copy differs from the run's export")
    with open(os.path.join(dest, "SHA256SUMS"), "w", encoding="utf-8") as handle:
        handle.write(sums)
    provenance = {
        "schema": "scholarchain.p6-retention-provenance.v1", "p6RunId": spark_run, "localChainRunId": summary["runId"],
        "git": summary["git"], "jobJarSha256": summary["pins"]["job-jar"], "jobJarEqualsSManifest": True,
        "sparkTemplateSha256": p6_local.sha256_file(config_sources["spark-config-template"]),
        "sparkTemplateEqualsManifest": p6_local.sha256_file(config_sources["spark-config-template"]) == summary["pins"]["spark-config-template"],
        "inputTree": summary["inputTree"], "inputTreeSha256": summary["inputTreeSha256"],
        "inputTreeSha256Definition": "sha256 of the sorted 'sha256  relative-path' listing of every file of the input tree",
        "allArtifactPins": summary["pins"], "runtimeArchiveSha256": summary["runtimeArchiveSha256"],
        "startUtc": summary["chainStartUtc"], "endUtc": summary["chainEndUtc"], "substitutions": summary["substitutions"],
        "workarounds": summary["workarounds"],
        "sha256sumsSha256": p6_local.sha256_file(os.path.join(dest, "SHA256SUMS")), "renderReport": None,
        "check": "cd %s && shasum -a 256 -c SHA256SUMS" % os.path.relpath(dest, REPO),
    }
    with open(os.path.join(dest, "provenance.json"), "w", encoding="utf-8") as handle:
        json.dump(provenance, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("RETAINED %s sha256sums=%s" % (os.path.relpath(dest, REPO), provenance["sha256sumsSha256"]))


def seal(args):
    dest = os.path.abspath(args.retention_dir)
    path = os.path.join(dest, "provenance.json")
    with open(path, encoding="utf-8") as handle:
        provenance = json.load(handle)
    with open(args.render_report, encoding="utf-8") as handle:
        report = json.load(handle)
    problems = []
    if report.get("sourceRunId") != provenance["p6RunId"]:
        problems.append("sourceRunId %s != p6RunId %s" % (report.get("sourceRunId"), provenance["p6RunId"]))
    if report.get("mode") != "render-only" or report.get("embeddingCalls") != 0:
        problems.append("the report is not a render-only report with embeddingCalls 0")
    if p6_local.sha256_file(os.path.join(dest, "SHA256SUMS")) != provenance["sha256sumsSha256"]:
        problems.append("SHA256SUMS changed since retention")
    with open(os.path.join(dest, "SHA256SUMS"), encoding="utf-8") as handle:
        recorded = handle.read()
    if p6_local.sha256sums(os.path.join(dest, "spark"), prefix="spark/") != recorded:
        problems.append("the retained export no longer matches SHA256SUMS")
    if problems:
        raise Refused("; ".join(problems))
    os.makedirs(os.path.join(dest, "render"), exist_ok=True)
    target = os.path.join(dest, "render", "render-report.json")
    if os.path.exists(target):
        raise Refused("%s already exists" % target)
    shutil.copyfile(args.render_report, target)
    qualifications = args.render_report + ".source-qualifications.json"
    if os.path.isfile(qualifications):
        shutil.copyfile(qualifications, target + ".source-qualifications.json")
    provenance["renderReport"] = {"path": "render/render-report.json", "sha256": p6_local.sha256_file(target),
                                  "sourceRunId": report["sourceRunId"], "selectedDocuments": report.get("selectedDocuments"),
                                  "sizeEvidence": report.get("sizeEvidence"), "embeddingCalls": report["embeddingCalls"]}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(provenance, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)
    print("SEALED %s sourceRunId=%s" % (os.path.relpath(dest, REPO), report["sourceRunId"]))
    return 0


def progress(args, line):
    if args.progress:
        with open(args.progress, "a", encoding="utf-8") as handle:
            handle.write("- " + line + "\n")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("--size", choices=sorted(SIZES), required=True)
    p.add_argument("--root", default=os.path.join(REPO, "target", "phase15", "p6"))
    p.add_argument("--retain", action="store_true")
    p.add_argument("--hadoop-client-opts", default="-Xmx4g")
    p.add_argument("--er-config", default="", help="DIAGNOSTIC: a local ER config used instead of the pinned one (recorded; never with --retain)")
    p.add_argument("--er-xmx", default="", help="recorded override of the planned ER_XMX (workaround for D3); default: the plan's value")
    p.add_argument("--workaround-hadoop-cli", action="store_true",
                   help="recorded workaround for defects D1/D2 of the hadoop-prep step (non-v4 --run-id; file:// --output-root); without it the step fails as it would on EMR")
    p.add_argument("--progress", default="")
    p.set_defaults(fn=run)
    p = sub.add_parser("seal")
    p.add_argument("--retention-dir", required=True)
    p.add_argument("--render-report", required=True)
    p.set_defaults(fn=seal)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except Refused as error:
        print("P6-REFUSED: %s" % error, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
