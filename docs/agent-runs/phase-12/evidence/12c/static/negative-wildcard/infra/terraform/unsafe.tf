resource "aws_kms_key" "k" { policy = jsonencode({Statement=[{Effect="Allow",Action=["kms:Decrypt"],Resource="*"}]}) }
locals { p = [{Effect="Deny",Action=["s3:*"],Resource="*",Principal="*"},{Effect="Allow",Action=["*"],Resource=["arn:aws:s3:::synthetic-course/*"]}] }
