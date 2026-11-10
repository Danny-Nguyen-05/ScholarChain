"""scripts/upload-emr-artifacts.sh (replan G6): upload of the EMR bootstrap, step programs, job JARs, config files and input datasets
to the artifacts bucket under emr/<run_prefix>/.

Everything runs against a fake aws that keeps a bucket in a directory (fake_tool.py, FAKE_S3_DIR): no cloud, no credentials.
Hand-derived expectations: the fixture holds 1 bootstrap + 4 step programs + 4 job JARs + 3 config files + 2 datasets x 4 sample files
= 1 + 4 + 4 + 3 + 8 = 20 planned files (a hidden .DS_Store inside a dataset is skipped, not uploaded). The expected sha256 and the
expected plan hash are computed here with hashlib, independent of the script: the plan hash is sha256 over the sorted lines
"<key> TAB <bytes> TAB <sha256> LF". S3's ChecksumSHA256 is base64 of the raw sha256 digest.
"""
import hashlib
import json
import os
import re
import sys
import unittest

from helpers import FAKE_ACCOUNT, SCRIPTS_DIR, Fixture, account_hash, b64_sha256, sha256_bytes

sys.path.insert(0, os.path.join(SCRIPTS_DIR, "lib"))
import upload_emr_artifacts  # noqa: E402

PREFIX = "run-20261115"
OTHER_ACCOUNT = "9" * 12  # a different account than FAKE_ACCOUNT, built without a 12-digit literal
ROOT = "emr/%s" % PREFIX
BUCKET = "scholarchain-course-%s-artifacts" % FAKE_ACCOUNT
MANIFEST_REL = os.path.join("target", "phase14", "evidence", "15a", "emr-upload-manifest.json")
STEP_NAMES = ("sc-ceiling-check.py", "sc-class-origin-verify.py", "sc-render-spark-config.py", "sc-step.sh")
JAR_FILE = {"hadoop-submit-jar": "hadoop-submit.jar", "hadoop-dependency-bundle": "hadoop-bundle.jar", "entity-resolution-job-jar": "entity-resolution.jar", "spark-job-jar": "spark-job.jar"}
ROLES = ("hadoop-dependency-bundle", "hadoop-submit-jar", "entity-resolution-job-jar", "spark-job-jar")
SAMPLES = ("dblp/linked-records.xml", "openalex/works.jsonl", "crossref/works.jsonl", "orcid/records.jsonl")
DATASETS = ("small", "medium")
BOOTSTRAP = b"#!/bin/bash\n# synthetic bootstrap\n"


def plan_hash(entries):
    """Independent of the script: sha256 of the sorted '<key>\\t<bytes>\\t<sha256>\\n' lines."""
    text = "".join("%s\t%d\t%s\n" % (key, len(data), sha256_bytes(data)) for key, data in sorted(entries.items()))
    return hashlib.sha256(text.encode()).hexdigest()


