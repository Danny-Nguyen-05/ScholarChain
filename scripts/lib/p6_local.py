#!/usr/bin/env python3
"""Phase 15 P6: local stand-ins for the EMR node tools, so that scripts/emr/sc-step.sh runs UNCHANGED on a laptop (stdlib).

The P6 harness (scripts/lib/p6_local_chain.py) puts scripts/p6local/bin first on PATH. Each file there calls one main below.
None of them can reach AWS: `aws` serves only `s3 ls` and `s3 cp` from a local directory standing in for S3 (P6_S3_ROOT) and
refuses every other command with exit 97. Every call is appended to P6_SHIM_LOG (argv only, never environment values).

  aws            s3 ls URI --recursive --summarize | s3 cp SRC DST [--recursive] [--exclude P|--include P]... [--no-follow-symlinks]
                 s3://BUCKET/KEY maps to P6_S3_ROOT/BUCKET/KEY. Filters follow awscli/customizations/s3/filters.py: every file is
                 included unless a filter matches; the pattern is joined to the source directory and fnmatch'ed against the full
                 path (so '*' also matches '/'); the LAST matching filter wins.
  hadoop         fs -copyToLocal s3://... DEST (from the stand-in) | jar JAR ARGS... -> Java 17 org.apache.hadoop.util.RunJar on
                 HADOOP_CLASSPATH + the Hadoop client classpath (P6_HADOOP_CLIENT_CLASSPATH). SUBSTITUTION (disclosed): there is no
                 YARN, so `--execution-mode cluster` becomes `--execution-mode local` (Hadoop LocalJobRunner, same job classes).
  yarn           application -list ... (no applications) | application -kill ID (no-op)
  timeout        --kill-after=K SECONDS CMD...: GNU semantics used by sc-step.sh (124 on timeout, 137 when KILL was needed)
  spark-submit   installed as RUNTIME_DIR/bin/spark-submit of the LOCAL copy of the portable runtime; it runs the runtime's own
                 spark-submit (renamed spark-submit.real) with two SUBSTITUTIONS (disclosed): `--master yarn --deploy-mode cluster`
                 becomes `--master local-cluster[N,C,M]` (N = spark.dynamicAllocation.maxExecutors, C = spark.executor.cores,
                 M = spark.executor.memory in MiB: separate executor JVMs as on YARN); the local: job JAR is used in place AFTER
                 the runtime jars (SPARK_DIST_CLASSPATH; YARN's order; standalone would fetch a copy); and, because standalone mode cannot
                 generate the per-application authentication secret that YARN generates, a throwaway random secret is passed
                 in a 0600 properties file that is deleted when the job ends.
"""
import fnmatch
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time

REFUSED = 97


def log_call(tool, argv):
    path = os.environ.get("P6_SHIM_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"tool": tool, "argv": list(argv), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")


def refuse(tool, message):
    sys.stderr.write("P6-LOCAL-%s-REFUSED: %s\n" % (tool.upper(), message))
    return REFUSED


# ---- S3 stand-in -----------------------------------------------------------------------------------------------------
def s3_split(uri):
    """s3://bucket/key -> (bucket, key). Refuses anything that could leave the stand-in root."""
    match = re.match(r"^(s3|s3a|s3n)://([a-z0-9][a-z0-9.-]{1,61}[a-z0-9])(/.*)?$", uri)
    if not match:
        raise ValueError("not an s3 URI: %s" % uri)
    key = (match.group(3) or "/")[1:]
    if any(part in ("..", ".") for part in key.split("/")):
        raise ValueError("an s3 key with a '.' or '..' component is refused: %s" % uri)
    return match.group(2), key


def s3_local(root, uri):
    bucket, key = s3_split(uri)
    return os.path.join(root, bucket, *[p for p in key.split("/") if p]) + ("/" if key.endswith("/") or key == "" else "")


def filter_keep(full_path, source_root, filters):
    """awscli filter semantics for one file: included by default, the last matching filter wins."""
    keep = True
    for action, pattern in filters:
        if fnmatch.fnmatch(full_path, os.path.join(source_root, pattern)):
            keep = action == "include"
    return keep


