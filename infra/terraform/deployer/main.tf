provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = {
      course               = "CS441"
      project              = "ScholarChain"
      environment          = "deployer"
      owner                = var.owner
      "scholarchain:stack" = "deployer"
    }
  }
}

locals {
  role_arn = "arn:aws:iam::${var.account_id}:role/${var.role_name}"

  # Trust: exactly one named principal, MFA required.
  trust_policy = {
    Version = "2012-10-17"
    Statement = [{
      Sid       = "OperatorWithMfaOnly"
      Effect    = "Allow"
      Principal = { AWS = var.operator_principal_arn }
      Action    = "sts:AssumeRole"
      Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
    }]
  }

  # Document the human operator must hold to call AssumeRole. Output only; this
  # root attaches nothing to the operator.
  operator_caller_policy = {
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AssumeOnlyDeployerRoleWithMfa"
      Effect    = "Allow"
      Action    = ["sts:AssumeRole"]
      Resource  = [local.role_arn]
      Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
    }]
  }

  # Same-device `aws login` (browser OAuth) for this role. Independent of the
  # permission sets because every set needs it. Mirrors the reviewed billing-role login
  # policy in docs/agent-runs/phase-12/evidence/12d-human-identity-bootstrap/
  # user-supplied-policy-readbacks/role-login-policy.json. It grants sign-in only.
  # https://aws.amazon.com/blogs/security/introducing-oauth-support-for-aws-mcp-server/
  login_policy = {
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DeployerSameDeviceLogin"
      Effect   = "Allow"
      Action   = ["signin:AuthorizeOAuth2Access", "signin:CreateOAuth2Token"]
      Resource = ["arn:aws:signin:${var.region}:${var.account_id}:oauth2/public-client/localhost"]
      Condition = {
        StringEquals = { "signin:OAuthClientId" = "arn:aws:signin:::devtools/same-device" }
      }
    }]
  }

  known_sets   = keys(local.permission_sets)
  unknown_sets = [for s in var.enabled_permission_sets : s if !contains(local.known_sets, s)]

  # Flatten selected permission sets into one policy per (set, part).
  selected_policies = merge([
    for s in var.enabled_permission_sets : {
      for part, doc in lookup(local.permission_sets, s, {}) :
      "${s}--${part}" => { set = s, part = part, document = doc }
    }
  ]...)
}

resource "aws_iam_role" "deployer" {
  name                 = var.role_name
  description          = "Scoped ScholarChain deployer; assumed by one MFA-authenticated human operator."
  max_session_duration = 3600
  assume_role_policy   = jsonencode(local.trust_policy)

  lifecycle {
    precondition {
      condition     = length(local.unknown_sets) == 0
      error_message = "Unknown permission set(s) requested: ${join(", ", local.unknown_sets)}. Known: ${join(", ", local.known_sets)}."
    }
  }
}

# Ceiling policy for the spike's own IAM roles. The deployer may only create
# spike roles that carry exactly this boundary.
resource "aws_iam_policy" "spike_boundary" {
  count       = contains(var.enabled_permission_sets, "spike-emr") ? 1 : 0
  name        = local.spike_boundary_name
  description = "Permissions boundary for scholarchain-spike-emr-* roles."
  policy      = jsonencode(local.spike_boundary_policy)
}

resource "aws_iam_policy" "permission_set" {
  for_each    = local.selected_policies
  name        = "${var.role_name}-${each.key}"
  description = "Deployer permission set ${each.value.set}, part ${each.value.part}."
  policy      = jsonencode(each.value.document)
}

resource "aws_iam_role_policy_attachment" "permission_set" {
  for_each   = local.selected_policies
  role       = aws_iam_role.deployer.name
  policy_arn = aws_iam_policy.permission_set[each.key].arn
}

# Always attached, whatever enabled_permission_sets contains.
resource "aws_iam_role_policy" "login" {
  name   = "${var.role_name}-same-device-login"
  role   = aws_iam_role.deployer.id
  policy = jsonencode(local.login_policy)
}

