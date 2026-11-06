"""cleanup.sh (F3, R2, R5): preservation policy, listed destructive actions, token bound to the exact saved plan,
protection released first through a separately approved preparation, confined private outputs.

Hand-derived expectations: the classification of each fake state address, the sorted action list and
the token = sha256 over (plan sha256, account sha256, region, environment, sorted action list).
"""
import glob
import hashlib
import json
import os
import re
import stat
import unittest

from helpers import FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, REGION, STATE_LINEAGE, Fixture, account_hash, sha256_bytes

OTHER_ACCOUNT = "999988887777"
PRIVATE_CANARY = "CANARY-CLEANUP-PRIVATE-VALUE-4412"
ARN_TABLE = "arn:aws:dynamodb:us-east-2:%s:table/scholarchain-course-RunLedger" % FAKE_ACCOUNT
TAG_JSON = json.dumps({"ResourceTagMappingList": [{"ResourceARN": ARN_TABLE}]})

# state addresses of the destroy root and their expected classes under the pinned policy
STATE = [
    'module.datalake.aws_s3_bucket.zone["curated"]',  # preserved: S3 bucket (type and address rule)
    'module.identity.aws_kms_key.data',  # preserved: KMS key
    'module.observability.aws_cloudwatch_log_group.service["query-api"]',  # preserved: grading log group
    'module.runtime.aws_ecs_service.service["query-api"]',  # teardown: ECS runtime
    'module.dynamodb.aws_dynamodb_table.table["RunLedger"]',  # teardown: DynamoDB
    "module.network.aws_nat_gateway.course",  # teardown: network
    "module.identity.aws_iam_role.deployment",  # NOT targeted: unlisted
]
TEARDOWN_ADDRESSES = [
    'module.runtime.aws_ecs_service.service["query-api"]',
    'module.dynamodb.aws_dynamodb_table.table["RunLedger"]',
    "module.network.aws_nat_gateway.course",
]
EXPECTED_TARGETS = ["module.dynamodb.aws_dynamodb_table.table", "module.network.aws_nat_gateway.course", "module.runtime.aws_ecs_service.service"]
TEARDOWN_CHANGES = [
    ('module.runtime.aws_ecs_service.service["query-api"]', "aws_ecs_service", ["delete"]),
    ('module.dynamodb.aws_dynamodb_table.table["RunLedger"]', "aws_dynamodb_table", ["delete"]),
    ("module.network.aws_nat_gateway.course", "aws_nat_gateway", ["delete"]),
    ("module.network.aws_eip.nat", "aws_eip", ["delete"]),
    ("aws_cloudwatch_log_group.nothing", "aws_cloudwatch_log_group", ["no-op"]),
]
SORTED_ACTIONS = sorted(
    [
        'delete module.runtime.aws_ecs_service.service["query-api"]',
        'delete module.dynamodb.aws_dynamodb_table.table["RunLedger"]',
        "delete module.network.aws_nat_gateway.course",
        "delete module.network.aws_eip.nat",
    ]
)


# Teardown resources of the live stack that carry a deletion protection, and their released forms.
NEPTUNE = 'module.neptune.aws_neptune_cluster.graph'
ALB = 'module.runtime.aws_lb.query'
TABLE = 'module.dynamodb.aws_dynamodb_table.table["RunLedger"]'
ECR = 'module.runtime.aws_ecr_repository.service["query-api"]'
LOCK_TABLE = "module.foundation.aws_dynamodb_table.lock"  # preserved: never a preparation target
PROTECTED = {
    "neptune": (NEPTUNE, "aws_neptune_cluster", {"deletion_protection": True}, "deletion_protection=true"),
    "alb": (ALB, "aws_lb", {"enable_deletion_protection": True}, "enable_deletion_protection=true"),
    "dynamodb": (TABLE, "aws_dynamodb_table", {"deletion_protection_enabled": True}, "deletion_protection_enabled=true"),
    "ecr": (ECR, "aws_ecr_repository", {"force_delete": False}, "force_delete=false"),
}
RELEASED = {
    "neptune": (NEPTUNE, "aws_neptune_cluster", {"deletion_protection": False}),
    "alb": (ALB, "aws_lb", {"enable_deletion_protection": False}),
    "dynamodb": (TABLE, "aws_dynamodb_table", {"deletion_protection_enabled": False}),
    "ecr": (ECR, "aws_ecr_repository", {"force_delete": True}),
}


def state_document(resources):
    """A `terraform show -json` state fixture: [(address, type, values)] in the root module."""
    return {"format_version": "1.0", "values": {"root_module": {"resources": [{"address": a, "type": t, "values": v} for a, t, v in resources]}}}


def update_change(address, rtype, before, after):
    return {"address": address, "type": rtype, "change": {"actions": ["update"], "before": before, "after": after, "after_unknown": {}}}


def expected_token(plan_sha, account, region, environment, actions):
    body = "scholarchain-destroy-token-v1\nplan_sha256=%s\naccount_sha256=%s\nregion=%s\nenvironment=%s\n" % (plan_sha, account, region, environment)
    body += "".join(a + "\n" for a in sorted(actions))
    return hashlib.sha256(body.encode()).hexdigest()


