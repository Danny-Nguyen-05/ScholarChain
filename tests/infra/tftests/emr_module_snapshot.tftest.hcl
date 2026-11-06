# Test-engineer snapshot (copied into the SCRATCH wrapper root of the EMR module as tests/zz_emr_module_snapshot.tftest.hcl).
# It asserts nothing: it applies the wrapper against mock_provider (no AWS call is possible) so the Python tests can read the
# rendered IAM and EFS policies that embed resource ARNs.
mock_provider "aws" {
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
  mock_resource "aws_security_group" {
    defaults = {
      id = "sg-0123456789abcdef9"
    }
  }
}

run "snapshot" {
  command = apply
}
