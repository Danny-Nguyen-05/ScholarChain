output "arn" { value = aws_sfn_state_machine.embedding_dispatch.arn }
output "producer_role_arn" { value = aws_iam_role.producer.arn }
output "controls" { value = { definition = aws_sfn_state_machine.embedding_dispatch.definition, producer_policy = aws_iam_role_policy.producer.policy, trust = aws_iam_role.producer.assume_role_policy, encryption = aws_sfn_state_machine.embedding_dispatch.encryption_configuration } }
