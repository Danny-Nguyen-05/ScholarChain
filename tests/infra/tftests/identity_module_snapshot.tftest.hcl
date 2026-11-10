# Test-engineer snapshot (copied into the SCRATCH wrapper root of modules/identity as tests/zz_identity_module_snapshot.tftest.hcl).
# Asserts nothing: it applies the wrapper (module "m") against mock_provider so the Python tests can read the IAM policy documents
# that embed the key ARN, which the real provider leaves unknown in an offline plan.
mock_provider "aws" {
  mock_resource "aws_kms_key" {
    defaults = { arn = "arn:aws:kms:us-east-2:111122223333:key/11111111-2222-3333-4444-555555555555", key_id = "11111111-2222-3333-4444-555555555555" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::111122223333:role/synthetic" }
  }
}

run "snapshot" {
  command = apply
}