class EmrBase(Fixture):
    def setUp(self):
        super().setUp()
        self.s3 = os.path.join(self.tmp, "s3")
        os.makedirs(self.s3)
        self.expected = {}
        self.step_data = {name: ("# synthetic %s\n" % name).encode() for name in STEP_NAMES}
        self.jar_data = {role: ("PK synthetic jar %s\n" % role).encode() for role in ROLES}
        self.write_bytes("scripts/emr/bootstrap.sh", BOOTSTRAP)
        for name, data in self.step_data.items():
            self.write_bytes("scripts/emr/" + name, data)
        pins = {"bin_dir": "/opt/scholarchain-spike/bin", "programs": {n: sha256_bytes(d) for n, d in self.step_data.items()}}
        self.write("infra/terraform/emr-step-programs.json", json.dumps(pins))
        self.write_artifact_manifest()
        self.config_files = {
            "--er-policy": self.write_bytes("../cfg/policy.json", b'{"policy": 1}\n'),
            "--er-config": self.write_bytes("../cfg/erc.json", b'{"er": 2}\n'),
            "--spark-config-template": self.write_bytes("../cfg/template.json", b'{"spark": 3}\n'),
        }
        self.datasets = {label: self.make_dataset(label) for label in DATASETS}
        self.expected[ROOT + "/bin/bootstrap.sh"] = BOOTSTRAP
        for name, data in self.step_data.items():
            self.expected["%s/steps/%s" % (ROOT, name)] = data
        for role, data in self.jar_data.items():
            self.expected["%s/jars/%s" % (ROOT, JAR_FILE[role])] = data
        self.expected[ROOT + "/config/er-policy.json"] = b'{"policy": 1}\n'
        self.expected[ROOT + "/config/er-config.json"] = b'{"er": 2}\n'
        self.expected[ROOT + "/config/spark-config-template.json"] = b'{"spark": 3}\n'

    # ---- fixtures ---------------------------------------------------------------------------
    def write_bytes(self, rel, data):
        path = os.path.normpath(os.path.join(self.repo, rel))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def write_artifact_manifest(self, jar_data=None, roles=ROLES, schema="scholarchain.emr-artifact-manifest.v1", path_for=None):
        jar_data = jar_data or self.jar_data
        entries = []
        for role in roles:
            rel = (path_for or (lambda r: "target/%s/%s.jar" % (r, r)))(role)
            data = self.jar_data.get(role, b"x")
            if not rel.startswith("/") and ".." not in rel:
                self.write_bytes(rel, jar_data.get(role, data))
            entries.append({"role": role, "path": rel, "bytes": len(data), "sha256": sha256_bytes(data), "byteReproducible": True})
        self.write_bytes("target/emr-artifacts/emr-artifact-manifest.json", json.dumps({"schema": schema, "projectVersion": "0", "artifacts": entries}).encode())

    def make_dataset(self, label):
        root = os.path.join(self.tmp, "datasets-" + label)
        for sample in SAMPLES:
            data = ("synthetic %s %s\n" % (label, sample)).encode()
            path = os.path.join(root, "datasets", "samples", sample)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(data)
            self.expected["%s/input/%s/datasets/samples/%s" % (ROOT, label, sample)] = data
        with open(os.path.join(root, "datasets", "samples", "dblp", ".DS_Store"), "wb") as handle:
            handle.write(b"hidden")
        return root

    def dataset_args(self, labels=DATASETS):
        args = []
        for label in labels:
            args += ["--input-dataset", "%s=%s" % (label, self.datasets[label])]
        return args

    def stored(self, key):
        with open(os.path.join(self.s3, BUCKET, key), "rb") as handle:
            return handle.read()

    def stored_keys(self):
        base = os.path.join(self.s3, BUCKET)
        found = []
        for current, _dirs, files in os.walk(base):
            for name in files:
                found.append(os.path.relpath(os.path.join(current, name), base).replace(os.sep, "/"))
        return sorted(found)

    def seed(self, key, data, checksum="auto"):
        path = os.path.join(self.s3, BUCKET, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        meta = os.path.join(self.s3, ".meta", BUCKET, key + ".json")
        os.makedirs(os.path.dirname(meta), exist_ok=True)
        with open(meta, "w", encoding="utf-8") as handle:
            json.dump({"ChecksumSHA256": b64_sha256(data) if checksum == "auto" else checksum, "VersionId": "seeded-version"}, handle)

    # ---- approval records -------------------------------------------------------------------
    def approval_text(self, entries=None, plan_sha=None, account=FAKE_ACCOUNT, region="us-east-2", action="upload-emr-artifacts", omit=(), extra=""):
        values = {
            "APPROVED_ACTION": action,
            "APPROVED_PLAN_SHA256": plan_sha or plan_hash(entries or self.expected),
            "APPROVED_ACCOUNT_SHA256": account_hash(account),
            "APPROVED_REGION": region,
        }
        lines = ["# approval written by the human", ""] + ["%s=%s" % (k, v) for k, v in values.items() if k not in omit]
        return "\n".join(lines) + "\n" + extra

    def write_record(self, text=None, name="approval.md"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.approval_text() if text is None else text)
        return path

    # ---- runners ----------------------------------------------------------------------------
    def args(self, execute=False, prefix=PREFIX, bucket=BUCKET, profile="scholarchain-pipeline", role="operator-loader", approval="auto",
             extra=(), configs=True, labels=DATASETS):
        argv = ["--artifacts-bucket", bucket, "--run-prefix", prefix, "--region", "us-east-2"] + self.dataset_args(labels)
        if configs:
            for flag, path in self.config_files.items():
                argv += [flag, path]
        if execute:
            if profile:
                argv += ["--profile", profile]
            if role:
                argv += ["--principal-role", role]
            if approval == "auto":
                approval = self.write_record()
            if approval:
                argv += ["--approval", approval]
            argv.append("--execute")
        return argv + list(extra)

    def run_upload(self, execute=False, env=None, **kwargs):
        environment = {"FAKE_S3_DIR": self.s3}
        environment.update(env or {})
        return self.run_script("upload-emr-artifacts.sh", *self.args(execute=execute, **kwargs), **environment)

    def aws_calls(self, op=None):
        calls = [args for _n, args in self.calls("aws")]
        return [a for a in calls if op is None or a.startswith("s3api %s" % op) or a.startswith(op)]

    def manifest(self, rel=MANIFEST_REL):
        with open(os.path.join(self.repo, rel), encoding="utf-8") as handle:
            return json.load(handle)


class DryRunTests(EmrBase):
    def test_the_dry_run_plans_every_file_with_key_bytes_and_sha256_and_calls_no_aws(self):
        result = self.run_upload()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.calls("aws"), [], "a dry run makes no aws call at all")
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)), "a dry run writes no manifest")
        self.assertEqual(len(self.expected), 20)
        for key, data in self.expected.items():
            self.assertIn("key=%s bytes=%d sha256=%s" % (key, len(data), sha256_bytes(data)), result.stdout)
        self.assertEqual(len(re.findall(r"^UPLOAD-FILE: ", result.stdout, re.M)), 20)
        self.assertIn("EMR-UPLOAD: run=%s files=20 bytes=%d datasets=2" % (PREFIX, sum(len(d) for d in self.expected.values())), result.stdout)
        self.assertTrue(result.result_line().startswith("RESULT: PASS dry run: 20 file(s) planned under %s/; nothing was uploaded" % ROOT), result.result_line())

    def test_every_key_is_inside_emr_run_prefix_and_the_hidden_file_is_skipped(self):
        result = self.run_upload()
        keys = re.findall(r" key=(\S+) ", result.stdout)
        self.assertEqual(sorted(keys), sorted(self.expected))
        for key in keys:
            self.assertTrue(key.startswith(ROOT + "/"), key)
        self.assertNotIn(".DS_Store", result.stdout.replace("skipped_hidden", ""))
        self.assertIn("EMR-INPUT-DATASET: label=small files=4 bytes=", result.stdout)
        self.assertIn("skipped_hidden=1", result.stdout)

    def test_the_plan_hash_and_the_approval_lines_are_printed_for_the_human(self):
        result = self.run_upload()
        digest = plan_hash(self.expected)
        self.assertIn("PLAN-SHA256: %s" % digest, result.stdout)
        for line in ("APPROVAL-LINE: APPROVED_ACTION=upload-emr-artifacts", "APPROVAL-LINE: APPROVED_PLAN_SHA256=%s" % digest,
                     "APPROVAL-LINE: APPROVED_ACCOUNT_SHA256=%s" % account_hash(), "APPROVAL-LINE: APPROVED_REGION=us-east-2"):
            self.assertIn(line, result.stdout)

    def test_the_values_to_copy_next_are_printed_with_the_step_destinations_and_input_prefixes(self):
        result = self.run_upload()
        spark = self.jar_data["spark-job-jar"]
        self.assertIn("EMR-CONFIG: bootstrap_uri=s3://scholarchain-course-<acct>-artifacts/%s/bin/bootstrap.sh bootstrap_sha256=%s" % (ROOT, sha256_bytes(BOOTSTRAP)), result.stdout)
        self.assertIn("job_jar_uri=s3://scholarchain-course-<acct>-artifacts/%s/jars/spark-job.jar job_jar_sha256=%s" % (ROOT, sha256_bytes(spark)), result.stdout)
        for name, data in self.step_data.items():
            self.assertIn("EMR-CONFIG: extra_artifact uri=s3://scholarchain-course-<acct>-artifacts/%s/steps/%s sha256=%s dest=/opt/scholarchain-spike/bin/%s" % (ROOT, name, sha256_bytes(data), name), result.stdout)
        for label in DATASETS:
            self.assertIn("input-prefix label=%s uri=s3://scholarchain-course-<acct>-artifacts/%s/input/%s files=4" % (label, ROOT, label), result.stdout)
        self.assertNotIn(FAKE_ACCOUNT, result.out, "the account in the bucket name is shown as <acct>")

    def test_the_dry_run_prints_the_sha256_values_in_the_names_render_manifests_py_takes(self):
        """experiments/scripts/render_manifests.py --sha NAME=HEX with NAME in hadoop-submit-jar, hadoop-libjars, er-jar, job-jar, er-policy,
        er-config, spark-config-template: the jar roles map to those names (hadoop-dependency-bundle is hadoop-libjars, the ER job JAR is er-jar,
        the Spark job JAR is job-jar)."""
        result = self.run_upload()
        expected = {
            "hadoop-submit-jar": self.jar_data["hadoop-submit-jar"], "hadoop-libjars": self.jar_data["hadoop-dependency-bundle"],
            "er-jar": self.jar_data["entity-resolution-job-jar"], "job-jar": self.jar_data["spark-job-jar"],
            "er-policy": b'{"policy": 1}\n', "er-config": b'{"er": 2}\n', "spark-config-template": b'{"spark": 3}\n',
        }
        found = dict(re.findall(r"^EMR-RENDER: --sha (\S+)=([0-9a-f]{64})", result.stdout, re.M))
        self.assertEqual(found, {name: sha256_bytes(data) for name, data in expected.items()})
        self.assertIn("output prefix", result.stdout)
        self.assertIn("pipeline/%s/15a/size-N" % PREFIX, result.stdout)

    def test_the_dry_run_prints_the_commands_execute_would_run_with_the_checksum_and_conditional_write(self):
        result = self.run_upload()
        put = [line for line in result.stdout.splitlines() if line.startswith("DRY-RUN CMD:") and "put-object" in line]
        self.assertEqual(len(put), 1)
        for needle in ("--checksum-algorithm SHA256", "--checksum-sha256", "--if-none-match", "--bucket", "<acct>"):
            self.assertIn(needle, put[0])
        self.assertIn("get-object-attributes", result.stdout)
        self.assertIn("head-object", result.stdout)

    def test_the_dry_run_needs_neither_profile_nor_role_nor_approval(self):
        result = self.run_upload(profile=None, role=None, approval=None)
        self.assertEqual(result.rc, 0, result.out)

    def test_the_dry_run_checks_an_approval_record_when_one_is_given(self):
        good = self.run_upload(extra=["--approval", self.write_record()])
        self.assertEqual(good.rc, 0, good.out)
        self.assertIn("APPROVAL-OK: action=upload-emr-artifacts", good.stdout)
        bad = self.run_upload(extra=["--approval", self.write_record(self.approval_text(plan_sha="0" * 64))])
        self.assertEqual(bad.rc, 3, bad.out)

    def test_help_documents_the_layout_the_approval_record_the_refusals_and_the_exit_codes(self):
        result = self.run_script("upload-emr-artifacts.sh", "--help")
        self.assertEqual(result.rc, 0)
        for needle in ("emr/<run-prefix>/", "APPROVED_PLAN_SHA256", "Dry run (default)", "--principal-role", "must exist", "never overwritten", "emr-step-programs.json",
                       "--if-none-match", "PIPELINE_MAX_INPUT_BYTES", "Usage errors (exit 2", "Refusals (exit 3", "NOT uploaded here", "G5"):
            self.assertIn(needle, result.stdout)
        self.assertNotRegex(result.stdout, r"\b\d{12}\b")
        usage_part = result.stdout.split("Usage errors (exit 2", 1)[1].split("Refusals (exit 3", 1)[0]
        self.assertIn("^run-[a-z0-9][a-z0-9-]{1,27}$", usage_part, "a bad run prefix is a usage error (exit 2), and the help says so")


