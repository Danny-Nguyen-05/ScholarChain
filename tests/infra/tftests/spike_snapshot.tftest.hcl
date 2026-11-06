# Test-engineer snapshot (tests/infra/infra_support.py copies this file into a SCRATCH copy of the spike root as
# tests/zz_spike_snapshot.tftest.hcl and runs it with `terraform test -json -verbose`). It asserts nothing: its only
# purpose is to apply the root against mock_provider (no AWS call is possible) so the Python tests can read the
# post-apply state, where IAM policies that embed resource ARNs are fully rendered. The mock ARNs below are the
# same fixed values the root's own tests use.
mock_provider "aws" {
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:us-east-2:111122223333:key/11111111-2222-3333-4444-555555555555"
      key_id = "11111111-2222-3333-4444-555555555555"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = {
      id  = "scholarchain-spike-emr-111122223333-us-east-2"
      arn = "arn:aws:s3:::scholarchain-spike-emr-111122223333-us-east-2"
    }
  }
  mock_resource "aws_efs_file_system" {
    defaults = {
      id  = "fs-0123456789abcdef0"
      arn = "arn:aws:elasticfilesystem:us-east-2:111122223333:file-system/fs-0123456789abcdef0"
    }
  }
  mock_resource "aws_efs_access_point" {
    defaults = {
      id  = "fsap-0123456789abcdef0"
      arn = "arn:aws:elasticfilesystem:us-east-2:111122223333:access-point/fsap-0123456789abcdef0"
    }
  }
  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::111122223333:role/mock-role"
    }
  }
  mock_resource "aws_iam_instance_profile" {
    defaults = {
      arn = "arn:aws:iam::111122223333:instance-profile/mock-profile"
    }
  }
}

variables {
  account_id               = "111122223333"
  owner                    = "example-owner"
  expiration_date          = "2026-11-04"
  permissions_boundary_arn = "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary"
  deployer_role_arn        = "arn:aws:iam::111122223333:role/scholarchain-deployer"
  runtime_tgz_path         = "tests/fixtures/runtime-fixture.bin"
  runtime_tgz_sha256       = "3cdbba1642f4fa67dee2a3d68b95263c0155f21e6c05735ce428ecac875ab782"
  inputs_tgz_path          = "../../../../docs/agent-runs/phase-12/evidence/12d-portable-runtime/g1-upstream-inputs.tgz"
  g1_config_template_path  = "../../../../docs/agent-runs/phase-12/evidence/12d-portable-runtime/build/relocated-g1-config.json"
}

run "snapshot" {
  command = apply
}
