import hashlib
import io
import json
import os
import tarfile
import unittest

from helpers import EMR_DIR, ShimTestCase, write_exec

BOOTSTRAP = os.path.join(EMR_DIR, "bootstrap.sh")
BUCKET = "scholarchain-spike-emr-111122223333-us-east-2"
JAR = b"fake job jar\n"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def tgz(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class BootstrapTests(ShimTestCase):
    def setUp(self):
        super().setUp()
        self.runtime_blob = tgz({
            "scholarchain-runtime/application/scholarchain-job.jar": JAR,
            "scholarchain-runtime/bin/spark-submit": b"#!/bin/sh\n",
        })
        self.inputs_blob = tgz({"g1/er/resolution-manifest.json": b"{}\n"})
        self.put(f"s3/{BUCKET}/staging/runtime/scholarchain-runtime.tgz", self.runtime_blob, "wb")
        self.put(f"s3/{BUCKET}/staging/inputs/g1-upstream-inputs.tgz", self.inputs_blob, "wb")
        self.put(f"s3/{BUCKET}/staging/config/spark-g1-portable.json", "{}\n")
        self.put(f"s3/{BUCKET}/staging/config/spark-defaults.conf", "spark.authenticate true\n")
        self.put(f"s3/{BUCKET}/staging/bin/run-step.sh", "#!/bin/bash\n")
        self.put(f"s3/{BUCKET}/staging/bin/collect-results.sh", "#!/bin/bash\n")
        self.opt = os.path.join(self.tmp, "opt")
        self.mnt = os.path.join(self.tmp, "mnt-scholarchain")
        self.proc_mounts = os.path.join(self.tmp, "proc-mounts")
        self.uptime = os.path.join(self.tmp, "uptime")
        self.instance_json = os.path.join(self.tmp, "instance.json")
        open(self.proc_mounts, "w").close()
        with open(self.uptime, "w") as h:
            h.write("125.50 400.00\n")
        with open(self.instance_json, "w") as h:
            h.write('{"isMaster": true}\n')
        java_home = os.path.join(self.tmp, "java17")
        os.makedirs(os.path.join(java_home, "bin"))
        write_exec(os.path.join(java_home, "bin", "java"), '#!/bin/bash\necho \'openjdk version "17.0.13" 2024\' >&2\n')
        self.java_home = java_home
        # shims: record, then behave
        self.add_shim("sudo", 'exec "$@"')
        self.add_shim("shutdown", "exit 0")
        self.add_shim("dnf", "exit 0")
        self.add_shim("mount", 'for last; do :; done; echo "fs $last efs rw 0 0" >> "$SC_PROC_MOUNTS"; exit 0')
        self.add_shim("sha256sum", 'exec shasum -a 256 "$@"')
        # a PATH `java` that is Java 11, so the `command -v java` candidate never finds a real JDK
        write_exec(os.path.join(self.bin, "java"), '#!/bin/bash\necho \'openjdk version "11.0.2"\' >&2\n')
        self.jvm = os.path.join(self.tmp, "jvm")
        self.alt = os.path.join(self.tmp, "alternatives-jre")
        self.java_file = os.path.join(self.tmp, "java-home-file")
        # logging aws wrapper: order log is shared through SHIM_ORDER_LOG (fake_aws appends)

    def fake_java(self, home, major="17"):
        os.makedirs(os.path.join(home, "bin"), exist_ok=True)
        write_exec(os.path.join(home, "bin", "java"), f'#!/bin/bash\necho \'openjdk version "{major}.0.13" 2024\' >&2\n')
        return home

    def args(self, runtime_sha=None, max_minutes="120", allowance="5", extra=None):
        a = [
            "--bucket", BUCKET, "--region", "us-east-2",
            "--max-minutes", max_minutes, "--startup-allowance-minutes", allowance,
            "--runtime-key", "staging/runtime/scholarchain-runtime.tgz",
            "--runtime-sha256", runtime_sha or sha(self.runtime_blob),
            "--job-jar-sha256", sha(JAR),
            "--inputs-key", "staging/inputs/g1-upstream-inputs.tgz", "--inputs-sha256", sha(self.inputs_blob),
            "--g1-config-key", "staging/config/spark-g1-portable.json",
            "--spark-defaults-key", "staging/config/spark-defaults.conf",
            "--run-step-key", "staging/bin/run-step.sh", "--collect-key", "staging/bin/collect-results.sh",
            "--efs-id", "fs-0123", "--access-point-id", "fsap-0123", "--java-home", self.java_home,
        ]
        return a + (extra or [])

    def run_bs(self, args):
        return self.run_script(
            BOOTSTRAP, args,
            SC_RUNTIME_DEST=os.path.join(self.opt, "scholarchain-runtime"),
            SC_SPIKE_BIN=os.path.join(self.opt, "scholarchain-spike", "bin"),
            SC_MNT=self.mnt, SC_PROC_MOUNTS=self.proc_mounts, SC_PROC_UPTIME=self.uptime,
            SC_INSTANCE_JSON=self.instance_json, SC_WORK=os.path.join(self.tmp, "work"),
            SC_JVM_DIR=self.jvm, SC_ALT_JRE=self.alt, SC_JAVA_HOME_FILE=self.java_file,
        )

    def test_arms_shutdown_before_any_download(self):
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        order = self.order()
        first_shutdown = next(i for i, l in enumerate(order) if l.startswith("shutdown "))
        first_aws = next(i for i, l in enumerate(order) if l.startswith("aws "))
        self.assertLess(first_shutdown, first_aws)
        self.assertEqual(order[0].split()[0], "sudo", order[0])  # the very first command is `sudo shutdown ...`
        self.assertTrue(order[1].startswith("shutdown -h +"), order[1])

    def test_deadline_minutes_account_for_uptime_and_allowance(self):
        # uptime 125.5 s -> 3 minutes (rounded up); 120 - 3 - 5 = 112
        self.run_bs(self.args())
        self.assertIn("shutdown -h +112 ", " ".join(self.order()) + " ")

    def test_deadline_floors_at_one_minute(self):
        self.run_bs(self.args(max_minutes="4"))
        self.assertTrue(any(l.startswith("shutdown -h +1 ") for l in self.order()))

    def test_checksum_mismatch_exits_nonzero_before_mount(self):
        r = self.run_bs(self.args(runtime_sha="0" * 64))
        self.assertEqual(r.returncode, 3)
        self.assertIn("sha256 mismatch", r.stderr)
        order = " ".join(self.order())
        self.assertIn("shutdown -h", order)  # the deadline was armed first anyway
        self.assertNotIn("mount -t efs", order)
        self.assertNotIn("dnf install", order)
        self.assertFalse(os.path.exists(os.path.join(self.opt, "scholarchain-runtime")))

    def test_job_jar_mismatch_fails(self):
        a = self.args()
        a[a.index("--job-jar-sha256") + 1] = "1" * 64
        r = self.run_bs(a)
        self.assertEqual(r.returncode, 3)
        self.assertNotIn("mount -t efs", " ".join(self.order()))

    def test_missing_max_minutes_arms_fallback_then_fails(self):
        a = [x for x in self.args()]
        i = a.index("--max-minutes")
        del a[i:i + 2]
        r = self.run_bs(a)
        self.assertEqual(r.returncode, 64)
        self.assertTrue(any(l.startswith("shutdown -h +") for l in self.order()))
        self.assertFalse(any(l.startswith("aws ") for l in self.order()))

    def test_unarmable_deadline_fails_closed(self):
        self.add_shim("shutdown", "exit 1")
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 10)
        self.assertFalse(any(l.startswith("aws ") for l in self.order()))

    def test_efs_mounted_with_tls_iam_and_access_point(self):
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        mount = next(l for l in self.order() if l.startswith("mount "))
        self.assertIn("-t efs", mount)
        self.assertIn("tls,iam,accesspoint=fsap-0123", mount)
        self.assertIn("fs-0123:/", mount)

    def test_runtime_extracted_and_spark_conf_installed(self):
        self.run_bs(self.args())
        self.assertTrue(os.path.exists(os.path.join(self.opt, "scholarchain-runtime", "application", "scholarchain-job.jar")))
        with open(os.path.join(self.opt, "scholarchain-runtime", "conf", "spark-defaults.conf")) as h:
            self.assertIn("spark.authenticate true", h.read())
        self.assertTrue(os.access(os.path.join(self.opt, "scholarchain-spike", "bin", "run-step.sh"), os.X_OK))

    def test_primary_prepares_efs_and_inputs_core_does_not(self):
        self.run_bs(self.args())
        self.assertTrue(os.path.exists(os.path.join(self.mnt, "inputs", "g1", "er", "resolution-manifest.json")))
        self.assertTrue(os.path.isdir(os.path.join(self.mnt, "results")))
        self.assertTrue(os.path.exists(os.path.join(self.mnt, "config", "spark-g1-portable.json")))

    def test_core_node_skips_inputs(self):
        with open(self.instance_json, "w") as h:
            h.write('{"isMaster": false}\n')
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.mnt, "inputs")))
        self.assertFalse(any("g1-upstream-inputs" in l for l in self.order()))

    def test_refuses_local_directory_when_mount_did_not_happen(self):
        self.add_shim("mount", "exit 0")  # claims success but never appears in /proc/mounts
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 5)
        self.assertIn("not a mount point", r.stderr)

    def no_java_arg(self):
        a = self.args()
        i = a.index("--java-home")
        del a[i:i + 2]
        return a

    def test_resolves_jre17_when_only_it_exists(self):
        home = self.fake_java(os.path.join(self.jvm, "jre-17"))
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as h:
            self.assertEqual(h.read().strip(), home)
        self.assertIn(f"resolved JAVA_HOME={home}", r.stderr)

    def test_falls_back_to_the_alternatives_symlink(self):
        real = self.fake_java(os.path.join(self.tmp, "real-jre"))
        os.symlink(real, self.alt)
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as h:
            self.assertEqual(h.read().strip(), os.path.realpath(real))

    def test_corretto_directory_is_a_candidate_after_jre17(self):
        self.fake_java(os.path.join(self.jvm, "java-17-amazon-corretto"))
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as h:
            self.assertTrue(h.read().strip().endswith("java-17-amazon-corretto"))

    def test_rejects_a_java11_candidate_and_takes_the_next_valid_one(self):
        self.fake_java(os.path.join(self.jvm, "jre-17"), major="11")
        good = self.fake_java(os.path.join(self.jvm, "java-17-amazon-corretto"))
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as h:
            self.assertEqual(h.read().strip(), good)

    def test_only_java11_exits_4_and_lists_the_candidates(self):
        self.fake_java(os.path.join(self.jvm, "jre-17"), major="11")
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 4)
        self.assertIn("candidates tried:", r.stderr)
        self.assertIn("jre-17", r.stderr)
        self.assertIn("java-17-amazon-corretto", r.stderr)
        self.assertNotIn("mount -t efs", " ".join(self.order()))

    def test_no_java_at_all_exits_4_and_the_deadline_was_armed_first(self):
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 4)
        order = self.order()
        self.assertTrue(order[1].startswith("shutdown -h +"), order[:3])
        self.assertFalse(os.path.exists(self.java_file))

    def test_explicit_java_home_wins_when_valid(self):
        self.fake_java(os.path.join(self.jvm, "jre-17"))
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.java_file) as h:
            self.assertEqual(h.read().strip(), self.java_home)

    def test_spark_defaults_get_the_resolved_java_home_not_a_hardcoded_one(self):
        self.put(f"s3/{BUCKET}/staging/config/spark-defaults.conf", "spark.authenticate true\nspark.executorEnv.JAVA_HOME /usr/lib/jvm/java-17-amazon-corretto\n")
        home = self.fake_java(os.path.join(self.jvm, "jre-17"))
        r = self.run_bs(self.no_java_arg())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.opt, "scholarchain-runtime", "conf", "spark-defaults.conf")) as h:
            text = h.read()
        self.assertIn(f"spark.yarn.appMasterEnv.JAVA_HOME {home}\n", text)
        self.assertIn(f"spark.executorEnv.JAVA_HOME {home}\n", text)
        self.assertNotIn("java-17-amazon-corretto", text)
        self.assertIn("spark.authenticate true", text)

    def test_wrong_java_version_fails(self):
        write_exec(os.path.join(self.java_home, "bin", "java"), '#!/bin/bash\necho \'openjdk version "11.0.1"\' >&2\n')
        r = self.run_bs(self.args())
        self.assertEqual(r.returncode, 4)


if __name__ == "__main__":
    unittest.main()
