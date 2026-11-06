"""package.sh: artifacts, manifest, image build, architecture gate, Docker fallback, runtime archive."""
import hashlib
import json
import os
import unittest

from helpers import SERVICES, Fixture, sha256_bytes

MAINS = {
    "query-api": "edu.uic.cs441.scholarchain.services.QueryApiMain",
    "graph-service": "edu.uic.cs441.scholarchain.services.GraphServiceMain",
    "semantic-service": "edu.uic.cs441.scholarchain.services.SemanticServiceMain",
    "embedding-worker": "edu.uic.cs441.scholarchain.services.EmbeddingWorkerMain",
}
ARCHIVE_BYTES = b"fixture-archive-bytes"


class PackageBase(Fixture):
    def manifest_path(self):
        return os.path.join(self.repo, "target", "release", self.head(), "release-manifest.json")

    def manifest(self):
        with open(self.manifest_path()) as handle:
            return json.load(handle)

    def package(self, *args, **env):
        return self.run_script("package.sh", *args, **env)


class PackageRetainedLogRedactionTests(PackageBase):
    """F4: retained build logs and the timeout trace carry no canary private value, account ID or secret."""

    def test_retained_sbt_log_and_trace_are_redacted(self):
        private = os.path.join(self.tmp, "owner.local.tfvars")
        with open(private, "w") as handle:
            handle.write('owner_note = "CANARY-PKG-PRIVATE-VALUE-5512"\n')
        emit = "sbt saw CANARY-PKG-PRIVATE-VALUE-5512 for account 123456789012 with FAKE-SESSION-TOKEN-ZZZZ9999yyyyXXXX8888 and FAKE/SECRET+KEY-0123456789abcdefghijklmnop"
        result = self.package(SCHOLARCHAIN_TF_PRIVATE_VARS=private, FAKE_EMIT=emit)
        self.assertEqual(result.rc, 0, result.out)
        log = os.path.join(self.repo, "target", "release", self.head(), "logs", "sbt-packageRelease.log")
        with open(log) as handle:
            retained = handle.read()
        self.assertIn("sbt saw <redacted> for account <acct> with <redacted> and <redacted>", retained, "the diagnostic is kept, redacted")
        with open(self.timeout_log) as handle:
            trace = handle.read()
        for canary in ("CANARY-PKG-PRIVATE-VALUE-5512", "123456789012", "FAKE-SESSION-TOKEN-ZZZZ9999yyyyXXXX8888", "FAKE/SECRET+KEY-0123456789abcdefghijklmnop", private):
            self.assertNotIn(canary, retained, canary)
            self.assertNotIn(canary, trace, canary)
            self.assertNotIn(canary, result.out, canary)


