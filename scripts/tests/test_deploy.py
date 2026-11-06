"""deploy.sh: approval record, pre-spend gate, plan provenance, stages, image verification (fakes only).

Repair round 1: F1 dirty-tree exemption, F2 plan provenance and verified copy, F5 pre-spend gate, F6 image and ECS
verification, F7 stages. Repair round 2: R1 state binding, R3 receipt hash in the approval and the source Terraform
would load, R4 push record, R6 recorded order (push needs no plan), R7 pre-spend re-verification before every paid
operation, R8 dry run defers inspection, R9 the archive copy. Expectations are hand-derived.
"""
import datetime
import glob
import json
import os
import unittest

from helpers import (
    FAKE_ACCOUNT,
    FAKE_PASSWORD,
    FAKE_SECRET,
    FAKE_TOKEN,
    MISSING,
    REGION,
    SERVICES,
    STATE_LINEAGE,
    Fixture,
    account_hash,
    fake_image_id,
    head_object_text,
    registry_digest,
    sha256_bytes,
    utc_hours_ago,
)

ARCHIVE_BYTES = b"tiny-runtime-archive"
ARCHIVE_SHA = sha256_bytes(ARCHIVE_BYTES)
OTHER_ACCOUNT = "999988887777"
PRIOR = "c" * 40
PLAN_STAGES = ("base-apply", "runtime-apply")


def utc_in_hours(hours):
    when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


class DeployBase(Fixture):
    def setUp(self):
        super().setUp()
        self.archive = os.path.join(self.tmp, "runtime.tgz")
        with open(self.archive, "wb") as handle:
            handle.write(ARCHIVE_BYTES)
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)), RUNTIME_ARCHIVE_EXPECTED_SHA256=ARCHIVE_SHA)
        self.arrange("runtime-apply")

    def arrange(self, stage="runtime-apply", reuse_revision=None, plan_content=b"fake-plan-bytes\n"):
        """Write a consistent plan, receipt, planned-variables fixture, pre-spend receipt, push record and approval record.
        A push stage has NO plan, receipt or plan line (the recorded order: base apply, push, runtime plan, runtime apply)."""
        self.stage = stage
        self.revision = None if stage == "base-apply" else (reuse_revision or self.head())
        stale_record = os.path.join(self.repo, "target", "release", self.head(), "push-record.json")
        if os.path.exists(stale_record):
            os.remove(stale_record)  # only a runtime-apply arrangement owns a push record
        if stage == "push":
            self.plan = self.plan_sha = self.receipt = self.receipt_sha_value = None
            self.show = self.write_show_json([], image_revision=self.revision)
        else:
            self.plan, self.plan_sha = self.make_plan(plan_content)
            self.show = self.write_show_json([("aws_s3_bucket.a", "aws_s3_bucket", ["create"])], image_revision=self.revision)
            self.receipt = self.write_plan_receipt(self.plan, self.plan_sha, image_revision=self.revision)
            self.receipt_sha_value = self.receipt_sha(self.plan)
        self.set_prespend()
        if stage in ("push", "runtime-apply") and not reuse_revision:
            self.manifest = self.write_release_manifest()
        if stage == "runtime-apply" and not reuse_revision:
            self.push_record = self.write_push_record()
        self.base_env = {
            "SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI": "s3://bucket-test/key/runtime.tgz",
            "FAKE_HEAD_OBJECT": head_object_text(ARCHIVE_BYTES),
            "FAKE_SHOW_JSON": self.show,
            "FAKE_ECS_TAG": self.revision or "",
        }

    def record_text(self, **kwargs):
        kwargs.setdefault("prespend_sha", self.prespend_sha)
        kwargs.setdefault("stage", self.stage)
        if self.plan:
            kwargs.setdefault("receipt_sha", self.receipt_sha_value)
        return self.approval_text(self.plan_sha, **kwargs)

    def set_prespend(self, **overrides):
        self.prespend, self.prespend_sha = self.write_prespend(**overrides)
        self.set_approval()

    def set_approval(self, **kwargs):
        self.approval = self.write_approval(self.record_text(**kwargs))

    def rewrite_receipt(self, reapprove=True, **overrides):
        """Write a different receipt next to the plan; by default the human 'reviews' it, so the approval names its hash."""
        overrides.setdefault("image_revision", self.revision)
        self.receipt = self.write_plan_receipt(self.plan, self.plan_sha, **overrides)
        self.receipt_sha_value = self.receipt_sha(self.plan)
        if reapprove:
            self.set_approval()

    def args(self, *extra):
        out = ["--stage", self.stage, "--region", REGION, "--approval", self.approval, "--prespend", self.prespend]
        if self.plan:
            out += ["--plan", self.plan]
        return out + list(extra)

    def deploy(self, *extra, **env):
        merged = dict(self.base_env)
        merged.update(env)
        return self.run_script("deploy.sh", *self.args(*extra), **merged)

    def execute(self, *extra, **env):
        return self.deploy("--execute", "--profile", "approved-profile", *extra, **env)

    def assert_refused(self, result, step, code=3):
        self.assertEqual(result.rc, code, result.out)
        self.assertEqual(result.steps()[-1], step, "last STEP should be the failed check: %s" % result.steps())
        self.assertIn("RESULT: REFUSED step=%s" % step, result.stdout)
        self.assertEqual(self.mutating_calls(), [])

    def assert_nothing_ran(self):
        """No docker call, no aws call other than the identity check, no apply, no upload."""
        self.assertEqual(self.calls("docker"), [])
        self.assertEqual([a for _n, a in self.calls("aws") if not a.startswith("sts get-caller-identity")], [])
        self.assertEqual(self.applied(), [])
        self.assertEqual(self.mutating_calls(), [])

    def applied(self):
        path = self.log + ".applied"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def uploads(self):
        path = self.log + ".uploads"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def chdir_lines(self):
        path = self.log + ".chdir"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def terraform_non_version(self):
        return [a for _n, a in self.calls("terraform") if not a.startswith("version")]

    def cloud_calls(self):
        """Every call except the terraform version probe and the read-only init and show of the verified plan copy."""
        return [(n, a) for n, a in self.calls() if not (n == "terraform" and (a.startswith("version") or " show -json " in " " + a + " " or " init " in " " + a + " "))]

    def deploy_manifests(self, stage):
        found = []
        release_dir = os.path.join(self.repo, "target", "release", self.head())
        if os.path.isdir(release_dir):
            for name in os.listdir(release_dir):
                if name.startswith("deploy-manifest-%s-" % stage):
                    with open(os.path.join(release_dir, name)) as handle:
                        found.append(json.load(handle))
        return found


class DeployDirtyTreeTests(DeployBase):
    """F1: only the literal configured approval-record path is exempt, by exact path comparison."""

    def test_dirty_tree_refused_before_anything_else(self):
        self.write("junk.txt", "untracked\n")
        result = self.execute()
        self.assert_refused(result, "clean-tree")
        self.assertNotIn("approval-record", result.steps())
        self.assertEqual(self.calls("aws"), [])
        self.assertEqual(self.calls("docker"), [])

    def test_modified_tracked_file_is_dirty(self):
        self.write("Dockerfile", "# changed\n")
        self.assert_refused(self.execute(), "clean-tree")
        self.assertEqual(self.calls("aws"), [])

    def test_alternate_in_repo_approval_path_makes_the_tree_dirty(self):
        alternate = os.path.join(self.repo, "docs", "alternate-gate.md")
        os.makedirs(os.path.dirname(alternate), exist_ok=True)
        with open(alternate, "w") as handle:
            handle.write(self.record_text())
        result = self.run_script("deploy.sh", *self.args("--execute", "--profile", "p")[:2], *self._with_approval(alternate, "--execute", "--profile", "p"), **self.base_env)
        self.assert_refused(result, "clean-tree")
        self.assertIn("alternate-gate.md", result.out, "the dirty path is named")
        self.assertEqual(self.calls("aws"), [])
        self.assertEqual(self.calls("docker"), [])

    def _with_approval(self, approval, *extra):
        """The arguments of deploy() with another --approval path (the first two --stage arguments are passed separately)."""
        args = self.args(*extra)
        index = args.index("--approval")
        args[index + 1] = approval
        return args[2:]

    def test_ignored_alternate_approval_path_is_not_dirty(self):
        alternate = os.path.join(self.repo, "target", "gate.md")  # target/ is git-ignored in the fixture
        os.makedirs(os.path.dirname(alternate), exist_ok=True)
        with open(alternate, "w") as handle:
            handle.write(self.record_text())
        result = self.run_script("deploy.sh", *self.args()[:2], *self._with_approval(alternate), **self.base_env)
        self.assertEqual(result.rc, 0, result.out)

    def test_approval_flag_naming_a_modified_source_file_does_not_exempt_it(self):
        """The reviewer's attack: pass a modified source path as --approval to hide it from the gate."""
        self.write("Dockerfile", "# modified source\n")
        result = self.run_script("deploy.sh", *self.args()[:2], *self._with_approval(os.path.join(self.repo, "Dockerfile"), "--execute", "--profile", "p"), **self.base_env)
        self.assert_refused(result, "clean-tree")
        self.assertEqual(self.calls("aws"), [])

    def test_inherited_exclusion_environment_variable_is_ignored(self):
        self.write("Dockerfile", "# modified source\n")
        for name in ("SC_DIRTY_EXTRA_EXCLUDE", "GIT_EXCLUDE", "SCHOLARCHAIN_DIRTY_EXCLUDE"):
            with self.subTest(name):
                result = self.execute(**{name: "Dockerfile"})
                self.assert_refused(result, "clean-tree")
                self.assertEqual(self.calls("aws"), [])

    def test_pathspec_metacharacters_never_exempt_anything(self):
        exempt = os.path.join(self.repo, "docs", "agent-runs", "phase-14", "human-gate.md")
        os.makedirs(os.path.dirname(exempt))
        with open(exempt, "w") as handle:
            handle.write(self.record_text())
        for name in ("*", ":(exclude)Dockerfile", "docs/agent-runs/phase-14/human-gate.md.bak", "docs/agent-runs/phase-14/human-gate.m?"):
            with self.subTest(name):
                path = os.path.join(self.repo, name)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as handle:
                    handle.write("x\n")
                args = ["--stage", self.stage, "--region", REGION, "--prespend", self.prespend, "--plan", self.plan, "--execute", "--profile", "p"]
                result = self.run_script("deploy.sh", *args, **self.base_env)
                self.assert_refused(result, "clean-tree")
                self.assertEqual(self.calls("aws"), [])
                os.remove(path)

    def test_the_literal_default_record_path_alone_is_exempt(self):
        record = os.path.join(self.repo, "docs", "agent-runs", "phase-14", "human-gate.md")
        os.makedirs(os.path.dirname(record))
        with open(record, "w") as handle:
            handle.write(self.record_text())
        args = ["--stage", self.stage, "--region", REGION, "--prespend", self.prespend, "--plan", self.plan]
        result = self.run_script("deploy.sh", *args, **self.base_env)
        self.assertEqual(result.rc, 0, result.out)

    def test_failing_git_status_refuses_instead_of_reading_as_clean(self):
        self.install_git_wrapper("fail")
        result = self.execute()
        self.assert_refused(result, "clean-tree")
        self.assertIn("cannot determine whether the work tree is clean", result.out)
        self.assertEqual(self.calls("aws"), [])
        self.assertEqual(self.calls("docker"), [])

    def test_unparsable_git_status_output_refuses(self):
        self.install_git_wrapper("garbage")
        result = self.execute()
        self.assert_refused(result, "clean-tree")
        self.assertIn("cannot determine", result.out)
        self.assertEqual(self.calls("aws"), [])

    def test_inherited_git_dir_cannot_redirect_the_gate(self):
        """GIT_DIR pointing at a clean repository must not hide the dirty one being gated."""
        other = os.path.join(self.tmp, "other-repo")
        os.makedirs(other)
        self.write("junk.txt", "untracked\n")
        result = self.execute(GIT_DIR=os.path.join(other, ".git"), GIT_WORK_TREE=other)
        self.assert_refused(result, "clean-tree")