class CleanupBase(Fixture):
    def setUp(self):
        super().setUp()
        self.private_vars = os.path.join(self.tmp, "private.local.tfvars")
        with open(self.private_vars, "w") as handle:
            handle.write('notification_email = "%s"\n' % PRIVATE_CANARY)
        self.show = self.write_show_json(TEARDOWN_CHANGES, name="destroy-show.json")
        self.released_state = self.write_state_json(list(RELEASED.values()), "state-released.json")
        self.env_all = {
            "SCHOLARCHAIN_TF_PRIVATE_VARS": self.private_vars,
            "FAKE_STATE_LIST": ";".join(STATE),
            "FAKE_STATE_JSON": self.released_state,
            "FAKE_TAG_JSON": TAG_JSON,
            "FAKE_SHOW_JSON": self.show,
            "FAKE_PLAN_SALT": "destroy-salt",
        }

    def write_state_json(self, resources, name):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as handle:
            json.dump(state_document(resources), handle)
        return path

    def cleanup(self, *args, **env):
        merged = dict(self.env_all)
        merged.update(env)
        return self.run_script("cleanup.sh", *args, **merged)

    def execute(self, *extra, **env):
        return self.cleanup("--env", "course", "--region", REGION, "--profile", "approved", "--execute", *extra, **env)

    def show_with(self, changes, name):
        return self.write_show_json(changes, name=name)

    def destroy_calls(self):
        return [a for n, a in self.calls("terraform") if " -destroy " in " " + a + " " or " apply " in " " + a + " "]

    def applied(self):
        path = self.log + ".applied"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def listing(self, **env):
        return self.execute(**env)

    def confirm(self, token, plan_path, **env):
        return self.execute("--confirm", token, "--plan", plan_path, **env)

    @staticmethod
    def token_of(stdout):
        match = re.search(r"^CONFIRM-TOKEN: ([0-9a-f]{64})$", stdout, re.M)
        return match.group(1) if match else None

    @staticmethod
    def plan_file_from(stdout, label="DESTROY-PLAN-FILE"):
        match = re.search(r"^%s: (\S+)$" % label, stdout, re.M)
        return match.group(1) if match else None

    def plans_root(self):
        return os.path.join(self.repo, "target", "plans")

    def evidence_root(self):
        return os.path.join(self.repo, "target", "cleanup-evidence")

    def evidence_dirs(self):
        return sorted(glob.glob(os.path.join(self.evidence_root(), "*")))

    def latest_evidence(self):
        dirs = self.evidence_dirs()
        self.assertTrue(dirs, "no evidence directory was created")
        return max(dirs, key=os.path.getmtime)

    @staticmethod
    def sha_of(path):
        with open(path, "rb") as handle:
            return sha256_bytes(handle.read())


class CleanupDryRunTests(CleanupBase):
    def test_dry_run_lists_commands_policy_and_preserve_list_and_runs_nothing(self):
        result = self.cleanup("--env", "course", "--region", REGION)
        self.assertEqual(result.rc, 0, result.out)
        self.assertEqual(result.result_line()[:15], "RESULT: DRY-RUN")
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])
        out = result.stdout
        self.assertEqual(len(re.findall(r"terraform -chdir=\S+ state list", out)), 4, "two roots, before and after")
        self.assertIn("infra/terraform/deployer state list", out)
        self.assertRegex(out, r"-chdir=\S+/target/plans/\S+/source/%s/infra/terraform state list" % self.head())
        self.assertIn("aws resourcegroupstaggingapi get-resources --region us-east-2", out)
        self.assertIn("Key=project", out)
        self.assertIn("plan -destroy", out)
        self.assertIn("-target=<each-teardown-address-from-the-classified-state-list>", out)
        self.assertIn(" show -json ", out)
        self.assertIn(" show -no-color ", out)
        self.assertRegex(out, r"apply -input=false -lock-timeout=60s <verified-private-copy-of-destroy-course\.tfplan>")
        for item in ("terraform-state", "s3-buckets-and-objects", "s3-vectors", "kms-keys-and-policies", "grading-log-groups"):
            self.assertIn("PRESERVE: %s" % item, out)
        self.assertIn("PRESERVE-RULES types: aws_s3_bucket,aws_s3_object,aws_s3vectors_,aws_kms_,aws_cloudwatch_log_group", out)
        self.assertIn("TEARDOWN-RULES addresses: module.runtime.,module.emr.,module.neptune.,module.dynamodb.,module.messaging.,module.workflow.,module.network.", out)
        self.assertIn("protection-check", result.steps())
        self.assertIn("PROTECTION-RULES: aws_neptune_cluster:deletion_protection=true", out)
        # The inventory commands are printed before the destroy commands.
        self.assertLess(out.index("state list"), out.index("plan -destroy"))
        self.assertFalse(os.path.exists(self.plans_root()), "a dry run creates no run directory")
        self.assertFalse(os.path.exists(self.evidence_root()), "and no evidence directory")

    def test_usage_and_version_errors(self):
        self.assertEqual(self.cleanup("--region", REGION).rc, 2)
        self.assertEqual(self.cleanup("--env", "course").rc, 2)
        wrong = self.cleanup("--env", "course", "--region", REGION, FAKE_TF_VERSION="1.13.4")
        self.assertEqual(wrong.rc, 3, wrong.out)
        self.assertIn("1.13.4", wrong.out)
        self.assertEqual(self.cleanup("--env", "course", "--region", REGION, "--confirm", "a" * 64, "--plan", "x", "--prepare").rc, 2)
        self.assertEqual(self.cleanup("--env", "course", "--region", REGION, "--execute", "--profile", "p", "--confirm", "a" * 64).rc, 2, "--confirm needs --plan")
        self.assertEqual(self.cleanup("--env", "course", "--region", REGION, "--plan", "x").rc, 2, "--plan needs --confirm")
        self.assertEqual(self.cleanup("--env", "course", "--region", REGION, "--image-revision", "c" * 40).rc, 2, "--image-revision needs --prepare")
        self.assertEqual(self.cleanup("--env", "course", "--region", REGION, "--prepare", "--image-revision", "abc").rc, 2)


class CleanupPolicyConfigTests(CleanupBase):
    def test_policy_rules_are_pinned_not_environment_overridable(self):
        result = self.cleanup(
            "--env", "course", "--region", REGION,
            CLEANUP_PRESERVE_TYPE_RULES="x", CLEANUP_PRESERVE_ADDRESS_RULES="x.", CLEANUP_TEARDOWN_ADDRESS_RULES="module.datalake.",
            CLEANUP_PROTECTION_RULES="aws_lb:enable_deletion_protection=false", CLEANUP_PREPARE_ALLOWED_ATTRS="aws_instance:anything",
        )
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("CONFIG-IGNORED", result.stdout)
        self.assertIn("PRESERVE-RULES types: aws_s3_bucket,", result.stdout)
        self.assertNotIn("TEARDOWN-RULES addresses: module.datalake.", result.stdout)
        self.assertIn("PROTECTION-RULES: aws_neptune_cluster:deletion_protection=true", result.stdout)


