"""Cross-script safety: no secret or raw account ID in output, STEP and RESULT markers, helper-wrapped cloud calls."""
import os
import re
import unittest

from helpers import FAKE_ACCOUNT, FAKE_PASSWORD, FAKE_SECRET, FAKE_TOKEN, REGION, SERVICES, Fixture, account_hash, head_object_text, registry_digest, sha256_bytes

ARCHIVE_BYTES = b"tiny-runtime-archive"
FORBIDDEN = (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, FAKE_PASSWORD, "AKIAFAKEFAKEFAKEFAKE")
PRIOR = "c" * 40
PRIVATE_CANARY = "CANARY-SAFETY-PRIVATE-VALUE-9931"


class SafetyTests(Fixture):
    def setUp(self):
        super().setUp()
        self.private_vars = os.path.join(self.tmp, "p.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write('aws_account_id = "%s"\nnotification_email = "%s"\n' % (FAKE_ACCOUNT, PRIVATE_CANARY))
        self.plan, self.plan_sha = self.make_plan()
        self.write_plan_receipt(self.plan, self.plan_sha, image_revision=self.head())
        self.prespend, self.prespend_sha = self.write_prespend()
        self.approval = self.write_approval(self.approval_text(self.plan_sha, prespend_sha=self.prespend_sha, stage="runtime-apply", receipt_sha=self.receipt_sha(self.plan)))
        self.push_approval = self.write_approval(self.approval_text(prespend_sha=self.prespend_sha, stage="push"), name="push-gate.md")
        self.write_release_manifest()
        self.write_push_record()
        self.previous = self.write_deploy_manifest(revision=PRIOR, digests={s: registry_digest(s, PRIOR) for s in SERVICES})
        self.archive = os.path.join(self.tmp, "a.tgz")
        with open(self.archive, "wb") as handle:
            handle.write(ARCHIVE_BYTES)
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)), RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE_BYTES))
        self.runtime_show = self.write_show_json([("aws_s3_bucket.a", "aws_s3_bucket", ["create"])], image_revision=self.head(), name="runtime-show.json")
        self.base_show = self.write_show_json([("aws_s3_bucket.a", "aws_s3_bucket", ["create"])], name="base-show.json")
        self.env_all = {
            "SCHOLARCHAIN_TF_PRIVATE_VARS": self.private_vars,
            "FAKE_SHOW_JSON": self.runtime_show,
            "FAKE_STATE_LIST": "aws_s3_bucket.a;module.runtime.aws_ecs_service.service[\"query-api\"]",
            "FAKE_TAG_JSON": '{"ResourceTagMappingList": [{"ResourceARN": "arn:aws:s3:::scholarchain-course-%s-a"}]}' % FAKE_ACCOUNT,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI": "s3://bucket-test/key/a.tgz",
            "FAKE_HEAD_OBJECT": head_object_text(ARCHIVE_BYTES),
            "FAKE_ECS_TAG": self.head(),
            "FAKE_EMIT": "diagnostic mentioning %s and %s" % (FAKE_ACCOUNT, PRIVATE_CANARY),
        }

    def deploy_args(self, stage="runtime-apply", approval=None):
        args = ["--stage", stage, "--region", REGION, "--approval", approval or self.approval, "--prespend", self.prespend]
        return args if stage == "push" else args + ["--plan", self.plan]

    def scenarios(self):
        deploy = self.deploy_args()
        plan_env = {"FAKE_SHOW_JSON": self.base_show}
        return {
            "check constitution": ("check.sh", ["--only", "constitution"], {}),
            "package": ("package.sh", [], {}),
            "plan dry": ("plan.sh", ["--env", "course", "--region", REGION], {}),
            "plan execute": ("plan.sh", ["--env", "course", "--region", REGION, "--profile", "p", "--execute"], plan_env),
            "deploy dry": ("deploy.sh", deploy, {}),
            "deploy execute": ("deploy.sh", deploy + ["--profile", "p", "--execute"], {}),
            "deploy push execute": ("deploy.sh", self.deploy_args("push", self.push_approval) + ["--profile", "p", "--execute"], {}),
            "rollback dry": ("rollback.sh", ["--env", "course", "--region", REGION, "--previous-manifest", self.previous], {}),
            "rollback execute plan": ("rollback.sh", ["--env", "course", "--region", REGION, "--previous-manifest", self.previous, "--profile", "p", "--stage", "plan", "--execute"], {"FAKE_SHOW_JSON": self.write_show_json([], image_revision=PRIOR, name="prior-show.json")}),
            "cleanup dry": ("cleanup.sh", ["--env", "course", "--region", REGION], {}),
            "cleanup execute": ("cleanup.sh", ["--env", "course", "--region", REGION, "--profile", "p", "--execute"], {}),
        }

    def run_scenario(self, script, args, extra):
        env = dict(self.env_all)
        env.update(extra)
        return self.run_script(script, *args, **env)

    def test_no_secret_or_account_id_in_any_output_and_every_run_has_steps_and_one_result(self):
        for label, (script, args, extra) in self.scenarios().items():
            with self.subTest(label):
                result = self.run_scenario(script, args, extra)
                for forbidden in FORBIDDEN + (PRIVATE_CANARY,):
                    self.assertNotIn(forbidden, result.out, "%s leaked %r" % (label, forbidden[:8]))
                self.assertNotIn(self.private_vars, result.out)
                self.assertGreaterEqual(len(result.steps()), 2, label)
                results = [l for l in result.stdout.splitlines() if l.startswith("RESULT: ")]
                self.assertEqual(len(results), 1, "%s must print exactly one RESULT line: %s" % (label, results))
                self.assertRegex(results[0], r"^RESULT: (PASS|FAIL|DRY-RUN|REFUSED|PARTIAL)\b")
                self.assertEqual(result.stdout.splitlines()[-1], results[0], "RESULT is the final stdout line")

    def test_no_script_artifact_or_retained_log_or_trace_contains_a_raw_account_id_or_secret(self):
        for label, (script, args, extra) in self.scenarios().items():
            self.run_scenario(script, args, extra)
        with open(self.timeout_log) as handle:
            trace = handle.read()
        for forbidden in FORBIDDEN + (PRIVATE_CANARY, self.private_vars):
            self.assertNotIn(forbidden, trace, "the timeout trace must be redacted: %r" % forbidden[:8])
        for base, _dirs, files in os.walk(self.repo):
            if os.sep + ".git" in base:
                continue
            for name in files:
                if name.endswith(".tfplan.json"):
                    continue  # raw `terraform show -json` output: git-ignored, documented as sensitive, never evidence
                path = os.path.join(base, name)
                with open(path, "rb") as handle:
                    data = handle.read()
                for forbidden in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, FAKE_PASSWORD, PRIVATE_CANARY):
                    self.assertNotIn(forbidden.encode(), data, "%s contains %r" % (path, forbidden[:6]))

    def test_stderr_and_stdout_are_free_of_the_account_hash_preimage_even_on_refusals(self):
        # A wrong account is refused without printing either the raw ID or its preimage form.
        approval = self.write_approval(self.approval_text(self.plan_sha, account=account_hash("111122223333"), prespend_sha=self.prespend_sha, receipt_sha=self.receipt_sha(self.plan)), name="other.md")
        result = self.run_script("deploy.sh", *self.deploy_args(approval=approval), "--profile", "p", "--execute", **self.env_all)
        self.assertEqual(result.rc, 3)
        self.assertNotIn(FAKE_ACCOUNT, result.out)
        self.assertNotRegex(result.out, r"(?<![0-9A-Za-z])\d{12}(?![0-9A-Za-z])")

    def test_execute_cloud_calls_are_all_wrapped_by_the_timeout_helper(self):
        for script, args, extra in (
            ("plan.sh", ["--env", "course", "--region", REGION, "--profile", "p", "--execute"], {"FAKE_SHOW_JSON": self.base_show}),
            ("deploy.sh", self.deploy_args() + ["--profile", "p", "--execute"], {}),
            ("cleanup.sh", ["--env", "course", "--region", REGION, "--profile", "p", "--execute"], {}),
        ):
            with self.subTest(script):
                open(self.log, "w").close()
                open(self.timeout_log, "w").close()
                self.run_scenario(script, args, extra)
                cloud = self.calls()
                helper = self.timeout_helper_lines()
                self.assertGreater(len(cloud), 0)
                self.assertEqual(len(helper), len(cloud), "every external command, including the terraform version probe, is recorded by the timeout helper")
                for line in helper:
                    self.assertRegex(line, r"^timeout=\d+ ")

    def test_dry_runs_never_call_cloud_tools(self):
        for label in ("plan dry", "deploy dry", "rollback dry", "cleanup dry"):
            with self.subTest(label):
                open(self.log, "w").close()
                script, args, extra = self.scenarios()[label]
                result = self.run_scenario(script, args, extra)
                self.assertEqual(result.rc, 0, result.out)
                # R8: only the terraform version probe may run (no show, no init, no aws, no docker).
                allowed = [c for c in self.calls() if not (c[0] == "terraform" and c[1].startswith("version"))]
                self.assertEqual(allowed, [], label)
                self.assertEqual(self.calls("aws"), [])
                self.assertEqual(self.calls("docker"), [])
                self.assertEqual(self.mutating_calls(), [])
                self.assertIn("DRY-RUN CMD:", result.stdout)

    def test_every_dry_run_prints_the_commands_it_would_execute(self):
        expectations = {
            "plan dry": ("terraform", "plan -input=false"),
            "deploy dry": ("aws ecs describe-services", "apply -input=false"),
            "rollback dry": ("imageTag=" + PRIOR, "--reuse-images"),
            "cleanup dry": ("state list", "plan -destroy"),
        }
        for label, needles in expectations.items():
            script, args, extra = self.scenarios()[label]
            result = self.run_scenario(script, args, extra)
            for needle in needles:
                self.assertIn(needle, result.stdout, "%s should print %r" % (label, needle))

    def test_account_id_redaction_does_not_mangle_checksums_that_contain_digit_runs(self):
        # A sha256 may contain 12 digits in a row bounded by hex letters; it is not an account ID.
        weird = "a" + "123456789012" + "b" + "c" * 50
        self.assertEqual(len(weird), 64)
        approval = self.write_approval(self.approval_text(weird, prespend_sha=self.prespend_sha, receipt_sha=self.receipt_sha(self.plan)), name="weird.md")
        result = self.run_script("deploy.sh", *self.deploy_args(approval=approval), **self.env_all)
        self.assertEqual(result.rc, 3)
        self.assertIn("APPROVED_PLAN_SHA256 " + weird, result.out)
        self.assertIn(self.plan_sha, result.out)


if __name__ == "__main__":
    unittest.main()