class DeployApprovalRecordTests(DeployBase):
    def test_missing_record_refused(self):
        result = self.run_script("deploy.sh", "--stage", self.stage, "--plan", self.plan, "--region", REGION, "--approval", os.path.join(self.tmp, "nope.md"))
        self.assert_refused(result, "approval-record")
        self.assertIn("not found", result.out)

    def test_default_record_path_missing_refused(self):
        result = self.run_script("deploy.sh", "--stage", self.stage, "--plan", self.plan, "--region", REGION)
        self.assert_refused(result, "approval-record")
        self.assertIn("docs/agent-runs/phase-14/human-gate.md", result.out)

    def test_malformed_records(self):
        good = self.record_text()
        cases = {
            "uppercase plan hex": good.replace(self.plan_sha, self.plan_sha.upper()),
            "short plan hex": good.replace(self.plan_sha, self.plan_sha[:63]),
            "non-hex plan": good.replace(self.plan_sha, "z" * 64),
            "short receipt hex": good.replace(self.receipt_sha_value, self.receipt_sha_value[:63]),
            "uppercase receipt hex": good.replace(self.receipt_sha_value, self.receipt_sha_value.upper()),
            "short commit": good.replace(self.head(), self.head()[:39]),
            "quoted value": good.replace("APPROVED_REGION=" + REGION, 'APPROVED_REGION="%s"' % REGION),
            "spaces around equals": good.replace("APPROVED_REGION=" + REGION, "APPROVED_REGION = " + REGION),
            "bad region": good.replace("APPROVED_REGION=" + REGION, "APPROVED_REGION=Ohio"),
            "bad environment": good.replace("APPROVED_ENVIRONMENT=course", "APPROVED_ENVIRONMENT=Course!"),
            "crlf line ending": good.replace("APPROVED_REGION=" + REGION + "\n", "APPROVED_REGION=" + REGION + "\r\n"),
            "bad account hash": good.replace(account_hash(), "12345"),
            "bad prespend hash": good.replace(self.prespend_sha, "12345"),
            "unknown stage": good.replace("APPROVED_STAGE=" + self.stage, "APPROVED_STAGE=everything"),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.approval = self.write_approval(text, name="rec-%s.md" % label.replace(" ", "-"))
                result = self.deploy()
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn(result.steps()[-1], ("approval-record", "stage-match"), result.steps())
                self.assertTrue("malformed" in result.out or "must be exactly" in result.out, result.out)
                self.assertEqual(self.mutating_calls(), [])

    def test_duplicate_key_refused(self):
        self.approval = self.write_approval(self.record_text(extra="APPROVED_REGION=%s\n" % REGION))
        result = self.deploy()
        self.assert_refused(result, "approval-record")
        self.assertIn("2 APPROVED_REGION lines", result.out)

    def test_each_missing_key_refused_for_a_plan_stage(self):
        for key in (
            "APPROVED_PLAN_SHA256", "APPROVED_RECEIPT_SHA256", "APPROVED_COMMIT", "APPROVED_ACCOUNT_SHA256", "APPROVED_REGION",
            "APPROVED_ENVIRONMENT", "APPROVED_PRESPEND_SHA256", "APPROVED_STAGE",
        ):
            with self.subTest(key):
                self.approval = self.write_approval(self.record_text(omit=(key,)), name="missing-%s.md" % key)
                result = self.deploy()
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("approval-record", result.steps())
                self.assertIn("no %s line" % key, result.out)

    def test_each_missing_key_refused_for_a_push(self):
        self.arrange("push")
        for key in ("APPROVED_COMMIT", "APPROVED_ACCOUNT_SHA256", "APPROVED_REGION", "APPROVED_ENVIRONMENT", "APPROVED_PRESPEND_SHA256", "APPROVED_STAGE"):
            with self.subTest(key):
                self.approval = self.write_approval(self.record_text(omit=(key,)), name="push-missing-%s.md" % key)
                result = self.deploy()
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("no %s line" % key, result.out)

    def test_stage_mismatch_refused_before_anything_runs(self):
        for approved in ("base-apply", "push"):
            with self.subTest(approved):
                self.set_approval(stage=approved)
                result = self.execute()
                self.assert_refused(result, "stage-match")
                self.assertIn("each Phase 14 step needs its own approval record", result.out)
                self.assertEqual(self.calls("aws"), [])
                self.assertEqual(self.calls("docker"), [])

    def test_a_push_record_naming_a_plan_or_receipt_is_refused(self):
        """R6: a push approval names no plan, so a plan line (or a receipt line) in it is refused, never ignored."""
        self.arrange("push")
        for key, value in (("APPROVED_PLAN_SHA256", "a" * 64), ("APPROVED_RECEIPT_SHA256", "b" * 64)):
            with self.subTest(key):
                self.approval = self.write_approval(self.record_text(extra="%s=%s\n" % (key, value)), name="push-%s.md" % key)
                result = self.execute()
                self.assert_refused(result, "approval-record")
                self.assertIn("must not contain a %s line" % key, result.out)
                self.assertEqual(self.calls("aws"), [])
                self.assertEqual(self.calls("docker"), [])

    def test_stage_is_required_and_validated(self):
        result = self.run_script("deploy.sh", "--plan", self.plan, "--region", REGION)
        self.assertEqual(result.rc, 2, result.out)
        result = self.run_script("deploy.sh", "--plan", self.plan, "--region", REGION, "--stage", "everything")
        self.assertEqual(result.rc, 2, result.out)
        reuse = self.run_script("deploy.sh", "--region", REGION, "--stage", "push", "--reuse-images", self.write_deploy_manifest())
        self.assertEqual(reuse.rc, 2, reuse.out)

    def test_a_push_has_no_plan_and_the_plan_stages_require_one(self):
        with_plan = self.run_script("deploy.sh", "--stage", "push", "--plan", self.plan, "--region", REGION)
        self.assertEqual(with_plan.rc, 2, with_plan.out)
        self.assertIn("--stage push has no plan", with_plan.out)
        for stage in PLAN_STAGES + ("cleanup-prepare",):
            without = self.run_script("deploy.sh", "--stage", stage, "--region", REGION)
            self.assertEqual(without.rc, 2, without.out)
            self.assertIn("--plan FILE is required", without.out)

    def test_commit_mismatch_refused(self):
        self.set_approval(commit="f" * 40)
        self.assert_refused(self.deploy(), "commit-match")

    def test_wrong_region_refused(self):
        result = self.run_script("deploy.sh", *self.args()[:2], "--region", "us-west-2", "--approval", self.approval, "--prespend", self.prespend, "--plan", self.plan, **self.base_env)
        self.assert_refused(result, "region-match")

    def test_environment_mismatch_refused(self):
        self.set_approval(environment="staging")
        result = self.deploy()
        self.assert_refused(result, "environment-match")
        self.assertIn("APPROVED_ENVIRONMENT staging", result.out)

    def test_plan_checksum_mismatch_refused(self):
        with open(self.plan, "ab") as handle:
            handle.write(b"tampered")
        result = self.deploy()
        self.assert_refused(result, "plan-checksum")
        self.assertIn("APPROVED_PLAN_SHA256", result.out)

    def test_missing_plan_file_refused(self):
        result = self.run_script(
            "deploy.sh", "--stage", self.stage, "--plan", os.path.join(self.tmp, "absent.tfplan"), "--region", REGION, "--approval", self.approval, "--prespend", self.prespend
        )
        self.assert_refused(result, "plan-checksum")

    def test_release_manifest_variants_refused_for_push_and_runtime_apply(self):
        head = self.head()
        bad_arch = [
            {"service": s, "image": "scholarchain-%s:%s" % (s, head), "status": "built", "os_arch": "linux/arm64" if s == "graph-service" else "linux/amd64"}
            for s in SERVICES
        ]
        skipped = [{"service": s, "image": "x", "status": "skipped", "os_arch": ""} for s in SERVICES]
        cases = {
            "dirty manifest": {"dirty": True},
            "commit mismatch": {"commit": "e" * 40},
            "wrong architecture": {"images": bad_arch},
            "images skipped": {"images": skipped, "status": "partial-no-images"},
            "arch gate failed": {"arch_gate": {"passed": False}},
            "wrong platform": {"image_platform": "linux/arm64"},
        }
        for stage in ("push", "runtime-apply"):
            self.arrange(stage)
            for label, overrides in cases.items():
                with self.subTest("%s %s" % (stage, label)):
                    if "commit" in overrides:
                        manifest = self.write_release_manifest()
                        with open(manifest) as handle:
                            data = json.load(handle)
                        data.update(overrides)
                        with open(manifest, "w") as handle:
                            json.dump(data, handle)
                    else:
                        self.write_release_manifest(**overrides)
                    result = self.deploy()
                    self.assert_refused(result, "release-manifest")
                    self.assertIn("MANIFEST-CHECK-FAILED", result.out)

    def test_missing_release_manifest_refused(self):
        os.remove(self.manifest)
        result = self.deploy()
        self.assert_refused(result, "release-manifest")
        self.assertIn("package.sh", result.out)

    def test_terraform_wrong_version_refused_with_found_version(self):
        result = self.deploy(FAKE_TF_VERSION="1.13.4")
        self.assert_refused(result, "terraform-version")
        self.assertIn("1.13.4", result.out)
        self.assertIn("1.13.5", result.out)

    def test_wrong_account_refused_before_any_mutating_command(self):
        result = self.execute(FAKE_ACCOUNT_ID=OTHER_ACCOUNT)
        self.assert_refused(result, "account-check")
        self.assertEqual([c for c in self.calls() if c[0] != "terraform"], [("aws", "sts get-caller-identity --region %s --query Account --output text" % REGION)])
        self.assertNotIn(OTHER_ACCOUNT, result.out)
        self.assertNotIn(FAKE_ACCOUNT, result.out)
        self.assertIn("no mutating command was run", result.out)

    def test_sts_failure_refused_before_any_mutating_command(self):
        result = self.execute(FAKE_STS_RC="255")
        self.assert_refused(result, "account-check")
        self.assertEqual(len([c for c in self.calls("aws")]), 1)

    def test_execute_requires_profile(self):
        env = dict(self.base_env)
        env["AWS_PROFILE"] = None
        result = self.run_script("deploy.sh", *self.args("--execute"), **env)
        self.assert_refused(result, "inputs")

    def test_usage_errors_exit_2(self):
        self.assertEqual(self.run_script("deploy.sh", "--bogus").rc, 2)
        result = self.run_script("deploy.sh", "--region", REGION)
        self.assertEqual(result.rc, 2)
        self.assertIn("RESULT: REFUSED step=usage", result.stdout)


class DeployPrespendTests(DeployBase):
    """F5: a human-approved pre-spend receipt gates every paid mutation (push, apply and upload)."""

    def refuse_in_every_stage(self, label, mutate, expected):
        for stage in ("base-apply", "push", "runtime-apply"):
            with self.subTest("%s / %s" % (label, stage)):
                self.arrange(stage)
                mutate()
                open(self.log, "w").close()
                result = self.execute()
                self.assert_refused(result, "prespend-receipt")
                self.assertIn(expected, result.out)
                # No push, apply or upload; not even the identity call: the gate runs before any cloud command.
                self.assertEqual(self.calls("aws"), [])
                self.assertEqual(self.calls("docker"), [])
                self.assertEqual(self.applied(), [])
                self.assertEqual(self.terraform_non_version(), [])

    def test_missing_receipt_refused(self):
        def mutate():
            os.remove(self.prespend)

        self.refuse_in_every_stage("missing receipt", mutate, "pre-spend receipt not found")

    def test_hash_mismatch_refused(self):
        def mutate():
            self.set_approval(prespend_sha="0" * 64)

        self.refuse_in_every_stage("hash mismatch", mutate, "!= APPROVED_PRESPEND_SHA256")

    def test_receipt_edited_after_approval_refused(self):
        def mutate():
            with open(self.prespend, "a") as handle:
                handle.write("\n")

        self.refuse_in_every_stage("edited", mutate, "!= APPROVED_PRESPEND_SHA256")

    def test_stale_cost_snapshot_refused(self):
        def mutate():
            self.set_prespend(cost_snapshot_utc=utc_hours_ago(25))

        self.refuse_in_every_stage("stale snapshot", mutate, "at most 24.0 h is accepted")

    def test_missing_snapshot_timestamp_refused(self):
        def mutate():
            self.set_prespend(cost_snapshot_utc=MISSING)

        self.refuse_in_every_stage("missing timestamp", mutate, "cost_snapshot_utc is missing")

    def test_monitoring_not_confirmed_refused(self):
        for value in (False, MISSING, "true", 1):
            def mutate(value=value):
                self.set_prespend(monitoring_confirmed_active=value)

            self.refuse_in_every_stage("monitoring=%r" % (value if value is not MISSING else "missing",), mutate, "monitoring_confirmed_active is not true")

    def test_insufficient_headroom_refused(self):
        def mutate():
            self.set_prespend(remaining_headroom_usd=19.99)

        self.refuse_in_every_stage("headroom 19.99", mutate, "below the required 20.0 USD")

    def test_negative_headroom_refused(self):
        def mutate():
            self.set_prespend(remaining_headroom_usd=-5)

        self.refuse_in_every_stage("negative headroom", mutate, "below the required")

    def test_every_cost_field_missing_null_or_non_numeric_is_refused_never_zero(self):
        fields = ("reported_spend_usd", "unreported_usage_allowance_usd", "reserves_usd", "remaining_headroom_usd")
        for field in fields:
            for label, value in (("missing", MISSING), ("null", None), ("string", "12.5"), ("boolean", True), ("list", [1])):
                def mutate(field=field, value=value):
                    self.set_prespend(**{field: value})

                self.refuse_in_every_stage("%s %s" % (field, label), mutate, "%s is missing or not a number" % field)

    def test_nan_and_infinity_are_refused(self):
        for literal in ("NaN", "Infinity", "-Infinity"):
            def mutate(literal=literal):
                self.set_prespend()
                with open(self.prespend) as handle:
                    text = handle.read().replace('"reserves_usd": 40', '"reserves_usd": %s' % literal)
                with open(self.prespend, "w") as handle:
                    handle.write(text)
                with open(self.prespend, "rb") as handle:
                    sha = sha256_bytes(handle.read())
                self.set_approval(prespend_sha=sha)

            self.refuse_in_every_stage("reserves=%s" % literal, mutate, "not valid JSON")

    def test_invalid_json_refused(self):
        def mutate():
            with open(self.prespend, "w") as handle:
                handle.write("not json")
            with open(self.prespend, "rb") as handle:
                self.set_approval(prespend_sha=sha256_bytes(handle.read()))

        self.refuse_in_every_stage("invalid json", mutate, "not valid JSON")

    def test_boundaries_pass(self):
        """Exactly 20 USD of headroom and a 23 hour old snapshot are accepted (dry run)."""
        self.set_prespend(remaining_headroom_usd=20, cost_snapshot_utc=utc_hours_ago(23))
        result = self.deploy()
        self.assertEqual(result.rc, 0, result.out)

    def test_dry_run_also_refuses_without_the_receipt(self):
        os.remove(self.prespend)
        self.assert_refused(self.deploy(), "prespend-receipt")

    def test_pins_cannot_be_weakened_from_the_environment(self):
        self.set_prespend(remaining_headroom_usd=5)
        result = self.deploy(PRESPEND_MIN_HEADROOM_USD="1", PRESPEND_MAX_AGE_HOURS="9999")
        self.assert_refused(result, "prespend-receipt")
        self.assertIn("CONFIG-IGNORED", result.stdout)


class DeployPrespendFreshnessTests(DeployBase):
    """R7: the pre-spend receipt is re-verified immediately before EACH paid operation. A controllable clock is honoured
    only with the announced test-only SCHOLARCHAIN_CONFIG_FILE mechanism."""

    def clock(self, **labels):
        """A clock file: 'default' is now; each LABEL=<hours> entry moves that operation's time forward."""
        table = {"default": utc_in_hours(0)}
        for label, hours in labels.items():
            table[label.replace("_", "-")] = utc_in_hours(hours)
        path = os.path.join(self.tmp, "clock.json")
        with open(path, "w") as handle:
            json.dump(table, handle)
        return path

    def test_the_clock_is_announced_and_a_valid_clock_changes_nothing(self):
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock())
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("CLOCK-OVERRIDE: using", result.stdout)
        self.assertIn("pre-spend receipt re-verified before terraform-apply", result.out)

    def test_the_clock_is_ignored_with_the_real_repository_config(self):
        """Without the test-only config file the override is ignored (and announced), so a far-future clock cannot matter."""
        result = self.execute(SCHOLARCHAIN_CONFIG_FILE=None, SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(default=500))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("CLOCK-IGNORED", result.stdout)
        self.assertNotIn("CLOCK-OVERRIDE", result.stdout)

    def test_a_malformed_clock_file_fails_closed(self):
        path = os.path.join(self.tmp, "clock.json")
        with open(path, "w") as handle:
            handle.write("not json")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=path)
        self.assert_refused(result, "prespend-receipt")
        self.assertIn("test clock file is unreadable", result.out)

    def test_every_paid_operation_re_verifies_the_receipt(self):
        """Hand-derived: push = login + 4 pushes, plus the initial check; each apply; the archive upload."""
        self.arrange("push")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock())
        self.assertEqual(result.rc, 0, result.out)
        for label in ["ecr-login"] + ["push-%s" % s for s in SERVICES]:
            self.assertIn("pre-spend receipt re-verified before %s" % label, result.out)
        self.arrange("base-apply")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock())
        self.assertEqual(result.rc, 0, result.out)
        for label in ("terraform-apply", "archive-upload"):
            self.assertIn("pre-spend receipt re-verified before %s" % label, result.out)

    def test_expiry_before_the_ecr_login_stops_every_push_and_login(self):
        self.arrange("push")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(ecr_login=25))
        self.assert_refused(result, "ecr-login")
        self.assertIn("pre-spend receipt rejected before ecr-login", result.out)
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecr get-login-password")], [])
        self.assertEqual([a for _n, a in self.calls("docker") if a.split()[0] in ("login", "tag", "push")], [])
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "release", self.head(), "push-record.json")))

    def test_expiry_before_the_second_push_stops_after_exactly_one_push(self):
        self.arrange("push")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(push_graph_service=25))
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "push-images")
        self.assertIn("RESULT: REFUSED step=push-images", result.stdout)
        self.assertIn("before push-graph-service", result.out)
        pushes = [a for _n, a in self.calls("docker") if a.startswith("push")]
        self.assertEqual(len(pushes), 1, "query-api (first in service order) was pushed; nothing after the expiry")
        self.assertTrue(pushes[0].endswith("/scholarchain-course/query-api:%s" % self.head()))
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "release", self.head(), "push-record.json")), "no push record for a partial push")

    def test_expiry_before_the_runtime_apply_stops_the_apply(self):
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(terraform_apply=25))
        self.assert_refused(result, "terraform-apply")
        self.assertIn("pre-spend receipt rejected before terraform-apply", result.out)
        self.assertEqual(self.applied(), [])
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecs ")], [])

    def test_expiry_before_the_base_apply_stops_the_apply_and_the_upload(self):
        self.arrange("base-apply")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(terraform_apply=25))
        self.assert_refused(result, "terraform-apply")
        self.assertEqual(self.applied(), [])
        self.assertEqual(self.uploads(), [])

    def test_expiry_after_the_base_apply_stops_the_archive_upload(self):
        """The receipt was valid at the start and at the apply, but not before the upload that follows it."""
        self.arrange("base-apply")
        result = self.execute(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(archive_upload=25))
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "runtime-archive-upload")
        self.assertIn("pre-spend receipt rejected before archive-upload", result.out)
        self.assertEqual(len(self.applied()), 1, "the apply happened (it preceded the expiry)")
        self.assertEqual(self.uploads(), [], "but the upload did not")
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3 ")], [])
        self.assertEqual(self.deploy_manifests("base-apply"), [])

    def test_the_gate_is_only_a_dry_run_note_without_execute(self):
        result = self.deploy(SCHOLARCHAIN_TEST_CLOCK_FILE=self.clock(terraform_apply=25))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("would be re-verified immediately before terraform-apply", result.out)