class CleanupListingTests(CleanupBase):
    def test_listing_builds_a_policy_compliant_target_plan_lists_every_action_and_refuses_without_destroying(self):
        result = self.listing()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("RESULT: REFUSED step=confirm", result.stdout)
        # Classification: teardown addresses become -target; preserved and unlisted ones never do.
        targets = sorted(l[len("TEARDOWN-TARGET: "):] for l in result.stdout.splitlines() if l.startswith("TEARDOWN-TARGET: "))
        self.assertEqual(targets, EXPECTED_TARGETS)
        plan_path = self.plan_file_from(result.stdout)
        self.assertIsNotNone(plan_path, result.stdout)
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " " and "-destroy" in a]
        self.assertEqual(len(plans), 1)
        self.assertEqual(sorted(w[len("-target="):] for w in plans[0].split() if w.startswith("-target=")), EXPECTED_TARGETS)
        self.assertNotIn("datalake", plans[0].replace("var-file", "").replace("/source/", ""))
        self.assertNotIn("aws_kms_key", plans[0])
        self.assertIn("-var=cleanup_mode=true", plans[0])
        self.assertIn("-out=%s" % os.path.realpath(plan_path), plans[0])
        # The destroy root runs from the materialized, state-bound copy of the committed source.
        for sub, chdir, files, binding in self.chdir_lines():
            if sub in ("plan", "show", "init", "state"):
                self.assertIn("/target/plans/", chdir) if "deployer" not in chdir else None
        self.assertTrue(any(binding == os.path.realpath(self.state_path()) for _s, _c, _f, binding in self.chdir_lines()))
        # The actual destructive actions are printed, complete and sorted.
        printed = [l[len("DESTROY-ACTION: "):] for l in result.stdout.splitlines() if l.startswith("DESTROY-ACTION: ")]
        self.assertEqual(printed, SORTED_ACTIONS)
        # The token binds the exact saved plan, the live account, region and environment.
        plan_sha = self.sha_of(plan_path)
        self.assertIn("DESTROY-PLAN-SHA256: %s" % plan_sha, result.stdout)
        self.assertEqual(self.token_of(result.stdout), expected_token(plan_sha, account_hash(), REGION, "course", SORTED_ACTIONS))
        self.assertIn("CONFIRM-BINDING: plan_sha256=%s account_sha256=%s region=%s environment=course actions=4" % (plan_sha, account_hash(), REGION), result.stdout)
        self.assertIn("--confirm %s --plan %s" % (self.token_of(result.stdout), plan_path), result.out)
        # Nothing destructive ran.
        self.assertEqual(self.applied(), [])
        self.assertEqual([a for a in self.destroy_calls() if " apply " in " " + a + " "], [])
        # Private outputs: ignored directory, 0700; files 0600.
        for suffix in ("", ".json", ".txt", ".log"):
            path = plan_path + suffix
            self.assertTrue(os.path.isfile(path), path)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600, path)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(plan_path)).st_mode), 0o700)
        evidence = self.latest_evidence()
        for name in ("before-inventory.txt", "destroy-plan.sha256", "destroy-actions.txt"):
            self.assertTrue(os.path.exists(os.path.join(evidence, name)), name)
        with open(os.path.join(evidence, "destroy-actions.txt")) as handle:
            self.assertEqual(handle.read().splitlines(), SORTED_ACTIONS)
        # Hygiene.
        for forbidden in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, self.private_vars, PRIVATE_CANARY):
            self.assertNotIn(forbidden, result.out)

    def chdir_lines(self):
        path = self.log + ".chdir"
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.rstrip("\n").split("\t") for line in handle]

    def test_every_preserved_class_in_the_plan_is_refused_and_no_token_is_offered(self):
        protected = {
            "s3 bucket": ('module.datalake.aws_s3_bucket.zone["evidence"]', "aws_s3_bucket", ["delete"]),
            "s3 bucket policy": ('module.datalake.aws_s3_bucket_policy.tls["curated"]', "aws_s3_bucket_policy", ["delete"]),
            "s3 object anywhere": ("module.workflow.aws_s3_object.definition", "aws_s3_object", ["delete"]),
            "s3 vectors index": ('module.s3vectors.aws_s3vectors_index.document', "aws_s3vectors_index", ["delete"]),
            "kms key": ("module.identity.aws_kms_key.data", "aws_kms_key", ["delete"]),
            "kms alias": ("module.identity.aws_kms_alias.data", "aws_kms_alias", ["delete"]),
            "log group in a teardown module": ("module.runtime.aws_cloudwatch_log_group.extra", "aws_cloudwatch_log_group", ["delete"]),
            "grading log group": ('module.observability.aws_cloudwatch_log_group.service["query-api"]', "aws_cloudwatch_log_group", ["delete"]),
            "state lock table": ("module.foundation.aws_dynamodb_table.lock", "aws_dynamodb_table", ["delete"]),
            "state bucket": ("module.foundation.aws_s3_bucket.state", "aws_s3_bucket", ["delete"]),
            "replaced bucket": ('module.datalake.aws_s3_bucket.zone["curated"]', "aws_s3_bucket", ["delete", "create"]),
        }
        for label, change in protected.items():
            with self.subTest(label):
                show = self.show_with(TEARDOWN_CHANGES + [change], "protected.json")
                open(self.log, "w").close()
                result = self.listing(FAKE_SHOW_JSON=show)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "destroy-policy", result.steps())
                self.assertIn("POLICY-VIOLATION: protected resource would be", result.stdout)
                self.assertIn(change[0].split("[")[0], result.stdout)
                self.assertIsNone(self.token_of(result.stdout), "no confirmation token for a violating plan")
                self.assertEqual(self.applied(), [])

    def test_an_unlisted_delete_is_refused(self):
        for label, change in {
            "rogue resource": ("aws_instance.rogue", "aws_instance", ["delete"]),
            "deployment role": ("module.identity.aws_iam_role.deployment", "aws_iam_role", ["delete"]),
            "root guard": ("terraform_data.configuration_guard", "terraform_data", ["delete"]),
        }.items():
            with self.subTest(label):
                show = self.show_with(TEARDOWN_CHANGES + [change], "unlisted.json")
                result = self.listing(FAKE_SHOW_JSON=show)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "destroy-policy")
                self.assertIn("POLICY-VIOLATION: delete is not in the teardown set: %s" % change[0], result.stdout)
                self.assertIsNone(self.token_of(result.stdout))
                self.assertEqual(self.applied(), [])

    def test_a_non_delete_action_in_a_destroy_plan_is_refused(self):
        show = self.show_with(TEARDOWN_CHANGES + [("module.network.aws_vpc.course", "aws_vpc", ["update"])], "update.json")
        result = self.listing(FAKE_SHOW_JSON=show)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("unexpected update action in a destroy plan", result.stdout)

    def test_nothing_to_tear_down_when_only_preserved_resources_are_in_state(self):
        result = self.listing(FAKE_STATE_LIST=";".join(STATE[:3]))
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("RESULT: PASS no teardown-class resource is in state", result.stdout)
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [])

    def test_state_list_failure_on_the_destroy_root_stops_the_run(self):
        result = self.listing(FAKE_TF_STATE_RC="1")
        self.assertEqual(result.rc, 5, result.out)
        self.assertEqual(self.destroy_calls(), [])

    def test_plan_failure_is_redacted_and_destroys_nothing(self):
        emit = "Error: bad value %s for var.notification_email in account %s" % (PRIVATE_CANARY, FAKE_ACCOUNT)
        result = self.listing(FAKE_TF_PLAN_RC="1", FAKE_EMIT=emit)
        self.assertEqual(result.rc, 5, result.out)
        for canary in (PRIVATE_CANARY, FAKE_ACCOUNT):
            self.assertNotIn(canary, result.out)
        logs = glob.glob(os.path.join(self.plans_root(), "*", "destroy-course.tfplan.log"))
        self.assertEqual(len(logs), 1)
        with open(logs[0]) as handle:
            retained = handle.read()
        self.assertNotIn(PRIVATE_CANARY, retained)
        self.assertNotIn(FAKE_ACCOUNT, retained)
        self.assertEqual(self.applied(), [])

    def test_execute_needs_profile_and_private_vars(self):
        no_profile = self.cleanup("--env", "course", "--region", REGION, "--execute")
        self.assertEqual(no_profile.rc, 3, no_profile.out)
        no_vars = self.cleanup("--env", "course", "--region", REGION, "--profile", "p", "--execute", SCHOLARCHAIN_TF_PRIVATE_VARS=None)
        self.assertEqual(no_vars.rc, 3, no_vars.out)
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])

    def test_a_missing_live_state_file_is_refused_before_any_aws_command_other_than_the_identity(self):
        os.remove(self.state_path())
        result = self.listing()
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "source")
        self.assertEqual([a for _n, a in self.calls("aws") if not a.startswith("sts ")], [])
        self.assertEqual(self.destroy_calls(), [])

    def test_commands_use_the_timeout_helper_and_trace_holds_no_secret(self):
        result = self.listing()
        self.assertEqual(len(self.timeout_helper_lines()), len(self.calls()))
        with open(self.timeout_log) as handle:
            trace = handle.read()
        for forbidden in (FAKE_SECRET, FAKE_TOKEN, FAKE_ACCOUNT, self.private_vars, PRIVATE_CANARY):
            self.assertNotIn(forbidden, result.out)
            self.assertNotIn(forbidden, trace)


