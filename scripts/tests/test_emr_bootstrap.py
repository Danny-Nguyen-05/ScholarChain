"""scripts/emr/bootstrap.sh (Subphase 13C): the main EMR bootstrap, run against fake binaries on PATH.

Covers carried 12D items 8 (sha256 of spark-defaults, step scripts and config), 28 (Java path validated for the
properties format) and 29 (JAVA_HOME removed across every separator, each key exactly once), the G5 runtime source
(S3 URI plus pinned sha256), the pinned install paths of scripts/config/release.conf, and fail-closed behaviour. Nothing
here calls AWS or the network: `aws`, `sudo`, `shutdown`, `mount`, `dnf` and `java` are shims that log their arguments.
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

from helpers import SCRIPTS_DIR

BOOTSTRAP = os.path.join(SCRIPTS_DIR, "emr", "bootstrap.sh")
RUNTIME_BUCKET = "scholarchain-course-111122223333-artifacts"
JAR = b"fake job jar\n"
GOOD_DEFAULTS = "spark.authenticate true\nspark.yarn.jars local:/opt/scholarchain-runtime/jars/*\nspark.io.encryption.enabled true\n"


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
    with open(path, "w") as handle:
        handle.write(text)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def parse_properties(text):
    """The keys of a java.util.Properties-style file: first token up to whitespace, '=' or ':' (leading whitespace skipped)."""
    keys = []
    for line in text.splitlines():
        stripped = line.lstrip(" \t")
        if not stripped or stripped[0] in "#!":
            continue
        match = re.match(r"([^\s=:]+)", stripped)
        keys.append(match.group(1))
    return keys


class BootstrapCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-bootstrap-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.bin = os.path.join(self.tmp, "bin")
        self.s3 = os.path.join(self.tmp, "s3")
        os.makedirs(self.bin)
        os.makedirs(self.s3)
        self.order_log = os.path.join(self.tmp, "order.log")
        open(self.order_log, "w").close()
        self.opt = os.path.join(self.tmp, "opt")
        self.runtime = os.path.join(self.opt, "scholarchain-runtime")
        self.step_bin = os.path.join(self.opt, "scholarchain-spike", "bin")
        self.java_file = os.path.join(self.opt, "scholarchain-spike", "java-home")
        self.mnt = os.path.join(self.tmp, "mnt-scholarchain")
        self.proc_mounts = os.path.join(self.tmp, "proc-mounts")
        self.uptime = os.path.join(self.tmp, "uptime")
        self.instance_json = os.path.join(self.tmp, "instance.json")
        open(self.proc_mounts, "w").close()
        with open(self.uptime, "w") as handle:
            handle.write("125.50 400.00\n")
        with open(self.instance_json, "w") as handle:
            handle.write('{"isMaster": true}\n')
        self.runtime_blob = tgz({"scholarchain-runtime/bin/spark-submit": b"#!/bin/sh\n", "scholarchain-runtime/application/old.jar": b"old"})
        self.put("runtime/scholarchain-runtime.tgz", self.runtime_blob)
        self.put("jar/scholarchain-job.jar", JAR)
        self.java_home = self.fake_java(os.path.join(self.tmp, "java17"))
        self.jvm = os.path.join(self.tmp, "jvm")
        self.alt = os.path.join(self.tmp, "alternatives-jre")
        self.add_shim("sudo", 'exec "$@"')
        self.add_shim("shutdown", "exit 0")
        self.add_shim("dnf", "exit 0")
        self.add_shim("mount", 'for last; do :; done; echo "fs $last efs rw 0 0" >> "$SC_PROC_MOUNTS"; exit 0')
        write_exec(
            os.path.join(self.bin, "sha256sum"),
            '#!/bin/bash\npython3 -I -c \'import hashlib,sys\nfor p in sys.argv[1:]:\n    print(hashlib.sha256(open(p,"rb").read()).hexdigest()+"  "+p)\' "$@"\n',
        )
        write_exec(
            os.path.join(self.bin, "aws"),
            '#!/bin/bash\necho "aws $*" >> "$SHIM_ORDER_LOG"\n'
            'if [[ "$1 $2" == "s3 cp" ]]; then\n  src="${3#s3://}"\n  [[ -f "$FAKE_S3/$src" ]] || { echo "404 $src" >&2; exit 1; }\n  cp "$FAKE_S3/$src" "$4"\n  exit 0\nfi\nexit 2\n',
        )
        # a PATH java that is Java 11, so the `command -v java` candidate never finds a real JDK
        write_exec(os.path.join(self.bin, "java"), '#!/bin/bash\necho \'openjdk version "11.0.2"\' >&2\n')

    # ---- helpers -------------------------------------------------------------------------------------------------
    def put(self, key, data):
        path = os.path.join(self.s3, RUNTIME_BUCKET, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode())
        return "s3://%s/%s" % (RUNTIME_BUCKET, key)

    def fake_java(self, home, major="17"):
        os.makedirs(os.path.join(home, "bin"), exist_ok=True)
        write_exec(os.path.join(home, "bin", "java"), "#!/bin/bash\necho 'openjdk version \"%s.0.13\" 2024' >&2\n" % major)
        return home

    def add_shim(self, name, body):
        write_exec(os.path.join(self.bin, name), '#!/bin/bash\necho "%s $*" >> "$SHIM_ORDER_LOG"\n%s\n' % (name, body))

    def order(self):
        with open(self.order_log) as handle:
            return [line.rstrip("\n") for line in handle if line.strip()]

    def args(self, defaults=GOOD_DEFAULTS, runtime_sha=None, jar_sha=None, defaults_sha=None, self_sha=None, max_minutes="240", extra=None, java_home=None):
        a = [
            "--region", "us-east-2", "--max-minutes", max_minutes, "--startup-allowance-minutes", "5",
            "--self-sha256", self_sha or sha(open(BOOTSTRAP, "rb").read()),
            "--runtime-uri", "s3://%s/runtime/scholarchain-runtime.tgz" % RUNTIME_BUCKET, "--runtime-sha256", runtime_sha or sha(self.runtime_blob),
            "--job-jar-uri", "s3://%s/jar/scholarchain-job.jar" % RUNTIME_BUCKET, "--job-jar-sha256", jar_sha or sha(JAR),
            "--spark-defaults-b64", base64.b64encode(defaults.encode()).decode(), "--spark-defaults-sha256", defaults_sha or sha(defaults),
            "--efs-id", "fs-0123abcd", "--access-point-id", "fsap-0123abcd", "--java-home", java_home or self.java_home,
        ]
        return a + (extra or [])

    def env(self, **extra):
        env = {
            "PATH": self.bin + ":/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": self.tmp,
            "LC_ALL": "C",
            "FAKE_S3": self.s3,
            "SHIM_ORDER_LOG": self.order_log,
            "SC_RUNTIME_DEST": self.runtime,
            "SC_JOB_JAR_PATH": os.path.join(self.runtime, "application", "scholarchain-job.jar"),
            "SC_STEP_BIN": self.step_bin,
            "SC_MNT": self.mnt,
            "SC_PROC_MOUNTS": self.proc_mounts,
            "SC_PROC_UPTIME": self.uptime,
            "SC_INSTANCE_JSON": self.instance_json,
            "SC_WORK": os.path.join(self.tmp, "work"),
            "SC_JVM_DIR": self.jvm,
            "SC_ALT_JRE": self.alt,
            "SC_JAVA_HOME_FILE": self.java_file,
        }
        env.update(extra)
        return env

    def run_bs(self, args, **env):
        return subprocess.run(["bash", BOOTSTRAP] + list(args), env=self.env(**env), capture_output=True, text=True, timeout=120)

    def installed_defaults(self):
        with open(os.path.join(self.runtime, "conf", "spark-defaults.conf")) as handle:
            return handle.read()

    def nothing_installed(self):
        self.assertFalse(os.path.exists(os.path.join(self.runtime, "conf", "spark-defaults.conf")))
        self.assertFalse(os.path.exists(self.java_file))
        joined = " ".join(self.order())
        self.assertNotIn("mount -t efs", joined)
        self.assertNotIn("dnf install", joined)


class PinnedPathTests(unittest.TestCase):
    """The installed paths are exactly the ones release.conf pins and pipeline.py expects."""

    def conf(self):
        values = {}
        with open(os.path.join(SCRIPTS_DIR, "config", "release.conf"), encoding="utf-8") as handle:
            for line in handle:
                match = re.match(r"^([A-Z][A-Z0-9_]*)=(.*)$", line.rstrip("\n"))
                if match:
                    values[match.group(1)] = match.group(2)
        return values

    def test_the_script_defaults_equal_the_pinned_release_conf_paths(self):
        with open(BOOTSTRAP, encoding="utf-8") as handle:
            text = handle.read()
        conf = self.conf()
        self.assertIn('RUNTIME_DEST="${SC_RUNTIME_DEST:-%s}"' % conf["PIPELINE_RUNTIME_DIR"], text)
        self.assertIn('JOB_JAR_DEST="${SC_JOB_JAR_PATH:-%s}"' % conf["PIPELINE_JOB_JAR_PATH"], text)
        self.assertIn('MNT="${SC_MNT:-%s}"' % conf["PIPELINE_EFS_MOUNT"], text)
        self.assertIn('JAVA_HOME_FILE="${SC_JAVA_HOME_FILE:-%s}"' % conf["PIPELINE_JAVA_HOME_FILE"], text)

    def test_the_runtime_archive_hash_default_is_the_pinned_release_conf_hash(self):
        self.assertEqual(self.conf()["RUNTIME_ARCHIVE_EXPECTED_SHA256"], "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5")

    def test_no_hardcoded_java_path_and_no_hardcoded_bucket(self):
        with open(BOOTSTRAP, encoding="utf-8") as handle:
            text = handle.read()
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        self.assertNotIn("java-17-amazon-corretto.x86_64\"", code.replace('"${JVM_DIR}/java-17-amazon-corretto.x86_64"', ""))
        self.assertNotRegex(code, r"s3://(?!bucket/)[a-z0-9][a-z0-9.-]+/")
        self.assertNotRegex(text, r"(?<![\d.])\d{12}(?![\d.])")


class HappyPathTests(BootstrapCase):
    def test_installs_the_runtime_jar_defaults_java_home_and_efs_at_the_pinned_layout(self):
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.runtime, "bin", "spark-submit")))
        with open(os.path.join(self.runtime, "application", "scholarchain-job.jar"), "rb") as handle:
            self.assertEqual(handle.read(), JAR, "the job jar from its own S3 URI replaces the archive's copy")
        with open(self.java_file) as handle:
            self.assertEqual(handle.read(), self.java_home + "\n")
        self.assertIn("mount -t efs -o tls,iam,accesspoint=fsap-0123abcd fs-0123abcd:/ %s" % self.mnt, " ".join(self.order()))
        for sub in ("runs", "staging", "config"):
            self.assertTrue(os.path.isdir(os.path.join(self.mnt, sub)), sub)
        self.assertIn("bootstrap complete", r.stderr)

    def test_a_core_node_mounts_but_prepares_nothing_on_efs(self):
        with open(self.instance_json, "w") as handle:
            handle.write('{"isMaster": false}\n')
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.mnt, "runs")))

    def test_arms_the_shutdown_deadline_before_any_download_and_accounts_for_uptime(self):
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        order = self.order()
        self.assertEqual(order[0].split()[0], "sudo", order[0])
        self.assertTrue(order[1].startswith("shutdown -h +"), order[1])
        # uptime 125.5 s rounds up to 3 minutes: 240 - 3 - 5 = 232
        self.assertTrue(order[1].startswith("shutdown -h +232 "), order[1])
        first_aws = next(i for i, line in enumerate(order) if line.startswith("aws "))
        self.assertLess(1, first_aws)

    def test_the_deadline_floors_at_one_minute(self):
        self.run_bs(self.args(max_minutes="4"))
        self.assertTrue(any(line.startswith("shutdown -h +1 ") for line in self.order()))

    def test_a_missing_max_minutes_arms_the_fallback_then_fails_before_any_download(self):
        a = self.args()
        i = a.index("--max-minutes")
        del a[i:i + 2]
        r = self.run_bs(a)
        self.assertEqual(r.returncode, 64)
        self.assertTrue(any(line.startswith("shutdown -h +") for line in self.order()))
        self.assertFalse(any(line.startswith("aws ") for line in self.order()))


class ShaVerificationTests(BootstrapCase):
    """Item 8 and G5: everything is verified against sha256 before it is used; any mismatch fails closed."""

    def assert_closed(self, r, code=3):
        self.assertEqual(r.returncode, code, r.stderr)
        self.assertNotIn("bootstrap complete", r.stderr)

    def test_a_runtime_archive_mismatch_refuses_before_extracting_or_mounting(self):
        r = self.run_bs(self.args(runtime_sha="0" * 64))
        self.assert_closed(r)
        self.assertIn("sha256 mismatch for runtime archive", r.stderr)
        self.assertFalse(os.path.exists(self.runtime))
        self.nothing_installed()

    def test_the_runtime_is_hashed_before_it_is_extracted(self):
        self.run_bs(self.args())
        # a tampered archive in S3 (same key, other bytes) fails the pinned hash
        self.put("runtime/scholarchain-runtime.tgz", tgz({"scholarchain-runtime/bin/evil": b"x"}))
        shutil.rmtree(self.opt, ignore_errors=True)
        r = self.run_bs(self.args())
        self.assert_closed(r)
        self.assertFalse(os.path.exists(os.path.join(self.runtime, "bin", "evil")))

    def test_a_job_jar_mismatch_fails(self):
        r = self.run_bs(self.args(jar_sha="1" * 64))
        self.assert_closed(r)
        self.assertIn("sha256 mismatch for job jar", r.stderr)
        self.nothing_installed()

    def test_a_spark_defaults_mismatch_fails_and_installs_no_defaults(self):
        r = self.run_bs(self.args(defaults_sha="2" * 64))
        self.assert_closed(r)
        self.assertIn("sha256 mismatch for spark-defaults", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.runtime, "conf", "spark-defaults.conf")))
        self.assertNotIn("mount -t efs", " ".join(self.order()))

    def test_tampered_spark_defaults_content_fails_the_recorded_hash(self):
        tampered = GOOD_DEFAULTS + "spark.authenticate false\n"
        r = self.run_bs(self.args(defaults=tampered, defaults_sha=sha(GOOD_DEFAULTS)))
        self.assert_closed(r)
        self.assertIn("sha256 mismatch for spark-defaults", r.stderr)

    def test_a_changed_bootstrap_script_fails_the_self_check_before_any_download(self):
        r = self.run_bs(self.args(self_sha="3" * 64))
        self.assert_closed(r)
        self.assertIn("bootstrap script (drift check)", r.stderr)
        self.assertFalse(any(line.startswith("aws ") for line in self.order()))

    def test_a_failed_self_check_never_deletes_the_script_itself(self):
        before = open(BOOTSTRAP, "rb").read()
        self.assertEqual(self.run_bs(self.args(self_sha="3" * 64)).returncode, 3)
        self.assertTrue(os.path.isfile(BOOTSTRAP))
        self.assertEqual(open(BOOTSTRAP, "rb").read(), before)

    def test_an_artifact_mismatch_fails_and_a_matching_one_is_installed_with_the_right_mode(self):
        uri = self.put("steps/run-step.sh", "#!/bin/bash\necho hi\n")
        dest = os.path.join(self.step_bin, "run-step.sh")
        bad = self.run_bs(self.args(extra=["--artifact", "%s,%s,%s" % (uri, "4" * 64, dest)]))
        self.assert_closed(bad)
        self.assertFalse(os.path.exists(dest))
        shutil.rmtree(self.opt, ignore_errors=True)
        good = self.run_bs(self.args(extra=["--artifact", "%s,%s,%s" % (uri, sha("#!/bin/bash\necho hi\n"), dest)]))
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertTrue(os.access(dest, os.X_OK))

    def test_an_efs_config_artifact_is_verified_and_installed_only_on_the_primary_after_the_mount(self):
        uri = self.put("config/g1.json", "{}\n")
        dest = os.path.join(self.mnt, "config", "g1.json")
        spec = "%s,%s,%s" % (uri, sha("{}\n"), dest)
        r = self.run_bs(self.args(extra=["--artifact", spec]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(dest))
        order = self.order()
        mount_index = next(i for i, line in enumerate(order) if line.startswith("mount "))
        config_fetch = next(i for i, line in enumerate(order) if line.startswith("aws ") and "config/g1.json" in line)
        self.assertLess(mount_index, config_fetch)
        # a mismatch on the EFS artifact fails closed too
        shutil.rmtree(self.mnt, ignore_errors=True)
        shutil.rmtree(self.opt, ignore_errors=True)
        r = self.run_bs(self.args(extra=["--artifact", "%s,%s,%s" % (uri, "5" * 64, dest)]))
        self.assert_closed(r)

    def test_an_artifact_destination_outside_the_allowed_directories_is_refused_before_any_download(self):
        uri = self.put("steps/x.sh", "x")
        for dest in ("/etc/cron.d/evil", os.path.join(self.runtime, "..", "escape"), os.path.join(self.step_bin, "a b")):
            with self.subTest(dest=dest):
                r = self.run_bs(self.args(extra=["--artifact", "%s,%s,%s" % (uri, sha("x"), dest)]))
                self.assertEqual(r.returncode, 64, r.stderr)
                self.assertFalse(any(line.startswith("aws ") for line in self.order()))

    def test_a_download_failure_fails_closed(self):
        os.remove(os.path.join(self.s3, RUNTIME_BUCKET, "runtime", "scholarchain-runtime.tgz"))
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 6, r.stderr)
        self.nothing_installed()

    def test_an_archive_member_outside_the_runtime_directory_is_refused(self):
        for name in ("../evil", "/etc/evil", "scholarchain-runtime/../../evil", "other/evil"):
            with self.subTest(member=name):
                shutil.rmtree(self.opt, ignore_errors=True)
                blob = tgz({name: b"x"})
                self.put("runtime/scholarchain-runtime.tgz", blob)
                r = self.run_bs(self.args(runtime_sha=sha(blob)))
                self.assertEqual(r.returncode, 3, r.stderr)
                self.assertIn("outside scholarchain-runtime", r.stderr)
                self.assertFalse(os.path.exists(self.runtime))

    def test_malformed_arguments_are_refused_before_any_download(self):
        for flag, value in (("--runtime-sha256", "XYZ"), ("--runtime-uri", "https://example.invalid/x"), ("--job-jar-uri", "s3://b/../x y"), ("--region", "nowhere"), ("--efs-id", "fs-ZZ"), ("--access-point-id", "ap-1")):
            with self.subTest(flag=flag):
                a = self.args()
                a[a.index(flag) + 1] = value
                r = self.run_bs(a)
                self.assertEqual(r.returncode, 64, r.stderr)
                self.assertFalse(any(line.startswith("aws ") for line in self.order()))

    def test_an_unknown_argument_and_a_missing_required_argument_are_refused(self):
        self.assertEqual(self.run_bs(self.args(extra=["--bogus", "1"])).returncode, 64)
        a = self.args()
        i = a.index("--job-jar-uri")
        del a[i:i + 2]
        self.assertEqual(self.run_bs(a).returncode, 64)


class JavaResolutionTests(BootstrapCase):
    """Java 17 is resolved at run time (never hard-coded); item 28: the resolved path must be safe for the properties format."""

    def test_the_first_java_17_candidate_wins_and_a_wrong_version_is_skipped(self):
        self.fake_java(os.path.join(self.jvm, "jre-17"), major="11")
        self.fake_java(os.path.join(self.jvm, "java-17-amazon-corretto"), major="17")
        r = self.run_bs(self.args(java_home=os.path.join(self.tmp, "no-such-java")))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as handle:
            self.assertEqual(handle.read().strip(), os.path.join(self.jvm, "java-17-amazon-corretto"))

    def test_no_java_17_anywhere_fails_with_the_candidates_listed(self):
        r = self.run_bs(self.args(java_home=self.fake_java(os.path.join(self.tmp, "java11"), major="11")))
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn("no Java 17 found", r.stderr)
        self.nothing_installed()

    def test_a_java_home_with_unsafe_characters_is_rejected_even_when_it_is_a_working_java_17(self):
        bad_names = ["java\ninjected", "java 17", "java#17", "java=17", "java:17", "java\\17", "java\ttab", "java$17", "java;17"]
        for name in bad_names:
            with self.subTest(name=repr(name)):
                home = self.fake_java(os.path.join(self.tmp, name))
                r = self.run_bs(self.args(java_home=home))
                self.assertEqual(r.returncode, 4, r.stderr)
                self.assertIn("unsafe characters", r.stderr)
                self.assertFalse(os.path.exists(self.java_file), "no Java-home file may be written for an unsafe path")
                self.assertFalse(os.path.exists(os.path.join(self.runtime, "conf", "spark-defaults.conf")))
                shutil.rmtree(home, ignore_errors=True)

    def test_a_dotdot_component_is_rejected(self):
        home = self.fake_java(os.path.join(self.tmp, "java17"))
        r = self.run_bs(self.args(java_home=home + "/../java17"))
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertFalse(os.path.exists(self.java_file))

    def test_a_relative_path_is_rejected(self):
        self.fake_java(os.path.join(self.tmp, "rel-java"))
        r = subprocess.run(["bash", BOOTSTRAP] + self.args(java_home="rel-java"), env=self.env(), cwd=self.tmp, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 4, r.stderr)

    def test_an_unsafe_candidate_is_skipped_when_a_safe_java_17_exists(self):
        self.fake_java(os.path.join(self.jvm, "jre-17"))
        bad = self.fake_java(os.path.join(self.tmp, "bad java"))
        r = self.run_bs(self.args(java_home=bad))
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as handle:
            self.assertEqual(handle.read().strip(), os.path.join(self.jvm, "jre-17"))

    def test_the_resolved_path_is_what_the_defaults_carry_for_the_am_and_the_executors(self):
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self.installed_defaults()
        self.assertIn("spark.yarn.appMasterEnv.JAVA_HOME %s\n" % self.java_home, text)
        self.assertIn("spark.executorEnv.JAVA_HOME %s\n" % self.java_home, text)


class JavaHomeSeparatorTests(BootstrapCase):
    """Item 29: JAVA_HOME entries are removed whatever the separator, and each key occurs exactly once afterwards."""

    AM = "spark.yarn.appMasterEnv.JAVA_HOME"
    EX = "spark.executorEnv.JAVA_HOME"

    def render(self, lines):
        defaults = "\n".join(lines) + "\n"
        r = self.run_bs(self.args(defaults=defaults))
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.installed_defaults()

    def test_every_separator_form_is_removed_and_each_key_occurs_exactly_once(self):
        forms = [
            "%s /old/am", "%s\t/old/am", "%s=/old/am", "%s = /old/am", "%s: /old/am", "  %s /old/am", "\t%s\t/old/am",
            " \t %s=/old/am", "%s", "%s ",
        ]
        for form in forms:
            with self.subTest(form=repr(form)):
                shutil.rmtree(self.opt, ignore_errors=True)
                text = self.render(["spark.authenticate true", form % self.AM, form.replace("/old/am", "/old/ex") % self.EX, "spark.io.encryption.enabled true"])
                keys = parse_properties(text)
                self.assertEqual(keys.count(self.AM), 1, text)
                self.assertEqual(keys.count(self.EX), 1, text)
                self.assertNotIn("/old/", text)
                self.assertIn("spark.authenticate true", text)
                self.assertIn("spark.io.encryption.enabled true", text)
                self.assertIn("%s %s" % (self.AM, self.java_home), text)

    def test_repeated_entries_in_mixed_forms_collapse_to_exactly_one(self):
        text = self.render([self.AM + " /a", "  " + self.AM + "=/b", self.AM + "\t/c", self.EX + " /d", "\t" + self.EX + ": /e"])
        keys = parse_properties(text)
        self.assertEqual((keys.count(self.AM), keys.count(self.EX)), (1, 1), text)
        self.assertNotRegex(text, r"/[a-e]\b")

    def test_a_similarly_named_key_is_not_removed(self):
        text = self.render(["spark.executorEnv.JAVA_HOME_EXTRA keep", "spark.yarn.appMasterEnv.JAVA_HOMEX keep2", "spark.executorEnv.JAVA_OPTS keep3"])
        for needle in ("spark.executorEnv.JAVA_HOME_EXTRA keep", "spark.yarn.appMasterEnv.JAVA_HOMEX keep2", "spark.executorEnv.JAVA_OPTS keep3"):
            self.assertIn(needle, text)
        keys = parse_properties(text)
        self.assertEqual((keys.count(self.AM), keys.count(self.EX)), (1, 1))

    def test_a_file_without_a_trailing_newline_still_gets_both_keys_on_their_own_lines(self):
        defaults = "spark.authenticate true"
        r = self.run_bs(self.args(defaults=defaults))
        self.assertEqual(r.returncode, 0, r.stderr)
        keys = parse_properties(self.installed_defaults())
        self.assertEqual(sorted(keys), sorted(["spark.authenticate", self.AM, self.EX]))

    def test_a_line_continuation_is_refused_because_it_could_swallow_the_appended_keys(self):
        r = self.run_bs(self.args(defaults="spark.a b\\\nspark.c d\n"))
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("line continuation", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.runtime, "conf", "spark-defaults.conf")))

    def test_the_rendered_file_of_the_real_decision_12_10_settings_gets_exactly_one_of_each(self):
        with open(os.path.join(SCRIPTS_DIR, "config", "spark-12-10.conf"), encoding="utf-8") as handle:
            lines = [line.rstrip("\n") for line in handle if line.strip() and not line.startswith("#")]
        text = self.render(lines)
        keys = parse_properties(text)
        self.assertEqual((keys.count(self.AM), keys.count(self.EX)), (1, 1))
        self.assertEqual(len(keys), len(lines) + 2)


class SyntaxTests(unittest.TestCase):
    def test_bash_syntax_and_shellcheck_zero_findings_and_strict_mode(self):
        self.assertEqual(subprocess.run(["bash", "-n", BOOTSTRAP], capture_output=True, text=True).returncode, 0)
        with open(BOOTSTRAP, encoding="utf-8") as handle:
            text = handle.read()
        self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
        self.assertIn("\nset -euo pipefail\n", text)
        if not shutil.which("shellcheck"):
            self.skipTest("shellcheck is not installed")
        result = subprocess.run(["shellcheck", "-x", BOOTSTRAP], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