class UsageTests(EmrBase):
    def test_a_missing_or_invalid_run_prefix_is_a_usage_error(self):
        for prefix in ("", "pipeline", "run-", "run-a", "RUN-20261115", "run-../x", "run-20261115/", "run-" + "a" * 40):
            with self.subTest(prefix=prefix):
                argv = ["--artifacts-bucket", BUCKET, "--region", "us-east-2"] + self.dataset_args()
                if prefix:
                    argv += ["--run-prefix", prefix]
                result = self.run_script("upload-emr-artifacts.sh", *argv, FAKE_S3_DIR=self.s3)
                self.assertEqual(result.rc, 2, result.out)
                self.assertIn("RESULT: REFUSED step=usage", result.stdout)
        self.assertEqual(self.calls("aws"), [])

    def test_a_bucket_that_is_not_the_artifacts_bucket_is_a_usage_error(self):
        for bucket in ("", "scholarchain-course-%s-curated" % FAKE_ACCOUNT, "scholarchain-course-artifacts", "other-%s-artifacts" % FAKE_ACCOUNT, "scholarchain-course-12345-artifacts"):
            with self.subTest(bucket=bucket):
                result = self.run_script("upload-emr-artifacts.sh", "--artifacts-bucket", bucket, "--run-prefix", PREFIX, "--region", "us-east-2", *self.dataset_args())
                self.assertEqual(result.rc, 2, result.out)

    def test_no_input_dataset_is_a_usage_error(self):
        result = self.run_script("upload-emr-artifacts.sh", "--artifacts-bucket", BUCKET, "--run-prefix", PREFIX, "--region", "us-east-2")
        self.assertEqual(result.rc, 2, result.out)

    def test_execute_needs_a_profile_a_principal_role_and_an_approval_option(self):
        for kwargs, needle in (({"profile": None}, "--profile"), ({"role": None}, "--principal-role"), ({"approval": None}, "--approval")):
            with self.subTest(needle):
                result = self.run_upload(execute=True, env={"AWS_PROFILE": None}, **kwargs)
                self.assertEqual(result.rc, 2, result.out)
                self.assertIn("--execute needs %s" % needle, result.out)
        self.assertEqual(self.aws_calls(), [])

    def test_a_malformed_principal_role_is_a_usage_error(self):
        for role in ("Operator", "a", "role/x", "x" * 50):
            with self.subTest(role=role):
                self.assertEqual(self.run_upload(execute=True, role=role).rc, 2)

    def test_an_unknown_option_and_a_missing_value_are_usage_errors(self):
        self.assertEqual(self.run_script("upload-emr-artifacts.sh", "--nope").rc, 2)
        self.assertEqual(self.run_script("upload-emr-artifacts.sh", "--run-prefix").rc, 2)