class CleanupConfirmTests(CleanupBase):
    def listed(self, **env):
        first = self.listing(**env)
        self.assertEqual(first.rc, 3, first.out)
        token = self.token_of(first.stdout)
        self.assertIsNotNone(token)
        self.plan_path = self.plan_file_from(first.stdout)
        self.assertIsNotNone(self.plan_path)
        self.listing_evidence = self.latest_evidence()
        return token

    def saved_plan_sha(self):
        return self.sha_of(self.plan_path)

    def test_matching_token_applies_the_verified_copy_of_the_exact_saved_plan(self):
        token = self.listed()
        listing_sha = self.saved_plan_sha()
        open(self.log, "w").close()
        result = self.confirm(token, self.plan_path)
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS"))
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [], "the confirmed run does NOT re-plan")
        applied = self.applied()
        self.assertEqual(len(applied), 1)
        self.assertNotEqual(os.path.realpath(applied[0][0]), os.path.realpath(self.plan_path), "the verified private copy is applied, not the mutable saved file")
        self.assertEqual(applied[0][1], listing_sha, "the applied bytes are exactly the listed plan")
        applies = [a for n, a in self.calls("terraform") if " apply " in " " + a + " "]
        self.assertEqual(len(applies), 1)
        self.assertNotIn("-auto-approve", applies[0])
        order = result.steps()
        self.assertLess(order.index("account-identity"), order.index("verify-saved-plan"))
        self.assertLess(order.index("verify-saved-plan"), order.index("destroy-apply"))
        self.assertLess(order.index("destroy-apply"), order.index("after-inventory"))
        evidence = self.latest_evidence()
        self.assertNotEqual(evidence, self.listing_evidence, "each run has its own fresh evidence directory")
        with open(os.path.join(evidence, "destroy-plan.sha256")) as handle:
            self.assertTrue(handle.read().startswith(listing_sha))
        for name in ("before-inventory.txt", "after-inventory.txt", "destroy-actions.txt"):
            self.assertTrue(os.path.exists(os.path.join(evidence, name)), name)
        printed = [l[len("DESTROY-ACTION: "):] for l in result.stdout.splitlines() if l.startswith("DESTROY-ACTION: ")]
        self.assertEqual(printed, SORTED_ACTIONS, "the confirmed run prints the exact actions again")
        for forbidden in (FAKE_ACCOUNT, FAKE_SECRET, FAKE_TOKEN, self.private_vars, PRIVATE_CANARY):
            self.assertNotIn(forbidden, result.out)

    def test_wrong_or_mistyped_token_refuses_and_destroys_nothing(self):
        self.listed()
        result = self.confirm("0" * 64, self.plan_path)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "verify-saved-plan")
        self.assertIn("does not match the exact saved plan", result.out)
        self.assertEqual(self.applied(), [])

    def test_confirm_without_a_saved_plan_is_refused(self):
        missing = os.path.join(self.plans_root(), "no-such-run", "destroy-course.tfplan")
        result = self.confirm("a" * 64, missing)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("no saved destroy plan", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_plan_outside_the_plan_directory_is_refused(self):
        token = self.listed()
        outside = os.path.join(self.tmp, "outside.tfplan")
        with open(self.plan_path, "rb") as source, open(outside, "wb") as target:
            target.write(source.read())
        result = self.confirm(token, outside)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("must live inside target/plans", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_plan_reached_through_a_symlink_is_refused(self):
        token = self.listed()
        link = os.path.join(self.plans_root(), "alias.tfplan")
        os.symlink(self.plan_path, link)
        result = self.confirm(token, link)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("symlink", result.out)
        self.assertEqual(self.applied(), [])

    def test_a_plan_changed_after_the_listing_is_refused(self):
        token = self.listed()
        with open(self.plan_path, "ab") as handle:
            handle.write(b"modified after listing\n")
        result = self.confirm(token, self.plan_path)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("does not match the exact saved plan", result.out)
        self.assertEqual(self.applied(), [])

    def test_an_action_list_changed_after_the_listing_is_refused(self):
        token = self.listed()
        grown = self.show_with(TEARDOWN_CHANGES + [("module.network.aws_subnet.data", "aws_subnet", ["delete"])], "grown.json")
        result = self.confirm(token, self.plan_path, FAKE_SHOW_JSON=grown)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.applied(), [])

    def test_a_saved_plan_that_now_touches_a_protected_resource_is_refused_even_with_a_token(self):
        token = self.listed()
        protected = self.show_with(TEARDOWN_CHANGES + [("module.datalake.aws_s3_bucket.zone", "aws_s3_bucket", ["delete"])], "now-protected.json")
        result = self.confirm(token, self.plan_path, FAKE_SHOW_JSON=protected)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("POLICY-VIOLATION", result.stdout)
        self.assertEqual(self.applied(), [])

    def test_a_token_from_another_account_is_refused(self):
        """Token reuse across accounts: a listing under account A cannot be confirmed under account B."""
        token = self.listed()
        result = self.confirm(token, self.plan_path, FAKE_ACCOUNT_ID=OTHER_ACCOUNT)
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("does not match the exact saved plan, the live account", result.out)
        self.assertEqual(self.applied(), [])
        for account in (FAKE_ACCOUNT, OTHER_ACCOUNT):
            self.assertNotIn(account, result.out)
        # Hand-derived: the other account's token for the very same plan and actions is different.
        other = expected_token(self.saved_plan_sha(), account_hash(OTHER_ACCOUNT), REGION, "course", SORTED_ACTIONS)
        self.assertNotEqual(other, token)

    def test_a_token_for_another_region_is_refused(self):
        token = self.listed()
        result = self.cleanup("--env", "course", "--region", "us-west-2", "--profile", "approved", "--execute", "--confirm", token, "--plan", self.plan_path)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(self.applied(), [])

    def test_the_original_saved_plan_replaced_after_verification_does_not_change_what_is_applied(self):
        token = self.listed()
        listing_sha = self.saved_plan_sha()
        result = self.confirm(token, self.plan_path, FAKE_REPLACE_FILE=self.plan_path)
        self.assertEqual(result.rc, 0, result.out)
        applied = self.applied()
        self.assertEqual(len(applied), 1)
        self.assertEqual(applied[0][1], listing_sha)

    def test_the_verified_copy_altered_before_apply_is_refused(self):
        token = self.listed()
        result = self.confirm(token, self.plan_path, FAKE_TAMPER_ARG="1")
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("verified plan copy changed after verification", result.out)
        self.assertEqual(self.applied(), [])

    def test_failed_first_pass_is_partial_with_the_item_24_note(self):
        token = self.listed()
        result = self.confirm(token, self.plan_path, FAKE_TF_APPLY_RC="1")
        self.assertEqual(result.rc, 5, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PARTIAL"))
        self.assertIn("aws_eip.nat", result.out)
        self.assertIn("do not widen IAM", result.out)
        self.assertTrue(os.path.exists(os.path.join(self.latest_evidence(), "after-inventory.txt")))


class CleanupProtectionTests(CleanupBase):
    """R5: active deletion protection blocks the destructive sequence until a separately approved preparation released it."""

    def protected_state(self, *kinds, name="state-protected.json"):
        resources = []
        for kind in ("neptune", "alb", "dynamodb", "ecr"):
            resources.append(PROTECTED[kind][:3] if kind in kinds else RELEASED[kind])
        return self.write_state_json(resources, name)

    def test_every_kind_of_active_protection_blocks_the_listing(self):
        for kind, (address, _rtype, _values, shown) in PROTECTED.items():
            with self.subTest(kind):
                open(self.log, "w").close()
                result = self.listing(FAKE_STATE_JSON=self.protected_state(kind))
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "protection-check", result.steps())
                self.assertIn("PROTECTION-ACTIVE: %s %s" % (address, shown), result.stdout)
                self.assertIn("PREPARE-REQUIRED", result.out)
                self.assertIn("scripts/cleanup.sh --prepare --execute", result.out)
                self.assertIsNone(self.token_of(result.stdout), "no token while protection is active")
                self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [], "no destroy plan is even built")
                self.assertEqual(self.applied(), [])

    def test_all_four_protections_are_listed_together(self):
        result = self.listing(FAKE_STATE_JSON=self.protected_state("neptune", "alb", "dynamodb", "ecr"))
        self.assertEqual(result.rc, 3, result.out)
        lines = [l for l in result.stdout.splitlines() if l.startswith("PROTECTION-ACTIVE: ")]
        self.assertEqual(len(lines), 4)

    def test_a_protected_preserved_resource_is_not_a_blocker(self):
        """The state lock table is preserved and protected on purpose: only teardown resources gate the sequence."""
        resources = list(RELEASED.values()) + [(LOCK_TABLE, "aws_dynamodb_table", {"deletion_protection_enabled": True})]
        result = self.listing(FAKE_STATE_JSON=self.write_state_json(resources, "state-with-lock.json"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "confirm", "the listing went on to the token step")
        self.assertNotIn("PROTECTION-ACTIVE", result.stdout)

    def test_active_protection_also_blocks_a_confirmed_run_even_with_a_valid_token(self):
        listing = self.listing()
        token = CleanupBase.token_of(listing.stdout)
        plan = self.plan_file_from(listing.stdout)
        result = self.confirm(token, plan, FAKE_STATE_JSON=self.protected_state("dynamodb"))
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "protection-check")
        self.assertIn("PREPARE-REQUIRED", result.out)
        self.assertEqual(self.applied(), [])

    def test_after_preparation_the_sequence_proceeds_to_the_token_step_and_the_confirmed_run_destroys(self):
        blocked = self.listing(FAKE_STATE_JSON=self.protected_state("neptune", "alb", "dynamodb", "ecr"))
        self.assertEqual(blocked.steps()[-1], "protection-check")
        # The preparation was applied (state fixture with every protection released).
        proceeded = self.listing(FAKE_STATE_JSON=self.released_state)
        self.assertEqual(proceeded.rc, 3, proceeded.out)
        self.assertEqual(proceeded.steps()[-1], "confirm", "now it reaches the human confirmation token")
        token = self.token_of(proceeded.stdout)
        self.assertIsNotNone(token)
        done = self.confirm(token, self.plan_file_from(proceeded.stdout), FAKE_STATE_JSON=self.released_state)
        self.assertEqual(done.rc, 0, done.out)
        self.assertEqual(len(self.applied()), 1)

    def test_the_state_is_read_with_show_json_into_a_private_temp_file_and_no_value_is_printed(self):
        secret = "STATE-PRIVATE-VALUE-5512"
        resources = list(RELEASED.values()) + [("module.runtime.aws_ecs_service.service[\"query-api\"]", "aws_ecs_service", {"note": secret})]
        result = self.listing(FAKE_STATE_JSON=self.write_state_json(resources, "state-secret.json"))
        self.assertNotIn(secret, result.out)
        shows = [a for n, a in self.calls("terraform") if a.endswith(" show -json")]
        self.assertGreaterEqual(len(shows), 1, "the current state is read with `terraform show -json`")
        for path, _dirs, files in os.walk(self.repo):
            for name in files:
                if ".git" in path.split(os.sep):
                    continue
                with open(os.path.join(path, name), "rb") as handle:
                    self.assertNotIn(secret.encode(), handle.read(), "the state values are never persisted: " + name)

    def test_the_two_pass_item_24_note_and_the_no_iam_widening_rule_are_kept(self):
        result = self.cleanup("--env", "course", "--region", REGION, "--help")
        self.assertEqual(result.rc, 0)
        listing = self.listing()
        token = self.token_of(listing.stdout)
        failed = self.confirm(token, self.plan_file_from(listing.stdout), FAKE_TF_APPLY_RC="1")
        self.assertIn("aws_eip.nat", failed.out)
        self.assertIn("do not widen IAM", failed.out)


