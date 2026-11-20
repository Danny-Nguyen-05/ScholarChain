#!/usr/bin/env python3
"""Phase 15 second-size experiment: run the unchanged Spark job (Phase6Main) locally on a Hadoop run + an identity ER run root.

ER BYPASSED: identity pass-through (no cross-source resolution), local only, not the EMR path.

Reproduces the P6 S spark-job step outside the chain, changing only paths and the run label:
  * the spark-submit argv is the one the P6 S run logged for Phase6Main (<p6-work>/logs/shim-calls.jsonl), with the S run root replaced
    by this run's root, the config path replaced, and the S run id in --name / spark.yarn.tags replaced by this run's label;
  * the job JAR is the P6 S runtime's installed application JAR (sha256 must equal the pinned job-jar sha);
  * the config is rendered from experiments/inputs/15a/spark-emr-template.json (sha256 must equal the pin) by the unchanged
    scripts/emr/sc-render-spark-config.py;
  * spark-submit is the P6 runtime's bin/spark-submit (the unchanged P6 stand-in: local-cluster[maxExecutors,cores,MiB], client mode);
  * environment as sc-step.sh spark_env plus the P6 chain environment (TMPDIR, P6_SPARK_LOCAL_DIRS, LANG/LC_ALL=C, AWS files /dev/null).
Samples (every --interval s) the summed RSS of the process tree and the bytes under spark-local, spark-checkpoint and spark output, then
reads counters.json, analytics-report.json, event-log-summary.json and the neptune-opencypher-csv sidecar into <base>/summary.json.
No network, no AWS. Refuses an existing <base>.

Usage (repository root):
  python3 -I experiments/scripts/run_spark_bypass.py --label L --hadoop-root DIR --er-root DIR --base DIR \
      --p6-work target/phase15/p6/work/p6-S-20261116T164523Z [--kill-after-seconds 7200]
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DISCLOSURE = "ER bypassed: identity pass-through (no cross-source resolution), local only, not the EMR path"
TEMPLATE = os.path.join(REPO, "experiments", "inputs", "15a", "spark-emr-template.json")
RENDER = os.path.join(REPO, "scripts", "emr", "sc-render-spark-config.py")
SPARK_MAIN = "edu.uic.cs441.scholarchain.spark.Phase6Main"
EMR_SPARK_STEP_CAP_SECONDS = 2160
LOADER_PART_CAP = 16 * 1024 * 1024


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_bytes(root):
    total = 0
    for current, _dirs, files in os.walk(root):
        for name in files:
            try:
                total += os.lstat(os.path.join(current, name)).st_size
            except OSError:
                pass
    return total


def tree_rss(root_pid):
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="], capture_output=True, text=True).stdout
    children, rss = {}, {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            pid, ppid, kb = int(parts[0]), int(parts[1]), int(parts[2])
            children.setdefault(ppid, []).append(pid)
            rss[pid] = kb * 1024
    total, stack, seen = 0, [root_pid], set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        total += rss.get(pid, 0)
        stack.extend(children.get(pid, []))
    return total, len(seen)


def logged_spark_argv(p6_work):
    with open(os.path.join(p6_work, "logs", "shim-calls.jsonl"), encoding="utf-8") as handle:
        calls = [json.loads(line) for line in handle]
    jobs = [c["argv"] for c in calls if c["tool"] == "spark-submit" and SPARK_MAIN in c["argv"]]
    if len(jobs) != 1:
        raise SystemExit("expected exactly one logged Phase6Main spark-submit in %s" % p6_work)
    return jobs[0]


def localize_argv(argv, p6_work, base, label, config_path):
    run_id = os.path.basename(p6_work.rstrip("/"))
    old_root = os.path.join(p6_work, "mnt")
    out, changes = [], []
    for i, arg in enumerate(argv):
        new = arg
        if arg.startswith("spark.yarn.stagingDir="):
            new = "spark.yarn.stagingDir=file://%s" % os.path.join(base, "staging")
        elif i == len(argv) - 1:
            new = config_path
        elif arg == "scholarchain-bounded-%s" % run_id:
            new = "scholarchain-bounded-%s" % label
        elif arg == "spark.yarn.tags=%s" % run_id:
            new = "spark.yarn.tags=%s" % label
        elif old_root in arg and not arg.startswith("local:"):
            raise SystemExit("unexpected S path in argv: %s" % arg)
        if new != arg:
            changes.append({"from": arg, "to": new})
        out.append(new)
    return out, changes


def collect(export):
    ev = {"export": export}
    with open(os.path.join(export, "counters.json"), encoding="utf-8") as handle:
        counters = {r["name"]: r["value"] for r in json.load(handle) if r.get("context", {}).get("windowId") is None}
    ev["counters"] = counters
    with open(os.path.join(export, "analytics-report.json"), encoding="utf-8") as handle:
        report = json.load(handle)
    vertices = {m["window"]: m["rows"] for m in report["metrics"]}
    ev["componentsByWindow"] = {c["window"]: {k: c[k] for k in ("components", "largestSize", "largestFraction", "singletons")}
                                for c in report["components"]}
    ev["communityConvergence"] = {c["window"]: c for c in report["communityConvergence"]}
    edges = {}
    sidecar = os.path.join(export, "neptune-opencypher-csv")
    parts = []
    for current, _dirs, files in os.walk(sidecar):
        for name in files:
            full = os.path.join(current, name)
            if name.endswith(".csv"):
                parts.append((os.path.relpath(full, export), os.path.getsize(full)))
                if os.sep + "coauthor-edges" + os.sep in full:
                    with open(full, encoding="utf-8", newline="") as handle:
                        reader = csv.reader(handle)
                        header = next(reader, None)
                        if header:
                            idx = header.index("windowId:String")
                            for row in reader:
                                edges[row[idx]] = edges.get(row[idx], 0) + 1
    ev["graphByWindow"] = {w: {"activeResearchers": vertices.get(w), "coauthorEdges": edges.get(w),
                               **ev["componentsByWindow"].get(w, {})} for w in sorted(set(vertices) | set(edges))}
    ev["sidecar"] = {"csvParts": len(parts), "maxPartBytes": max([b for _, b in parts] or [0]), "capBytes": LOADER_PART_CAP,
                     "partsOverCap": [p for p in parts if p[1] > LOADER_PART_CAP], "totalBytes": sum(b for _, b in parts)}
    with open(os.path.join(export, "event-log-summary.json"), encoding="utf-8") as handle:
        events = json.load(handle)
    stages = events.get("stages", [])
    ev["eventLog"] = {"stages": len(stages), "tasks": sum(s.get("tasks", 0) for s in stages),
                      "failedTasks": sum(s.get("failedTasks", 0) for s in stages),
                      "shuffleWriteBytes": sum(s.get("shuffleWriteBytes", 0) for s in stages),
                      "otherKeys": sorted(k for k in events if k != "stages")}
    ev["exportBytes"] = tree_bytes(export)
    with open(os.path.join(export, "run-metadata.json"), encoding="utf-8") as handle:
        ev["runMetadata"] = json.load(handle)
    ev["sparkComplete"] = os.path.isfile(os.path.join(export, "_SCHOLARCHAIN_SPARK_COMPLETE"))
    return ev


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", required=True)
    parser.add_argument("--hadoop-root", required=True)
    parser.add_argument("--er-root", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--p6-work", required=True)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--kill-after-seconds", type=int, default=7200)
    args = parser.parse_args(argv)
    base, p6_work = os.path.abspath(args.base), os.path.abspath(args.p6_work)
    if os.path.lexists(base):
        raise SystemExit("REFUSED: %s exists" % base)
    with open(os.path.join(p6_work, "evidence", "rendered-manifest.json"), encoding="utf-8") as handle:
        pins = json.load(handle)["pipeline"]["artifact_sha256"]
    runtime = os.path.join(p6_work, "runtime", "scholarchain-runtime")
    job_jar = os.path.join(runtime, "application", "scholarchain-job.jar")
    if sha256_file(job_jar) != pins["job-jar"] or sha256_file(TEMPLATE) != pins["spark-config-template"]:
        raise SystemExit("REFUSED: job jar or spark template does not have the pinned sha256")
    with open(os.path.join(p6_work, "java-home"), encoding="utf-8") as handle:
        java_home = handle.readline().strip()
    for sub in ("logs", "config", "spark-local", "tmp", "staging"):
        os.makedirs(os.path.join(base, sub))
    spark_out, checkpoint = os.path.join(base, "spark"), os.path.join(base, "spark-checkpoint")
    os.makedirs(spark_out)
    os.makedirs(checkpoint)
    config = os.path.join(base, "config", "spark-config.json")
    subprocess.run([sys.executable, RENDER, TEMPLATE, config, os.path.abspath(args.hadoop_root), os.path.abspath(args.er_root),
                    spark_out, checkpoint], check=True)
    label = "lbypass-%s" % args.label
    spark_argv, changes = localize_argv(logged_spark_argv(p6_work), p6_work, base, label, config)
    command = [os.path.join(runtime, "bin", "spark-submit")] + spark_argv
    env = {
        "PATH": "%s/bin:/usr/bin:/bin:/usr/sbin:/sbin" % java_home, "HOME": os.environ.get("HOME", "/tmp"), "LANG": "C", "LC_ALL": "C",
        "TMPDIR": os.path.join(base, "tmp"), "JAVA_HOME": java_home, "SPARK_HOME": runtime, "SPARK_CONF_DIR": os.path.join(runtime, "conf"),
        "SPARK_SCALA_VERSION": "2.13", "HADOOP_CONF_DIR": "/etc/hadoop/conf", "YARN_CONF_DIR": "/etc/hadoop/conf",
        "P6_SPARK_LOCAL_DIRS": os.path.join(base, "spark-local"), "P6_SHIM_LOG": os.path.join(base, "logs", "shim-calls.jsonl"),
        "AWS_CONFIG_FILE": "/dev/null", "AWS_SHARED_CREDENTIALS_FILE": "/dev/null", "AWS_EC2_METADATA_DISABLED": "true",
    }
    record = {"disclosure": DISCLOSURE, "label": args.label, "startUtc": utc(), "command": command, "argvChangesFromP6S": changes,
              "envKeys": sorted(env), "jobJar": job_jar, "jobJarSha256": pins["job-jar"], "templateSha256": pins["spark-config-template"],
              "renderProgramSha256": sha256_file(RENDER), "hadoopRoot": os.path.abspath(args.hadoop_root),
              "erRoot": os.path.abspath(args.er_root), "p6Work": p6_work, "emrSparkStepCapSeconds": EMR_SPARK_STEP_CAP_SECONDS}
    with open(os.path.join(base, "command.json"), "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    peak = {"rssBytes": 0, "processes": 0, "sparkLocalBytes": 0, "checkpointBytes": 0, "outputBytes": 0, "sumDiskBytes": 0}
    samples = 0
    t0 = time.monotonic()
    with open(os.path.join(base, "logs", "spark-job.stdout.log"), "w") as out, open(os.path.join(base, "logs", "spark-job.stderr.log"), "w") as err:
        proc = subprocess.Popen(command, cwd=base, env=env, stdout=out, stderr=err)
        killed = False
        while proc.poll() is None:
            rss, n = tree_rss(proc.pid)
            local_b, ck_b, out_b = tree_bytes(os.path.join(base, "spark-local")), tree_bytes(checkpoint), tree_bytes(spark_out)
            peak["rssBytes"], peak["processes"] = max(peak["rssBytes"], rss), max(peak["processes"], n)
            peak["sparkLocalBytes"] = max(peak["sparkLocalBytes"], local_b)
            peak["checkpointBytes"] = max(peak["checkpointBytes"], ck_b)
            peak["outputBytes"] = max(peak["outputBytes"], out_b)
            peak["sumDiskBytes"] = max(peak["sumDiskBytes"], local_b + ck_b + out_b)
            samples += 1
            if time.monotonic() - t0 > args.kill_after_seconds and not killed:
                proc.terminate()
                killed = True
            time.sleep(args.interval)
        rc = proc.returncode
    wall = round(time.monotonic() - t0, 2)
    record.update({"endUtc": utc(), "exitCode": rc, "wallSeconds": wall, "killedAtCap": killed, "samples": samples,
                   "sampleIntervalSeconds": args.interval, "peak": peak,
                   "checkA_over15min": wall > 900, "overEmrSparkStepCap": wall > EMR_SPARK_STEP_CAP_SECONDS})
    exports = sorted(d for d in os.listdir(spark_out) if d.startswith("run:"))
    record["sparkExports"] = exports
    if rc == 0 and len(exports) == 1:
        record["results"] = collect(os.path.join(spark_out, exports[0]))
    with open(os.path.join(base, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
    print(json.dumps({k: record[k] for k in ("label", "exitCode", "wallSeconds", "peak", "sparkExports", "checkA_over15min")}, indent=2))
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
