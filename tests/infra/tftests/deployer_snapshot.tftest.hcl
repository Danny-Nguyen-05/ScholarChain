# Test-engineer snapshot (copied into a SCRATCH copy of the deployer root as tests/zz_deployer_snapshot.tftest.hcl).
# It asserts nothing: it applies the root against mock_provider (no AWS call is possible) so the Python tests can
# read resource-to-resource attachments, for example which role the always-attached login policy targets.
mock_provider "aws" {
  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::111122223333:role/mock-role"
    }
  }
  mock_resource "aws_iam_policy" {
    defaults = {
      arn = "arn:aws:iam::111122223333:policy/mock-policy"
    }
  }
}

variables {
  account_id             = "111122223333"
  operator_principal_arn = "arn:aws:iam::111122223333:user/example-operator"
  owner                  = "example-owner"
  # Decision 14-6 made phase14-main the default; this snapshot serves the Phase 13 spike-era suites, so it pins spike-emr.
  enabled_permission_sets = ["spike-emr"]
}

run "snapshot" {
  command = apply
}