class CleanupPrepareTests(CleanupBase):
    """R5: `cleanup.sh --prepare` plans the release of the protections and refuses anything but protection/force flag updates."""

    def prepare_show(self, *kinds, extra=(), image_revision=None, name="prepare-show.json"):
        changes = []
        for kind in kinds:
            address, rtype, before, _shown = PROTECTED[kind]
            after = dict(RELEASED[kind][2])
            changes.append(update_change(address, rtype, before, after))
        return self.write_show_json([], image_revision=image_revision, extra_changes=changes + list(extra), name=name)

    def protected_state(self, *kinds):
        resources = []
        for kind in ("neptune", "alb", "dynamodb", "ecr"):
            resources.append(PROTECTED[kind][:3] if kind in kinds else RELEASED[kind])
        return self.write_state_json(resources, "state-protected.json")

    def prepare(self, *extra, kinds=("neptune", "alb", "dynamodb", "ecr"), show=None, **env):
        merged = {"FAKE_STATE_JSON": self.protected_state(*kinds), "FAKE_SHOW_JSON": show or self.prepare_show(*kinds)}
        merged.update(env)
        return self.cleanup("--env", "course", "--region", REGION, "--profile", "approved", "--prepare", "--execute", *extra, **merged)

    def test_dry_run_prints_the_preparation_commands_and_runs_nothing(self):
        result = self.cleanup("--env", "course", "--region", REGION, "--prepare")
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: DRY-RUN"))
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])
        out = result.stdout
        for step in ("source", "protection-check", "prepare-plan"):
            self.assertIn(step, result.steps())
        self.assertRegex(out, r"show -json\s*\n", "the protection check reads the current state (no plan file argument)")
        self.assertIn("-var=cleanup_mode=true", out)
        self.assertIn("-target=<each-protected-teardown-resource-found-by-the-protection-check>", out)
        self.assertNotIn("plan -destroy", out)
        self.assertIn("scripts/deploy.sh --stage cleanup-prepare", out)
        self.assertIn("APPROVED_STAGE=cleanup-prepare", out)
        self.assertFalse(os.path.exists(self.plans_root()))

    def test_it_plans_exactly_the_protected_teardown_resources_with_cleanup_mode_and_never_applies(self):
        result = self.prepare()
        self.assertEqual(result.rc, 0, result.out)
        self.assertTrue(result.result_line().startswith("RESULT: PASS"))
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " "]
        self.assertEqual(len(plans), 1)
        words = plans[0].split()
        self.assertNotIn("-destroy", words, "a normal plan, not a destroy plan")
        self.assertIn("-var=cleanup_mode=true", words)
        self.assertEqual(sorted(w[len("-target="):] for w in words if w.startswith("-target=")), sorted([NEPTUNE, ALB, TABLE, ECR]))
        self.assertNotIn("datalake", plans[0].replace("var-file", "").replace("/source/", ""), "preserved resources are never targeted")
        self.assertEqual(self.applied(), [])
        self.assertEqual(self.mutating_calls(), [])

    def test_the_preparation_receipt_and_the_candidate_approval_lines(self):
        result = self.prepare()
        plan_path = self.plan_file_from(result.stdout, "PLAN-FILE")
        self.assertIsNotNone(plan_path)
        receipt_path = plan_path + ".receipt.json"
        with open(receipt_path) as handle:
            receipt = json.load(handle)
        self.assertEqual(receipt["purpose"], "cleanup-prepare")
        self.assertEqual(receipt["plan_sha256"], self.sha_of(plan_path))
        self.assertEqual(receipt["commit"], self.head())
        self.assertEqual(receipt["env"], "course")
        self.assertEqual(receipt["state"]["lineage"], STATE_LINEAGE)
        self.assertEqual(receipt["source_tree_sha256"], self.tree_sha())
        self.assertIsNone(receipt["image_revision"])
        self.assertEqual(receipt["summary"]["destroy"], 0)
        self.assertEqual(receipt["summary"]["add"], 0)
        self.assertEqual(receipt["summary"]["change"], 4)
        self.assertIn("APPROVED_STAGE=cleanup-prepare", result.stdout)
        self.assertIn("APPROVED_PLAN_SHA256=%s" % self.sha_of(plan_path), result.stdout)
        self.assertIn("APPROVED_RECEIPT_SHA256=%s" % self.sha_of(receipt_path), result.stdout)
        self.assertIn("APPROVED_ENVIRONMENT=course", result.stdout)
        self.assertEqual(stat.S_IMODE(os.stat(receipt_path).st_mode), 0o600)
        for forbidden in (FAKE_ACCOUNT, PRIVATE_CANARY, self.private_vars):
            self.assertNotIn(forbidden, result.out)

    def test_the_deployed_image_revision_is_passed_so_no_task_definition_changes(self):
        revision = "c" * 40
        show = self.prepare_show("dynamodb", image_revision=revision)
        result = self.prepare("--image-revision", revision, kinds=("dynamodb",), show=show)
        self.assertEqual(result.rc, 0, result.out)
        plans = [a for n, a in self.calls("terraform") if " plan " in " " + a + " "]
        self.assertIn("-var=image_revision=%s" % revision, plans[0])
        with open(self.plan_file_from(result.stdout, "PLAN-FILE") + ".receipt.json") as handle:
            self.assertEqual(json.load(handle)["image_revision"], revision)

    def test_a_plan_with_the_wrong_image_revision_is_a_gate_failure(self):
        revision = "c" * 40
        result = self.prepare("--image-revision", revision, kinds=("dynamodb",), show=self.prepare_show("dynamodb"))
        self.assertEqual(result.rc, 4, result.out)

    def test_no_active_protection_needs_no_preparation(self):
        result = self.cleanup("--env", "course", "--region", REGION, "--profile", "approved", "--prepare", "--execute")
        self.assertEqual(result.rc, 0, result.out)
        self.assertIn("no preparation is needed", result.stdout)
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [])

    def test_a_preparation_plan_with_unexpected_changes_is_refused_and_no_receipt_is_written(self):
        base = lambda: self.prepare_show("dynamodb")  # noqa: E731
        bad = {
            "creates a resource": update_change("module.runtime.aws_ecr_repository.new", "aws_ecr_repository", {}, {}) | {"change": {"actions": ["create"], "before": None, "after": {"force_delete": True}, "after_unknown": {}}},
            "deletes a resource": {"address": "module.network.aws_nat_gateway.course", "type": "aws_nat_gateway", "change": {"actions": ["delete"], "before": {}, "after": None, "after_unknown": {}}},
            "replaces a resource": {"address": TABLE, "type": "aws_dynamodb_table", "change": {"actions": ["delete", "create"], "before": {}, "after": {}, "after_unknown": {}}},
            "changes another attribute": update_change(TABLE, "aws_dynamodb_table", {"deletion_protection_enabled": True, "billing_mode": "PAY_PER_REQUEST"}, {"deletion_protection_enabled": False, "billing_mode": "PROVISIONED"}),
            "updates a preserved bucket": update_change('module.datalake.aws_s3_bucket.zone["curated"]', "aws_s3_bucket", {"force_destroy": False}, {"force_destroy": True}),
            "updates an unlisted resource": update_change("aws_instance.rogue", "aws_instance", {"deletion_protection_enabled": True}, {"deletion_protection_enabled": False}),
            "updates the deployment role": update_change("module.identity.aws_iam_role.deployment", "aws_iam_role", {"x": 1}, {"x": 2}),
            "changes a flag of the wrong type": update_change(TABLE, "aws_dynamodb_table", {"force_delete": False}, {"force_delete": True}),
        }
        for label, change in bad.items():
            with self.subTest(label):
                open(self.log, "w").close()
                show = self.write_show_json([], extra_changes=[change], name="bad.json")
                result = self.prepare(kinds=("dynamodb",), show=show)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "prepare-policy")
                self.assertIn("POLICY-VIOLATION", result.stdout)
                self.assertIn("not offered for approval", result.out)
                self.assertNotIn("APPROVED_STAGE=cleanup-prepare", result.stdout)
                self.assertEqual(self.applied(), [])
        self.assertEqual(glob.glob(os.path.join(self.plans_root(), "*", "*.receipt.json")), [], "no receipt for a refused plan")
        del base

    def test_a_preparation_plan_for_another_account_or_environment_is_refused(self):
        for label, kwargs in (("account", {"account": OTHER_ACCOUNT}), ("environment", {"environment": "staging"}), ("project", {"project": "other"})):
            with self.subTest(label):
                show = self.write_show_json([], extra_changes=[update_change(TABLE, "aws_dynamodb_table", {"deletion_protection_enabled": True}, {"deletion_protection_enabled": False})], name="wrong.json", **kwargs)
                result = self.prepare(kinds=("dynamodb",), show=show)
                self.assertEqual(result.rc, 4, result.out)
                self.assertNotIn(OTHER_ACCOUNT, result.out)

    def test_a_dirty_tree_is_recorded_so_the_deploy_stage_will_refuse_it(self):
        self.write("junk.txt", "x\n")
        result = self.prepare()
        self.assertEqual(result.rc, 0, result.out)
        with open(self.plan_file_from(result.stdout, "PLAN-FILE") + ".receipt.json") as handle:
            self.assertFalse(json.load(handle)["clean"])

    def test_a_missing_state_is_refused_before_any_plan(self):
        os.remove(self.state_path())
        result = self.prepare()
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual([a for n, a in self.calls("terraform") if " plan " in " " + a + " "], [])


