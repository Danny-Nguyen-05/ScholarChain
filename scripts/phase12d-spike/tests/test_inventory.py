import json
import os
import unittest

from helpers import SCRIPTS_DIR, ShimTestCase

SCRIPT = os.path.join(SCRIPTS_DIR, "inventory.sh")
ACCT = "111122223333"
KEY = "11111111-2222-3333-4444-555555555555"
KEY_ARN = f"arn:aws:kms:us-east-2:{ACCT}:key/{KEY}"


class InventoryTests(ShimTestCase):
    def setUp(self):
        super().setUp()
        # a fully clean account: bucket 404, nothing tagged
        self.put("head-bucket.rc", "254")
        self.put("head-bucket.err", "An error occurred (404) when calling the HeadBucket operation: Not Found")

    def j(self, name, obj):
        self.put(name, json.dumps(obj))

    def run_inv(self):
        r = self.run_script(SCRIPT, ["--account", ACCT])
        out = json.loads(r.stdout) if r.stdout.strip() else None
        return r, out

    def test_clean_account_passes(self):
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue(out["clean"])
        self.assertEqual(out["billable_remaining"], [])

    def test_only_pending_deletion_key_is_expected_retained(self):
        self.j("resourcegroupstaggingapi-get-resources.json", {"ResourceTagMappingList": [{"ResourceARN": KEY_ARN}]})
        self.j(f"kms-describe-key-{KEY}.json", {"KeyMetadata": {"KeyId": KEY, "KeyState": "PendingDeletion"}})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertEqual(out["billable_remaining"], [])
        self.assertEqual(out["expected_retained"][0]["kind"], "kms-key")
        self.assertTrue(out["clean"])

    def test_enabled_key_is_billable(self):
        self.j("resourcegroupstaggingapi-get-resources.json", {"ResourceTagMappingList": [{"ResourceARN": KEY_ARN}]})
        self.j(f"kms-describe-key-{KEY}.json", {"KeyMetadata": {"KeyId": KEY, "KeyState": "Enabled"}})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)
        self.assertEqual(out["billable_remaining"][0]["kind"], "kms-key")

    def test_remaining_nat_gateway_fails(self):
        self.j("ec2-describe-nat-gateways.json", {"NatGateways": [{"NatGatewayId": "nat-1", "State": "available"}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)
        self.assertEqual(out["billable_remaining"][0]["kind"], "nat-gateway")

    def test_deleted_nat_gateway_is_ignored(self):
        self.j("ec2-describe-nat-gateways.json", {"NatGateways": [{"NatGatewayId": "nat-1", "State": "deleted"}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 0)

    def test_remaining_eip_fails(self):
        self.j("ec2-describe-addresses.json", {"Addresses": [{"AllocationId": "eipalloc-1"}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)
        self.assertEqual(out["billable_remaining"][0]["kind"], "elastic-ip")

    def test_remaining_cluster_fails(self):
        self.j("emr-list-clusters.json", {"Clusters": [{"Id": "j-1", "Name": "scholarchain-spike-emr-cluster", "Status": {"State": "RUNNING"}}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)
        self.assertEqual(out["billable_remaining"][0]["kind"], "emr-cluster")

    def test_unrelated_cluster_is_ignored(self):
        self.j("emr-list-clusters.json", {"Clusters": [{"Id": "j-9", "Name": "someone-elses", "Status": {"State": "RUNNING"}}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 0)

    def test_stopped_instance_still_counts(self):
        self.j("ec2-describe-instances.json", {"Reservations": [{"Instances": [{"InstanceId": "i-1", "State": {"Name": "stopped"}}]}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)

    def test_volume_eni_efs_and_bucket_fail(self):
        self.j("ec2-describe-volumes.json", {"Volumes": [{"VolumeId": "vol-1", "State": "available"}]})
        self.j("ec2-describe-network-interfaces.json", {"NetworkInterfaces": [{"NetworkInterfaceId": "eni-1", "Status": "in-use"}]})
        self.j("efs-describe-file-systems.json", {"FileSystems": [{"FileSystemId": "fs-1", "LifeCycleState": "available", "Tags": [{"Key": "scholarchain:stack", "Value": "spike-emr"}]}]})
        self.put("head-bucket.rc", "0")
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)
        kinds = {b["kind"] for b in out["billable_remaining"]}
        self.assertEqual(kinds, {"ebs-volume", "network-interface", "efs-file-system", "s3-bucket"})

    def test_unrelated_efs_is_ignored(self):
        self.j("efs-describe-file-systems.json", {"FileSystems": [{"FileSystemId": "fs-9", "LifeCycleState": "available", "Tags": []}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 0)

    def test_unclassified_tagged_resource_fails_closed(self):
        self.j("resourcegroupstaggingapi-get-resources.json", {"ResourceTagMappingList": [{"ResourceARN": f"arn:aws:lambda:us-east-2:{ACCT}:function:mystery"}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 2)
        self.assertTrue(out["billable_remaining"][0]["kind"].startswith("unclassified-"))

    def test_leftover_vpc_is_reported_but_not_billable(self):
        self.j("resourcegroupstaggingapi-get-resources.json", {"ResourceTagMappingList": [{"ResourceARN": f"arn:aws:ec2:us-east-2:{ACCT}:vpc/vpc-1"}]})
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 0)
        self.assertEqual(out["nonbillable_residual"][0]["kind"], "ec2:vpc")

    def test_inconclusive_when_a_describe_fails(self):
        self.put("ec2-describe-nat-gateways.rc", "255")
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 3)
        self.assertFalse(out["clean"])

    def test_inconclusive_when_bucket_status_unknown(self):
        self.put("head-bucket.rc", "254")
        self.put("head-bucket.err", "An error occurred (403) when calling the HeadBucket operation: Forbidden")
        r, out = self.run_inv()
        self.assertEqual(r.returncode, 3)

    def test_only_read_only_calls_are_made(self):
        self.run_inv()
        with open(self.aws_log) as handle:
            calls = [l for l in handle if l.strip()]
        for call in calls:
            self.assertRegex(call, r"aws (resourcegroupstaggingapi get-resources|emr list-clusters|ec2 describe-|efs describe-|kms (list-aliases|describe-key)|s3api head-bucket)")


if __name__ == "__main__":
    unittest.main()