class DeployReceiptBindingTests(DeployBase):
    """R3: the approval names the hash of the plan receipt; the receipt binds source, state and planned variables."""

    def run_refused(self, step, **env):
        result = self.execute(**env)
        self.assert_refused(result, step)
        self.assert_nothing_ran()
        return result

    def test_a_receipt_edited_after_review_is_refused(self):
        with open(self.receipt) as handle:
            document = json.load(handle)
        document["clean"] = True
        document["notes"] = "edited after the human reviewed it"
        with open(self.receipt, "w") as handle:
            json.dump(document, handle)
        result = self.run_refused("plan-provenance")
        self.assertIn("!= APPROVED_RECEIPT_SHA256", result.out)
        self.assertIn("changed after the human reviewed it", result.out)

    def test_a_receipt_for_a_different_run_of_the_same_plan_bytes_is_refused(self):
        """The same plan bytes with a different (equally 'clean') receipt: the approval names the reviewed receipt only."""
        self.rewrite_receipt(reapprove=False, created_utc="2000-01-01T00:00:00Z")
        result = self.run_refused("plan-provenance")
        self.assertIn("APPROVED_RECEIPT_SHA256", result.out)

    def test_the_reviewed_receipt_is_accepted(self):
        self.rewrite_receipt(created_utc="2000-01-01T00:00:00Z")
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)

    def test_a_receipt_of_the_wrong_purpose_is_refused(self):
        self.rewrite_receipt(purpose="cleanup-prepare")
        result = self.run_refused("plan-provenance")
        self.assertIn("receipt purpose cleanup-prepare differs", result.out)

    def test_a_receipt_whose_planned_environment_or_project_differs_is_refused(self):
        for key, value, needle in (
            ("planned_environment", "staging", "planned_environment differs"),
            ("planned_project", "other", "planned_project differs"),
            ("planned_environment", MISSING, "planned_environment differs"),
        ):
            with self.subTest("%s=%r" % (key, value)):
                self.rewrite_receipt(**{key: value})
                result = self.run_refused("plan-provenance")
                self.assertIn(needle, result.out)

    def test_a_planned_environment_that_differs_from_the_approval_is_refused_after_inspection(self):
        """The saved plan's own environment variable, not a label in the receipt, is checked."""
        self.write_show_json([], image_revision=self.revision, environment="staging", name="show.json")
        result = self.run_refused("plan-inspect")
        self.assertIn("planned environment staging != expected course", result.out)

    def test_a_planned_project_that_differs_is_refused(self):
        self.write_show_json([], image_revision=self.revision, project="otherproj", name="show.json")
        result = self.run_refused("plan-inspect")
        self.assertIn("planned project otherproj != expected scholarchain", result.out)

    def test_a_receipt_tree_hash_that_differs_from_the_materialized_source_is_refused(self):
        self.rewrite_receipt(source_tree_sha256="0" * 64)
        result = self.run_refused("plan-inspect")
        self.assertIn("SOURCE-TREE-FAILED", result.out)
        self.assertEqual([a for a in self.terraform_non_version() if " show " in " " + a + " "], [], "refused before terraform loaded anything")

    def test_a_receipt_without_a_tree_hash_is_refused(self):
        self.rewrite_receipt(source_tree_sha256=MISSING)
        result = self.run_refused("plan-inspect")
        self.assertIn("holds no source_tree_sha256", result.out)

    def test_ignored_override_files_in_the_worktree_never_reach_deploys_terraform(self):
        """Terraform runs in a materialized git archive: an ignored override.tf in the work tree has no effect and the hash still matches."""
        self.write("infra/terraform/override.tf", 'variable "x" { default = "injected" }\n')
        self.write("infra/terraform/zz_override.tf", "# injected\n")
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        lines = self.chdir_lines()
        self.assertTrue(lines)
        for sub, chdir, files, binding in lines:
            self.assertNotIn("override.tf", files.split(","), sub)
            self.assertNotIn("zz_override.tf", files.split(","), sub)
            self.assertIn("zz_scholarchain_state_binding.tf", files.split(","), sub)
            self.assertNotEqual(os.path.realpath(chdir), os.path.realpath(os.path.join(self.repo, "infra", "terraform")), sub + " must not run in the work tree")
            self.assertEqual(binding, os.path.realpath(self.state_path()))
        self.assertEqual({sub for sub, *_ in lines}, {"init", "show", "apply"})


