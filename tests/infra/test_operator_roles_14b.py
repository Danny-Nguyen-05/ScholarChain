"""Phase 14B replan, workstream W5a: the operator roles and the runtime boundary, from the requirement (test-engineer).

Real offline `terraform plan` of the deployer root (real provider, fake credentials, closed proxy) on a scratch copy; the repository is
never written. The named invariants O1..O9 are in operator_checks.py. Three groups:
  * RealTree: the invariants on the real sources (default off; enabled on).
  * InMemoryMutations: each invariant is also proven to FIRE by editing a copy of the parsed plan in memory (no Terraform run), so
    a check that silently stopped checking is caught. Each result goes to $SC_INFRA_EVIDENCE_FILE when set.
"""
import copy
import json
import unittest

import operator_checks as oc
from infra_support import TfTree, managed_changes, record_mutation


class RealTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TfTree("deployer14") as off:
            cls.off = off.plan_json()
        with TfTree("deployer14ops") as on:
            cls.on = on.plan_json()

    def test_roles_are_absent_by_default(self):
        self.assertEqual(oc.check_off_by_default(self.off), [])

    def test_enabled_plan_has_exactly_the_four_named_roles_and_no_other_new_role(self):
        self.assertEqual(oc.check_three_roles(self.on), [])
        names = {rc["change"]["after"]["name"] for a, rc in managed_changes(self.on).items() if rc["type"] == "aws_iam_role"}
        self.assertEqual(names, {"scholarchain-deployer"} | {"scholarchain-course-operator-%s" % k for k in oc.KINDS})
        self.assertEqual(oc.KINDS, ("cleanup", "loader", "pipeline", "reader"))

    def test_each_role_trusts_only_the_operator_with_mfa(self):
        self.assertEqual(oc.check_trust(self.on), [])

    def test_each_role_has_a_four_hour_session_and_the_deployer_keeps_one_hour(self):
        self.assertEqual(oc.check_session(self.on), [])
        deployer = managed_changes(self.on)["aws_iam_role.deployer"]["change"]["after"]
        self.assertEqual(deployer["max_session_duration"], 3600)

    def test_each_role_has_the_same_device_login_policy(self):
        self.assertEqual(oc.check_login_policy(self.on), [])

    def test_no_marketplace_permission_anywhere_in_either_plan(self):
        self.assertEqual(oc.check_no_marketplace(self.on), [])
        self.assertEqual(oc.check_no_marketplace(self.off), [])

    def test_no_wildcard_action_and_no_bare_wildcard_resource_in_the_operator_policies(self):
        self.assertEqual(oc.check_no_wildcards(self.on), [])
        self.assertTrue(oc.operator_policies(self.on), "the control case: policies exist to be checked")

    def test_the_operator_policies_are_data_plane_and_run_scoped(self):
        self.assertEqual(oc.check_data_plane_scope(self.on), [])

    def test_the_runtime_boundary_has_the_four_ecs_exec_actions_and_no_neptune_load_or_write(self):
        self.assertEqual(oc.check_runtime_boundary(self.on), [])
        self.assertEqual(oc.check_runtime_boundary(self.off), [])

    def test_the_pipeline_role_trust_session_and_no_boundary(self):
        self.assertEqual(oc.check_pipeline_role_basics(self.on), [])

    def test_the_pipeline_role_has_exactly_the_seven_emr_actions_on_the_tagged_project_cluster(self):
        self.assertEqual(oc.check_pipeline_emr(self.on), [])

    def test_the_pipeline_role_cannot_start_or_end_a_cluster_delete_objects_or_touch_iam(self):
        self.assertEqual(oc.check_pipeline_forbidden(self.on), [])

    def test_the_pipeline_role_s3_is_create_only_under_emr_and_read_only_elsewhere(self):
        self.assertEqual(oc.check_pipeline_s3(self.on), [])

    def test_the_pipeline_role_uses_kms_through_s3_only_and_no_other_service(self):
        self.assertEqual(oc.check_pipeline_kms(self.on), [])
        self.assertEqual(oc.check_pipeline_services(self.on), [])

    def test_the_loader_writes_runtime_artifacts_create_only_and_can_never_delete(self):
        self.assertEqual(oc.check_loader_runtime_artifact(self.on), [])

    def test_the_operator_policies_name_the_run_prefix_and_the_six_tables(self):
        text = json.dumps([doc for _, doc in oc.operator_policies(self.on).values()])
        self.assertIn("run-20261115/*", text)
        for table in ("RunLedger", "EntityLinkCache", "QuerySession", "EvidenceBundle", "ArtifactRegistry", "ResearcherMetricCache"):
            self.assertIn("scholarchain-course-" + table, text)

    def test_the_operator_policies_do_not_reach_the_deployer_or_billing_roles(self):
        text = json.dumps([doc for _, doc in oc.operator_policies(self.on).values()])
        self.assertNotIn("role/scholarchain-deployer", text)
        self.assertNotIn("billing", text)