class PackageSuccessTests(PackageBase):
    def test_jars_images_and_manifest(self):
        result = self.package()
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS"), result.result_line())
        for step in ("preflight", "runtime-archive", "jdk17", "sbt-package-release", "collect-artifacts", "static-dockerfile-check", "arch-gate-ecs", "docker-images", "write-manifest"):
            self.assertIn(step, result.steps())
        manifest = self.manifest()
        head = self.head()
        self.assertEqual(manifest["commit"], head)
        self.assertRegex(manifest["commit"], r"^[0-9a-f]{40}$")
        self.assertFalse(manifest["dirty"])
        self.assertEqual(manifest["image_tag"], head)
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["image_platform"], "linux/amd64")
        self.assertEqual(manifest["ecs_architecture"], "linux/amd64")
        self.assertTrue(manifest["arch_gate"]["passed"])
        self.assertIn("openjdk version", manifest["toolchain"]["java"])
        self.assertEqual(manifest["toolchain"]["sbt"], "1.10.7")
        # Artifact hashes are hand-derived from the bytes the fake sbt writes.
        by_name = {a["name"]: a for a in manifest["artifacts"]}
        self.assertEqual(by_name["hadoop-submit-jar"]["sha256"], sha256_bytes(b"submit"))
        self.assertEqual(by_name["hadoop-submit-jar"]["size"], 6)
        self.assertEqual(by_name["hadoop-dependency-bundle"]["sha256"], sha256_bytes(b"bundle"))
        self.assertEqual(by_name["spark-job-jar"]["sha256"], sha256_bytes(b"spark"))
        dist = by_name["service-distribution"]
        self.assertEqual(dist["files"], 4)
        self.assertEqual(dist["size"], len(b"services") + len(b"dep") + len(b"p") + len(b"{}"))
        self.assertEqual(dist["services_jar_sha256"], sha256_bytes(b"services"))
        listing = sorted(
            "%s %s %d" % (rel, sha256_bytes(data), len(data))
            for rel, data in (("lib/dep.jar", b"dep"), ("prompts/runtime/p.txt", b"p"), ("prompts/schemas/s.json", b"{}"), ("services.jar", b"services"))
        )
        self.assertEqual(dist["sha256"], hashlib.sha256("\n".join(listing).encode()).hexdigest())
        # Images: one buildx build per service with the documented flags.
        builds = [a for n, a in self.calls("docker") if a.startswith("buildx build")]
        self.assertEqual(len(builds), 4)
        for svc, build in zip(SERVICES, builds):
            for token in ("--platform linux/amd64", "--provenance=false", "--sbom=false", "--build-arg MAIN_CLASS=%s" % MAINS[svc], "-t scholarchain-%s:%s" % (svc, head), "--load"):
                self.assertIn(token, build)
        self.assertEqual({i["service"] for i in manifest["images"]}, set(SERVICES))
        self.assertTrue(all(i["status"] == "built" and i["os_arch"] == "linux/amd64" for i in manifest["images"]))
        self.assertTrue(all(i["local_image_id"].startswith("sha256:") for i in manifest["images"]))
        # Nothing was pushed or logged in to.
        self.assertEqual(self.mutating_calls(), [])
        self.assertEqual(self.calls("aws"), [])
        # JDK 17 environment was applied for sbt.
        env_line = self.sbt_env_lines()[0]
        self.assertIn("JAVA_HOME=%s" % self.jdk, env_line)
        self.assertIn("-Dlogback.configurationFile=", env_line)
        self.assertIn("xml-repair-logback.xml", env_line)
        sbt_calls = [a for n, a in self.calls("sbt")]
        self.assertEqual(sbt_calls, ["-batch packageRelease"])

    def test_dirty_tree_tags_images_dirty(self):
        self.write("junk.txt", "x\n")
        result = self.package()
        self.assertEqual(result.rc, 0, result.out)
        manifest = self.manifest()
        self.assertTrue(manifest["dirty"])
        self.assertTrue(manifest["image_tag"].endswith("-dirty"))
        self.assertTrue(all(i["image"].endswith(self.head() + "-dirty") for i in manifest["images"]))

    def test_builds_go_through_the_timeout_helper(self):
        self.package()
        helper = self.timeout_helper_lines()
        self.assertTrue(any("sbt -batch packageRelease" in l for l in helper))
        self.assertEqual(len([l for l in helper if "docker buildx build" in l]), 4)


class PackageArchitectureGateTests(PackageBase):
    def test_arm64_image_fails_the_gate_and_writes_no_manifest(self):
        result = self.package(FAKE_IMAGE_ARCH="arm64")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(result.steps()[-1], "arch-gate-image-query-api")
        self.assertIn("RESULT: FAIL step=arch-gate-image-query-api", result.stdout)
        self.assertIn("is linux/arm64, expected linux/amd64", result.out)
        self.assertFalse(os.path.exists(self.manifest_path()))

    def test_ecs_arm64_with_amd64_config_fails_before_any_docker_build(self):
        self.write("infra/terraform/modules/runtime/compute.tf", 'runtime_platform {\n  cpu_architecture = "ARM64"\n}\n')
        self.commit("arm task")
        result = self.package()
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(result.steps()[-1], "arch-gate-ecs")
        self.assertIn("ECS task architecture linux/arm64", result.out)
        self.assertEqual([a for n, a in self.calls("docker") if a.startswith("buildx build")], [])
        self.assertFalse(os.path.exists(self.manifest_path()))

    def test_config_platform_override_matching_ecs_arm64_passes_the_ecs_check(self):
        self.write("infra/terraform/modules/runtime/compute.tf", 'cpu_architecture = "ARM64"\n')
        self.commit("arm task")
        self.use_config(IMAGE_PLATFORM="linux/arm64")
        result = self.package(FAKE_IMAGE_ARCH="arm64")
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.manifest()["ecs_architecture"], "linux/arm64")

    def test_unparseable_ecs_architecture_fails(self):
        for body in ("# nothing here\n", 'cpu_architecture = "RISCV"\n', 'cpu_architecture = "X86_64"\ncpu_architecture = "ARM64"\n'):
            with self.subTest(body=body):
                self.write("infra/terraform/modules/runtime/compute.tf", body)
                self.commit("variant")
                result = self.package()
                self.assertEqual(result.rc, 4, result.out)
                self.assertEqual(result.steps()[-1], "arch-gate-ecs")