class DeployStateBindingTests(DeployBase):
    """R1: apply refuses a missing, different or changed live state, before apply (and again immediately before it)."""

    def run_refused(self, step, **env):
        result = self.execute(**env)
        self.assert_refused(result, step)
        self.assert_nothing_ran()
        return result

    def test_matching_state_is_accepted_and_apply_runs_in_the_state_bound_root(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("state binding ok: lineage %s serial 7" % STATE_LINEAGE, result.out)
        apply_lines = [l for l in self.chdir_lines() if l[0] == "apply"]
        self.assertEqual(len(apply_lines), 1)
        self.assertEqual(apply_lines[0][3], os.path.realpath(self.state_path()), "apply uses the LIVE state file")

    def test_a_missing_state_file_is_refused_before_anything_runs(self):
        os.remove(self.state_path())
        result = self.run_refused("state-binding")
        self.assertIn("the live state file is missing", result.out)
        self.assertEqual(self.terraform_non_version(), [], "refused before terraform init or show")

    def test_a_state_with_a_different_lineage_is_refused(self):
        self.write_state(lineage="ffffeeee-dddd-cccc-bbbb-aaaa00009999")
        result = self.run_refused("state-binding")
        self.assertIn("lineage differs", result.out)
        self.assertEqual(self.terraform_non_version(), [])

    def test_a_state_that_changed_after_the_plan_is_refused(self):
        self.write_state(serial=8)
        result = self.run_refused("state-binding")
        self.assertIn("changed after the plan", result.out)

    def test_a_state_with_the_same_serial_but_other_bytes_is_refused(self):
        self.write_state(extra={"outputs": {"changed": {"value": 1}}})
        result = self.run_refused("state-binding")
        self.assertIn("changed after the plan", result.out)

    def test_a_state_file_that_is_not_a_state_is_refused(self):
        with open(self.state_path(), "w") as handle:
            handle.write("garbage")
        result = self.run_refused("state-binding")
        self.assertIn("STATE-BINDING-FAILED", result.out)

    def test_a_receipt_without_a_state_record_is_refused(self):
        self.rewrite_receipt(state=MISSING)
        result = self.run_refused("state-binding")
        self.assertIn("holds no state record", result.out)

    def test_a_receipt_for_a_first_deployment_refuses_an_existing_state(self):
        self.rewrite_receipt(state={"present": False})
        result = self.run_refused("state-binding")
        self.assertIn("a state file now exists", result.out)

    def test_a_first_deployment_plan_is_accepted_while_the_state_is_still_absent(self):
        self.arrange("base-apply")
        self.rewrite_receipt(state={"present": False})
        os.remove(self.state_path())
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("no state file, as recorded", result.out)

    def test_a_state_changed_between_verification_and_apply_is_refused_immediately_before_apply(self):
        """The state is checked once at verification and AGAIN immediately before apply (terraform's own stale-plan check aside)."""
        result = self.execute(FAKE_SHOW_BUMP_STATE=self.state_path())
        self.assert_refused(result, "terraform-apply")
        self.assertIn("changed after the plan", result.out)
        self.assertEqual(self.applied(), [])
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith(("s3 ", "ecs "))], [])

    def test_the_state_binding_is_also_checked_in_a_dry_run(self):
        os.remove(self.state_path())
        result = self.deploy()
        self.assert_refused(result, "state-binding")