def walk_files(root, follow):
    out = []
    for current, dirs, files in os.walk(root, followlinks=follow):
        if not follow:
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current, d))]
        for name in files:
            full = os.path.join(current, name)
            if os.path.islink(full) and not follow:
                continue
            out.append(full)
    return sorted(out)


def s3_list(root, uri):
    """Objects under an s3 prefix (string prefix, as S3 lists): [(key, local path)]."""
    bucket, prefix = s3_split(uri)
    base = os.path.join(root, bucket)
    found = []
    for full in walk_files(base, True) if os.path.isdir(base) else []:
        key = os.path.relpath(full, base).replace(os.sep, "/")
        if key.startswith(prefix):
            found.append((key, full))
    return found


def aws_main(argv):
    log_call("aws", argv)
    root = os.environ.get("P6_S3_ROOT", "")
    if not root or not os.path.isdir(root):
        return refuse("aws", "P6_S3_ROOT is not a directory: the local stand-in serves no request without it")
    if argv[:2] not in (["s3", "ls"], ["s3", "cp"]):
        return refuse("aws", "only `aws s3 ls` and `aws s3 cp` are served locally; refused: aws %s" % " ".join(argv[:2]))
    flags, filters, positional, i = set(), [], [], 2
    while i < len(argv):
        arg = argv[i]
        if arg in ("--exclude", "--include"):
            if i + 1 >= len(argv):
                return refuse("aws", "%s needs a pattern" % arg)
            filters.append((arg[2:], argv[i + 1]))
            i += 2
            continue
        if arg == "--region":
            i += 2
            continue
        if arg in ("--recursive", "--summarize", "--no-follow-symlinks", "--only-show-errors"):
            flags.add(arg)
            i += 1
            continue
        if arg.startswith("--"):
            return refuse("aws", "unsupported option %s" % arg)
        positional.append(arg)
        i += 1
    try:
        if argv[1] == "ls":
            if len(positional) != 1 or not {"--recursive", "--summarize"} <= flags or filters:
                return refuse("aws", "s3 ls is served only as: s3 ls URI --recursive --summarize")
            objects = s3_list(root, positional[0])
            total = sum(os.path.getsize(path) for _, path in objects)
            for key, path in objects:
                print("2026-01-01 00:00:00 %10d %s" % (os.path.getsize(path), key))
            print("\nTotal Objects: %d\n   Total Size: %d" % (len(objects), total))
            return 0 if objects else 1
        if len(positional) != 2:
            return refuse("aws", "s3 cp needs exactly SRC and DST")
        return s3_copy(root, positional[0], positional[1], "--recursive" in flags, filters, "--no-follow-symlinks" not in flags)
    except ValueError as error:
        return refuse("aws", str(error))


def _copy(src, dest):
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    shutil.copyfile(src, dest)


def s3_copy(root, src, dst, recursive, filters, follow):
    src_s3, dst_s3 = src.startswith("s3://"), dst.startswith("s3://")
    if src_s3 == dst_s3:
        raise ValueError("exactly one of SRC and DST must be an s3 URI")
    if not recursive:
        if filters:
            raise ValueError("filters are served only with --recursive")
        if src_s3:
            local_src = s3_local(root, src).rstrip("/")
            if not os.path.isfile(local_src):
                sys.stderr.write("fatal error: An error occurred (404) when calling the HeadObject operation: Key not found\n")
                return 1
            dest = os.path.join(dst, os.path.basename(local_src)) if dst.endswith("/") or os.path.isdir(dst) else dst
            _copy(local_src, dest)
            return 0
        if not os.path.isfile(src) or (os.path.islink(src) and not follow):
            raise ValueError("the local source is not a regular file: %s" % src)
        dest = s3_local(root, dst)
        if dest.endswith("/"):
            dest = os.path.join(dest, os.path.basename(src))
        _copy(src, dest)
        return 0
    if src_s3:
        bucket, prefix = s3_split(src)
        prefix = prefix if prefix.endswith("/") or prefix == "" else prefix + "/"
        source_root = os.path.join(root, bucket, prefix).rstrip("/")
        for key, path in s3_list(root, "s3://%s/%s" % (bucket, prefix)):
            if filter_keep(path, source_root, filters):
                _copy(path, os.path.join(dst, *key[len(prefix):].split("/")))
        return 0
    source_root = src.rstrip("/")
    if not os.path.isdir(source_root):
        raise ValueError("the local source is not a directory: %s" % src)
    dest_root = s3_local(root, dst if dst.endswith("/") else dst + "/")
    for full in walk_files(source_root, follow):
        if filter_keep(full, source_root, filters):
            _copy(full, os.path.join(dest_root, os.path.relpath(full, source_root)))
    return 0


