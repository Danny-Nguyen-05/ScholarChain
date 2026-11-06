"""Repair round 3 (S1, N5) helper-level tests: runtime-live and runtime-preservation (verify.py), the bound deploy
manifest and the push-record revision (tools.py, records.py), and the S3 checksum comparison (verify.py s3-checksum).

No cloud and no Terraform: each helper is run as the scripts run it (python3 -I) on hand-written fixture files.
"""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from helpers import SCRIPTS_DIR, SERVICES, account_hash, registry_digest

LIB = os.path.join(SCRIPTS_DIR, "lib")
MODULE = "module.runtime"
TYPES = "aws_ecs_service,aws_lb,aws_lb_listener,aws_lb_target_group,aws_ecs_cluster"
INDICATORS = "aws_ecs_service=4,aws_lb=1,aws_lb_target_group=1,aws_lb_listener=0-1"
REV = "d" * 40
REPOS = " ".join("scholarchain-course/%s" % s for s in SERVICES)


def run(script, *args):
    completed = subprocess.run([sys.executable, "-I", os.path.join(LIB, script)] + list(args), capture_output=True, text=True)
    return completed.returncode, completed.stdout + completed.stderr


# Round 4 (T1): the default now includes the target group. The round-3 default (cluster, services, load balancer, listener)
# encoded a "live" runtime that compute.tf cannot produce (aws_lb.query and aws_lb_target_group.query share one count).
def runtime_resources(module=MODULE, types=("aws_ecs_cluster", "aws_ecs_service", "aws_lb", "aws_lb_listener", "aws_lb_target_group")):
    return [{"module": module, "mode": "managed", "type": t, "name": "x", "instances": [{"index_key": i} for i in range(4 if t == "aws_ecs_service" else 1)]} for t in types]


class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-guard-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def put(self, name, content, binary=False):
        path = os.path.join(self.tmp, name)
        with open(path, "wb" if binary else "w") as handle:
            if binary:
                handle.write(content)
            elif isinstance(content, str):
                handle.write(content)
            else:
                json.dump(content, handle)
        return path

    def state(self, resources, name="terraform.tfstate"):
        return self.put(name, {"version": 4, "serial": 3, "lineage": "l", "outputs": {}, "resources": resources})

    def receipt(self, actions, name="receipt.json"):
        document = {"schema": "scholarchain.plan-receipt.v2"}
        if actions is not None:
            document["actions"] = actions
        return self.put(name, document)

    def show(self, changes, name="show.json"):
        return self.put(name, {"resource_changes": [{"address": a, "type": t, "change": {"actions": acts}} for a, t, acts in changes]})


SERVICE_ADDRESS = 'module.runtime.aws_ecs_service.service["query-api"]'


class RuntimeLiveTests(Files):
    def live(self, path):
        return run("verify.py", "runtime-live", "--state", path, "--module", MODULE, "--indicators", INDICATORS, "--types", TYPES)

    def test_a_state_with_runtime_class_resources_is_live(self):
        rc, out = self.live(self.state(runtime_resources()))
        self.assertEqual(rc, 0, out)
        # Round 4 (T1): 7 deployed-runtime INDICATOR instances (4 services, load balancer, target group, listener); the
        # cluster is no longer counted (round 3 counted it among "7 runtime-class" instances with no target group).
        self.assertIn("RUNTIME-LIVE: yes (7 deployed-runtime indicator instance(s)", out)

    def test_an_empty_state_or_a_missing_file_is_not_live(self):
        for path in (self.state([]), os.path.join(self.tmp, "absent.tfstate")):
            rc, out = self.live(path)
            self.assertEqual(rc, 0, out)
            self.assertIn("RUNTIME-LIVE: no (0", out)

    def test_other_modules_and_other_types_do_not_count(self):
        resources = runtime_resources(module="module.network") + runtime_resources(types=("aws_ecr_repository", "aws_ecs_task_definition"))
        rc, out = self.live(self.state(resources))
        self.assertEqual(rc, 0, out)
        self.assertIn("RUNTIME-LIVE: no", out)

    def test_a_nested_module_of_the_runtime_counts_and_a_data_source_does_not(self):
        # Round 4 (T1): a nested module still counts, but a lone load balancer is now an incomplete (partial) runtime, so
        # the nested case is the complete indicator set; the lone load balancer is covered as partial below.
        nested = runtime_resources(module="module.runtime.module.inner")
        data = [dict(r, mode="data") for r in runtime_resources()]
        self.assertIn("RUNTIME-LIVE: yes", self.live(self.state(nested))[1])
        self.assertIn("RUNTIME-LIVE: no", self.live(self.state(data))[1])
        rc, out = self.live(self.state(runtime_resources(module="module.runtime.module.inner", types=("aws_lb",))))
        self.assertEqual(rc, 1, out)
        self.assertIn("RUNTIME-LIVE: partial", out)

    def test_an_unreadable_state_fails_closed(self):
        for content in ("not json", '{"resources": "nope"}'):
            rc, out = self.live(self.put("bad.tfstate", content))
            self.assertEqual(rc, 1, out)
            self.assertIn("RUNTIME-LIVE-CHECK-FAILED", out)

    def test_no_attribute_or_value_is_printed(self):
        resources = runtime_resources()
        resources[0]["instances"][0]["attributes"] = {"secret": "CANARY-STATE-VALUE-7731"}
        rc, out = self.live(self.state(resources))
        self.assertNotIn("CANARY-STATE-VALUE-7731", out)