class DeployPlanProvenanceTests(DeployBase):
    """F2: the saved plan's own target and provenance are verified; the verified bytes are applied."""

    def run_refused(self, step, **env):
        result = self.execute(**env)
        self.assert_refused(result, step)
        self.assert_nothing_ran()
        return result

    def test_missing_receipt_refused(self):
        os.remove(self.receipt)
        result = self.run_refused("plan-provenance")
        self.assertIn("REQUIRED", result.out)

    def test_receipt_plan_sha_mismatch_refused(self):
        self.rewrite_receipt(plan_sha256="0" * 64)
        result = self.run_refused("plan-provenance")
        self.assertIn("receipt plan_sha256 differs from the plan checksum", result.out)

    def test_dirty_provenance_receipt_refused(self):
        self.rewrite_receipt(clean=False)
        result = self.run_refused("plan-provenance")
        self.assertIn("dirty work tree at plan time", result.out)

    def test_receipt_commit_account_region_environment_version_mismatches_refused(self):
        cases = {
            "commit": ("receipt commit differs", {"commit": "e" * 40}),
            "scripts commit": ("receipt scripts_commit differs from HEAD", {"scripts_commit": "e" * 40}),
            "account": ("receipt account differs", {"account_sha256": "f" * 64}),
            "region": ("receipt region differs", {"region": "us-west-2"}),
            "environment": ("receipt environment differs", {"env": "staging"}),
            "terraform version": ("terraform_version differs", {"terraform_version": "1.13.4"}),
            "image revision": ("receipt image_revision differs", {"image_revision": PRIOR}),
            "unknown schema": ("unexpected plan receipt schema", {"schema": "scholarchain.plan-receipt.v1"}),
        }
        for label, (expected, overrides) in cases.items():
            with self.subTest(label):
                self.rewrite_receipt(**overrides)
                result = self.run_refused("plan-provenance")
                self.assertIn(expected, result.out)

    def test_planned_region_mismatch_refused(self):
        self.write_show_json([], region="us-west-2", image_revision=self.revision, name="show.json")
        result = self.run_refused("plan-inspect")
        self.assertIn("planned provider region us-west-2 != expected %s" % REGION, result.out)

    def test_planned_account_mismatch_refused_without_printing_either_id(self):
        self.write_show_json([], account=OTHER_ACCOUNT, image_revision=self.revision, name="show.json")
        result = self.run_refused("plan-inspect")
        self.assertIn("ACCOUNT-BINDING-MISMATCH", result.out)
        self.assertNotIn(OTHER_ACCOUNT, result.out)
        self.assertNotIn(FAKE_ACCOUNT, result.out)

    def test_planned_image_revision_mismatch_refused(self):
        self.write_show_json([], image_revision=PRIOR, name="show.json")
        result = self.run_refused("plan-inspect")
        self.assertIn("planned image_revision %s != expected %s" % (PRIOR, self.head()), result.out)

    def test_runtime_plan_without_an_image_revision_refused(self):
        self.write_show_json([], image_revision=None, name="show.json")
        self.run_refused("plan-inspect")

    def test_base_apply_plan_that_carries_an_image_revision_refused(self):
        self.arrange("base-apply")
        self.write_show_json([], image_revision=self.head(), name="show.json")
        result = self.run_refused("plan-inspect")
        self.assertIn("expects none", result.out)

    def test_plan_without_an_aws_provider_region_reference_refused(self):
        with open(self.show) as handle:
            document = json.load(handle)
        document["configuration"] = {"provider_config": {}}
        with open(self.show, "w") as handle:
            json.dump(document, handle)
        result = self.run_refused("plan-inspect")
        self.assertIn("no aws provider configuration", result.out)

    def test_original_plan_replaced_after_verification_applies_the_verified_copy(self):
        base_apply_plan_original = self.plan
        result = self.execute(FAKE_REPLACE_FILE=self.plan)
        self.assertEqual(result.rc, 0, result.out)
        with open(self.plan, "rb") as handle:
            self.assertEqual(handle.read(), b"replaced-after-verification\n", "the fake really swapped the original")
        applied = self.applied()
        self.assertEqual(len(applied), 1)
        applied_path, applied_digest = applied[0]
        self.assertNotEqual(applied_path, base_apply_plan_original, "apply must use the private verified copy, not the mutable original")
        self.assertEqual(applied_digest, self.plan_sha, "the applied bytes are exactly the approved plan")
        self.assertNotEqual(applied_digest, sha256_bytes(b"replaced-after-verification\n"))

    def test_verified_copy_altered_before_apply_is_refused(self):
        result = self.execute(FAKE_TAMPER_ARG="1")
        self.assert_refused(result, "terraform-apply")
        self.assertIn("verified plan copy changed after verification", result.out)
        self.assertEqual(self.applied(), [])
        self.assertEqual(self.calls("docker"), [])
        self.assertEqual([a for _n, a in self.calls("aws") if not a.startswith(("sts ", "ecr describe"))], [])

    def test_apply_command_never_names_the_original_plan_path(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        applies = [a for a in self.terraform_non_version() if " apply " in " " + a + " "]
        self.assertEqual(len(applies), 1)
        self.assertNotIn(self.plan, applies[0])
        self.assertNotIn("-auto-approve", applies[0])


class DeployDryRunTests(DeployBase):
    def test_every_stage_passes_all_local_checks_and_runs_no_cloud_command(self):
        for stage in ("base-apply", "push", "runtime-apply"):
            with self.subTest(stage):
                self.arrange(stage)
                open(self.log, "w").close()
                result = self.deploy()
                self.assertEqual(result.rc, 0, result.out)
                self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"), result.result_line())
                steps = ["terraform-version", "clean-tree", "approval-record", "stage-match", "commit-match", "region-match", "environment-match", "prespend-receipt", "release-manifest", "runtime-archive", "account-check", "write-deploy-manifest"]
                if stage != "push":
                    steps += ["plan-checksum", "plan-provenance", "state-binding", "plan-inspect"]
                for step in steps:
                    self.assertIn(step, result.steps())
                if stage == "push":
                    for absent in ("plan-checksum", "plan-provenance", "state-binding", "plan-inspect"):
                        self.assertNotIn(absent, result.steps())
                self.assertEqual(self.calls("aws"), [], "dry run must not call aws")
                self.assertEqual(self.calls("docker"), [], "dry run must not call docker")
                self.assertEqual(self.applied(), [])
                # R8: nothing beyond the Terraform version probe, in particular no show, init or apply.
                self.assertEqual(self.terraform_non_version(), [], self.calls("terraform"))
                self.assertEqual(len(self.calls("terraform")), 1)
                self.assertIn("DRY-RUN CMD: timeout=120s env AWS_PROFILE=", result.stdout)
                self.assertIn("aws sts get-caller-identity", result.stdout)
                self.assertIn("account comparison runs only with --execute", result.out)
                self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "plans")), "a dry run creates no run directory")

    def test_plan_stages_print_the_show_command_and_defer_the_inspection_to_execute(self):
        for stage in ("base-apply", "runtime-apply"):
            with self.subTest(stage):
                self.arrange(stage)
                result = self.deploy()
                self.assertEqual(result.rc, 0, result.out)
                self.assertIn("DEFERRED to --execute", result.out)
                self.assertIn("nothing beyond the version probe runs now", result.out)
                shows = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:") and " show -json " in l]
                self.assertEqual(len(shows), 1, shows)
                self.assertIn("<verified-private-copy-of-plan.tfplan>", shows[0])
                inits = [l for l in result.stdout.splitlines() if l.startswith("DRY-RUN CMD:") and " init -input=false -lockfile=readonly" in l]
                self.assertEqual(len(inits), 1, inits)
                self.assertEqual(self.terraform_non_version(), [])

    def test_the_inspection_is_mandatory_before_any_execute_path_mutation(self):
        """In execute the show and plan-target check run before the account check and before every mutating command."""
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        steps = result.steps()
        self.assertLess(steps.index("plan-inspect"), steps.index("account-check"))
        self.assertLess(steps.index("plan-inspect"), steps.index("terraform-apply"))
        calls = self.calls()
        names = [(n, a.split()[1] if n == "terraform" and len(a.split()) > 1 else a) for n, a in calls]
        first_show = next(i for i, (n, a) in enumerate(calls) if n == "terraform" and " show -json " in " " + a + " ")
        first_apply = next(i for i, (n, a) in enumerate(calls) if n == "terraform" and " apply " in " " + a + " ")
        self.assertLess(first_show, first_apply, names)
        first_sts = next(i for i, (n, a) in enumerate(calls) if n == "aws")
        self.assertLess(first_show, first_sts)

    def test_base_apply_dry_run_prints_apply_and_upload_only(self):
        self.arrange("base-apply")
        result = self.deploy()
        steps = result.steps()
        self.assertIn("terraform-apply", steps)
        self.assertIn("runtime-archive-upload", steps)
        for absent in ("push-images", "ecr-login", "ecr-repositories-exist", "record-ecs"):
            self.assertNotIn(absent, steps)
        self.assertIn("aws s3 cp <private-copy-of-the-runtime-archive>", result.stdout)
        self.assertIn("apply -input=false -lock-timeout=60s", result.stdout)
        self.assertNotIn("docker push", result.stdout)

    def test_push_dry_run_prints_pushes_and_no_apply(self):
        self.arrange("push")
        result = self.deploy()
        steps = result.steps()
        for step in ("push-record-path", "ecr-repositories-exist", "verify-local-images", "ecr-login", "push-images", "record-digests", "write-push-record"):
            self.assertIn(step, steps)
        for absent in ("terraform-apply", "runtime-archive-upload", "record-ecs"):
            self.assertNotIn(absent, steps)
        for svc in SERVICES:
            self.assertIn("<acct>.dkr.ecr.%s.amazonaws.com/scholarchain-course/%s:%s" % (REGION, svc, self.head()), result.stdout)
        self.assertIn("docker push", result.stdout)
        self.assertNotIn("apply -input=false", result.stdout)
        self.assertIn("would create target/release/%s/push-record.json exclusively" % self.head(), result.out)

    def test_runtime_apply_dry_run_prints_apply_of_the_verified_copy_and_ecs_checks(self):
        result = self.deploy()
        self.assertIn("verify-registry-images", result.steps())
        self.assertIn("push-record", result.steps())
        self.assertIn("record-ecs", result.steps())
        self.assertNotIn("docker push", result.stdout)
        applies = [line for line in result.stdout.splitlines() if "apply -input=false -lock-timeout=60s" in line]
        self.assertEqual(len(applies), 1)
        self.assertNotIn(self.plan, applies[0], "the original plan path is never applied")
        self.assertIn("aws ecs describe-services", result.stdout)
        self.assertIn("aws ecs describe-task-definition", result.stdout)

    def test_reuse_images_dry_run_prints_digest_verification_and_pushes_nothing(self):
        previous = self.write_deploy_manifest(revision=PRIOR, digests={s: registry_digest(s, PRIOR) for s in SERVICES})
        self.arrange("runtime-apply", reuse_revision=PRIOR)
        result = self.deploy("--reuse-images", previous)
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("imageTag=%s" % PRIOR, result.stdout)
        self.assertIn("rollback mode", result.out)
        self.assertNotIn("push-record", result.steps(), "a rollback takes its digests from the previous deploy manifest")
        self.assertEqual(self.mutating_calls(), [])
        self.assertNotIn("docker push", result.stdout.replace("DRY-RUN CMD", ""))