class CleanupOutputConfinementTests(CleanupBase):
    """R2: cleanup outputs are fresh, confined, symlink-safe and distinct."""

    def test_each_run_has_its_own_run_and_evidence_directory(self):
        first = self.listing()
        second = self.listing()
        self.assertEqual((first.rc, second.rc), (3, 3))
        self.assertNotEqual(self.plan_file_from(first.stdout), self.plan_file_from(second.stdout))
        self.assertEqual(len(self.evidence_dirs()), 2)
        self.assertEqual(stat.S_IMODE(os.stat(self.evidence_dirs()[0]).st_mode), 0o700)

    def test_a_preexisting_symlink_at_each_evidence_file_is_refused_and_the_canary_is_unchanged(self):
        canary = os.path.join(self.tmp, "canary.txt")
        for name in ("before-inventory.txt", "after-inventory.txt", "destroy-plan.sha256", "destroy-actions.txt"):
            with self.subTest(name):
                with open(canary, "w") as handle:
                    handle.write("CANARY-UNTOUCHED\n")
                evidence = os.path.join(self.evidence_root(), "victim-" + name.split(".")[0])
                os.makedirs(evidence, exist_ok=True)
                os.symlink(canary, os.path.join(evidence, name))
                open(self.log, "w").close()
                result = self.execute("--evidence-dir", evidence)
                self.assertEqual(result.rc, 3, result.out)
                self.assertEqual(result.steps()[-1], "output-paths")
                self.assertRegex(result.out, "already exists|symlink")
                with open(canary) as handle:
                    self.assertEqual(handle.read(), "CANARY-UNTOUCHED\n")
                self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [], "refused before any command")

    def test_an_existing_evidence_file_is_never_overwritten(self):
        evidence = os.path.join(self.evidence_root(), "earlier")
        os.makedirs(evidence)
        with open(os.path.join(evidence, "before-inventory.txt"), "w") as handle:
            handle.write("EARLIER\n")
        result = self.execute("--evidence-dir", evidence)
        self.assertEqual(result.rc, 3, result.out)
        with open(os.path.join(evidence, "before-inventory.txt")) as handle:
            self.assertEqual(handle.read(), "EARLIER\n")

    def test_an_evidence_dir_outside_the_evidence_root_is_refused(self):
        for target in (os.path.join(self.tmp, "elsewhere"), os.path.join(self.repo, "docs", "evidence"), os.path.join(self.repo, "target", "plans", "x")):
            with self.subTest(target):
                result = self.execute("--evidence-dir", target)
                self.assertEqual(result.rc, 3, result.out)
                self.assertIn("must live inside target/cleanup-evidence", result.out)
                self.assertFalse(os.path.exists(target))

    def test_an_evidence_dir_that_escapes_through_dotdot_or_a_symlinked_directory_is_refused(self):
        os.makedirs(self.evidence_root())
        outside = os.path.join(self.tmp, "outside-evidence")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(self.evidence_root(), "link"))
        for target in (os.path.join(self.evidence_root(), "..", "x"), os.path.join(self.evidence_root(), "link", "x")):
            with self.subTest(target):
                result = self.execute("--evidence-dir", target)
                self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(os.listdir(outside), [])

    def test_an_evidence_dir_that_aliases_the_private_plan_directory_is_refused(self):
        """Colliding outputs: with both pinned directories equal, evidence would land beside the private plan outputs."""
        self.use_config(CLEANUP_EVIDENCE_DIR="target/plans")
        result = self.execute()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("separate from the private plan directory", result.out)
        self.assertEqual([c for c in self.calls() if not c[1].startswith("version")], [])

    def test_an_evidence_dir_nested_in_the_plan_directory_is_refused(self):
        self.use_config(CLEANUP_EVIDENCE_DIR="target/plans/evidence")
        result = self.execute()
        self.assertEqual(result.rc, 3, result.out)
        self.assertIn("separate from the private plan directory", result.out)

    def test_dry_run_also_validates_the_evidence_path(self):
        evidence = os.path.join(self.evidence_root(), "dry")
        os.makedirs(evidence)
        os.symlink(os.path.join(self.tmp, "nowhere"), os.path.join(evidence, "before-inventory.txt"))
        result = self.cleanup("--env", "course", "--region", REGION, "--evidence-dir", evidence)
        self.assertEqual(result.rc, 3, result.out)
        self.assertEqual(result.steps()[-1], "output-paths")


if __name__ == "__main__":
    unittest.main()