class PackageDockerFallbackTests(PackageBase):
    def test_docker_unreachable_builds_jars_and_records_skipped_images(self):
        result = self.package(FAKE_DOCKER_INFO_RC="1")
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("Docker is unreachable", result.out)
        self.assertIn("images-skipped", result.result_line())
        self.assertIn("dockerfile ok", result.out)
        manifest = self.manifest()
        self.assertEqual(manifest["status"], "partial-no-images")
        self.assertTrue(all(i["status"] == "skipped" for i in manifest["images"]))
        self.assertFalse(manifest["arch_gate"]["passed"])
        self.assertTrue(any("docker unreachable" in w for w in manifest["warnings"]))
        self.assertEqual([a for n, a in self.calls("docker") if a.startswith("buildx build")], [])
        self.assertEqual({a["name"] for a in manifest["artifacts"]}, {"hadoop-submit-jar", "hadoop-dependency-bundle", "spark-job-jar", "service-distribution"})

    def test_require_images_makes_unreachable_docker_fatal(self):
        result = self.package("--require-images", FAKE_DOCKER_INFO_RC="1")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("RESULT: REFUSED step=docker-images", result.stdout)

    def test_static_dockerfile_checks(self):
        with open(os.path.join(self.repo, "Dockerfile")) as handle:
            original = handle.read()
        cases = {
            "unpinned FROM": original.replace("@sha256:", ":latest-not-a-digest#"),
            "allowlist missing a service": original.replace("edu.uic.cs441.scholarchain.services.EmbeddingWorkerMain)", ")"),
            "COPY source missing": original + "COPY does/not/exist /x\n",
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.write("Dockerfile", text)
                self.commit(label)
                result = self.package(FAKE_DOCKER_INFO_RC="1")
                self.assertEqual(result.rc, 4, result.out)
                self.assertEqual(result.steps()[-1], "static-dockerfile-check")
                self.assertIn("DOCKERFILE-CHECK-FAILED", result.out)


class PackageRuntimeArchiveTests(PackageBase):
    def setUp(self):
        super().setUp()
        self.archive = os.path.join(self.tmp, "archive.tgz")
        with open(self.archive, "wb") as handle:
            handle.write(ARCHIVE_BYTES)
        self.pins = {"SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive}
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)), RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE_BYTES))

    def test_matching_archive_is_verified_and_recorded(self):
        result = self.package(**self.pins)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("CONFIG-FILE: using", result.stdout)
        archive = self.manifest()["runtime_archive"]
        self.assertEqual(archive["status"], "verified")
        self.assertEqual(archive["sha256"], sha256_bytes(ARCHIVE_BYTES))
        self.assertEqual(archive["size"], len(ARCHIVE_BYTES))

    def test_hash_mismatch_is_fatal_before_the_build(self):
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)), RUNTIME_ARCHIVE_EXPECTED_SHA256="0" * 64)
        result = self.package(**self.pins)
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(result.steps()[-1], "runtime-archive")
        self.assertIn("sha256", result.out)
        self.assertEqual(self.calls("sbt"), [])
        self.assertFalse(os.path.exists(self.manifest_path()))

    def test_size_mismatch_is_fatal(self):
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE="999", RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE_BYTES))
        result = self.package(**self.pins)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("size", result.out)

    def test_explicit_missing_path_is_fatal(self):
        result = self.package(SCHOLARCHAIN_RUNTIME_ARCHIVE=os.path.join(self.tmp, "gone.tgz"))
        self.assertEqual(result.rc, 4, result.out)

    def test_absent_archive_recorded_and_fatal_only_when_required(self):
        result = self.package()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.manifest()["runtime_archive"]["status"], "absent")
        required = self.package("--require-runtime-archive")
        self.assertEqual(required.rc, 3, required.out)
        self.assertIn("RESULT: REFUSED step=runtime-archive", required.stdout)

    def test_default_ignored_path_is_used_when_it_exists(self):
        default = os.path.join(self.repo, "target", "phase12d-runtime-repair-20261103", "artifacts", "scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz")
        os.makedirs(os.path.dirname(default))
        with open(default, "wb") as handle:
            handle.write(ARCHIVE_BYTES)
        pins = dict(self.pins)
        del pins["SCHOLARCHAIN_RUNTIME_ARCHIVE"]
        result = self.package(**pins)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.manifest()["runtime_archive"]["status"], "verified")

    def test_pinned_settings_ignore_same_named_environment_variables(self):
        """With the real config, env vars named like the pins are ignored and announced."""
        self.config_file = None
        result = self.package(
            SCHOLARCHAIN_RUNTIME_ARCHIVE=self.archive,
            RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)),
            RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE_BYTES),
        )
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(result.steps()[-1], "runtime-archive")
        self.assertIn("CONFIG-IGNORED: pinned settings cannot be overridden by the environment", result.stdout)
        self.assertIn("RUNTIME_ARCHIVE_EXPECTED_SHA256", result.stdout)
        self.assertIn("321876735", result.out, "the real pinned size is what was compared")
        arm = self.package(IMAGE_PLATFORM="linux/arm64", FAKE_IMAGE_ARCH="arm64")
        self.assertEqual(arm.rc, 4, "IMAGE_PLATFORM from the environment is ignored; amd64 images are required")
        self.assertIn("CONFIG-IGNORED", arm.stdout)

    def test_real_config_pins_are_the_g5_values(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "release.conf")) as handle:
            text = handle.read()
        self.assertIn("RUNTIME_ARCHIVE_EXPECTED_SHA256=789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5", text)
        self.assertIn("RUNTIME_ARCHIVE_EXPECTED_SIZE=321876735", text)


