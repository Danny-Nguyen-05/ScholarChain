"""Independent tests of scripts/emr/bootstrap.sh (Subphase 13C, test-engineer), run against fake binaries on PATH.

Carried 12D items: 8 (spark-defaults, step scripts and config are checked against sha256 like the runtime and the job JAR),
28 (the Java path is validated for the properties format) and 29 (every JAVA_HOME key exactly once, whatever the separator),
plus the pinned install paths of scripts/config/release.conf and the fail-closed ordering (deadline armed before any
download, a sha256 mismatch stops before anything is installed).

Expectations are hand-derived from the plan (Subphase 13C task 1), decision 12-10 and the carried-finding texts, not from
the script's own code. Nothing here calls AWS or the network: `aws`, `sudo`, `shutdown`, `mount`, `dnf`, `java` and
`sha256sum` are shims that log their arguments. Each property also has a MUTATION case: a scratch copy of the script with
the guard removed must make the same scenario check fail (the real script is never edited).
"""
import base64
import hashlib
import io
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO / "scripts" / "emr" / "bootstrap.sh"
RELEASE_CONF = REPO / "scripts" / "config" / "release.conf"
BUCKET = "scholarchain-course-111122223333-artifacts"
JAR = b"job jar bytes\n"
STEP_SCRIPT = b"#!/bin/bash\necho step\n"
CONFIG_JSON = b'{"k": 1}\n'
DEFAULTS = "spark.authenticate true\nspark.yarn.jars local:/opt/scholarchain-runtime/jars/*\nspark.io.encryption.enabled true\n"