def mutate_policy(plan, address, edit):
    """A deep copy of `plan` where the JSON document of `address` (policy or assume_role_policy) is replaced by edit(document)."""
    new = copy.deepcopy(plan)
    for rc in new["resource_changes"]:
        if rc["address"] == address:
            key = "policy" if "policy" in rc["change"]["after"] else "assume_role_policy"
            doc = json.loads(rc["change"]["after"][key])
            edit(doc)
            rc["change"]["after"][key] = json.dumps(doc)
            return new
    raise AssertionError("address not in plan: " + address)


def mutate_attr(plan, address, **attrs):
    new = copy.deepcopy(plan)
    for rc in new["resource_changes"]:
        if rc["address"] == address:
            rc["change"]["after"].update(attrs)
            return new
    raise AssertionError("address not in plan: " + address)


def drop(plan, address):
    new = copy.deepcopy(plan)
    new["resource_changes"] = [rc for rc in new["resource_changes"] if rc["address"] != address]
    return new


LOADER_DATA = 'aws_iam_role_policy.operator["loader--data"]'
LOADER_TUNNEL = 'aws_iam_role_policy.operator["loader--tunnel"]'
CLEANUP_DATA = 'aws_iam_role_policy.operator["cleanup--data"]'
LOADER = 'aws_iam_role.operator["loader"]'
LOGIN = 'aws_iam_role_policy.operator_login["reader"]'
PIPE = "aws_iam_role_policy.operator_pipeline[0]"
PIPE_ROLE = "aws_iam_role.operator_pipeline[0]"
PIPE_LOGIN = "aws_iam_role_policy.operator_pipeline_login[0]"
BOUNDARY = "aws_iam_policy.main_boundary_runtime"


def statement(doc, sid):
    return next(s for s in doc["Statement"] if s.get("Sid") == sid)


class InMemoryMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TfTree("deployer14ops") as on:
            cls.on = on.plan_json()
        with TfTree("deployer14") as off:
            cls.off = off.plan_json()
        cls.boundary_address = next(rc["address"] for rc in cls.on["resource_changes"] if rc["address"].startswith(BOUNDARY))

    def expect(self, name, plan, check, fragment):
        problems = check(plan)
        record_mutation("operator-" + name, {"check": check.__name__, "problems": len(problems), "caught": bool(problems)})
        self.assertTrue(problems, "mutation %r was not caught by %s" % (name, check.__name__))
        self.assertTrue(any(fragment in p for p in problems), "%r: expected %r in %s" % (name, fragment, problems))

    def test_o1_a_role_planned_by_default_is_reported(self):
        plan = copy.deepcopy(self.off)
        plan["resource_changes"].append(copy.deepcopy(next(rc for rc in self.on["resource_changes"] if rc["address"] == LOADER)))
        self.expect("o1-role-in-default", plan, oc.check_off_by_default, "O1")

    def test_o2_a_missing_role_and_a_renamed_role_are_reported(self):
        self.expect("o2-missing-role", drop(self.on, 'aws_iam_role.operator["cleanup"]'), oc.check_three_roles, "O2")
        self.expect("o2-missing-pipeline-role", drop(self.on, PIPE_ROLE), oc.check_three_roles, "O2")
        self.expect("o2-renamed", mutate_attr(self.on, LOADER, name="scholarchain-course-loader"), oc.check_three_roles, "O2")

    def test_o3_trust_mutations_are_reported(self):
        self.expect("o3-no-mfa", mutate_policy(self.on, LOADER, lambda d: d["Statement"][0].pop("Condition")), oc.check_trust, "MFA")
        self.expect("o3-mfa-false", mutate_policy(self.on, LOADER, lambda d: d["Statement"][0]["Condition"]["Bool"].update(
            {"aws:MultiFactorAuthPresent": "false"})), oc.check_trust, "MFA")
        self.expect("o3-wildcard-principal", mutate_policy(self.on, LOADER, lambda d: d["Statement"][0].update(Principal={"AWS": "*"})),
                    oc.check_trust, "principal")
        self.expect("o3-account-root", mutate_policy(self.on, LOADER, lambda d: d["Statement"][0].update(
            Principal={"AWS": "arn:aws:iam::111122223333:root"})), oc.check_trust, "principal")

    def test_o4_session_mutations_are_reported(self):
        self.expect("o4-3600", mutate_attr(self.on, LOADER, max_session_duration=3600), oc.check_session, "O4")
        self.expect("o4-43200", mutate_attr(self.on, LOADER, max_session_duration=43200), oc.check_session, "O4")

    def test_o5_login_policy_mutations_are_reported(self):
        self.expect("o5-missing", drop(self.on, LOGIN), oc.check_login_policy, "O5")
        self.expect("o5-no-condition", mutate_policy(self.on, LOGIN, lambda d: d["Statement"][0].pop("Condition")),
                    oc.check_login_policy, "condition")
        self.expect("o5-extra-action", mutate_policy(self.on, LOGIN, lambda d: d["Statement"][0]["Action"].append("sts:AssumeRole")),
                    oc.check_login_policy, "actions")
        self.expect("o5-other-resource", mutate_policy(self.on, LOGIN, lambda d: d["Statement"][0].update(Resource=["*"])),
                    oc.check_login_policy, "resource")

    def test_o6_a_marketplace_action_is_reported_in_an_operator_and_in_a_boundary_document(self):
        self.expect("o6-operator", mutate_policy(self.on, CLEANUP_DATA, lambda d: d["Statement"].append(
            {"Sid": "X", "Effect": "Allow", "Action": ["aws-marketplace:Subscribe"], "Resource": ["arn:aws:s3:::b/k/*"]})),
            oc.check_no_marketplace, "aws-marketplace")
        self.expect("o6-boundary", mutate_policy(self.on, self.boundary_address, lambda d: d["Statement"].append(
            {"Sid": "X", "Effect": "Allow", "Action": ["aws-marketplace:ViewSubscriptions"], "Resource": ["*"]})),
            oc.check_no_marketplace, "aws-marketplace")

    def test_o7_wildcards_are_reported(self):
        def add(action, resource=("arn:aws:s3:::b/k/*",)):
            return lambda d: d["Statement"].append({"Sid": "X", "Effect": "Allow", "Action": [action], "Resource": list(resource)})
        for label, action in (("star-star", "*"), ("service-star", "s3:*"), ("prefix-star", "dynamodb:Get*")):
            self.expect("o7-" + label, mutate_policy(self.on, LOADER_DATA, add(action)), oc.check_no_wildcards, "wildcard action")
        self.expect("o7-bare-resource", mutate_policy(self.on, LOADER_DATA, add("s3:GetObject", ("*",))), oc.check_no_wildcards, "bare wildcard")
        self.expect("o7-iam", mutate_policy(self.on, LOADER_TUNNEL, add("iam:CreateRole")), oc.check_no_wildcards, "iam:CreateRole")

    def test_o8_scope_mutations_are_reported(self):
        def add(action, resource):
            return lambda d: d["Statement"].append({"Sid": "X", "Effect": "Allow", "Action": [action], "Resource": [resource]})
        self.expect("o8-other-service", mutate_policy(self.on, LOADER_DATA, add("ec2:RunInstances", "arn:aws:ec2:us-east-2:111122223333:instance/i")),
                    oc.check_data_plane_scope, "uses service")
        self.expect("o8-whole-bucket", mutate_policy(self.on, LOADER_DATA, add("s3:PutObject", "arn:aws:s3:::scholarchain-course-111122223333-graph/*")),
                    oc.check_data_plane_scope, "whole bucket")
        self.expect("o8-every-table", mutate_policy(self.on, LOADER_DATA, add("dynamodb:PutItem", "arn:aws:dynamodb:us-east-2:111122223333:table/*")),
                    oc.check_data_plane_scope, "every table")
        self.expect("o8-other-model", mutate_policy(self.on, LOADER_DATA, add("bedrock:InvokeModel", "arn:aws:bedrock:us-east-2::foundation-model/*")),
                    oc.check_data_plane_scope, "bedrock")

    def test_o9_boundary_mutations_are_reported(self):
        def edit_exec(drop_action=None, add_action=None):
            def f(d):
                st = next(s for s in d["Statement"] if "ssmmessages:OpenDataChannel" in s.get("Action", []))
                if drop_action:
                    st["Action"].remove(drop_action)
                if add_action:
                    st["Action"].append(add_action)
            return f
        self.expect("o9-missing-ssmmessages", mutate_policy(self.on, self.boundary_address, edit_exec(drop_action="ssmmessages:OpenDataChannel")),
                    oc.check_runtime_boundary, "ssmmessages")
        self.expect("o9-extra-ssm", mutate_policy(self.on, self.boundary_address, edit_exec(add_action="ssmmessages:StartSession")),
                    oc.check_runtime_boundary, "ssmmessages")
        for action in ("neptune-db:StartLoaderJob", "neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery", "neptune-db:*"):
            def add(d, action=action):
                st = next(s for s in d["Statement"] if "neptune-db:ReadDataViaQuery" in s.get("Action", []))
                st["Action"].append(action)
            self.expect("o9-" + action.split(":")[1], mutate_policy(self.on, self.boundary_address, add), oc.check_runtime_boundary, action)