class ApprovalRecordTests(EmrBase):
    """The record is the human gate: nothing is uploaded, and no aws command runs, without a matching one."""

    def refused(self, record, **kwargs):
        result = self.run_upload(execute=True, approval=record, **kwargs)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.calls("aws"), [], "an approval refusal happens before any aws call")
        self.assertEqual(self.stored_keys(), [])
        return result

    def test_a_missing_approval_record_is_refused_before_anything_else(self):
        result = self.refused(os.path.join(self.tmp, "no-such-record.md"))
        self.assertIn("the approval record does not exist", result.out)
        self.assertIn("approval-record", result.steps())
        self.assertNotIn("artifact-scan", result.steps(), "the cheapest refusal comes first, before even the local scan")

    def test_an_approval_record_that_is_a_link_is_refused(self):
        real = self.write_record(name="real.md")
        link = os.path.join(self.tmp, "link.md")
        os.symlink(real, link)
        self.refused(link)

    def test_a_directory_is_not_an_approval_record(self):
        self.refused(self.tmp)

    def test_a_record_for_another_plan_is_refused(self):
        result = self.refused(self.write_record(self.approval_text(plan_sha="f" * 64)))
        self.assertIn("APPROVED_PLAN_SHA256 does not match", result.out)

    def test_a_record_for_another_account_or_region_is_refused(self):
        self.assertIn("APPROVED_ACCOUNT_SHA256 does not match", self.refused(self.write_record(self.approval_text(account=OTHER_ACCOUNT))).out)
        self.assertIn("APPROVED_REGION does not match", self.refused(self.write_record(self.approval_text(region="us-west-2"))).out)

    def test_a_record_with_another_action_a_missing_a_duplicate_or_an_unknown_key_is_refused(self):
        self.assertIn("APPROVED_ACTION", self.refused(self.write_record(self.approval_text(action="run-bounded-pipeline"))).out)
        for key in ("APPROVED_ACTION", "APPROVED_PLAN_SHA256", "APPROVED_ACCOUNT_SHA256", "APPROVED_REGION"):
            with self.subTest(omit=key):
                self.assertIn("missing %s" % key, self.refused(self.write_record(self.approval_text(omit=(key,)))).out)
        dup = self.refused(self.write_record(self.approval_text(extra="APPROVED_REGION=us-east-2\n")))
        self.assertIn("duplicate APPROVED_REGION", dup.out)
        unknown = self.refused(self.write_record(self.approval_text(extra="APPROVED_PLAN_SHA265=%s\n" % ("a" * 64))))
        self.assertIn("unknown key APPROVED_PLAN_SHA265", unknown.out)

    def test_a_malformed_line_is_refused_not_skipped(self):
        digest = plan_hash(self.expected)
        for label, line in (("quoted", 'APPROVED_PLAN_SHA256="%s"' % digest), ("indented", "  APPROVED_PLAN_SHA256=%s" % digest),
                            ("spaced", "APPROVED_PLAN_SHA256 = %s" % digest), ("uppercase", "APPROVED_PLAN_SHA256=%s" % digest.upper()), ("short", "APPROVED_PLAN_SHA256=%s" % digest[:63])):
            with self.subTest(label):
                text = self.approval_text(omit=("APPROVED_PLAN_SHA256",), extra=line + "\n")
                self.refused(self.write_record(text))
        crlf = self.approval_text().replace("\n", "\r\n")
        self.refused(self.write_record(crlf))

    def test_a_matching_record_is_accepted_and_prose_around_it_is_ignored(self):
        text = "# Human gate\n\nI reviewed the dry run.\n" + self.approval_text() + "\nThanks.\n"
        result = self.run_upload(execute=True, approval=self.write_record(text))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("APPROVAL-OK: action=upload-emr-artifacts plan_sha256=%s" % plan_hash(self.expected), result.stdout)

    def test_a_changed_file_changes_the_plan_hash_so_the_old_record_no_longer_matches(self):
        old = self.write_record()
        self.write_bytes("scripts/emr/bootstrap.sh", BOOTSTRAP + b"# edited after approval\n")
        result = self.refused(old)
        self.assertIn("APPROVED_PLAN_SHA256 does not match", result.out)