# ---- hadoop and yarn ---------------------------------------------------------------------------------------------------
V4_RUN_ID = re.compile(r"^run:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def hadoop_jar_command(argv, java, hadoop_classpath, client_classpath, opts, drop_non_v4_run_id=False):
    """`hadoop jar JAR ARGS...` -> the Java command that RunJar would run, with the disclosed substitution(s).

    drop_non_v4_run_id (opt-in P6 WORKAROUND for two defects of the hadoop-prep step as written, off by default, recorded):
    (1) HadoopPrepPipeline accepts only a `run:<uuid v4>` run id, while sc-step.sh passes the pipeline run id (SAFE_RUN_ID, no ':'
    allowed), so the real step fails at once; the pair is removed and HadoopPrepMain generates its own v4 id. (2) sc-step.sh passes
    `--output-root file://<dir>`, which FsPaths.runPath resolves as a relative path; the scheme is removed."""
    if len(argv) < 2 or argv[0] != "jar":
        raise ValueError("expected: jar JAR ARGS...")
    args = list(argv[2:])
    substitutions = []
    for index in range(len(args) - 1):
        if args[index] == "--execution-mode" and args[index + 1] == "cluster":
            args[index + 1] = "local"
            substitutions.append("--execution-mode cluster -> local (no YARN on the laptop; Hadoop LocalJobRunner)")
    if drop_non_v4_run_id:
        for index in range(len(args) - 1):
            if args[index] == "--run-id" and not V4_RUN_ID.match(args[index + 1]):
                substitutions.append("WORKAROUND --run-id %s removed (not a run:<uuid v4>; HadoopPrepMain generates one)" % args[index + 1])
                del args[index:index + 2]
                break
        # Second defect: FsPaths.runPath treats a non-remote root as a java.nio path, so `file:///abs` becomes the RELATIVE path
        # `file:/abs` under the working directory and job J03 fails on the glob of a `file:` component.
        for index in range(len(args) - 1):
            if args[index] == "--output-root" and args[index + 1].startswith("file:///"):
                substitutions.append("WORKAROUND --output-root %s -> %s (FsPaths.runPath does not accept a file: URI)" % (args[index + 1], args[index + 1][len("file://"):]))
                args[index + 1] = args[index + 1][len("file://"):]
    classpath = ":".join(part for part in (hadoop_classpath, client_classpath) if part)
    return [java] + list(opts) + ["-cp", classpath, "org.apache.hadoop.util.RunJar", argv[1]] + args, substitutions


def run_forwarding(command, env=None):
    """Runs a child in its own session and forwards TERM/INT to its process group; returns the shell-style exit code."""
    child = subprocess.Popen(command, env=env, start_new_session=True)

    def forward(signum, _frame):
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass

    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    rc = child.wait()
    return 128 - rc if rc < 0 else rc


def hadoop_main(argv):
    log_call("hadoop", argv)
    if argv[:2] == ["fs", "-copyToLocal"] and len(argv) == 4:
        root = os.environ.get("P6_S3_ROOT", "")
        try:
            local = s3_local(root, argv[2]).rstrip("/")
        except ValueError as error:
            return refuse("hadoop", str(error))
        if not root or not os.path.isfile(local):
            sys.stderr.write("copyToLocal: `%s': No such file or directory\n" % argv[2])
            return 1
        _copy(local, argv[3])
        return 0
    if argv[:1] == ["jar"]:
        java = os.path.join(os.environ.get("P6_JAVA_HOME", ""), "bin", "java")
        client = os.environ.get("P6_HADOOP_CLIENT_CLASSPATH", "")
        if not os.path.isfile(java) or not client:
            return refuse("hadoop", "P6_JAVA_HOME and P6_HADOOP_CLIENT_CLASSPATH are required")
        opts = os.environ.get("P6_HADOOP_CLIENT_OPTS", "").split()
        try:
            command, substitutions = hadoop_jar_command(argv, java, os.environ.get("HADOOP_CLASSPATH", ""), client, opts,
                                                        os.environ.get("P6_WORKAROUND_HADOOP_CLI") == "1")
        except ValueError as error:
            return refuse("hadoop", str(error))
        for item in substitutions:
            sys.stderr.write("P6-SUBSTITUTION hadoop: %s\n" % item)
        return run_forwarding(command)
    return refuse("hadoop", "only `fs -copyToLocal` and `jar` are served locally")


def yarn_main(argv):
    log_call("yarn", argv)
    if argv[:2] == ["application", "-list"]:
        print("Total number of applications (application-types: [], states: [] and tags: []):0")
        return 0
    if argv[:2] == ["application", "-kill"] and len(argv) == 3:
        return 0
    return refuse("yarn", "only `application -list` and `application -kill` are served locally")


# ---- timeout -----------------------------------------------------------------------------------------------------------
def parse_timeout(argv):
    kill_after, i = None, 0
    while i < len(argv) and argv[i].startswith("-"):
        if argv[i].startswith("--kill-after="):
            kill_after = argv[i].split("=", 1)[1]
        elif argv[i] in ("-k", "--kill-after") and i + 1 < len(argv):
            kill_after = argv[i + 1]
            i += 1
        else:
            raise ValueError("unsupported timeout option %s" % argv[i])
        i += 1
    if i + 1 >= len(argv) or not re.match(r"^[0-9]+$", argv[i]) or (kill_after is not None and not re.match(r"^[0-9]+$", kill_after)):
        raise ValueError("expected: [--kill-after=K] SECONDS COMMAND...")
    return int(argv[i]), (int(kill_after) if kill_after is not None else None), argv[i + 1:]


def timeout_main(argv):
    try:
        seconds, kill_after, command = parse_timeout(argv)
    except ValueError as error:
        sys.stderr.write("timeout: %s\n" % error)
        return 125
    child = subprocess.Popen(command, start_new_session=True)
    state = {"signalled": False}

    def group(signum):
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass

    def forward(signum, _frame):
        state["signalled"] = True
        group(signum)

    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    try:
        rc = child.wait(timeout=seconds if seconds > 0 else None)
        return 128 - rc if rc < 0 else rc
    except subprocess.TimeoutExpired:
        pass
    group(signal.SIGTERM)
    try:
        child.wait(timeout=kill_after)
        return 124
    except subprocess.TimeoutExpired:
        group(signal.SIGKILL)
        child.wait()
        return 137


# ---- spark-submit ------------------------------------------------------------------------------------------------------
def memory_mib(text):
    match = re.match(r"^([0-9]+)([kmgt]?)b?$", text.strip().lower())
    if not match:
        raise ValueError("unparseable memory size %s" % text)
    value, unit = int(match.group(1)), match.group(2) or "m"
    return {"k": value // 1024, "m": value, "g": value * 1024, "t": value * 1024 * 1024}[unit]


def spark_submit_translate(argv):
    """The EMR spark-submit argv -> (local argv without the secret, substitutions, authenticate?)."""
    out, confs, substitutions, i, master, mode = [], {}, [], 0, None, None
    while i < len(argv):
        arg = argv[i]
        if arg in ("--master", "--deploy-mode", "--name", "--class", "--conf"):
            if i + 1 >= len(argv):
                raise ValueError("%s needs a value" % arg)
            value = argv[i + 1]
            if arg == "--master":
                master = value
            elif arg == "--deploy-mode":
                mode = value
            else:
                if arg == "--conf":
                    if "=" not in value:
                        raise ValueError("--conf needs key=value")
                    key, val = value.split("=", 1)
                    confs[key] = val
                out += [arg, value]
            i += 2
            continue
        if arg.startswith("--"):
            raise ValueError("unsupported spark-submit option %s" % arg)
        out += argv[i:]
        break
    if master != "yarn" or mode != "cluster":
        raise ValueError("expected the EMR form --master yarn --deploy-mode cluster")
    executors = int(confs.get("spark.dynamicAllocation.maxExecutors", "0"))
    cores = int(confs.get("spark.executor.cores", "0"))
    mib = memory_mib(confs.get("spark.executor.memory", "0"))
    if executors < 1 or cores < 1 or mib < 512:
        raise ValueError("maxExecutors, executor cores and executor memory are required")
    local_master = "local-cluster[%d,%d,%d]" % (executors, cores, mib)
    substitutions.append("--master yarn --deploy-mode cluster -> --master %s (client mode; separate executor JVMs)" % local_master)
    primary = next((a for a in out if a.startswith("local:")), None)
    dist_classpath = ""
    if primary:
        # YARN uses a local: resource in place on every node, AFTER the spark.yarn.jars runtime jars; standalone fetches a copy into
        # the executor work directory, which the class-origin verifier (rightly) refuses. Appending the node-local JAR after the
        # runtime jars (SPARK_DIST_CLASSPATH is the last class path entry of the driver and of every executor) restores that order.
        dist_classpath = primary[len("local:"):]
        substitutions.append("the local: job JAR is used in place, after the runtime jars (SPARK_DIST_CLASSPATH), as on YARN; not a fetched copy")
    authenticate = confs.get("spark.authenticate", "false").lower() == "true"
    if authenticate:
        substitutions.append("spark.authenticate: throwaway per-run secret in a 0600 properties file (YARN generates one; standalone cannot)")
    return ["--master", local_master] + out, substitutions, authenticate, dist_classpath


def spark_submit_main(argv):
    log_call("spark-submit", argv)
    real = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "spark-submit.real")
    if not os.path.isfile(real):
        return refuse("spark-submit", "the runtime's own spark-submit.real is missing next to this stand-in")
    try:
        args, substitutions, authenticate, dist_classpath = spark_submit_translate(argv)
    except ValueError as error:
        return refuse("spark-submit", str(error))
    for item in substitutions:
        sys.stderr.write("P6-SUBSTITUTION spark-submit: %s\n" % item)
    env = dict(os.environ)
    if os.environ.get("P6_SPARK_LOCAL_DIRS"):
        env["SPARK_LOCAL_DIRS"] = os.environ["P6_SPARK_LOCAL_DIRS"]
    if dist_classpath:
        env["SPARK_DIST_CLASSPATH"] = dist_classpath
    private = None
    try:
        if authenticate:
            private = tempfile.mkdtemp(prefix="p6-spark-auth.")
            props = os.path.join(private, "auth.properties")
            fd = os.open(props, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write("spark.authenticate.secret %s\n" % secrets.token_hex(32))
            args = ["--properties-file", props] + args
        return run_forwarding(["bash", real] + args, env=env)
    finally:
        if private:
            shutil.rmtree(private, ignore_errors=True)


# ---- evidence helpers --------------------------------------------------------------------------------------------------
def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256sums(base, prefix=""):
    """`shasum -a 256` lines for every regular file under base: '<hex>  <prefix><relative path>', sorted by path (bytes)."""
    rows = []
    for full in walk_files(base, False):
        rel = prefix + os.path.relpath(full, base).replace(os.sep, "/")
        if "\n" in rel or "\\" in rel:
            raise ValueError("a path with a newline or backslash cannot be listed: %r" % rel)
        rows.append((rel.encode("utf-8"), "%s  %s\n" % (sha256_file(full), rel)))
    return "".join(line for _, line in sorted(rows))


def tree_sha256(base):
    """The sha256 of the sorted sha256sums listing of a tree: one value for a whole input tree."""
    return hashlib.sha256(sha256sums(base).encode("utf-8")).hexdigest()


MAINS = {"aws": aws_main, "hadoop": hadoop_main, "yarn": yarn_main, "timeout": timeout_main, "spark-submit": spark_submit_main}