class RuntimePreservationTests(Files):
    def check(self, state, source_flag, source, expect="any"):
        return run("verify.py", "runtime-preservation", "--state", state, "--module", MODULE, "--indicators", INDICATORS, "--types", TYPES, source_flag, source, "--expect", expect)

    def test_a_live_runtime_kept_by_updates_passes_on_the_receipt_and_the_show_json(self):
        state = self.state(runtime_resources())
        keep = [{"address": SERVICE_ADDRESS, "type": "aws_ecs_service", "actions": "update"}, {"address": "module.runtime.aws_ecs_task_definition.service[\"query-api\"]", "type": "aws_ecs_task_definition", "actions": "create+delete"}]
        rc, out = self.check(state, "--receipt", self.receipt(keep), "live")
        self.assertEqual(rc, 0, out)
        self.assertIn("runtime preservation ok", out)
        changes = [(SERVICE_ADDRESS, "aws_ecs_service", ["update"]), ("module.runtime.aws_ecs_task_definition.service", "aws_ecs_task_definition", ["create", "delete"])]
        rc, out = self.check(state, "--show-json", self.show(changes), "live")
        self.assertEqual(rc, 0, out)

    def test_a_delete_or_replace_of_every_runtime_class_type_is_refused(self):
        state = self.state(runtime_resources())
        for rtype, address in (
            ("aws_ecs_service", SERVICE_ADDRESS),
            ("aws_lb", "module.runtime.aws_lb.query[0]"),
            ("aws_lb_listener", "module.runtime.aws_lb_listener.https[0]"),
            ("aws_lb_target_group", "module.runtime.aws_lb_target_group.query[0]"),
            ("aws_ecs_cluster", "module.runtime.aws_ecs_cluster.course"),
        ):
            for verbs, word in (("delete", "delete"), ("create+delete", "replace"), ("delete+create", "replace")):
                with self.subTest(type=rtype, verbs=verbs):
                    rc, out = self.check(state, "--receipt", self.receipt([{"address": address, "type": rtype, "actions": verbs}]))
                    self.assertEqual(rc, 1, out)
                    self.assertIn("RUNTIME-PRESERVATION-FAILED: the plan would %s the live runtime resource %s" % (word, address), out)
            rc, out = self.check(state, "--show-json", self.show([(address, rtype, ["delete"])]))
            self.assertEqual(rc, 1, out)

    def test_a_receipt_without_an_action_list_fails_closed_while_the_runtime_is_live(self):
        state = self.state(runtime_resources())
        for path in (self.receipt(None), self.put("garbage.json", "not json"), os.path.join(self.tmp, "absent.json"), self.put("bad-entry.json", {"actions": ["x"]})):
            rc, out = self.check(state, "--receipt", path)
            self.assertEqual(rc, 1, out)
            self.assertIn("unreadable or holds no action list", out)

    def test_a_state_without_a_live_runtime_has_nothing_to_preserve(self):
        state = self.state([])
        rc, out = self.check(state, "--receipt", self.receipt([{"address": SERVICE_ADDRESS, "type": "aws_ecs_service", "actions": "delete"}]))
        self.assertEqual(rc, 0, out)
        self.assertIn("nothing to preserve", out)

    def test_expect_live_and_not_live_pin_what_the_state_must_show(self):
        live, idle = self.state(runtime_resources()), self.state([], name="idle.tfstate")
        quiet = self.receipt([])
        rc, out = self.check(idle, "--receipt", quiet, "live")
        self.assertEqual(rc, 1, out)
        self.assertIn("no live runtime", out)
        rc, out = self.check(live, "--receipt", quiet, "not-live")
        self.assertEqual(rc, 1, out)
        self.assertIn("LIVE runtime", out)
        self.assertEqual(self.check(live, "--receipt", quiet, "live")[0], 0)
        self.assertEqual(self.check(idle, "--receipt", quiet, "not-live")[0], 0)

    def test_deleting_resources_outside_the_runtime_module_or_the_listed_types_is_not_this_safety_nets_concern(self):
        state = self.state(runtime_resources())
        other = [
            {"address": "module.network.aws_lb.x", "type": "aws_lb", "actions": "delete"},
            {"address": "module.runtime.aws_ecr_repository.service[\"query-api\"]", "type": "aws_ecr_repository", "actions": "delete"},
        ]
        self.assertEqual(self.check(state, "--receipt", self.receipt(other))[0], 0)

    def test_the_account_id_is_redacted_from_a_refused_address(self):
        state = self.state(runtime_resources())
        address = "module.runtime.aws_ecs_service.svc-123456789012"
        rc, out = self.check(state, "--receipt", self.receipt([{"address": address, "type": "aws_ecs_service", "actions": "delete"}]))
        self.assertEqual(rc, 1, out)
        self.assertNotIn("123456789012", out)