class DeployBaseApplyTests(DeployBase):
    def setUp(self):
        super().setUp()
        self.arrange("base-apply")

    def test_base_apply_runs_identity_apply_upload_only(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        non_tf = self.cloud_calls()
        self.assertEqual(non_tf[0], ("aws", "sts get-caller-identity --region %s --query Account --output text" % REGION))
        self.assertEqual(self.calls("docker"), [], "base-apply never touches docker")
        verbs = [" ".join(a.split()[:2]) for n, a in self.calls("aws")]
        self.assertEqual(verbs, ["sts get-caller-identity", "s3 cp", "s3api head-object"])
        self.assertEqual(len(self.applied()), 1)
        data = self.deploy_manifests("base-apply")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["stage"], "base-apply")
        self.assertEqual(data[0]["images"], [])
        self.assertEqual(data[0]["ecs_services"], [])
        self.assertEqual(data[0]["plan_sha256"], self.plan_sha)
        self.assertEqual(data[0]["account_sha256"], account_hash())

    def test_base_apply_does_not_need_the_ecr_repositories(self):
        result = self.execute(FAKE_ECR_REPO_RC="254")
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecr")], [])

    def test_runtime_archive_hash_mismatch_refused(self):
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE_BYTES)), RUNTIME_ARCHIVE_EXPECTED_SHA256="0" * 64)
        result = self.execute()
        self.assert_refused(result, "runtime-archive")

    def test_upload_verification_failure_is_a_gate_failure(self):
        result = self.execute(FAKE_HEAD_OBJECT=head_object_text(ARCHIVE_BYTES, size=5, sha="0" * 64))
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=runtime-archive-upload", result.stdout)

    def test_apply_failure_stops_with_exit_5_before_upload(self):
        result = self.execute(FAKE_TF_APPLY_RC="1")
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("RESULT: FAIL step=terraform-apply", result.stdout)
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3")], [])

    def test_skip_runtime_archive_uploads_nothing(self):
        result = self.execute("--skip-runtime-archive")
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3")], [])

    # ---- R9 ------------------------------------------------------------------------------------
    def test_the_upload_reads_a_private_copy_whose_hash_is_the_metadata_never_the_original_path(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        uploads = self.uploads()
        self.assertEqual(len(uploads), 1)
        source, observed_sha, metadata = uploads[0]
        self.assertNotEqual(os.path.realpath(source), os.path.realpath(self.archive), "the original path is never uploaded")
        self.assertIn("/target/plans/", source)
        self.assertIn("/verified/", source)
        self.assertEqual(observed_sha, ARCHIVE_SHA, "the bytes the fake observed being uploaded are the pinned bytes")
        self.assertEqual(metadata, "sha256=%s" % observed_sha, "the metadata hash equals the hash of the uploaded bytes")
        self.assertIn("runtime archive verified on its private copy", result.out)
        data = self.deploy_manifests("base-apply")
        self.assertEqual(data[0]["runtime_archive"]["sha256"], ARCHIVE_SHA)
        self.assertEqual(data[0]["runtime_archive"]["status"], "uploaded")

    def test_an_original_replaced_during_apply_is_never_uploaded_or_recorded_as_verified(self):
        """The fake apply replaces the original archive with same-size, different bytes."""
        replacement = b"X" * len(ARCHIVE_BYTES)
        self.assertEqual(len(replacement), len(ARCHIVE_BYTES))
        result = self.execute(FAKE_APPLY_REPLACE_FILE=self.archive)
        with open(self.archive, "rb") as handle:
            self.assertEqual(handle.read(), replacement, "the fake really replaced the original")
        self.assertEqual(result.rc, 0, result.out)
        uploads = self.uploads()
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0][1], ARCHIVE_SHA, "the verified copy was uploaded")
        self.assertNotEqual(uploads[0][1], sha256_bytes(replacement), "the replacement was never uploaded")
        self.assertEqual(uploads[0][2], "sha256=%s" % ARCHIVE_SHA)
        data = self.deploy_manifests("base-apply")
        self.assertEqual(data[0]["runtime_archive"]["sha256"], ARCHIVE_SHA)
        self.assertNotIn(sha256_bytes(replacement), json.dumps(data))

    def test_a_replaced_original_before_the_copy_is_refused_by_the_pins(self):
        with open(self.archive, "wb") as handle:
            handle.write(b"X" * len(ARCHIVE_BYTES))
        result = self.execute()
        self.assert_refused(result, "runtime-archive")
        self.assertEqual(self.uploads(), [])

    def test_a_private_copy_altered_after_verification_is_not_uploaded(self):
        result = self.execute(FAKE_APPLY_REPLACE_GLOB=os.path.join(self.repo, "target", "plans", "*", "verified", "copy-runtime.tgz-*"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("private archive copy changed after verification", result.out)
        self.assertEqual(self.uploads(), [])
        self.assertEqual(self.deploy_manifests("base-apply"), [])

    def test_the_run_directory_and_its_archive_copy_are_removed_at_exit(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        leftovers = glob.glob(os.path.join(self.repo, "target", "plans", "*"))
        self.assertEqual(leftovers, [], "the private run directory (source, copies, 20-byte archive here) is gone")


class DeployPushTests(DeployBase):
    def setUp(self):
        super().setUp()
        self.arrange("push")

    def push_record_path(self):
        return os.path.join(self.repo, "target", "release", self.head(), "push-record.json")

    def test_push_stage_pushes_verified_images_and_never_applies(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        non_tf = self.cloud_calls()
        self.assertEqual(non_tf[0], ("aws", "sts get-caller-identity --region %s --query Account --output text" % REGION))
        pushes = [a for n, a in non_tf if n == "docker" and a.startswith("push")]
        self.assertEqual(len(pushes), 4)
        for svc, push in zip(SERVICES, pushes):
            self.assertTrue(push.endswith("/scholarchain-course/%s:%s" % (svc, self.head())), push)
        self.assertEqual(self.applied(), [], "push stage performs no apply")
        self.assertEqual(self.terraform_non_version(), [], "a push needs no plan: terraform is only probed for its version")
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("s3")], [], "push stage uploads nothing")
        # Order: identity, repository checks, local image inspection, login, tag+push, digest records.
        kinds = []
        for n, a in non_tf:
            words = a.split()
            kinds.append(n + ":" + (words[0] if n == "docker" else " ".join(words[:2])))
        first_push = kinds.index("docker:push")
        self.assertLess(kinds.index("aws:sts get-caller-identity"), kinds.index("aws:ecr describe-repositories"))
        self.assertLess(kinds.index("aws:ecr describe-repositories"), kinds.index("docker:image"))
        self.assertLess(kinds.index("docker:image"), kinds.index("aws:ecr get-login-password"))
        self.assertLess(kinds.index("aws:ecr get-login-password"), first_push)
        self.assertLess(max(i for i, k in enumerate(kinds) if k == "docker:push"), max(i for i, k in enumerate(kinds) if k == "aws:ecr describe-images"))
        # Each local image is tagged by the VERIFIED image ID from the release manifest, never by the mutable tag.
        tags = [a.split() for n, a in non_tf if n == "docker" and a.startswith("tag")]
        self.assertEqual(len(tags), 4)
        for svc, words in zip(SERVICES, tags):
            self.assertEqual(words[1], fake_image_id("scholarchain-%s:%s" % (svc, self.head())))
        # The manifest records the registry digests and the stage; every output is clean.
        data = self.deploy_manifests("push")
        self.assertEqual(len(data), 1)
        self.assertEqual({i["service"]: i["registry_digest"] for i in data[0]["images"]}, {s: registry_digest(s, self.head()) for s in SERVICES})
        self.assertEqual(data[0]["plan_sha256"], "none")
        for forbidden in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, FAKE_PASSWORD):
            self.assertNotIn(forbidden, result.out)
            self.assertNotIn(forbidden, json.dumps(data))
        self.assertIn("<acct>.dkr.ecr.%s.amazonaws.com" % REGION, result.out)
        # Every cloud command went through the timeout helper.
        self.assertEqual(len(self.timeout_helper_lines()), len(self.calls()))

    def test_the_push_writes_a_private_record_of_commit_account_region_repositories_and_digests(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        path = self.push_record_path()
        self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
        with open(path) as handle:
            record = json.load(handle)
        self.assertEqual(record["schema"], "scholarchain.push-record.v1")
        self.assertEqual(record["commit"], self.head())
        self.assertEqual(record["account_sha256"], account_hash())
        self.assertEqual(record["region"], REGION)
        self.assertEqual(record["environment"], "course")
        self.assertEqual({i["service"]: i["pushed_digest"] for i in record["images"]}, {s: registry_digest(s, self.head()) for s in SERVICES})
        self.assertEqual({i["repository"] for i in record["images"]}, {"scholarchain-course/%s" % s for s in SERVICES})
        self.assertEqual({i["tag"] for i in record["images"]}, {self.head()})
        self.assertNotIn(FAKE_ACCOUNT, json.dumps(record))

    def test_an_existing_push_record_is_never_overwritten_and_nothing_is_pushed(self):
        os.makedirs(os.path.dirname(self.push_record_path()), exist_ok=True)
        with open(self.push_record_path(), "w") as handle:
            handle.write("EARLIER-RECORD\n")
        result = self.execute()
        self.assert_refused(result, "push-record-path")
        self.assertIn("already exists", result.out)
        self.assertEqual(self.calls("docker"), [])
        with open(self.push_record_path()) as handle:
            self.assertEqual(handle.read(), "EARLIER-RECORD\n")

    def test_a_symlinked_push_record_path_is_refused_and_the_target_untouched(self):
        canary = os.path.join(self.tmp, "canary.json")
        with open(canary, "w") as handle:
            handle.write("CANARY\n")
        os.makedirs(os.path.dirname(self.push_record_path()), exist_ok=True)
        os.symlink(canary, self.push_record_path())
        result = self.execute()
        self.assert_refused(result, "push-record-path")
        with open(canary) as handle:
            self.assertEqual(handle.read(), "CANARY\n")

    def test_replaced_local_tag_refused_before_any_login_or_push(self):
        result = self.execute(FAKE_IMAGE_REPLACED="graph-service")
        self.assert_refused(result, "verify-local-images")
        self.assertIn("tag was replaced", result.out)
        self.assertEqual([a for n, a in self.calls("docker") if a.split()[0] in ("push", "login", "tag")], [])
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecr get-login-password")], [])

    def test_wrong_local_architecture_refused_before_any_push(self):
        result = self.execute(FAKE_IMAGE_ARCH="arm64")
        self.assert_refused(result, "verify-local-images")
        self.assertIn("expected linux/amd64", result.out)
        self.assertEqual([a for n, a in self.calls("docker") if a.split()[0] in ("push", "login", "tag")], [])

    def test_manifest_without_image_ids_refused(self):
        manifest = self.write_release_manifest()
        with open(manifest) as handle:
            data = json.load(handle)
        for image in data["images"]:
            image["local_image_id"] = ""
        with open(manifest, "w") as handle:
            json.dump(data, handle)
        result = self.execute()
        self.assert_refused(result, "verify-local-images")

    def test_registry_digest_that_differs_from_the_pushed_digest_is_a_gate_failure(self):
        result = self.execute(FAKE_PUSH_DIGEST="sha256:" + "7" * 64)
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=record-digests", result.stdout)
        self.assertIn("!= the digest pushed", result.out)
        self.assertEqual(self.deploy_manifests("push"), [], "nothing is recorded as a success")
        self.assertFalse(os.path.exists(self.push_record_path()), "and no push record is written")

    def test_missing_ecr_repository_refuses_before_any_push(self):
        result = self.execute(FAKE_ECR_REPO_RC="254")
        self.assert_refused(result, "ecr-repositories-exist")
        self.assertIn("apply the approved infrastructure first", result.out)
        self.assertEqual(self.calls("docker"), [])
        self.assertFalse(os.path.exists(self.push_record_path()))

    def test_a_push_needs_no_plan_receipt_or_state_file(self):
        os.remove(self.state_path())
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)


class DeployRuntimeApplyTests(DeployBase):
    def test_runtime_apply_verifies_registry_applies_the_copy_and_checks_all_four_services(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        non_tf = self.cloud_calls()
        self.assertEqual(non_tf[0][0:2], ("aws", "sts get-caller-identity --region %s --query Account --output text" % REGION))
        self.assertEqual([a for n, a in self.calls("docker")], [], "runtime-apply pushes nothing")
        describe_images = [i for i, (n, a) in enumerate(non_tf) if n == "aws" and a.startswith("ecr describe-images")]
        apply_index = next(i for i, (n, a) in enumerate(non_tf) if n == "terraform" and " apply " in " " + a + " ")
        self.assertEqual(len(describe_images), 4)
        self.assertLess(max(describe_images), apply_index, "every image is verified in the registry before apply")
        ecs_index = min(i for i, (n, a) in enumerate(non_tf) if n == "aws" and a.startswith("ecs "))
        self.assertGreater(ecs_index, apply_index, "the ECS check runs after apply")
        applies = self.applied()
        self.assertEqual(len(applies), 1)
        self.assertEqual(applies[0][1], self.plan_sha)
        self.assertNotEqual(applies[0][0], self.plan)
        ecs = [a for n, a in self.calls("aws") if a.startswith("ecs describe-task-definition")]
        self.assertEqual(len(ecs), 4, "one task-definition check per service")
        data = self.deploy_manifests("runtime-apply")
        self.assertEqual(len(data), 1)
        self.assertEqual({e["service"] for e in data[0]["ecs_services"]}, set(SERVICES))
        self.assertEqual({i["service"] for i in data[0]["images"]}, set(SERVICES))
        self.assertTrue(all(i["registry_digest"] == registry_digest(i["service"], self.head()) for i in data[0]["images"]))
        self.assertEqual(data[0]["plan_sha256"], self.plan_sha)
        self.assertEqual(data[0]["commit"], self.head())
        self.assertEqual(data[0]["region"], REGION)
        self.assertNotIn(FAKE_ACCOUNT, json.dumps(data[0]))
        for forbidden in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, FAKE_PASSWORD):
            self.assertNotIn(forbidden, result.out)

    def test_missing_ecr_repository_refuses_before_apply(self):
        result = self.execute(FAKE_ECR_REPO_RC="254")
        self.assert_refused(result, "ecr-repositories-exist")
        self.assertEqual(self.applied(), [])

    def test_missing_service_is_not_recorded_as_a_success(self):
        result = self.execute(FAKE_ECS_SERVICES="query-api")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=record-ecs", result.stdout)
        self.assertIn("ECS-CHECK-FAILED: ECS service graph-service is missing", result.out)
        self.assertEqual(self.deploy_manifests("runtime-apply"), [])

    def test_no_service_at_all_is_not_a_success(self):
        result = self.execute(FAKE_ECS_SERVICES="")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.deploy_manifests("runtime-apply"), [])

    def test_stale_task_definition_image_is_not_recorded_as_a_success(self):
        result = self.execute(FAKE_ECS_STALE_SERVICE="semantic-service")
        self.assertEqual(result.rc, 4, result.out)
        self.assertIn("RESULT: FAIL step=record-ecs", result.stdout)
        self.assertIn("semantic-service does not reference scholarchain-course/semantic-service:%s" % self.head(), result.out)
        self.assertEqual(self.deploy_manifests("runtime-apply"), [])

    def test_task_definition_that_runs_another_services_image_is_refused(self):
        result = self.execute(FAKE_ECS_SWAP_SERVICE="graph-service")
        self.assertEqual(result.rc, 4, result.out)
        self.assertEqual(self.deploy_manifests("runtime-apply"), [])

    def test_unpushed_tag_refused_before_apply(self):
        result = self.execute(FAKE_IMAGE_DIGEST="None")
        self.assert_refused(result, "verify-registry-images")
        self.assertEqual(self.applied(), [])

    def test_apply_failure_stops_with_exit_5_and_checks_no_ecs(self):
        result = self.execute(FAKE_TF_APPLY_RC="1")
        self.assertEqual(result.rc, 5, result.out)
        self.assertIn("RESULT: FAIL step=terraform-apply", result.stdout)
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecs")], [])

    def test_rollback_reuse_with_moved_tag_refused_before_apply(self):
        previous = self.write_deploy_manifest(revision=PRIOR, digests={s: "sha256:" + "1" * 64 for s in SERVICES})
        self.arrange("runtime-apply", reuse_revision=PRIOR)
        result = self.execute("--reuse-images", previous)
        self.assert_refused(result, "verify-registry-images")
        self.assertIn("does not resolve to the recorded digest", result.out)
        self.assertEqual(self.applied(), [])

    def test_rollback_reuse_with_matching_digests_applies_and_verifies_ecs_for_the_previous_revision(self):
        previous = self.write_deploy_manifest(revision=PRIOR, digests={s: registry_digest(s, PRIOR) for s in SERVICES})
        self.arrange("runtime-apply", reuse_revision=PRIOR)
        result = self.execute("--reuse-images", previous)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(self.calls("docker"), [])
        data = self.deploy_manifests("runtime-apply")
        self.assertEqual(data[0]["image_revision"], PRIOR)
        self.assertEqual(len(data[0]["ecs_services"]), 4)

    def test_source_commit_override_is_refused_outside_base_apply(self):
        result = self.execute("--source-commit", PRIOR)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.calls("aws"), [])