class ScanRefusalTests(EmrBase):
    def refused(self, rc=3, execute=False, **kwargs):
        result = self.run_upload(execute=execute, **kwargs)
        self.assertEqual(result.rc, rc, result.out)
        self.assertEqual(self.calls("aws"), [], "a refusal happens before any aws call")
        self.assertEqual(self.stored_keys(), [])
        return result

    def test_a_step_program_that_differs_from_the_terraform_pin_is_refused(self):
        self.write_bytes("scripts/emr/sc-step.sh", b"# edited, not re-pinned\n")
        result = self.refused()
        self.assertIn("STEP-PROGRAM-DRIFT: sc-step.sh", result.stdout)

    def test_a_missing_step_program_is_refused(self):
        os.remove(os.path.join(self.repo, "scripts/emr/sc-ceiling-check.py"))
        self.assertIn("step program sc-ceiling-check.py is missing", self.refused().stdout)

    def test_a_pin_that_does_not_list_exactly_four_programs_is_refused(self):
        self.write("infra/terraform/emr-step-programs.json", json.dumps({"bin_dir": "/opt/scholarchain-spike/bin", "programs": {"sc-step.sh": sha256_bytes(self.step_data["sc-step.sh"])}}))
        self.assertIn("exactly four programs", self.refused().stdout)

    def test_a_job_jar_that_differs_from_the_artifact_manifest_is_refused(self):
        self.write_bytes("target/spark-job-jar/spark-job-jar.jar", b"rebuilt after the manifest")
        result = self.refused()
        self.assertIn("artifact spark-job-jar differs from the manifest", result.stdout)

    def test_a_missing_job_jar_is_refused(self):
        os.remove(os.path.join(self.repo, "target/hadoop-submit-jar/hadoop-submit-jar.jar"))
        self.assertIn("artifact hadoop-submit-jar is missing locally", self.refused().stdout)

    def test_a_manifest_without_the_four_roles_is_refused(self):
        self.write_artifact_manifest(roles=ROLES[:3])
        self.assertIn("must hold exactly the roles", self.refused().stdout)

    def test_a_manifest_with_another_schema_or_no_file_is_refused(self):
        self.write_artifact_manifest(schema="something.else")
        self.assertIn("does not carry the schema", self.refused().stdout)
        os.remove(os.path.join(self.repo, "target/emr-artifacts/emr-artifact-manifest.json"))
        self.assertIn("missing or not valid JSON", self.refused().stdout)

    def test_a_manifest_path_that_leaves_the_repository_is_refused(self):
        for rel in ("../outside.jar", "/etc/hosts"):
            with self.subTest(rel=rel):
                self.write_artifact_manifest(path_for=lambda role, rel=rel: rel if role == "spark-job-jar" else "target/%s/%s.jar" % (role, role))
                self.assertIn("unsafe path", self.refused().stdout)

    def test_a_symbolic_link_bootstrap_is_never_uploaded(self):
        target = os.path.join(self.tmp, "elsewhere.sh")
        with open(target, "wb") as handle:
            handle.write(BOOTSTRAP)
        os.remove(os.path.join(self.repo, "scripts/emr/bootstrap.sh"))
        os.symlink(target, os.path.join(self.repo, "scripts/emr/bootstrap.sh"))
        self.assertIn("symbolic link", self.refused().stdout)

    def test_a_dataset_without_one_of_the_four_sample_files_is_refused(self):
        os.remove(os.path.join(self.datasets["small"], "datasets/samples/orcid/records.jsonl"))
        result = self.refused()
        self.assertIn("input dataset small lacks datasets/samples/orcid/records.jsonl", result.stdout)

    def test_a_dataset_above_the_pipeline_input_ceiling_is_refused(self):
        self.use_config(PIPELINE_MAX_INPUT_BYTES="100")
        result = self.refused()
        self.assertIn("PIPELINE_MAX_INPUT_BYTES", result.stdout)

    def test_a_dataset_at_exactly_the_ceiling_is_accepted(self):
        total = sum(len(d) for k, d in self.expected.items() if "/input/small/" in k)
        self.use_config(PIPELINE_MAX_INPUT_BYTES=str(total))
        self.assertEqual(self.run_upload(labels=("small",)).rc, 0)
        self.use_config(PIPELINE_MAX_INPUT_BYTES=str(total - 1))
        self.assertEqual(self.run_upload(labels=("small",)).rc, 3)

    def test_a_symbolic_link_inside_a_dataset_is_refused(self):
        target = os.path.join(self.tmp, "outside.jsonl")
        with open(target, "wb") as handle:
            handle.write(b"x")
        os.symlink(target, os.path.join(self.datasets["small"], "datasets/samples/openalex/extra.jsonl"))
        self.assertIn("symbolic link", self.refused().stdout)

    def test_a_symlinked_datasets_directory_is_refused(self):
        real = os.path.join(self.tmp, "real-datasets")
        os.rename(os.path.join(self.datasets["medium"], "datasets"), real)
        os.symlink(real, os.path.join(self.datasets["medium"], "datasets"))
        self.assertIn("not a real directory", self.refused().stdout)

    def test_dataset_labels_must_be_valid_unique_and_at_most_three(self):
        for spec, needle in ((("Bad_Label", "small"), "LABEL matching"), (("small", "small"), "used twice")):
            with self.subTest(spec=spec):
                argv = ["--artifacts-bucket", BUCKET, "--run-prefix", PREFIX, "--region", "us-east-2"]
                argv += ["--input-dataset", "%s=%s" % (spec[0], self.datasets["small"]), "--input-dataset", "%s=%s" % (spec[1], self.datasets["medium"])]
                result = self.run_script("upload-emr-artifacts.sh", *argv, FAKE_S3_DIR=self.s3)
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn(needle, result.stdout)
        self.datasets["third"] = self.make_dataset("third")
        self.datasets["fourth"] = self.make_dataset("fourth")
        result = self.run_upload(labels=("small", "medium", "third", "fourth"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("at most 3 input datasets", result.stdout)
        self.assertEqual(self.run_upload(labels=("small", "medium", "third")).rc, 0)

    def test_a_missing_or_linked_config_file_is_refused_and_the_config_keys_are_fixed_names(self):
        result = self.run_upload(extra=["--er-policy", os.path.join(self.tmp, "nope.json")])
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("--er-policy file nope.json does not exist", result.stdout)
        link = os.path.join(self.tmp, "link.json")
        os.symlink(self.config_files["--er-config"], link)
        self.assertIn("symbolic link", self.run_upload(configs=False, extra=["--er-config", link]).stdout)
        # whatever the local file names are, the object names are the three fixed ones the experiment manifests refer to
        keys = re.findall(r" key=(\S+) ", self.run_upload().stdout)
        self.assertEqual(sorted(k for k in keys if "/config/" in k), [ROOT + "/config/er-config.json", ROOT + "/config/er-policy.json", ROOT + "/config/spark-config-template.json"])

    def test_the_config_files_are_optional_each(self):
        result = self.run_upload(configs=False, extra=["--er-policy", self.config_files["--er-policy"]])
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(re.findall(r"^UPLOAD-FILE: ", result.stdout, re.M)), 18, "20 minus the two config files that were not named")

    def test_the_job_jars_get_the_fixed_object_names_the_experiment_manifests_use(self):
        keys = re.findall(r" key=(\S+) ", self.run_upload().stdout)
        for name in ("hadoop-submit.jar", "hadoop-bundle.jar", "entity-resolution.jar", "spark-job.jar"):
            self.assertIn("%s/jars/%s" % (ROOT, name), keys)
        self.assertEqual(len([k for k in keys if "/jars/" in k]), 4)
        self.assertIn(ROOT + "/bin/bootstrap.sh", keys)

    def test_a_manifest_output_outside_target_or_already_existing_is_refused_before_any_aws_call(self):
        for out in (os.path.join(self.tmp, "elsewhere.json"), os.path.join(self.repo, "docs", "m.json")):
            with self.subTest(out=out):
                self.assertEqual(self.run_upload(execute=True, extra=["--manifest-out", out]).rc, 3)
        path = os.path.join(self.repo, MANIFEST_REL)
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("earlier evidence")
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 3, result.out)
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "earlier evidence")
        self.assertEqual(self.calls("aws"), [])


