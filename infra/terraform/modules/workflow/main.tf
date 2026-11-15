locals { state_machine_arn = "arn:aws:states:${var.aws_region}:${var.aws_account_id}:stateMachine:${var.name_prefix}-embedding-dispatch" }
# This is the named pipeline producer identity. Phase 13 supplies the authorized caller.
resource "aws_iam_role" "producer" {
  # D1: runtime boundary created by the deployer root (name and ARN scheme documented in modules/identity/main.tf).
  permissions_boundary = "arn:aws:iam::${var.aws_account_id}:policy/${var.name_prefix}-permissions-boundary"
  name                 = "${var.name_prefix}-embedding-producer"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Principal = { Service = "states.amazonaws.com" }, Action = "sts:AssumeRole",
    Condition = { StringEquals = { "aws:SourceAccount" = var.aws_account_id }, ArnEquals = { "aws:SourceArn" = local.state_machine_arn } }
  }] })
  tags = var.tags
}
resource "aws_iam_role_policy" "producer" {
  name = "send-configured-embedding-work"
  role = aws_iam_role.producer.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "SendOnlyWorkAndFailureQueues", Effect = "Allow", Action = ["sqs:SendMessage"], Resource = [var.queue_arn, var.dlq_arn] },
    { Sid = "EncryptOnlyProjectQueueMessages", Effect = "Allow", Action = ["kms:GenerateDataKey", "kms:Decrypt"], Resource = [var.kms_key_arn], Condition = { StringEquals = { "kms:ViaService" = "sqs.${var.aws_region}.amazonaws.com" } } }
    ,
    { Sid = "EncryptWorkflowState", Effect = "Allow", Action = ["kms:GenerateDataKey", "kms:Decrypt"], Resource = [var.kms_key_arn], Condition = { StringEquals = { "kms:EncryptionContext:aws:states:stateMachineArn" = local.state_machine_arn } } }
  ] })
}
resource "aws_sfn_state_machine" "embedding_dispatch" {
  name     = "${var.name_prefix}-embedding-dispatch"
  role_arn = aws_iam_role.producer.arn
  type     = "STANDARD"
  # Caller supplies one serialized EmbeddingWorkItem string. It cannot choose a queue.
  # No execution-data logs: manifest/document payloads are not copied into CloudWatch.
  definition = jsonencode({
    Comment        = "Dispatch one validated embedding-work string; bounded retries and exact failure queue"
    StartAt        = "ValidateWork"
    TimeoutSeconds = 120
    States = {
      ValidateWork = { Type = "Choice", Choices = [{ And = [{ Variable = "$.workItem", IsPresent = true }, { Variable = "$.workItem", IsString = true }], Next = "Enqueue" }], Default = "InvalidWork" }
      InvalidWork  = { Type = "Fail", Error = "InvalidEmbeddingWork", Cause = "workItem must be a serialized EmbeddingWorkItem string" }
      Enqueue = {
        Type       = "Task", Resource = "arn:aws:states:::sqs:sendMessage", TimeoutSeconds = 20,
        Parameters = { QueueUrl = var.queue_url, "MessageBody.$" = "$.workItem" },
        Retry      = [{ ErrorEquals = ["States.TaskFailed", "States.Timeout"], IntervalSeconds = 2, BackoffRate = 2, MaxAttempts = 2 }],
        Catch      = [{ ErrorEquals = ["States.ALL"], ResultPath = "$.dispatchError", Next = "RecordFailure" }], End = true
      }
      RecordFailure = {
        Type       = "Task", Resource = "arn:aws:states:::sqs:sendMessage", TimeoutSeconds = 20,
        Parameters = { QueueUrl = var.dlq_url, "MessageBody.$" = "$.workItem" },
        Retry      = [{ ErrorEquals = ["States.TaskFailed", "States.Timeout"], IntervalSeconds = 2, MaxAttempts = 1 }],
        Next       = "DispatchFailed"
      }
      DispatchFailed = { Type = "Fail", Error = "EmbeddingDispatchFailed", Cause = "Work dispatch failed; inspect execution and configured DLQ" }
    }
  })
  encryption_configuration {
    type       = "CUSTOMER_MANAGED_KMS_KEY"
    kms_key_id = var.kms_key_arn
    # AWS always reports 300 (its default); leaving this null made every plan show an update the provider's waiter never sees.
    kms_data_key_reuse_period_seconds = 300
  }
  tags       = var.tags
  depends_on = [aws_iam_role_policy.producer]
}