class DeployPushRecordBindingTests(DeployBase):
    """R4: runtime apply is bound to the verified push record; a missing record or a changed digest refuses BEFORE apply."""

    def assert_refused_before_apply(self, result, step, needle):
        self.assert_refused(result, step)
        self.assertIn(needle, result.out)
        self.assertEqual(self.applied(), [])
        self.assertEqual([a for a in self.terraform_non_version() if " apply " in " " + a + " "], [])
        self.assertEqual(self.calls("docker"), [])

    def test_a_missing_push_record_refuses_before_apply_and_before_any_registry_call(self):
        os.remove(self.push_record)
        result = self.execute()
        self.assert_refused_before_apply(result, "push-record", "no push record for this commit")
        self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecr")], [])

    def test_a_tag_that_now_points_to_other_bytes_refuses_before_apply(self):
        """A pre-existing tag moved to different bytes: the registry digest is not the recorded pushed digest."""
        result = self.execute(FAKE_IMAGE_DIGEST="sha256:" + "9" * 64)
        self.assert_refused_before_apply(result, "verify-registry-images", "not the digest")
        self.assertIn("recorded by the verified push", result.out)

    def test_one_changed_repository_digest_in_the_record_refuses(self):
        self.write_push_record(digests={"graph-service": "sha256:" + "8" * 64})
        result = self.execute()
        self.assert_refused_before_apply(result, "verify-registry-images", "scholarchain-course/graph-service:%s" % self.head())

    def test_a_push_record_for_another_commit_account_region_or_environment_refuses(self):
        cases = {
            "commit": {"commit": "d" * 40},
            "account": {"account_sha256": "e" * 64},
            "region": {"region": "us-west-2"},
            "environment": {"environment": "staging"},
            "schema": {"schema": "scholarchain.push-record.v0"},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                self.write_push_record(**overrides)
                result = self.execute()
                self.assert_refused_before_apply(result, "push-record", "PUSH-RECORD-FAILED")
                self.assertEqual([a for _n, a in self.calls("aws") if a.startswith("ecr")], [])
                open(self.log, "w").close()

    def test_a_push_record_that_does_not_name_the_four_repositories_refuses(self):
        document = self.write_push_record()
        with open(document) as handle:
            record = json.load(handle)
        cases = {
            "a repository is missing": [i for i in record["images"] if i["service"] != "embedding-worker"],
            "a repository is another one": [dict(i, repository="other/%s" % i["service"]) if i["service"] == "query-api" else i for i in record["images"]],
            "a tag is not the commit": [dict(i, tag="f" * 40) if i["service"] == "query-api" else i for i in record["images"]],
            "a digest is malformed": [dict(i, pushed_digest="sha256:abc") if i["service"] == "query-api" else i for i in record["images"]],
            "a service appears twice": record["images"] + [record["images"][0]],
        }
        for label, images in cases.items():
            with self.subTest(label):
                self.write_push_record(images=images)
                result = self.execute()
                self.assert_refused_before_apply(result, "push-record", "PUSH-RECORD-FAILED")
                open(self.log, "w").close()

    def test_an_unreadable_push_record_refuses(self):
        with open(self.push_record, "w") as handle:
            handle.write("not json")
        result = self.execute()
        self.assert_refused_before_apply(result, "push-record", "PUSH-RECORD-FAILED")

    def test_a_valid_record_and_matching_digests_apply_and_the_four_task_definitions_reference_the_verified_tag(self):
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(self.applied()), 1)
        ecs = [a for _n, a in self.calls("aws") if a.startswith("ecs describe-task-definition")]
        self.assertEqual(len(ecs), 4)
        self.assertEqual({i["registry_digest"] for i in self.deploy_manifests("runtime-apply")[0]["images"]}, {registry_digest(s, self.head()) for s in SERVICES})

    def test_the_dry_run_also_requires_the_push_record(self):
        os.remove(self.push_record)
        result = self.deploy()
        self.assert_refused(result, "push-record")

    def test_a_rollback_that_reuses_images_needs_no_push_record_but_checks_the_previous_manifests_digests(self):
        previous = self.write_deploy_manifest(revision=PRIOR, digests={s: registry_digest(s, PRIOR) for s in SERVICES})
        self.arrange("runtime-apply", reuse_revision=PRIOR)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "release", self.head(), "push-record.json")))
        result = self.execute("--reuse-images", previous)
        self.assertEqual(result.rc, 0, result.out)