def sha(data):
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def tgz(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def write_exec(path, text):
    Path(path).write_text(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def properties_keys(text):
    """Keys of a java.util.Properties file: the first token up to whitespace, '=' or ':' (leading whitespace skipped)."""
    keys = []
    for line in text.splitlines():
        s = line.lstrip(" \t")
        if s and s[0] not in "#!":
            keys.append(re.match(r"([^\s=:]+)", s).group(1))
    return keys


def properties_value(text, key):
    for line in text.splitlines():
        s = line.lstrip(" \t")
        m = re.match(r"([^\s=:]+)[ \t]*[=: \t][ \t]*(.*)$", s)
        if m and m.group(1) == key:
            return m.group(2)
    return None


class Node:
    """A temp 'node': shims on PATH, a fake S3, and every install path redirected below one directory."""

    def __init__(self, test, script=BOOTSTRAP, uptime="125.50 400.00\n"):
        self.script = Path(script)
        self.tmp = Path(tempfile.mkdtemp(prefix="sc-bs13c-")).resolve()
        test.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.bin = self.tmp / "bin"
        self.s3 = self.tmp / "s3"
        self.bin.mkdir()
        self.s3.mkdir()
        self.order = self.tmp / "order.log"
        self.order.write_text("")
        self.opt = self.tmp / "opt"
        self.runtime = self.opt / "scholarchain-runtime"
        self.jar = self.runtime / "application" / "scholarchain-job.jar"
        self.step_bin = self.opt / "scholarchain-spike" / "bin"
        self.java_file = self.opt / "scholarchain-spike" / "java-home"
        self.mnt = self.tmp / "mnt"
        self.mounts = self.tmp / "proc-mounts"
        self.mounts.write_text("")
        self.uptime = self.tmp / "uptime"
        self.uptime.write_text(uptime)
        self.instance = self.tmp / "instance.json"
        self.instance.write_text('{"isMaster": true}\n')
        self.work = self.tmp / "work"
        self.jvm = self.tmp / "jvm"
        self.jvm.mkdir()
        self.runtime_blob = tgz({"scholarchain-runtime/bin/spark-submit": b"#!/bin/sh\n", "scholarchain-runtime/application/old.jar": b"old"})
        self.put("runtime/scholarchain-runtime.tgz", self.runtime_blob)
        self.put("jar/scholarchain-job.jar", JAR)
        self.put("steps/pipeline-step.sh", STEP_SCRIPT)
        self.put("config/spark-config.json", CONFIG_JSON)
        self.java17 = self.make_java(self.jvm / "jre-17", "17")
        self.shim("sudo", 'exec "$@"')
        self.shim("shutdown", "exit 0")
        self.shim("dnf", "exit 0")
        self.shim("mount", 'for last; do :; done; echo "fs $last efs rw 0 0" >> "$SC_PROC_MOUNTS"; exit 0')
        write_exec(self.bin / "sha256sum", '#!/bin/bash\npython3 -I -c \'import hashlib,sys\nfor p in sys.argv[1:]:\n'
                   '    print(hashlib.sha256(open(p,"rb").read()).hexdigest()+"  "+p)\' "$@"\n')
        write_exec(self.bin / "aws", '#!/bin/bash\necho "aws $*" >> "$SHIM_ORDER_LOG"\n'
                   'if [[ "$1 $2" == "s3 cp" ]]; then\n  src="${3#s3://}"\n  [[ -f "$FAKE_S3/$src" ]] || { echo "404 $src" >&2; exit 1; }\n'
                   '  cp "$FAKE_S3/$src" "$4"\n  exit 0\nfi\nexit 2\n')
        # a java on PATH that is Java 11, so the `command -v java` candidate can never supply a Java 17
        write_exec(self.bin / "java", '#!/bin/bash\necho \'openjdk version "11.0.2"\' >&2\n')

    def shim(self, name, body):
        write_exec(self.bin / name, '#!/bin/bash\necho "%s $*" >> "$SHIM_ORDER_LOG"\n%s\n' % (name, body))

    def put(self, key, data):
        path = self.s3 / BUCKET / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())

    @staticmethod
    def make_java(home, major):
        (Path(home) / "bin").mkdir(parents=True, exist_ok=True)
        write_exec(Path(home) / "bin" / "java", "#!/bin/bash\necho 'openjdk version \"%s.0.13\" 2024' >&2\n" % major)
        return str(home)

    def uri(self, key):
        return "s3://%s/%s" % (BUCKET, key)

    def artifact(self, key="steps/pipeline-step.sh", data=STEP_SCRIPT, dest=None, sha_value=None):
        dest = dest or str(self.step_bin / "pipeline-step.sh")
        return "%s,%s,%s" % (self.uri(key), sha_value or sha(data), dest)

    def args(self, defaults=DEFAULTS, runtime_sha=None, jar_sha=None, defaults_sha=None, self_sha=None, max_minutes="240",
             artifacts=(), java_home="", drop=()):
        a = {
            "--region": "us-east-2", "--max-minutes": max_minutes, "--startup-allowance-minutes": "5",
            "--self-sha256": self_sha or sha(self.script.read_bytes()),
            "--runtime-uri": self.uri("runtime/scholarchain-runtime.tgz"), "--runtime-sha256": runtime_sha or sha(self.runtime_blob),
            "--job-jar-uri": self.uri("jar/scholarchain-job.jar"), "--job-jar-sha256": jar_sha or sha(JAR),
            "--spark-defaults-b64": base64.b64encode(defaults.encode()).decode(), "--spark-defaults-sha256": defaults_sha or sha(defaults),
            "--efs-id": "fs-0123abcd", "--access-point-id": "fsap-0123abcd",
        }
        if java_home:
            a["--java-home"] = java_home
        out = []
        for k, v in a.items():
            if k not in drop:
                out += [k, v]
        for spec in artifacts:
            out += ["--artifact", spec]
        return out

    def env(self, **extra):
        env = {
            "PATH": "%s:/usr/bin:/bin:/usr/sbin:/sbin" % self.bin, "HOME": str(self.tmp), "LC_ALL": "C",
            "SC_RUNTIME_DEST": str(self.runtime), "SC_JOB_JAR_PATH": str(self.jar), "SC_STEP_BIN": str(self.step_bin),
            "SC_MNT": str(self.mnt), "SC_PROC_UPTIME": str(self.uptime), "SC_PROC_MOUNTS": str(self.mounts),
            "SC_INSTANCE_JSON": str(self.instance), "SC_WORK": str(self.work), "SC_JVM_DIR": str(self.jvm),
            "SC_ALT_JRE": str(self.tmp / "no-such-alternatives"), "SC_JAVA_HOME_FILE": str(self.java_file),
            "SHIM_ORDER_LOG": str(self.order), "FAKE_S3": str(self.s3),
        }
        env.update(extra)
        return env

    def run(self, args, **env):
        done = subprocess.run(["bash", str(self.script)] + list(args), env=self.env(**env), capture_output=True, text=True, timeout=120)
        return done

    def order_lines(self):
        return [line for line in self.order.read_text().splitlines() if line.strip()]

    def conf(self):
        path = self.runtime / "conf" / "spark-defaults.conf"
        return path.read_text() if path.exists() else None


def mutated_script(test, old, new):
    """A scratch copy of bootstrap.sh with one guard replaced (`old` must be present exactly as written)."""
    text = BOOTSTRAP.read_text()
    test.assertIn(old, text, "mutation anchor moved: update the mutation, do not skip it: %r" % old)
    directory = Path(tempfile.mkdtemp(prefix="sc-bs13c-mut-"))
    test.addCleanup(shutil.rmtree, str(directory), True)
    path = directory / "bootstrap.sh"
    path.write_text(text.replace(old, new, 1))
    path.chmod(0o755)
    return path


class Properties(unittest.TestCase):
    def test_install_paths_equal_the_pinned_values_of_release_conf(self):
        """The defaults in bootstrap.sh are the paths release.conf pins and the pipeline scripts expect."""
        conf = dict(re.findall(r"^(PIPELINE_[A-Z_]+)=(\S+)\s*$", RELEASE_CONF.read_text(), re.M))
        defaults = dict(re.findall(r'^([A-Z_]+)="\$\{SC_[A-Z_]+:-([^}]*)\}"', BOOTSTRAP.read_text(), re.M))
        self.assertEqual(defaults["RUNTIME_DEST"], conf["PIPELINE_RUNTIME_DIR"])
        self.assertEqual(defaults["JOB_JAR_DEST"], conf["PIPELINE_JOB_JAR_PATH"])
        self.assertEqual(defaults["JAVA_HOME_FILE"], conf["PIPELINE_JAVA_HOME_FILE"])
        self.assertEqual(defaults["MNT"], conf["PIPELINE_EFS_MOUNT"])
        # and the literal values the plan fixes (decision 12-10 / spike layout)
        self.assertEqual(conf["PIPELINE_RUNTIME_DIR"], "/opt/scholarchain-runtime")
        self.assertEqual(conf["PIPELINE_JOB_JAR_PATH"], "/opt/scholarchain-runtime/application/scholarchain-job.jar")
        self.assertEqual(conf["PIPELINE_JAVA_HOME_FILE"], "/opt/scholarchain-spike/java-home")
        self.assertEqual(conf["PIPELINE_EFS_MOUNT"], "/mnt/scholarchain")

    def test_a_green_run_installs_exactly_at_the_redirected_pinned_locations(self):
        n = Node(self)
        done = n.run(n.args(artifacts=[n.artifact(), n.artifact("config/spark-config.json", CONFIG_JSON, str(n.mnt / "config/spark-config.json"))],
                            java_home=n.java17))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((n.runtime / "bin" / "spark-submit").is_file())
        self.assertEqual(n.jar.read_bytes(), JAR)
        self.assertEqual(n.java_file.read_text(), n.java17 + "\n")
        self.assertEqual((n.step_bin / "pipeline-step.sh").read_bytes(), STEP_SCRIPT)
        self.assertEqual((n.mnt / "config" / "spark-config.json").read_bytes(), CONFIG_JSON, "primary installs EFS-side artifacts")
        self.assertIn("bootstrap complete", done.stderr)

    # ---- the hard deadline comes first -----------------------------------------------------------------------

    def check_deadline_first(self, script):
        n = Node(self, script=script)
        done = n.run(n.args(java_home=n.java17))
        self.assertEqual(done.returncode, 0, done.stderr)
        order = n.order_lines()
        shutdown = [i for i, line in enumerate(order) if line.startswith("shutdown ")]
        downloads = [i for i, line in enumerate(order) if line.startswith("aws s3 cp")]
        self.assertTrue(shutdown and downloads)
        self.assertLess(shutdown[0], downloads[0], "the node shutdown must be armed before the first download")
        # 240 min - ceil(125.5 s = 3 min uptime) - 5 min allowance = 232
        self.assertEqual(order[shutdown[0]], 'shutdown -h +232 scholarchain hard deadline')

    def test_the_node_shutdown_is_armed_before_any_download_with_the_hand_derived_minutes(self):
        self.check_deadline_first(BOOTSTRAP)

    def test_mutation_without_the_early_deadline_fails_the_ordering_check(self):
        text = BOOTSTRAP.read_text()
        old = 'arm_deadline "${MAX_MIN}"\n'
        self.assertEqual(text.count(old), 1)
        mutated = mutated_script(self, old, "")
        with self.assertRaises(AssertionError):
            self.check_deadline_first(mutated)

    # ---- item 8: sha256 mismatch fails closed before install -----------------------------------------------------------

    def check_runtime_tamper(self, script):
        n = Node(self, script=script)
        good = n.args(java_home=n.java17)
        done = n.run(n.args(java_home=n.java17, runtime_sha="0" * 64))
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIn("sha256 mismatch for runtime archive", done.stderr)
        self.assertFalse(n.runtime.exists(), "nothing of a mismatching runtime archive may be installed")
        self.assertFalse(n.jar.exists())
        self.assertFalse(n.java_file.exists())
        self.assertEqual(len([x for x in n.order_lines() if x.startswith("aws s3 cp")]), 1, "no later download after the failure")
        return good

    def test_runtime_archive_sha_mismatch_fails_closed_before_extraction(self):
        self.check_runtime_tamper(BOOTSTRAP)

    def test_mutation_without_the_runtime_check_is_caught(self):
        mutated = mutated_script(self, 'verify "${WORK}/runtime.tgz" "${RUNTIME_SHA}" "runtime archive"', "true")
        with self.assertRaises(AssertionError):
            self.check_runtime_tamper(mutated)

    def check_jar_tamper(self, script):
        n = Node(self, script=script)
        done = n.run(n.args(java_home=n.java17, jar_sha="1" * 64))
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIn("sha256 mismatch for job jar", done.stderr)
        self.assertFalse(n.jar.exists(), "a mismatching job jar must never reach the pinned path")
        self.assertFalse(n.java_file.exists())

    def test_job_jar_sha_mismatch_fails_closed_before_install(self):
        self.check_jar_tamper(BOOTSTRAP)

    def test_mutation_without_the_job_jar_check_is_caught(self):
        mutated = mutated_script(self, 'verify "${WORK}/job.jar" "${JOB_JAR_SHA}" "job jar"', "true")
        with self.assertRaises(AssertionError):
            self.check_jar_tamper(mutated)

    def check_defaults_tamper(self, script):
        n = Node(self, script=script)
        done = n.run(n.args(java_home=n.java17, defaults_sha="2" * 64))
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIn("sha256 mismatch for spark-defaults", done.stderr)
        self.assertIsNone(n.conf(), "a spark-defaults that fails its sha256 must not be installed")

    def test_spark_defaults_sha_mismatch_fails_closed_before_install(self):
        self.check_defaults_tamper(BOOTSTRAP)

    def test_mutation_without_the_spark_defaults_check_is_caught(self):
        mutated = mutated_script(self, 'verify "${WORK}/spark-defaults.conf" "${DEFAULTS_SHA}" "spark-defaults"', "true")
        with self.assertRaises(AssertionError):
            self.check_defaults_tamper(mutated)

    def test_a_defaults_payload_that_differs_from_its_declared_hash_is_refused_even_if_valid_base64(self):
        n = Node(self)
        done = n.run(n.args(java_home=n.java17, defaults=DEFAULTS + "spark.evil true\n", defaults_sha=sha(DEFAULTS)))
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIsNone(n.conf())

    def check_artifact_tamper(self, script):
        for dest_kind in ("step", "efs-config"):
            n = Node(self, script=script)
            if dest_kind == "step":
                spec = n.artifact(sha_value="3" * 64)
                dest = n.step_bin / "pipeline-step.sh"
            else:
                spec = n.artifact("config/spark-config.json", CONFIG_JSON, str(n.mnt / "config/spark-config.json"), sha_value="4" * 64)
                dest = n.mnt / "config" / "spark-config.json"
            done = n.run(n.args(java_home=n.java17, artifacts=[spec]))
            self.assertEqual(done.returncode, 3, "%s: %s" % (dest_kind, done.stderr))
            self.assertIn("sha256 mismatch for artifact", done.stderr)
            self.assertFalse(dest.exists(), "%s: a mismatching artifact must not be installed" % dest_kind)

    def test_step_script_and_config_artifact_sha_mismatch_fails_closed_before_install(self):
        self.check_artifact_tamper(BOOTSTRAP)

    def test_mutation_without_the_artifact_check_is_caught(self):
        mutated = mutated_script(self, 'verify "${tmp}" "${ART_SHA[$i]}" "artifact ${ART_DEST[$i]}"', "true")
        with self.assertRaises(AssertionError):
            self.check_artifact_tamper(mutated)

    def test_the_script_itself_is_checked_against_self_sha256_before_any_download(self):
        n = Node(self)
        done = n.run(n.args(java_home=n.java17, self_sha="5" * 64))
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertEqual([x for x in n.order_lines() if x.startswith("aws ")], [])
        self.assertFalse(n.runtime.exists())

    def test_artifact_destinations_outside_the_allowed_directories_are_refused_before_any_download(self):
        for dest in ("/etc/cron.d/x", "/opt/scholarchain-runtime/../etc/x", "/opt/scholarchain-spike/bin/../x", "relative/path"):
            with self.subTest(dest=dest):
                n = Node(self)
                done = n.run(n.args(java_home=n.java17, artifacts=[n.artifact(dest=dest)]))
                self.assertEqual(done.returncode, 64, done.stderr)
                self.assertEqual([x for x in n.order_lines() if x.startswith("aws ")], [])

    def test_runtime_archive_with_an_escaping_member_is_refused_before_extraction(self):
        for bad in ("../evil", "/abs/evil", "other-dir/file"):
            with self.subTest(member=bad):
                n = Node(self)
                blob = tgz({"scholarchain-runtime/bin/x": b"x", bad: b"evil"})
                n.put("runtime/scholarchain-runtime.tgz", blob)
                done = n.run(n.args(java_home=n.java17, runtime_sha=sha(blob)))
                self.assertEqual(done.returncode, 3, done.stderr)
                self.assertFalse(n.runtime.exists())

    def test_argument_errors_exit_64_but_still_arm_the_deadline_first(self):
        n = Node(self)
        done = n.run(n.args(java_home=n.java17, drop=("--region",)))
        self.assertEqual(done.returncode, 64, done.stderr)
        self.assertTrue(any(x.startswith("shutdown ") for x in n.order_lines()))
        self.assertEqual([x for x in n.order_lines() if x.startswith("aws ")], [])
        n2 = Node(self)
        done = n2.run(n2.args(java_home=n2.java17) + ["--surprise", "1"])
        self.assertEqual(done.returncode, 64, done.stderr)
        n3 = Node(self)
        done = n3.run(["--region", "us-east-2"])
        self.assertEqual(done.returncode, 64, done.stderr)
        self.assertTrue(any(x.startswith("shutdown +60") or x.startswith("shutdown -h +") for x in n3.order_lines()), "a fallback deadline is armed")

    # ---- item 28: the Java path is validated for the properties format ----------------------------------------------

    def check_unsafe_java_rejected(self, script):
        # Each of these characters could inject or end a spark-defaults line when the path is appended to the file.
        for label, suffix in (("space", "my java"), ("hash", "j#17"), ("equals", "j=17"), ("colon", "j:17"), ("backslash", "j\\17"),
                              ("newline", "j\nspark.evil true"), ("dollar", "j$17"), ("quote", 'j"17'), ("dotdot", "../real17")):
            n = Node(self, script=script)
            shutil.rmtree(n.jvm / "jre-17")  # no safe Java 17 anywhere: the only 17 is the unsafe candidate
            base = n.tmp / "unsafe"
            if label == "dotdot":
                n.make_java(n.tmp / "real17", "17")  # a genuine Java 17 reached through a '..' component
                unsafe = "%s/../real17" % base
                base.mkdir()
            else:
                unsafe = "%s/%s" % (base, suffix)
                n.make_java(unsafe, "17")
            done = n.run(n.args(java_home=unsafe))
            self.assertEqual(done.returncode, 4, "%s: %s" % (label, done.stderr))
            self.assertFalse(n.java_file.exists(), "%s: the unsafe path must never be written" % label)
            self.assertIsNone(n.conf(), "%s: spark-defaults must not be installed after the Java check failed" % label)
            self.assertNotIn("spark.evil", n.java_file.read_text() if n.java_file.exists() else "")

    def test_unsafe_java_paths_are_rejected_and_nothing_downstream_is_written(self):
        self.check_unsafe_java_rejected(BOOTSTRAP)

    def test_mutation_without_the_java_path_validation_is_caught(self):
        mutated = mutated_script(self, '[[ "$1" == /* ]] && [[ "$1" =~ ^/[A-Za-z0-9_.+/-]+$ ]] && [[ "$1" != *..* ]]', "true")
        with self.assertRaises(AssertionError):
            self.check_unsafe_java_rejected(mutated)

    def test_a_java_that_is_not_17_is_refused_and_a_safe_17_is_written_once(self):
        n = Node(self)
        n.make_java(n.jvm / "jre-17", "11")
        done = n.run(n.args())
        self.assertEqual(done.returncode, 4, done.stderr)
        self.assertFalse(n.java_file.exists())
        n2 = Node(self)
        done = n2.run(n2.args())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(n2.java_file.read_text(), str(n2.jvm / "jre-17") + "\n")

    def test_an_unsafe_jvm_directory_candidate_is_rejected_even_without_java_home_argument(self):
        n = Node(self)
        spaced = n.tmp / "a dir with spaces" / "jvm"
        n.make_java(spaced / "jre-17", "17")
        done = n.run(n.args(), SC_JVM_DIR=str(spaced))
        self.assertEqual(done.returncode, 4, done.stderr)
        self.assertFalse(n.java_file.exists())

    # ---- item 29: every JAVA_HOME key exactly once, whatever the separator ----------------------------------------

    VARIANTS = {
        "equals": "spark.executorEnv.JAVA_HOME=/old/jdk\nspark.yarn.appMasterEnv.JAVA_HOME=/old/jdk\n",
        "colon": "spark.executorEnv.JAVA_HOME:/old/jdk\nspark.yarn.appMasterEnv.JAVA_HOME:/old/jdk\n",
        "tab": "spark.executorEnv.JAVA_HOME\t/old/jdk\nspark.yarn.appMasterEnv.JAVA_HOME\t/old/jdk\n",
        "space": "spark.executorEnv.JAVA_HOME /old/jdk\nspark.yarn.appMasterEnv.JAVA_HOME /old/jdk\n",
        "leading whitespace": "  spark.executorEnv.JAVA_HOME /old/jdk\n\tspark.yarn.appMasterEnv.JAVA_HOME=/old/jdk\n",
        "no value": "spark.executorEnv.JAVA_HOME\nspark.yarn.appMasterEnv.JAVA_HOME\n",
        "duplicated": "spark.executorEnv.JAVA_HOME /a\nspark.executorEnv.JAVA_HOME /b\nspark.yarn.appMasterEnv.JAVA_HOME /c\n",
        "absent": "",
    }

    def check_java_home_once(self, script):
        for label, extra in self.VARIANTS.items():
            n = Node(self, script=script)
            defaults = DEFAULTS + extra
            done = n.run(n.args(defaults=defaults, java_home=n.java17))
            self.assertEqual(done.returncode, 0, "%s: %s" % (label, done.stderr))
            conf = n.conf()
            keys = properties_keys(conf)
            for key in ("spark.executorEnv.JAVA_HOME", "spark.yarn.appMasterEnv.JAVA_HOME"):
                self.assertEqual(keys.count(key), 1, "%s: %s appears %d times\n%s" % (label, key, keys.count(key), conf))
                self.assertEqual(properties_value(conf, key), n.java17, "%s: %s must name this node's resolved Java" % (label, key))
            self.assertNotIn("/old/jdk", conf, label)
            for kept in DEFAULTS.splitlines():
                self.assertIn(kept, conf.splitlines(), "%s: an unrelated setting was lost" % label)

    def test_java_home_keys_appear_exactly_once_with_the_resolved_value_for_every_separator(self):
        self.check_java_home_once(BOOTSTRAP)

    def test_mutation_that_only_removes_the_space_separated_key_is_caught(self):
        mutated = mutated_script(self, r"JAVA_KEY_RE='^[[:space:]]*spark\.(yarn\.appMasterEnv|executorEnv)\.JAVA_HOME([[:space:]=:]|$)'",
                                 r"JAVA_KEY_RE='^spark\.(yarn\.appMasterEnv|executorEnv)\.JAVA_HOME '")
        with self.assertRaises(AssertionError):
            self.check_java_home_once(mutated)

    def test_a_line_continuation_in_spark_defaults_is_refused(self):
        n = Node(self)
        defaults = DEFAULTS + "spark.x one \\\n"
        done = n.run(n.args(defaults=defaults, java_home=n.java17))
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIsNone(n.conf())


if __name__ == "__main__":
    unittest.main()