class PipelineInMemoryMutations(unittest.TestCase):
    """The pipeline-role and loader-runtime-artifact invariants each fire on a hand-made violation."""

    @classmethod
    def setUpClass(cls):
        with TfTree("deployer14ops") as on:
            cls.on = on.plan_json()

    def expect(self, name, plan, check, fragment):
        problems = check(plan)
        record_mutation("operator-pipeline-" + name, {"check": check.__name__, "problems": len(problems), "caught": bool(problems)})
        self.assertTrue(problems, "mutation %r was not caught by %s" % (name, check.__name__))
        self.assertTrue(any(fragment in p for p in problems), "%r: expected %r in %s" % (name, fragment, problems))

    def stmt(self, sid):
        return lambda d: next(s for s in d["Statement"] if s.get("Sid") == sid)

    def add(self, **fields):
        base = {"Sid": "X", "Effect": "Allow"}
        base.update(fields)
        return lambda d: d["Statement"].append(base)

    def test_p1_basics(self):
        self.expect("session", mutate_attr(self.on, PIPE_ROLE, max_session_duration=3600), oc.check_pipeline_role_basics, "session")
        self.expect("no-mfa", mutate_policy(self.on, PIPE_ROLE, lambda d: d["Statement"][0].pop("Condition")), oc.check_pipeline_role_basics, "trust")
        self.expect("boundary", mutate_attr(self.on, PIPE_ROLE, permissions_boundary="arn:aws:iam::111122223333:policy/x"), oc.check_pipeline_role_basics, "boundary")

    def test_p1_login_policy_of_the_pipeline_role(self):
        self.expect("login-removed", drop(self.on, PIPE_LOGIN), oc.check_login_policy, "O5")
        self.expect("login-no-condition", mutate_policy(self.on, PIPE_LOGIN, lambda d: d["Statement"][0].pop("Condition")), oc.check_login_policy, "condition")

    def test_p2_emr_mutations(self):
        sid = "EmrSubmitAndCancelStepsOnTheProjectClusterOnly"
        self.expect("emr-extra-action", mutate_policy(self.on, PIPE, lambda d: self.stmt(sid)(d)["Action"].append("elasticmapreduce:RunJobFlow")),
                    oc.check_pipeline_emr, "EMR actions")
        self.expect("emr-missing-action", mutate_policy(self.on, PIPE, lambda d: self.stmt(sid)(d)["Action"].remove("elasticmapreduce:CancelSteps")),
                    oc.check_pipeline_emr, "EMR actions")
        self.expect("emr-all-clusters", mutate_policy(self.on, PIPE, lambda d: self.stmt(sid)(d).update(Resource=["*"])), oc.check_pipeline_emr, "resource")
        self.expect("emr-no-stack-tag", mutate_policy(self.on, PIPE, lambda d: self.stmt(sid)(d)["Condition"]["StringEquals"].pop("aws:ResourceTag/scholarchain:stack")),
                    oc.check_pipeline_emr, "condition")
        self.expect("emr-no-region", mutate_policy(self.on, PIPE, lambda d: self.stmt(sid)(d)["Condition"]["StringEquals"].pop("aws:RequestedRegion")),
                    oc.check_pipeline_emr, "condition")
        self.expect("emr-other-environment", mutate_policy(self.on, PIPE, lambda d: self.stmt(sid)(d)["Condition"]["StringEquals"].update({"aws:ResourceTag/environment": "other"})),
                    oc.check_pipeline_emr, "condition")

    def test_p3_forbidden_actions(self):
        for action in ("elasticmapreduce:RunJobFlow", "elasticmapreduce:TerminateJobFlows", "s3:DeleteObject", "s3:DeleteObjectVersion",
                       "iam:PassRole", "sts:AssumeRole"):
            self.expect("forbidden-" + action, mutate_policy(self.on, PIPE, self.add(Action=[action], Resource=["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-20261115/*"])),
                        oc.check_pipeline_forbidden, action)

    def test_p4_p5_s3_mutations(self):
        up = "S3EmrArtifactsCreateOnlyWithIfNoneMatch"
        self.expect("s3-no-if-none-match", mutate_policy(self.on, PIPE, lambda d: self.stmt(up)(d)["Condition"].pop("Null")), oc.check_pipeline_s3, "neither create-only")
        self.expect("s3-overwrite-allowed", mutate_policy(self.on, PIPE, self.add(Action=["s3:PutObject"], Resource=["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-20261115/*"],
                                                                                Condition={"StringEquals": {"aws:RequestedRegion": "us-east-2"}})),
                    oc.check_pipeline_s3, "neither create-only")
        self.expect("s3-put-whole-bucket", mutate_policy(self.on, PIPE, lambda d: self.stmt(up)(d).update(Resource=["arn:aws:s3:::scholarchain-course-111122223333-artifacts/*"])),
                    oc.check_pipeline_s3, "outside the create-only")
        self.expect("s3-put-pipeline-outputs", mutate_policy(self.on, PIPE, self.add(Action=["s3:PutObject"], Resource=["arn:aws:s3:::scholarchain-course-111122223333-artifacts/pipeline/run-20261115/*"],
                                                                                    Condition={"Null": {"s3:if-none-match": "false"}, "StringEquals": {"aws:RequestedRegion": "us-east-2"}})),
                    oc.check_pipeline_s3, "outside the create-only")
        self.expect("s3-other-bucket", mutate_policy(self.on, PIPE, self.add(Action=["s3:GetObject"], Resource=["arn:aws:s3:::scholarchain-course-111122223333-raw/*"])),
                    oc.check_pipeline_s3, "other than artifacts and logs")
        ro = "S3PipelineOutputsAndEmrLogsReadOnly"
        self.expect("s3-readonly-prefix-writable", mutate_policy(self.on, PIPE, lambda d: self.stmt(ro)(d)["Action"].append("s3:AbortMultipartUpload")),
                    oc.check_pipeline_s3, "more than read")
        self.expect("s3-list-unrestricted", mutate_policy(self.on, PIPE, lambda d: self.stmt("S3ListEmrLogsPrefix")(d)["Condition"].pop("StringLike")),
                    oc.check_pipeline_s3, "lists without a prefix")

    def test_p6_p7_kms_and_services(self):
        kms = "ProjectKeyThroughS3Only"
        self.expect("kms-any-service", mutate_policy(self.on, PIPE, lambda d: self.stmt(kms)(d)["Condition"]["StringEquals"].update({"kms:ViaService": ["s3.us-east-2.amazonaws.com", "dynamodb.us-east-2.amazonaws.com"]})),
                    oc.check_pipeline_kms, "ViaService")
        self.expect("kms-extra-action", mutate_policy(self.on, PIPE, lambda d: self.stmt(kms)(d)["Action"].append("kms:CreateGrant")), oc.check_pipeline_kms, "KMS actions")
        self.expect("kms-no-alias", mutate_policy(self.on, PIPE, lambda d: self.stmt(kms)(d)["Condition"].pop("ForAnyValue:StringEquals")), oc.check_pipeline_kms, "alias")
        self.expect("extra-service", mutate_policy(self.on, PIPE, self.add(Action=["dynamodb:GetItem"], Resource=["arn:aws:dynamodb:us-east-2:111122223333:table/x"])),
                    oc.check_pipeline_services, "dynamodb")

    def test_l1_loader_runtime_artifact_mutations(self):
        put = "S3RuntimeArtifactCreateOnly"
        loader = 'aws_iam_role_policy.operator["loader--data"]'
        self.expect("loader-overwrite", mutate_policy(self.on, loader, lambda d: self.stmt(put)(d)["Condition"].pop("Null")), oc.check_loader_runtime_artifact, "create-only")
        self.expect("loader-delete", mutate_policy(self.on, loader, self.add(Action=["s3:DeleteObject"], Resource=["arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*"])),
                    oc.check_loader_runtime_artifact, "s3:DeleteObject")
        self.expect("loader-no-readback", mutate_policy(self.on, loader, lambda d: d["Statement"].remove(self.stmt("S3RuntimeArtifactReadBack")(d))),
                    oc.check_loader_runtime_artifact, "read-back")
        self.expect("loader-put-removed", mutate_policy(self.on, loader, lambda d: d["Statement"].remove(self.stmt(put)(d))), oc.check_loader_runtime_artifact, "exactly one")
        self.expect("loader-multipart", mutate_policy(self.on, loader, lambda d: self.stmt(put)(d)["Action"].append("s3:AbortMultipartUpload")),
                    oc.check_loader_runtime_artifact, "PutObject alone")


if __name__ == "__main__":
    unittest.main()