def deploy_manifest(**overrides):
    document = {
        "schema": "scholarchain.deploy-manifest.v1",
        "stage": "runtime-apply",
        "commit": REV,
        "image_revision": REV,
        "region": "us-east-2",
        "account_sha256": account_hash(),
        "images": [{"service": s, "repository": "scholarchain-course/%s" % s, "tag": REV, "registry_digest": registry_digest(s, REV)} for s in SERVICES],
        "ecs_services": [{"service": s, "task_definition": "arn:aws:ecs:us-east-2:<acct>:task-definition/scholarchain-course-%s:7" % s} for s in SERVICES],
    }
    document.update(overrides)
    return document


class BoundDeployManifestTests(Files):
    def verify(self, document, *extra):
        path = self.put("manifest.json", document)
        return run("tools.py", "verify-deploy-manifest", "--manifest", path, "--services", " ".join(SERVICES), *extra)

    BIND = ("--require-stage", "runtime-apply", "--account-sha256", account_hash(), "--region", "us-east-2", "--repositories", REPOS, "--require-ecs-services")

    def test_a_complete_runtime_apply_manifest_binds(self):
        rc, out = self.verify(deploy_manifest(), *self.BIND)
        self.assertEqual(rc, 0, out)

    def test_the_unbound_check_is_unchanged_for_an_application_rollback(self):
        document = deploy_manifest(stage="push", account_sha256="x", region="other", ecs_services=[])
        self.assertEqual(self.verify(document)[0], 0)

    def test_every_binding_dimension_is_enforced(self):
        images = deploy_manifest()["images"]
        cases = {
            "stage": (deploy_manifest(stage="push"), "is not runtime-apply"),
            "account": (deploy_manifest(account_sha256="e" * 64), "account differs"),
            "region": (deploy_manifest(region="us-west-2"), "region differs"),
            "repository": (deploy_manifest(images=[dict(i, repository="other/%s" % i["service"]) if i["service"] == "graph-service" else i for i in images]), "repository for graph-service"),
            "no ecs services": (deploy_manifest(ecs_services=[]), "no verified ECS task definition"),
            "one ecs service missing": (deploy_manifest(ecs_services=deploy_manifest()["ecs_services"][:3]), "embedding-worker"),
            "an ecs task definition is empty": (deploy_manifest(ecs_services=[dict(e, task_definition="") if e["service"] == "query-api" else e for e in deploy_manifest()["ecs_services"]]), "query-api"),
            "revision not 40 hex": (deploy_manifest(image_revision="c"), "40-hex"),
            "tag differs from revision": (deploy_manifest(images=[dict(i, tag="f" * 40) if i["service"] == "query-api" else i for i in images]), "image tag for query-api"),
            "malformed digest": (deploy_manifest(images=[dict(i, registry_digest="sha256:abc") if i["service"] == "query-api" else i for i in images]), "query-api is not sha256"),
            "schema": (deploy_manifest(schema="scholarchain.deploy-manifest.v0"), "schema"),
        }
        for label, (document, needle) in cases.items():
            with self.subTest(label):
                rc, out = self.verify(document, *self.BIND)
                self.assertEqual(rc, 1, out)
                self.assertIn("MANIFEST-CHECK-FAILED", out)
                self.assertIn(needle, out)


