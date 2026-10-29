from pathlib import Path
r=Path('/Users/danny/Documents/UIC/CS441/ScholarChain/infra/terraform')
p=r/'tests/phase12b.tftest.hcl';s=p.read_text();marker='run "inactive_defaults_and_vector_contract" {\n  command = plan\n';assert s.count(marker)==1
assertion='''  assert {
    condition = length([for statement in jsondecode(output.iam_controls.kms_policy).Statement : statement if try(statement.Principal.Service, "") == "indexing.s3vectors.amazonaws.com" && statement.Effect == "Allow" && statement.Action == ["kms:Decrypt"] && statement.Resource == "*" && try(statement.Condition, {}) == {
      StringEquals = { "aws:SourceAccount" = "111122223333" }
      ArnLike = { "aws:SourceArn" = "arn:aws:s3vectors:us-east-1:111122223333:bucket/scholarchain-course-111122223333-vectors" }
      "ForAnyValue:StringEquals" = { "kms:EncryptionContextKeys" = ["aws:s3vectors:arn", "aws:s3vectors:resource-id"] }
    }]) == 1 && length(jsondecode(output.iam_controls.kms_policy).Statement) == 2
    error_message = "B3: The project CMK must allow exactly one S3 Vectors indexing service decrypt grant, restricted to the expected account, exact vector bucket ARN and S3 Vectors encryption context keys."
  }
'''
s=s.replace(marker,marker+assertion);p.write_text(s)
p=r/'README.md';s=p.read_text();s+='''
B3 CMK control: the key policy grants only `kms:Decrypt` to
`indexing.s3vectors.amazonaws.com`, restricted to the configured account, exact
project vector-bucket ARN and S3 Vectors encryption-context keys. `Resource="*"`
in this key policy means this CMK only; the account-root delegation is unchanged.
[AWS S3 Vectors encryption requirements](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-data-encryption.html).
''';p.write_text(s)
