"""state_bind.py, records.py and the new verify.py subcommands (hand-derived inputs and expectations)."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR, sha256_bytes

STATE_BIND = os.path.join(SCRIPTS_DIR, "lib", "state_bind.py")
RECORDS = os.path.join(SCRIPTS_DIR, "lib", "records.py")
VERIFY = os.path.join(SCRIPTS_DIR, "lib", "verify.py")
RULES = [
    "--preserve-types", "aws_s3_bucket,aws_kms_", "--preserve-addresses", "module.foundation.,module.datalake.",
    "--teardown-addresses", "module.runtime.,module.neptune.,module.dynamodb.",
]
ALLOWED = "aws_neptune_cluster:deletion_protection+skip_final_snapshot,aws_dynamodb_table:deletion_protection_enabled"


def run(script, args, **kwargs):
    return subprocess.run([sys.executable, "-I", script] + args, capture_output=True, text=True, timeout=60, **kwargs)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-state-")
        self.addCleanup(subprocess.run, ["rm", "-rf", self.tmp])

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)
        return path


class StateIdentityTests(Tmp):
    def test_only_lineage_serial_and_sha256_are_reported_and_resource_values_never_are(self):
        body = json.dumps({"version": 4, "serial": 12, "lineage": "L-1", "resources": [{"instances": [{"attributes": {"password": "TOP-SECRET-STATE-VALUE"}}]}]})
        path = self.write("terraform.tfstate", body)
        result = run(STATE_BIND, ["inspect", "--state", path])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {"present": True, "lineage": "L-1", "serial": 12, "sha256": sha256_bytes(body.encode())})
        self.assertNotIn("TOP-SECRET-STATE-VALUE", result.stdout + result.stderr)

    def test_an_absent_state_is_reported_as_not_present(self):
        result = run(STATE_BIND, ["inspect", "--state", os.path.join(self.tmp, "none.tfstate")])
        self.assertEqual(json.loads(result.stdout), {"present": False})

    def test_invalid_states_symlinks_and_directories_are_refused(self):
        real = self.write("real.tfstate", "{}")
        os.symlink(real, os.path.join(self.tmp, "link.tfstate"))
        os.makedirs(os.path.join(self.tmp, "dir.tfstate"))
        cases = {
            "not json": self.write("bad1.tfstate", "nope"),
            "no lineage": self.write("bad2.tfstate", '{"serial": 1}'),
            "boolean serial": self.write("bad3.tfstate", '{"lineage": "x", "serial": true}'),
            "list": self.write("bad4.tfstate", "[]"),
            "symlink": os.path.join(self.tmp, "link.tfstate"),
            "directory": os.path.join(self.tmp, "dir.tfstate"),
        }
        for label, path in cases.items():
            with self.subTest(label):
                result = run(STATE_BIND, ["inspect", "--state", path])
                self.assertEqual(result.returncode, 1)
                self.assertIn("STATE-BINDING-FAILED", result.stdout)


class StateCheckTests(Tmp):
    def receipt(self, state):
        return self.write("receipt.json", json.dumps({"state": state}))

    def live(self, lineage="L", serial=3, extra=""):
        body = json.dumps({"lineage": lineage, "serial": serial}) + extra
        return self.write("live.tfstate", body), sha256_bytes(body.encode())

    def test_every_difference_is_refused_with_its_own_reason(self):
        path, digest = self.live()
        good = {"present": True, "lineage": "L", "serial": 3, "sha256": digest}
        self.assertEqual(run(STATE_BIND, ["check", "--state", path, "--receipt", self.receipt(good)]).returncode, 0)
        cases = {
            "different lineage": (dict(good, lineage="OTHER"), "lineage differs"),
            "different serial": (dict(good, serial=4), "changed after the plan"),
            "different bytes": (dict(good, sha256="0" * 64), "changed after the plan"),
            "first deployment but a state exists": ({"present": False}, "a state file now exists"),
        }
        for label, (state, needle) in cases.items():
            with self.subTest(label):
                result = run(STATE_BIND, ["check", "--state", path, "--receipt", self.receipt(state)])
                self.assertEqual(result.returncode, 1)
                self.assertIn(needle, result.stdout)
        missing = run(STATE_BIND, ["check", "--state", os.path.join(self.tmp, "gone"), "--receipt", self.receipt(good)])
        self.assertEqual(missing.returncode, 1)
        self.assertIn("the live state file is missing", missing.stdout)
        absent_ok = run(STATE_BIND, ["check", "--state", os.path.join(self.tmp, "gone"), "--receipt", self.receipt({"present": False})])
        self.assertEqual(absent_ok.returncode, 0)

    def test_a_receipt_without_a_state_record_is_refused(self):
        path, _digest = self.live()
        for label, document in (("missing", {}), ("not a dict", {"state": 1}), ("no present flag", {"state": {"lineage": "L"}})):
            with self.subTest(label):
                receipt = self.write("r.json", json.dumps(document))
                result = run(STATE_BIND, ["check", "--state", path, "--receipt", receipt])
                self.assertEqual(result.returncode, 1)
                self.assertIn("holds no state record", result.stdout)

    def test_check_tree_and_receipt_field(self):
        receipt = self.write("r.json", json.dumps({"source_tree_sha256": "a" * 64, "image_revision": None, "purpose": "deploy-plan"}))
        self.assertEqual(run(STATE_BIND, ["check-tree", "--receipt", receipt, "--tree-sha256", "a" * 64]).returncode, 0)
        self.assertEqual(run(STATE_BIND, ["check-tree", "--receipt", receipt, "--tree-sha256", "b" * 64]).returncode, 1)
        self.assertEqual(run(STATE_BIND, ["receipt-field", "--receipt", receipt, "--key", "image_revision"]).stdout, "\n")
        self.assertEqual(run(STATE_BIND, ["receipt-field", "--receipt", receipt, "--key", "purpose"]).stdout, "deploy-plan\n")
        self.assertEqual(run(STATE_BIND, ["receipt-field", "--receipt", receipt, "--key", "state"]).returncode, 2, "only whitelisted scalar fields can be read")


class TreeHashAndBindingTests(Tmp):
    def test_tree_hash_is_hand_derived_from_sorted_path_sha_size_and_exec_bit(self):
        root = os.path.join(self.tmp, "tree")
        self.write("tree/a.tf", "x")
        self.write("tree/sub/b.tf", "yy")
        lines = ["a.tf %s 1 0" % sha256_bytes(b"x"), "sub/b.tf %s 2 0" % sha256_bytes(b"yy")]
        expected = hashlib.sha256("\n".join(lines).encode()).hexdigest()
        result = run(STATE_BIND, ["tree-hash", "--root", root])
        self.assertEqual(result.stdout.strip(), expected)
        os.chmod(os.path.join(root, "a.tf"), 0o755)
        changed = run(STATE_BIND, ["tree-hash", "--root", root]).stdout.strip()
        self.assertNotEqual(changed, expected, "the executable bit is part of the hash")
        self.write("tree/override.tf", "injected")
        self.assertNotEqual(run(STATE_BIND, ["tree-hash", "--root", root]).stdout.strip(), changed, "an added file changes the hash")

    def test_write_binding_points_the_local_backend_at_the_live_state(self):
        root = os.path.join(self.tmp, "root")
        self.write("root/main.tf", 'resource "terraform_data" "x" {}\n')
        state = os.path.join(self.tmp, "live", "terraform.tfstate")
        result = run(STATE_BIND, ["write-binding", "--root", root, "--state", state])
        self.assertEqual(result.returncode, 0, result.stdout)
        with open(os.path.join(root, "zz_scholarchain_state_binding.tf")) as handle:
            text = handle.read()
        self.assertIn('backend "local" {', text)
        self.assertIn('path = "%s"' % state, text)
        again = run(STATE_BIND, ["write-binding", "--root", root, "--state", state])
        self.assertEqual(again.returncode, 1, "never overwritten")

    def test_write_binding_refuses_a_source_that_already_declares_a_backend_or_an_unsafe_path(self):
        root = os.path.join(self.tmp, "root2")
        self.write("root2/main.tf", 'terraform {\n  backend "s3" {}\n}\n')
        refused = run(STATE_BIND, ["write-binding", "--root", root, "--state", os.path.join(self.tmp, "s.tfstate")])
        self.assertEqual(refused.returncode, 1)
        self.assertIn("declares a backend", refused.stdout)
        clean = os.path.join(self.tmp, "root3")
        self.write("root3/main.tf", "# nothing\n")
        for bad in ('/tmp/a"b', "/tmp/${evil}", "/tmp/../etc/x", "relative/path"):
            with self.subTest(bad):
                self.assertEqual(run(STATE_BIND, ["write-binding", "--root", clean, "--state", bad]).returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(clean, "zz_scholarchain_state_binding.tf")))


class PushRecordTests(Tmp):
    COMMIT = "a" * 40
    ACCOUNT = "b" * 64
    SERVICES = "query-api graph-service"
    REPOS = "p-course/query-api p-course/graph-service"

    def pushed(self, digests=None):
        digests = digests or {"query-api": "sha256:" + "1" * 64, "graph-service": "sha256:" + "2" * 64}
        return self.write("pushed.tsv", "".join("%s\tp-course/%s\t%s\tsha256:%s\n" % (s, s, d, "f" * 64) for s, d in digests.items()))

    def write_record(self, name="record.json", **overrides):
        out = os.path.join(self.tmp, "repo", name)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        args = ["write-push-record", "--root", os.path.join(self.tmp, "repo"), "--out", out, "--commit", overrides.get("commit", self.COMMIT),
                "--account-sha256", self.ACCOUNT, "--region", "us-east-2", "--environment", "course", "--run-id", "r1", "--pushed-utc", "2026-11-05T00:00:00Z",
                "--pushed", overrides.get("pushed") or self.pushed()]
        return run(RECORDS, args), out

    def check(self, path, **overrides):
        args = ["check-push-record", "--file", path, "--commit", overrides.get("commit", self.COMMIT), "--account-sha256", overrides.get("account", self.ACCOUNT),
                "--region", overrides.get("region", "us-east-2"), "--environment", overrides.get("environment", "course"),
                "--repositories", overrides.get("repositories", self.REPOS), "--services", overrides.get("services", self.SERVICES)]
        return run(RECORDS, args)

    def test_write_then_check_round_trips_and_prints_each_services_pushed_digest(self):
        written, out = self.write_record()
        self.assertEqual(written.returncode, 0, written.stdout)
        self.assertEqual(oct(os.stat(out).st_mode & 0o777), "0o600")
        checked = self.check(out)
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertEqual(checked.stdout.splitlines(), ["query-api sha256:" + "1" * 64, "graph-service sha256:" + "2" * 64])

    def test_the_record_is_created_exclusively(self):
        _w, out = self.write_record()
        again, _out = self.write_record()
        self.assertEqual(again.returncode, 1)
        self.assertIn("already exists", again.stdout)

    def test_each_mismatch_is_refused(self):
        _w, out = self.write_record()
        cases = {
            "commit": {"commit": "c" * 40},
            "account": {"account": "d" * 64},
            "region": {"region": "us-west-2"},
            "environment": {"environment": "staging"},
            "repositories": {"repositories": "p-course/query-api other/graph-service"},
            "services": {"services": "query-api graph-service extra"},
        }
        for label, overrides in cases.items():
            with self.subTest(label):
                result = self.check(out, **overrides)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("PUSH-RECORD-FAILED", result.stdout)

    def test_a_malformed_digest_is_refused_at_write_time(self):
        pushed = self.pushed({"query-api": "sha256:abc", "graph-service": "sha256:" + "2" * 64})
        written, _out = self.write_record(pushed=pushed)
        self.assertEqual(written.returncode, 1)


class PrespendClockTests(Tmp):
    def receipt(self, snapshot):
        return self.write("pre.json", json.dumps({
            "monitoring_confirmed_active": True, "cost_snapshot_utc": snapshot, "reported_spend_usd": 1, "unreported_usage_allowance_usd": 1,
            "reserves_usd": 1, "remaining_headroom_usd": 100,
        }))

    def check(self, receipt, clock=None, label=None):
        args = ["prespend", "--file", receipt, "--max-age-hours", "24", "--min-headroom", "20"]
        if clock:
            args += ["--clock-file", clock, "--label", label or "initial"]
        return run(VERIFY, args)

    def test_the_clock_decides_freshness_per_label_with_a_default(self):
        receipt = self.receipt("2026-11-05T00:00:00Z")
        clock = self.write("clock.json", json.dumps({"default": "2026-11-05T12:00:00Z", "push-query-api": "2026-11-06T01:00:00Z"}))
        self.assertEqual(self.check(receipt, clock, "initial").returncode, 0)
        self.assertEqual(self.check(receipt, clock, "terraform-apply").returncode, 0, "unknown labels use the default: 12 h old")
        late = self.check(receipt, clock, "push-query-api")
        self.assertEqual(late.returncode, 1)
        self.assertIn("25.0 h old", late.stdout, "hand-derived: 2026-11-05T00:00Z to 2026-11-06T01:00Z is 25 hours")

    def test_a_missing_or_malformed_clock_fails_closed(self):
        receipt = self.receipt("2026-11-05T00:00:00Z")
        for label, text in (("not json", "nope"), ("no usable time", json.dumps({"other": "x"})), ("bad time", json.dumps({"default": "yesterday"}))):
            with self.subTest(label):
                result = self.check(receipt, self.write("c.json", text))
                self.assertEqual(result.returncode, 1)
                self.assertIn("test clock file is unreadable", result.stdout)
        self.assertEqual(self.check(receipt, os.path.join(self.tmp, "absent.json")).returncode, 1)


class PreparePolicyTests(Tmp):
    def show(self, changes):
        return self.write("show.json", json.dumps({"resource_changes": changes}))

    def change(self, address, rtype, actions, before=None, after=None, unknown=None):
        return {"address": address, "type": rtype, "change": {"actions": actions, "before": before, "after": after, "after_unknown": unknown or {}}}

    def policy(self, changes):
        return run(VERIFY, ["prepare-policy", "--show-json", self.show(changes), "--allowed-attrs", ALLOWED] + RULES)

    def test_an_in_place_protection_flag_update_of_a_teardown_resource_is_the_only_accepted_change(self):
        ok = self.policy([
            self.change("module.dynamodb.aws_dynamodb_table.t", "aws_dynamodb_table", ["update"], {"deletion_protection_enabled": True, "n": 1}, {"deletion_protection_enabled": False, "n": 1}),
            self.change("module.neptune.aws_neptune_cluster.g", "aws_neptune_cluster", ["update"], {"deletion_protection": True, "skip_final_snapshot": False}, {"deletion_protection": False, "skip_final_snapshot": True}),
            self.change("module.network.aws_vpc.v", "aws_vpc", ["no-op"]),
        ])
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertEqual(ok.stdout.splitlines(), ["PREPARE-CHANGE: update module.dynamodb.aws_dynamodb_table.t", "PREPARE-CHANGE: update module.neptune.aws_neptune_cluster.g"])

    def test_everything_else_is_a_violation(self):
        base = {"deletion_protection_enabled": True}
        flag = {"deletion_protection_enabled": False}
        cases = {
            "create": self.change("module.runtime.aws_x.y", "aws_x", ["create"], None, {}),
            "delete": self.change("module.runtime.aws_x.y", "aws_x", ["delete"], {}, None),
            "replace": self.change("module.dynamodb.aws_dynamodb_table.t", "aws_dynamodb_table", ["delete", "create"], base, flag),
            "other attribute": self.change("module.dynamodb.aws_dynamodb_table.t", "aws_dynamodb_table", ["update"], {"deletion_protection_enabled": True, "n": 1}, {"deletion_protection_enabled": False, "n": 2}),
            "unknown attribute": self.change("module.dynamodb.aws_dynamodb_table.t", "aws_dynamodb_table", ["update"], {"deletion_protection_enabled": True}, {"deletion_protection_enabled": False}, {"arn": True}),
            "preserved resource": self.change("module.datalake.aws_s3_bucket.b", "aws_s3_bucket", ["update"], {"force_destroy": False}, {"force_destroy": True}),
            "unlisted resource": self.change("aws_instance.i", "aws_instance", ["update"], base, flag),
            "attribute allowed for another type": self.change("module.dynamodb.aws_dynamodb_table.t", "aws_dynamodb_table", ["update"], {"deletion_protection": True}, {"deletion_protection": False}),
        }
        for label, change in cases.items():
            with self.subTest(label):
                result = self.policy([change])
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("POLICY-VIOLATION", result.stdout)

    def test_an_empty_plan_is_not_a_violation(self):
        result = self.policy([])
        self.assertEqual(result.returncode, 0)
        self.assertIn("holds no change", result.stdout)


class ProtectionStateTests(Tmp):
    def state(self, resources, child=False):
        module = {"resources": resources}
        root = {"child_modules": [module]} if child else module
        return self.write("state.json", json.dumps({"values": {"root_module": root}}))

    def check(self, path, targets=None):
        args = ["protection-state", "--state-json", path, "--rules", "aws_lb:enable_deletion_protection=true,aws_ecr_repository:force_delete=false"] + RULES
        if targets:
            args += ["--targets-out", targets]
        return run(VERIFY, args)

    def test_active_flags_of_teardown_resources_are_found_in_nested_modules_and_released_ones_are_not(self):
        resources = [
            {"address": "module.runtime.aws_lb.q", "type": "aws_lb", "values": {"enable_deletion_protection": True}},
            {"address": "module.runtime.aws_ecr_repository.r", "type": "aws_ecr_repository", "values": {"force_delete": True}},
            {"address": "module.foundation.aws_lb.preserved", "type": "aws_lb", "values": {"enable_deletion_protection": True}},
        ]
        for child in (False, True):
            targets = os.path.join(self.tmp, "targets-%s" % child)
            result = self.check(self.state(resources, child), targets)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout.splitlines(), ["PROTECTION-ACTIVE: module.runtime.aws_lb.q enable_deletion_protection=true"])
            with open(targets) as handle:
                self.assertEqual(handle.read().splitlines(), ["module.runtime.aws_lb.q"])

    def test_nothing_active_and_an_empty_state_pass_and_unreadable_state_is_an_error(self):
        released = [{"address": "module.runtime.aws_lb.q", "type": "aws_lb", "values": {"enable_deletion_protection": False}}]
        self.assertEqual(self.check(self.state(released)).returncode, 0)
        self.assertEqual(self.check(self.write("empty.json", "{}")).returncode, 0)
        self.assertEqual(self.check(self.write("bad.json", "nope")).returncode, 2)


class PlanTargetEnvironmentTests(Tmp):
    def show(self, **variables):
        values = {"aws_account_id": {"value": "x"}, "aws_region": {"value": "us-east-2"}, "environment": {"value": "course"}, "project": {"value": "scholarchain"}}
        values.update(variables)
        return self.write("show.json", json.dumps({
            "variables": values,
            "configuration": {"provider_config": {"aws": {"name": "aws", "expressions": {"region": {"references": ["var.aws_region"]}}}}},
        }))

    def target(self, path, environment="course", project="scholarchain"):
        return run(VERIFY, ["plan-target", "--show-json", path, "--region", "us-east-2", "--account-sha256", sha256_bytes(b"x"), "--environment", environment, "--project", project, "--no-image-revision"])

    def test_environment_and_project_are_compared_with_the_plans_own_variables(self):
        self.assertEqual(self.target(self.show()).returncode, 0)
        wrong_env = self.target(self.show(environment={"value": "staging"}))
        self.assertEqual(wrong_env.returncode, 1)
        self.assertIn("planned environment staging != expected course", wrong_env.stdout)
        wrong_project = self.target(self.show(project={"value": "other"}))
        self.assertIn("planned project other != expected scholarchain", wrong_project.stdout)
        missing = self.target(self.show(environment={}))
        self.assertIn("PLANNED-ENVIRONMENT-MISSING", missing.stdout)


if __name__ == "__main__":
    unittest.main()