class ExecuteTests(EmrBase):
    def test_execute_uploads_every_file_with_its_checksum_a_conditional_write_and_verifies_each(self):
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.stored_keys(), sorted(self.expected))
        for key, data in self.expected.items():
            self.assertEqual(self.stored(key), data, key)
        puts = self.aws_calls("put-object")
        self.assertEqual(len(puts), 20)
        for call in puts:
            self.assertIn("--checksum-algorithm SHA256", call)
            self.assertIn("--if-none-match", call)
            self.assertIn("--checksum-sha256", call)
        self.assertEqual(len(self.aws_calls("head-object")), 20, "every stored object is verified")
        self.assertEqual(len(self.aws_calls("list-objects-v2")), 1)
        self.assertEqual(len(self.aws_calls("get-object-attributes")), 0, "nothing existed, so nothing is compared")
        self.assertIn("RESULT: PASS 20 file(s) verified under %s/ (20 uploaded, 0 unchanged)" % ROOT, result.result_line())

    def test_the_manifest_records_key_class_bytes_sha256_and_version_for_every_file(self):
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        document = self.manifest()
        self.assertEqual(document["schema"], "scholarchain.emr-upload-manifest.v1")
        self.assertEqual((document["run_prefix"], document["root_prefix"], document["region"]), (PREFIX, ROOT, "us-east-2"))
        self.assertEqual(document["plan_sha256"], plan_hash(self.expected))
        self.assertEqual(document["bucket"], "scholarchain-course-<acct>-artifacts")
        self.assertEqual(document["totals"], {"files": 20, "bytes": sum(len(d) for d in self.expected.values()), "uploaded": 20, "unchanged": 0})
        by_key = {f["key"]: f for f in document["files"]}
        self.assertEqual(sorted(by_key), sorted(self.expected))
        for key, data in self.expected.items():
            self.assertEqual((by_key[key]["bytes"], by_key[key]["sha256"], by_key[key]["status"]), (len(data), sha256_bytes(data), "uploaded"))
            self.assertTrue(by_key[key]["version_id"])
        self.assertEqual({f["class"] for f in document["files"]} - {"input:small", "input:medium"}, {"bootstrap", "step-program", "config:er-policy.json", "config:er-config.json", "config:spark-config-template.json"} | {"jar:" + r for r in ROLES})
        self.assertEqual([d["label"] for d in document["datasets"]], ["small", "medium"])
        self.assertNotIn(FAKE_ACCOUNT, json.dumps(document))
        self.assertEqual(oct(os.stat(os.path.join(self.repo, MANIFEST_REL)).st_mode & 0o777), "0o600")

    def test_a_rerun_uploads_nothing_new_and_marks_every_file_unchanged(self):
        self.assertEqual(self.run_upload(execute=True).rc, 0)
        before = len(self.aws_calls("put-object"))
        second_out = os.path.join(self.repo, "target", "second-manifest.json")
        result = self.run_upload(execute=True, extra=["--manifest-out", second_out])
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(self.aws_calls("put-object")), before, "no further put-object")
        self.assertIn("(0 uploaded, 20 unchanged)", result.result_line())
        self.assertEqual(self.manifest(os.path.join("target", "second-manifest.json"))["totals"]["unchanged"], 20)

    def test_the_approval_record_is_checked_before_the_first_aws_call(self):
        result = self.run_upload(execute=True, approval=self.write_record(self.approval_text(plan_sha="1" * 64)))
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.calls("aws"), [])

    def test_an_existing_object_with_different_content_refuses_before_any_upload_and_is_not_overwritten(self):
        key = ROOT + "/bin/bootstrap.sh"
        self.seed(key, b"someone else's bytes")
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.aws_calls("put-object"), [])
        self.assertEqual(self.stored(key), b"someone else's bytes")
        self.assertEqual(self.stored_keys(), [key])

    def test_an_existing_object_without_a_sha256_checksum_cannot_be_proven_equal(self):
        key = ROOT + "/bin/bootstrap.sh"
        self.seed(key, BOOTSTRAP, checksum=None)
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_an_existing_object_of_the_same_size_but_another_sha256_is_a_conflict(self):
        key = ROOT + "/steps/sc-step.sh"
        self.seed(key, b"x" * len(self.step_data["sc-step.sh"]))
        self.assertEqual(self.run_upload(execute=True).rc, 3)

    def test_an_identical_existing_object_is_unchanged_and_the_rest_is_uploaded(self):
        key = ROOT + "/bin/bootstrap.sh"
        self.seed(key, BOOTSTRAP)
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("UNCHANGED: %s" % key, result.stdout)
        self.assertEqual(len(self.aws_calls("put-object")), 19)
        self.assertIn("(19 uploaded, 1 unchanged)", result.result_line())

    def test_only_emr_run_prefix_is_written(self):
        self.seed("other/keep.txt", b"keep")
        self.assertEqual(self.run_upload(execute=True).rc, 0)
        self.assertEqual(self.stored("other/keep.txt"), b"keep")
        written = [k for k in self.stored_keys() if k != "other/keep.txt"]
        self.assertTrue(all(k.startswith(ROOT + "/") for k in written), written)

    def test_a_caller_that_is_not_the_named_principal_role_is_refused(self):
        for arn in ("arn:aws:sts::%s:assumed-role/scholarchain-course-operator-reader/s" % FAKE_ACCOUNT, "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-loader-extra/s" % FAKE_ACCOUNT,
                    "arn:aws:iam::%s:user/someone" % FAKE_ACCOUNT, "arn:aws:sts::%s:assumed-role/scholarchain-other-operator-loader/s" % FAKE_ACCOUNT):
            with self.subTest(arn=arn):
                result = self.run_upload(execute=True, env={"FAKE_STS_ARN": arn})
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(self.aws_calls("put-object"), [])
        self.assertEqual(self.stored_keys(), [])

    def test_the_principal_role_is_a_parameter_not_a_constant(self):
        arn = "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-pipeline/session" % FAKE_ACCOUNT
        self.assertEqual(self.run_upload(execute=True, role="operator-loader", env={"FAKE_STS_ARN": arn}).rc, 3)
        result = self.run_upload(execute=True, role="operator-pipeline", env={"FAKE_STS_ARN": arn})
        self.assertEqual(result.rc, 0, result.out)

    def test_a_bucket_of_another_account_than_the_profile_is_refused(self):
        result = self.run_upload(execute=True, env={"FAKE_ACCOUNT_ID": OTHER_ACCOUNT}, approval=self.write_record())
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_a_stored_object_whose_checksum_differs_fails_verification_and_writes_no_manifest(self):
        result = self.run_upload(execute=True, env={"FAKE_S3_CORRUPT_KEY": ROOT + "/steps/sc-step.sh"})
        self.assertEqual(result.rc, 4, result.out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))

    def test_a_failed_put_exits_5_without_a_manifest_and_a_rerun_completes_the_rest(self):
        failing = ROOT + "/jars/spark-job.jar"
        result = self.run_upload(execute=True, env={"FAKE_S3_PUT_FAIL_KEY": failing})
        self.assertEqual(result.rc, 5, result.out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, MANIFEST_REL)))
        self.assertNotIn(failing, self.stored_keys())
        again = self.run_upload(execute=True)
        self.assertEqual(again.rc, 0, again.out)
        self.assertEqual(self.stored_keys(), sorted(self.expected))
        self.assertIn("uploaded,", again.result_line())
        self.assertNotIn("(20 uploaded", again.result_line())

    def test_an_aws_cli_without_conditional_writes_fails_closed(self):
        result = self.run_upload(execute=True, env={"FAKE_S3_NO_IF_NONE_MATCH": "1"})
        self.assertEqual(result.rc, 5, result.out)
        self.assertEqual(self.stored_keys(), [])

    def test_a_failing_listing_uploads_nothing(self):
        result = self.run_upload(execute=True, env={"FAKE_S3_LIST_RC": "255"})
        self.assertEqual(result.rc, 5, result.out)
        self.assertEqual(self.aws_calls("put-object"), [])

    def test_no_secret_or_raw_account_id_reaches_the_output(self):
        result = self.run_upload(execute=True)
        self.assertEqual(result.rc, 0, result.out)
        self.assertNotIn(FAKE_ACCOUNT, result.out)
        self.assertNotIn("FAKE/SECRET", result.out)