class PushRecordRevisionTests(Files):
    def record(self, **overrides):
        document = {
            "schema": "scholarchain.push-record.v1", "commit": REV, "account_sha256": account_hash(), "region": "us-east-2", "environment": "course",
            "images": [{"service": s, "repository": "scholarchain-course/%s" % s, "tag": REV, "pushed_digest": registry_digest(s, REV)} for s in SERVICES],
        }
        document.update(overrides)
        return self.put("push-record.json", document)

    def test_revision_prints_the_records_commit(self):
        rc, out = run("records.py", "revision", "--file", self.record())
        self.assertEqual((rc, out.strip()), (0, REV))

    def test_revision_refuses_a_bad_schema_a_bad_commit_and_junk(self):
        for path in (self.record(schema="scholarchain.push-record.v0"), self.record(commit="abc"), self.put("junk.json", "not json"), os.path.join(self.tmp, "absent.json")):
            rc, out = run("records.py", "revision", "--file", path)
            self.assertEqual(rc, 1, out)
            self.assertIn("PUSH-RECORD-FAILED", out)

    def check(self, path, *extra):
        return run("records.py", "check-push-record", "--file", path, "--commit", REV, "--region", "us-east-2", "--environment", "course", "--repositories", REPOS, "--services", " ".join(SERVICES), *extra)

    def test_the_account_is_compared_when_given_and_skipped_only_when_omitted(self):
        path = self.record(account_sha256="e" * 64)
        self.assertEqual(self.check(path)[0], 0, "rollback.sh's early pre-check has no account identity")
        rc, out = self.check(path, "--account-sha256", account_hash())
        self.assertEqual(rc, 1, out)
        self.assertIn("account", out)
        self.assertEqual(self.check(self.record(), "--account-sha256", account_hash())[0], 0)


def b64(raw):
    return base64.b64encode(raw).decode("ascii")


class S3ChecksumTests(Files):
    DATA = b"tiny-runtime-archive"

    def archive(self):
        return self.put("archive.bin", self.DATA, binary=True)

    def compare(self, checksum, parts=None):
        args = ["s3-checksum", "--file", self.archive(), "--checksum", checksum]
        if parts is not None:
            args += ["--parts-file", self.put("parts.txt", parts)]
        return run("verify.py", *args)

    def plain(self, data=None):
        return b64(hashlib.sha256(self.DATA if data is None else data).digest())

    def multipart(self, sizes, tamper=None):
        """(composite checksum, part list text) for DATA split at the given part sizes."""
        assert sum(sizes) == len(self.DATA)
        raws, lines, offset = [], [], 0
        for number, size in enumerate(sizes, 1):
            raw = hashlib.sha256(self.DATA[offset:offset + size]).digest()
            offset += size
            raws.append(raw)
            lines.append("%d\t%d\t%s" % (number, size, b64(b"\0" * 32 if tamper == number else raw)))
        composite = b64(hashlib.sha256(b"".join(raws)).digest()) + "-%d" % len(sizes)
        return composite, "\n".join(lines) + "\n"

    def test_a_single_part_checksum_equals_the_base64_of_the_raw_sha256(self):
        rc, out = self.compare(self.plain())
        self.assertEqual(rc, 0, out)
        self.assertTrue(out.startswith("S3-computed ChecksumSHA256 equals"))

    def test_the_hex_digest_is_not_the_s3_form(self):
        rc, out = self.compare(hashlib.sha256(self.DATA).hexdigest())
        self.assertEqual(rc, 1, out)

    def test_a_different_object_or_a_missing_value_fails_closed(self):
        for value in (self.plain(b"other bytes"), "", "None", "garbage"):
            with self.subTest(value=value):
                rc, out = self.compare(value)
                self.assertEqual(rc, 1, out)
                self.assertIn("S3-CHECKSUM-FAILED", out)

    def test_a_multipart_object_is_verified_part_by_part_against_the_part_list_s3_reports(self):
        composite, parts = self.multipart([8, 12])
        rc, out = self.compare(composite, parts)
        self.assertEqual(rc, 0, out)
        self.assertIn("composite ChecksumSHA256 (2 parts)", out)
        composite, parts = self.multipart([5, 5, 10])
        self.assertEqual(self.compare(composite, parts)[0], 0, "part sizes come from S3, not from a chunk size assumed here")

    def test_composite_failures(self):
        composite, parts = self.multipart([8, 12])
        bad_part = self.multipart([8, 12], tamper=2)[1]
        cases = {
            "a part checksum differs": (composite, bad_part, "part 2"),
            "no part list": (composite, None, "needs the part list"),
            "a truncated part list": (composite, parts.splitlines()[0] + "\n", "1 part(s) but the checksum names 2"),
            "the composite names more parts": (composite.rsplit("-", 1)[0] + "-3", parts, "names 3"),
            "part sizes do not add up": (composite, "1\t8\tAAAA\n2\t11\tBBBB\n", "do not add up"),
            "the composite is not of the parts": (b64(hashlib.sha256(b"x").digest()) + "-2", parts, "composite checksum is not"),
        }
        for label, (value, part_text, needle) in cases.items():
            with self.subTest(label):
                rc, out = self.compare(value, part_text)
                self.assertEqual(rc, 1, out)
                self.assertIn(needle, out)


if __name__ == "__main__":
    unittest.main()