class DeployFirstDeploymentSequenceTests(DeployBase):
    """R6: the recorded order, end to end with fakes and three separate approval records:
    approved base apply, then push, then the runtime plan, a new approval and the runtime apply."""

    def setUp(self):
        super().setUp()
        self.private_vars = os.path.join(self.tmp, "p.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write('owner_note = "SEQUENCE-PRIVATE-VALUE-1234"\n')
        self.write_release_manifest()
        os.remove(self.push_record)  # this sequence makes its own push record

    def plan_for(self, show, *extra):
        result = self.run_script(
            "plan.sh", "--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra,
            SCHOLARCHAIN_TF_PRIVATE_VARS=self.private_vars, FAKE_SHOW_JSON=show,
        )
        self.assertEqual(result.rc, 0, result.out)
        lines = dict(l.split("=", 1) for l in result.stdout.splitlines() if l.startswith(("APPROVED_PLAN_SHA256=", "APPROVED_RECEIPT_SHA256=")))
        return self.plan_file_of(result), lines["APPROVED_PLAN_SHA256"], lines["APPROVED_RECEIPT_SHA256"]

    def record(self, stage, name, plan_sha=None, receipt_sha=None):
        prespend, prespend_sha = self.write_prespend(name="prespend-%s.json" % name)
        text = self.approval_text(plan_sha, prespend_sha=prespend_sha, stage=stage, receipt_sha=receipt_sha)
        return self.write_approval(text, name="gate-%s.md" % name), prespend

    def deploy_stage(self, stage, approval, prespend, plan=None, show=None, **env):
        args = ["--stage", stage, "--region", REGION, "--approval", approval, "--prespend", prespend, "--execute", "--profile", "approved"]
        if plan:
            args += ["--plan", plan]
        merged = {
            "SCHOLARCHAIN_RUNTIME_ARCHIVE": self.archive,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI": "s3://bucket-test/key/runtime.tgz",
            "FAKE_HEAD_OBJECT": head_object_text(ARCHIVE_BYTES),
            "FAKE_ECS_TAG": self.head(),
        }
        if show:
            merged["FAKE_SHOW_JSON"] = show
        merged.update(env)
        return self.run_script("deploy.sh", *args, **merged)

    def test_base_apply_then_push_then_runtime_plan_then_runtime_apply_with_three_separate_records(self):
        base_show = self.write_show_json([("aws_ecr_repository.r", "aws_ecr_repository", ["create"])], name="base-show.json")
        runtime_show = self.write_show_json([("aws_ecs_service.s", "aws_ecs_service", ["create"])], image_revision=self.head(), name="runtime-show.json")

        # (0) A push approved BEFORE the base apply refuses: the ECR repositories do not exist yet.
        early_record, early_prespend = self.record("push", "early")
        early = self.deploy_stage("push", early_record, early_prespend, FAKE_ECR_REPO_RC="254")
        self.assertEqual(early.rc, 3, early.out)
        self.assertEqual(early.steps()[-1], "ecr-repositories-exist")
        self.assertEqual(self.calls("docker"), [], "nothing was pushed")
        self.assertFalse(os.path.exists(os.path.join(self.repo, "target", "release", self.head(), "push-record.json")))

        # (1) base plan, record 1 (base-apply), base apply (bumps the live state like a real apply).
        base_plan, base_plan_sha, base_receipt_sha = self.plan_for(base_show)
        record1, prespend1 = self.record("base-apply", "1", base_plan_sha, base_receipt_sha)
        base = self.deploy_stage("base-apply", record1, prespend1, plan=base_plan, show=base_show, FAKE_APPLY_BUMP_STATE=self.state_path())
        self.assertEqual(base.rc, 0, base.out)
        self.assertEqual(len(self.applied()), 1)
        self.assertEqual(len(self.uploads()), 1, "the archive upload follows the base apply")
        self.assertEqual(self.state_identity()["serial"], 8, "the fake apply changed the live state")

        # (2) push, record 2 (push): NO plan, NO receipt line. Records 1 and 3 cannot be used for it.
        wrong = self.deploy_stage("push", record1, prespend1)
        self.assertEqual(wrong.steps()[-1], "stage-match", wrong.out)
        record2, prespend2 = self.record("push", "2")
        with open(record2) as handle:
            self.assertNotRegex(handle.read(), r"(?m)^APPROVED_(PLAN|RECEIPT)_SHA256=")
        pushed = self.deploy_stage("push", record2, prespend2)
        self.assertEqual(pushed.rc, 0, pushed.out)
        self.assertEqual(len([a for _n, a in self.calls("docker") if a.startswith("push")]), 4)
        self.assertTrue(os.path.exists(os.path.join(self.repo, "target", "release", self.head(), "push-record.json")))
        self.assertEqual(len(self.applied()), 1, "the push applied nothing")

        # (3) the runtime plan comes AFTER the push (same image revision), then record 3, then the runtime apply.
        runtime_plan, runtime_plan_sha, runtime_receipt_sha = self.plan_for(runtime_show, "--image-revision", self.head())
        with open(runtime_plan + ".receipt.json") as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["state"]["serial"], 8, "the runtime plan was made against the state the base apply left")
        self.assertEqual(receipt["image_revision"], self.head())
        record3, prespend3 = self.record("runtime-apply", "3", runtime_plan_sha, runtime_receipt_sha)
        stale = self.deploy_stage("runtime-apply", record3, prespend3, plan=base_plan, show=runtime_show)
        self.assertEqual(stale.rc, 3, "the base plan with the runtime record is refused")
        runtime = self.deploy_stage("runtime-apply", record3, prespend3, plan=runtime_plan, show=runtime_show)
        self.assertEqual(runtime.rc, 0, runtime.out)
        self.assertEqual(len(self.applied()), 2)
        self.assertEqual({e["service"] for e in self.deploy_manifests("runtime-apply")[0]["ecs_services"]}, set(SERVICES))

        # Three records, three stages, three distinct manifests.
        self.assertEqual(len(self.deploy_manifests("base-apply")), 1)
        self.assertEqual(len(self.deploy_manifests("push")), 1)
        self.assertEqual(len(self.deploy_manifests("runtime-apply")), 1)
        for forbidden in (FAKE_ACCOUNT, "SEQUENCE-PRIVATE-VALUE-1234"):
            for result in (early, base, pushed, runtime):
                self.assertNotIn(forbidden, result.out)

    def test_a_runtime_apply_without_the_push_in_between_refuses(self):
        runtime_show = self.write_show_json([], image_revision=self.head(), name="runtime-show.json")
        plan, plan_sha, receipt_sha = self.plan_for(runtime_show, "--image-revision", self.head())
        record, prespend = self.record("runtime-apply", "3", plan_sha, receipt_sha)
        result = self.deploy_stage("runtime-apply", record, prespend, plan=plan, show=runtime_show)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "push-record")
        self.assertEqual(self.applied(), [])


class DeployCleanupPrepareStageTests(DeployBase):
    """R5: the preparation plan is applied through the deploy approval path (approval record, receipt, pre-spend), re-checked by policy."""

    PROTECTED_CHANGE = {
        "address": "module.dynamodb.aws_dynamodb_table.table[\"RunLedger\"]",
        "type": "aws_dynamodb_table",
        "change": {"actions": ["update"], "before": {"deletion_protection_enabled": True, "name": "t"}, "after": {"deletion_protection_enabled": False, "name": "t"}, "after_unknown": {}},
    }

    def arrange_prepare(self, change=None, revision=None, receipt_revision=None, **receipt_overrides):
        self.stage = "cleanup-prepare"
        self.plan, self.plan_sha = self.make_plan(b"prepare-plan-bytes\n", name="prepare.tfplan")
        self.revision = revision
        self.show = self.write_show_json([], image_revision=revision, extra_changes=[change or self.PROTECTED_CHANGE], name="prepare-show.json")
        receipt_overrides.setdefault("purpose", "cleanup-prepare")
        self.receipt = self.write_plan_receipt(self.plan, self.plan_sha, image_revision=receipt_revision if receipt_revision is not None else revision, **receipt_overrides)
        self.receipt_sha_value = self.receipt_sha(self.plan)
        self.set_prespend()
        self.base_env = {"FAKE_SHOW_JSON": self.show}

    def test_a_policy_compliant_preparation_plan_is_applied_after_the_full_approval_path(self):
        self.arrange_prepare()
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(len(self.applied()), 1)
        self.assertIn("NEXT: re-run scripts/cleanup.sh", result.out)
        self.assertEqual(self.calls("docker"), [])
        self.assertEqual(self.deploy_manifests("cleanup-prepare")[0]["stage"], "cleanup-prepare")
        self.assertIn("pre-spend receipt re-verified before terraform-apply", result.out)

    def test_it_needs_the_approval_record_the_receipt_hash_and_the_prespend_receipt(self):
        self.arrange_prepare()
        with open(self.receipt, "a") as handle:
            handle.write("\n")
        self.assert_refused(self.execute(), "plan-provenance")
        self.arrange_prepare()
        os.remove(self.prespend)
        self.assert_refused(self.execute(), "prespend-receipt")

    def test_a_receipt_that_is_a_normal_deploy_plan_is_not_accepted_for_cleanup_prepare(self):
        self.arrange_prepare(purpose="deploy-plan")
        result = self.execute()
        self.assert_refused(result, "plan-provenance")
        self.assertIn("receipt purpose deploy-plan differs from the expected cleanup-prepare", result.out)

    def test_a_preparation_plan_that_changes_anything_else_is_refused_before_apply(self):
        cases = {
            "creates a resource": {"address": "module.runtime.aws_ecr_repository.new", "type": "aws_ecr_repository", "change": {"actions": ["create"], "before": None, "after": {"force_delete": True}, "after_unknown": {}}},
            "deletes a resource": {"address": "module.dynamodb.aws_dynamodb_table.table[\"RunLedger\"]", "type": "aws_dynamodb_table", "change": {"actions": ["delete"], "before": {}, "after": None, "after_unknown": {}}},
            "replaces a resource": {"address": "module.dynamodb.aws_dynamodb_table.table[\"RunLedger\"]", "type": "aws_dynamodb_table", "change": {"actions": ["delete", "create"], "before": {}, "after": {}, "after_unknown": {}}},
            "changes another attribute": {"address": "module.dynamodb.aws_dynamodb_table.table[\"RunLedger\"]", "type": "aws_dynamodb_table", "change": {"actions": ["update"], "before": {"deletion_protection_enabled": True, "billing_mode": "PAY_PER_REQUEST"}, "after": {"deletion_protection_enabled": False, "billing_mode": "PROVISIONED"}, "after_unknown": {}}},
            "updates a preserved bucket": {"address": "module.datalake.aws_s3_bucket.zone[\"curated\"]", "type": "aws_s3_bucket", "change": {"actions": ["update"], "before": {"force_destroy": False}, "after": {"force_destroy": True}, "after_unknown": {}}},
            "updates an unlisted resource": {"address": "aws_instance.rogue", "type": "aws_instance", "change": {"actions": ["update"], "before": {"deletion_protection_enabled": True}, "after": {"deletion_protection_enabled": False}, "after_unknown": {}}},
            "makes a flag unknown": {"address": "module.dynamodb.aws_dynamodb_table.table[\"RunLedger\"]", "type": "aws_dynamodb_table", "change": {"actions": ["update"], "before": {"deletion_protection_enabled": True, "arn": "x"}, "after": {"deletion_protection_enabled": False}, "after_unknown": {"arn": True}}},
        }
        for label, change in cases.items():
            with self.subTest(label):
                self.arrange_prepare(change=change)
                open(self.log, "w").close()
                result = self.execute()
                self.assert_refused(result, "plan-inspect")
                self.assertIn("POLICY-VIOLATION", result.out)
                self.assertEqual(self.applied(), [])
                self.assertEqual([a for _n, a in self.calls("aws") if not a.startswith("sts ")], [])

    def test_the_receipts_image_revision_must_match_the_saved_plan(self):
        self.arrange_prepare(revision=None, receipt_revision=PRIOR)
        result = self.execute()
        self.assert_refused(result, "plan-inspect")
        self.assertIn("planned image_revision", result.out)

    def test_a_preparation_plan_made_with_the_deployed_revision_is_accepted(self):
        self.arrange_prepare(revision=PRIOR)
        result = self.execute()
        self.assertEqual(result.rc, 0, result.out)


if __name__ == "__main__":
    unittest.main()