class UnitTests(unittest.TestCase):
    def test_plan_hash_is_over_the_sorted_key_bytes_sha256_lines(self):
        files = [{"key": "emr/run-ab/b", "bytes": 2, "sha256": "b" * 64}, {"key": "emr/run-ab/a", "bytes": 1, "sha256": "a" * 64}]
        expected = hashlib.sha256(("emr/run-ab/a\t1\t%s\nemr/run-ab/b\t2\t%s\n" % ("a" * 64, "b" * 64)).encode()).hexdigest()
        self.assertEqual(upload_emr_artifacts.plan_hash(files), expected)
        self.assertEqual(upload_emr_artifacts.plan_hash(list(reversed(files))), expected)

    def test_a_different_byte_count_or_key_changes_the_plan_hash(self):
        base = [{"key": "emr/run-ab/a", "bytes": 1, "sha256": "a" * 64}]
        self.assertNotEqual(upload_emr_artifacts.plan_hash(base), upload_emr_artifacts.plan_hash([{"key": "emr/run-ab/a", "bytes": 2, "sha256": "a" * 64}]))
        self.assertNotEqual(upload_emr_artifacts.plan_hash(base), upload_emr_artifacts.plan_hash([{"key": "emr/run-ab/b", "bytes": 1, "sha256": "a" * 64}]))
        self.assertNotEqual(upload_emr_artifacts.plan_hash(base), upload_emr_artifacts.plan_hash([{"key": "emr/run-ab/a", "bytes": 1, "sha256": "b" * 64}]))


if __name__ == "__main__":
    unittest.main()