class PackagePreconditionTests(PackageBase):
    def test_sbt_failure_exit_5(self):
        result = self.package(FAKE_SBT_PACKAGE_RC="1")
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("RESULT: FAIL step=sbt-package-release", result.stdout)

    def test_no_jdk17_refused_with_clear_message(self):
        bad = os.path.join(self.tmp, "jdk21", "bin")
        os.makedirs(bad)
        with open(os.path.join(bad, "java"), "w") as handle:
            handle.write('#!/bin/bash\necho \'openjdk version "21.0.1"\' >&2\n')
        os.chmod(os.path.join(bad, "java"), 0o755)
        result = self.package(JAVA_HOME=os.path.dirname(bad), JAVA_HOME_TOOL="/nonexistent", JDK17_FALLBACK_HOME="/nonexistent")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("JDK 17 not found", result.out)
        self.assertEqual(self.calls("sbt"), [])

    def test_fallback_jdk_is_used_when_java_home_is_not_17(self):
        bad = os.path.join(self.tmp, "jdk21", "bin")
        os.makedirs(bad)
        with open(os.path.join(bad, "java"), "w") as handle:
            handle.write('#!/bin/bash\necho \'openjdk version "21.0.1"\' >&2\n')
        os.chmod(os.path.join(bad, "java"), 0o755)
        result = self.package(JAVA_HOME=os.path.dirname(bad), JAVA_HOME_TOOL="/nonexistent", JDK17_FALLBACK_HOME=self.jdk)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("JAVA_HOME=%s" % self.jdk, self.sbt_env_lines()[0])

    def test_missing_logback_file_refused(self):
        os.remove(os.path.join(self.repo, "docs", "agent-runs", "phase-04", "xml-repair-logback.xml"))
        result = self.package()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("logback", result.out)

    def test_missing_artifact_fails_the_gate(self):
        result = self.package(FAKE_SBT_PACKAGE_RC="0", ARTIFACT_SPARK_JOB_GLOB="modules/spark/target/does-not-exist-*.jar")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(result.steps()[-1], "collect-artifacts")

    def test_unknown_argument_exit_2(self):
        self.assertEqual(self.package("--nope").rc, 2)


if __name__ == "__main__":
    unittest.main()
