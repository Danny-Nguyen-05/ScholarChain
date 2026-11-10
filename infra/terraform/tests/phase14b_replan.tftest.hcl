# Replan W5b (Phase 14B, USD 25 course cap): ACM certificate, Neptune tunnel, Neptune and ALB outputs, purge-ready data stores.
# Every expectation is hand-derived from the work order and the naming contract (infra/terraform/deployer/README.md, "Replan W5a"):
#   - project = scholarchain, environment = course, so name_prefix = scholarchain-course;
#   - the runtime permissions boundary ARN is arn:aws:iam::<account>:policy/scholarchain-course-permissions-boundary;
#   - the tunnel role is scholarchain-course-neptune-tunnel-task, the task definition family scholarchain-course-neptune-tunnel;
#   - Fargate 256 CPU / 512 MiB is a valid pair; ECS Exec needs a writable root file system and an init process.
# The mock and override header is copied from phase14b_root.tftest.hcl (a test file cannot import another file's mocks) plus an
# aws_acm_certificate mock that returns one synthetic DNS validation option. All identifiers are synthetic (account 111122223333,
# api.example.invalid). Plan-only runs: never remove the mock_provider or change command to apply. No AWS client runs.

mock_provider "aws" {
  override_during = plan
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:us-east-1:111122223333:key/00000000-0000-0000-0000-000000000001"
      key_id = "00000000-0000-0000-0000-000000000001"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::synthetic-phase12a-bucket", id = "synthetic-phase12a-bucket" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-east-1:111122223333:table/synthetic-phase12a-table" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-1:111122223333:synthetic-phase12a-queue"
      id  = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-phase12a-queue"
      url = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-phase12a-queue"
    }
  }
  mock_resource "aws_sfn_state_machine" { defaults = { arn = "arn:aws:states:us-east-1:111122223333:stateMachine:scholarchain-course-embedding-dispatch" } }
  mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::111122223333:role/synthetic-phase12b-role" } }
  mock_resource "aws_s3vectors_vector_bucket" { defaults = { vector_bucket_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors" } }
  mock_resource "aws_neptune_cluster" { defaults = { cluster_resource_id = "cluster-synthetic-graph", endpoint = "synthetic.cluster.neptune.amazonaws.com", reader_endpoint = "synthetic.cluster-ro.neptune.amazonaws.com" } }
  mock_resource "aws_acm_certificate" {
    defaults = {
      arn = "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-0000000000a1"
      domain_validation_options = [{
        domain_name           = "api.example.invalid"
        resource_record_name  = "_0123456789abcdef.api.example.invalid."
        resource_record_type  = "CNAME"
        resource_record_value = "_fedcba9876543210.acm-validations.invalid."
      }]
    }
  }
  mock_resource "aws_ecs_cluster" { defaults = { id = "arn:aws:ecs:us-east-1:111122223333:cluster/scholarchain-course" } }
  mock_resource "aws_ecs_task_definition" { defaults = { arn = "arn:aws:ecs:us-east-1:111122223333:task-definition/synthetic-service:1" } }
  mock_resource "aws_ecr_repository" { defaults = { arn = "arn:aws:ecr:us-east-1:111122223333:repository/synthetic-phase12b-repo", repository_url = "111122223333.dkr.ecr.us-east-1.amazonaws.com/synthetic-phase12b-repo" } }
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:loadbalancer/app/synthetic/1234567890123456" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/synthetic/1234567890123456" } }
  mock_resource "aws_service_discovery_service" { defaults = { arn = "arn:aws:servicediscovery:us-east-1:111122223333:service/srv-synthetic" } }
  mock_resource "aws_vpc_endpoint" {
    defaults = { prefix_list_id = "pl-synthetic" }
  }
}
override_resource {
  target          = module.network.aws_route_table.public
  override_during = plan
  values          = { id = "rtb-synthetic-public" }
}
override_resource {
  target          = module.network.aws_route_table.application
  override_during = plan
  values          = { id = "rtb-synthetic-application" }
}
override_resource {
  target          = module.network.aws_route_table.data
  override_during = plan
  values          = { id = "rtb-synthetic-data" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["researcher-profile-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/researcher-profile-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-community-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/collaboration-community-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["paper-abstract-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/paper-abstract-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-path-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/collaboration-path-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["topic-institution-summary-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/topic-institution-summary-v1" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.embedding
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-1:111122223333:synthetic-work", url = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-work", id = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-work" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.dead_letter
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-1:111122223333:synthetic-dlq", url = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-dlq", id = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-dlq" }
}
override_resource {
  target          = module.identity.aws_iam_role.execution["graph-service"]
  override_during = plan
  values          = { arn = "arn:aws:iam::111122223333:role/synthetic-graph-service-execution" }
}
override_resource {
  target          = module.network.aws_subnet.application["0"]
  override_during = plan
  values          = { id = "subnet-synthetic-app-0" }
}
override_resource {
  target          = module.network.aws_subnet.application["1"]
  override_during = plan
  values          = { id = "subnet-synthetic-app-1" }
}
override_resource {
  target          = module.network.aws_security_group.role["graph-service"]
  override_during = plan
  values          = { id = "sg-synthetic-graph-service" }
}
override_resource {
  target          = module.identity.aws_iam_role.neptune_tunnel_task[0]
  override_during = plan
  values          = { arn = "arn:aws:iam::111122223333:role/synthetic-neptune-tunnel-task" }
}
variables {
  aws_account_id                   = "111122223333"
  aws_region                       = "us-east-1"
  aws_profile                      = "synthetic-not-a-real-profile"
  availability_zones               = ["us-east-1a", "us-east-1b"]
  deployment_trusted_principal_arn = "arn:aws:iam::111122223333:role/synthetic-architect"
  budget_limit_usd                 = 50 # Synthetic validation input, not the user's budget.
  # Base shape: the runtime is disabled; every run flips what it needs. Neptune is configured so the runtime runs are valid.
  runtime_enabled              = false
  runtime_composition_verified = false
  embedding_model_version      = "synthetic-pinned-version"
  synthesis_model_id           = "anthropic.claude-synthetic-test-v1:0"
  neptune_enabled              = true
  neptune_engine_version       = "1.4.6.3"
  neptune_parameter_family     = "neptune1.4"
  api_domain_name              = "api.example.invalid"
  service_secret_bindings = {
    "query-api" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-api-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-api-internal-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-api-internal-token-AbCdEf"
    }
    "graph-service" = {
      SCHOLARCHAIN_GRAPH_CURSOR_KEY      = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-graph-cursor-AbCdEf"
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-graph-service-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-graph-service-internal-hash-AbCdEf"
    }
    "semantic-service" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-semantic-service-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-semantic-service-internal-hash-AbCdEf"
    }
    "embedding-worker" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-embedding-worker-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-embedding-worker-internal-hash-AbCdEf"
    }
  }
}

# ---- ACM certificate: base-apply ----------------------------------------------------------------------------------------------------

run "base_apply_creates_the_certificate_and_no_validation_resource" {
  command = plan

  assert {
    condition     = length(output.phase14b_controls.certificates) == 1 && output.phase14b_controls.certificates[0].domain_name == "api.example.invalid" && output.phase14b_controls.certificates[0].validation_method == "DNS"
    error_message = "With api_domain_name set the base apply (runtime disabled) creates exactly one DNS-validated certificate for that name."
  }
  assert {
    condition     = length(output.phase14b_controls.validations) == 0
    error_message = "base-apply must not contain aws_acm_certificate_validation: it would block on the human's Cloudflare record."
  }
  assert {
    condition     = output.phase14b_controls.runtime_deployed == false && output.phase14b_controls.https_enabled == false && output.phase14b_controls.listener_cert == null && length(output.phase12b_controls.runtime.listeners) == 0 && length(output.phase12b_controls.runtime.load_balancers) == 0
    error_message = "Without the runtime there is no listener and no load balancer; the certificate alone does not enable HTTPS."
  }
  assert {
    condition     = output.alb_dns_name == null && output.neptune_tunnel == null
    error_message = "No ALB DNS name and no tunnel before the runtime exists."
  }
}

run "the_certificate_carries_the_required_project_tags_the_deployer_conditions_on" {
  command = plan

  assert {
    condition     = output.phase14b_controls.certificates[0].tags["project"] == "scholarchain" && output.phase14b_controls.certificates[0].tags["environment"] == "course"
    error_message = "acm:RequestCertificate is allowed only with aws:RequestTag/project = scholarchain and aws:RequestTag/environment = course."
  }
  assert {
    condition     = jsonencode(output.phase14b_controls.certificates[0].tags) == jsonencode(output.required_tags) && alltrue([for k in keys(output.phase14b_controls.certificates[0].tags) : contains(["course", "project", "environment", "owner", "expiration_date"], k)])
    error_message = "The certificate tags are the root's required tags only, a subset of the deployer's main_tag_keys (aws:TagKeys)."
  }
  assert {
    condition     = length(output.phase14b_controls.certificates) == 1 && !can(regex("key_algorithm|subject_alternative_names|private_key|certificate_body", file("phase14b.tf")))
    error_message = "The certificate uses the provider default key algorithm, has no SAN and imports no key material: none of those arguments is configured."
  }
}

run "the_dns_validation_record_is_a_root_output" {
  command = plan

  assert {
    condition     = length(output.acm_validation_records) == 1 && output.acm_validation_records[0].domain_name == "api.example.invalid" && output.acm_validation_records[0].name == "_0123456789abcdef.api.example.invalid." && output.acm_validation_records[0].type == "CNAME" && output.acm_validation_records[0].value == "_fedcba9876543210.acm-validations.invalid."
    error_message = "acm_validation_records lists name, type and value of the certificate's DNS validation option (the Cloudflare CNAME)."
  }
  assert {
    condition     = output.acm_certificate_arn == "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-0000000000a1"
    error_message = "acm_certificate_arn is the certificate's ARN."
  }
}

run "without_api_domain_name_there_is_no_certificate_and_no_record" {
  command = plan
  variables {
    api_domain_name = null
  }

  assert {
    condition     = length(output.phase14b_controls.certificates) == 0 && length(output.phase14b_controls.validations) == 0 && length(output.acm_validation_records) == 0 && output.acm_certificate_arn == null
    error_message = "api_domain_name = null (the default) creates nothing."
  }
}

# ---- ACM certificate: runtime-apply --------------------------------------------------------------------------------------------------

run "runtime_apply_adds_one_validation_with_the_default_15_minute_timeout" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }

  assert {
    condition     = length(output.phase14b_controls.validations) == 1 && output.phase14b_controls.validations[0].certificate_arn == output.acm_certificate_arn
    error_message = "The runtime stage adds exactly one aws_acm_certificate_validation for the certificate."
  }
  assert {
    condition     = output.phase14b_controls.validations[0].timeouts.create == "15m"
    error_message = "The validation wait is bounded by acm_validation_timeout, default 15m."
  }
}

run "the_https_listener_uses_the_validated_certificate_arn" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }

  assert {
    condition     = length(output.phase12b_controls.runtime.listeners) == 1 && output.phase12b_controls.runtime.listeners[0].protocol == "HTTPS" && output.phase12b_controls.runtime.listeners[0].port == 443
    error_message = "Runtime with api_domain_name: one HTTPS listener on 443."
  }
  assert {
    condition     = output.phase12b_controls.runtime.listeners[0].certificate_arn == output.phase14b_controls.validations[0].certificate_arn && output.phase14b_controls.listener_cert == output.phase14b_controls.validations[0].certificate_arn
    error_message = "The listener takes its certificate from aws_acm_certificate_validation.certificate_arn, never from the bare certificate."
  }
  assert {
    condition     = output.phase14b_controls.https_enabled == true && can(regex("one\\(aws_acm_certificate_validation\\.api\\[\\*\\]\\.certificate_arn\\)", file("phase14b.tf"))) && !can(regex("listener_cert_arn\\s*=[^\\n]*aws_acm_certificate\\.api\\[", file("phase14b.tf")))
    error_message = "In the mock plan the bare certificate ARN and the validation's ARN are equal, so the wiring is checked in the source too: the listener certificate is read from aws_acm_certificate_validation.api and never from the bare certificate."
  }
  assert {
    condition     = output.phase14b_controls.https_enabled == true && output.phase12b_controls.runtime.services["query-api"].health_check_grace_period_seconds == 300 && length(output.phase12b_controls.runtime.load_balancers) == 1
    error_message = "query-api is load-balanced (so it carries the 300 s grace period) although the certificate ARN is only known after apply."
  }
}

run "a_custom_validation_timeout_reaches_the_validation_resource" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    acm_validation_timeout       = "30m"
  }

  assert {
    condition     = output.phase14b_controls.validations[0].timeouts.create == "30m"
    error_message = "acm_validation_timeout reaches the validation resource."
  }
}

run "the_validation_needs_the_runtime_even_when_an_image_revision_is_given" {
  command = plan
  variables {
    image_revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }

  assert {
    condition     = length(output.phase14b_controls.certificates) == 1 && length(output.phase14b_controls.validations) == 0 && length(output.phase12b_controls.runtime.listeners) == 0
    error_message = "An image revision alone (runtime disabled) keeps the base shape: certificate, no validation, no listener."
  }
}

run "alb_dns_name_is_output_once_the_load_balancer_exists" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }

  assert {
    condition     = output.alb_dns_name != null && output.alb_dns_name == output.phase12b_controls.runtime.load_balancers[0].dns_name
    error_message = "alb_dns_name is the ALB DNS name the human points the Cloudflare CNAME at."
  }
}

# ---- timeout and domain name validation -----------------------------------------------------------------------------------------------

run "a_zero_minute_timeout_is_rejected" {
  command = plan
  variables {
    acm_validation_timeout = "0m"
  }
  expect_failures = [var.acm_validation_timeout]
}

run "a_timeout_above_60_minutes_is_rejected" {
  command = plan
  variables {
    acm_validation_timeout = "61m"
  }
  expect_failures = [var.acm_validation_timeout]
}

run "a_timeout_in_seconds_or_hours_is_rejected" {
  command = plan
  variables {
    acm_validation_timeout = "1h"
  }
  expect_failures = [var.acm_validation_timeout]
}

run "a_timeout_of_exactly_60_minutes_is_accepted" {
  command = plan
  variables {
    acm_validation_timeout = "60m"
  }

  assert {
    condition     = length(output.phase14b_controls.certificates) == 1
    error_message = "60m is the inclusive upper bound."
  }
}

run "a_two_label_domain_is_rejected_because_an_apex_cannot_take_a_cname" {
  command = plan
  variables {
    api_domain_name = "example.invalid"
  }
  expect_failures = [var.api_domain_name]
}

run "a_wildcard_domain_is_rejected" {
  command = plan
  variables {
    api_domain_name = "*.example.invalid"
  }
  expect_failures = [var.api_domain_name]
}

run "an_uppercase_domain_is_rejected" {
  command = plan
  variables {
    api_domain_name = "API.example.invalid"
  }
  expect_failures = [var.api_domain_name]
}

run "a_domain_with_a_trailing_dot_or_port_is_rejected" {
  command = plan
  variables {
    api_domain_name = "api.example.invalid:443"
  }
  expect_failures = [var.api_domain_name]
}

# ---- exactly one certificate source ----------------------------------------------------------------------------------------------------

run "both_certificate_sources_at_once_are_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    https_certificate_arn        = "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-000000000001"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "the_external_certificate_arn_alone_still_works_and_creates_no_certificate" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    api_domain_name              = null
    https_certificate_arn        = "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-000000000001"
  }

  assert {
    condition     = length(output.phase14b_controls.certificates) == 0 && length(output.phase14b_controls.validations) == 0 && output.acm_certificate_arn == null
    error_message = "An externally provided ARN creates no certificate and no validation."
  }
  assert {
    condition     = output.phase12b_controls.runtime.listeners[0].certificate_arn == "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-000000000001" && output.phase14b_controls.https_enabled == true
    error_message = "The external ARN is the listener certificate, unchanged behavior."
  }
}

run "an_external_arn_without_ingress_cidrs_is_still_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    api_domain_name              = null
    https_certificate_arn        = "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-000000000001"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "api_domain_name_with_the_runtime_but_without_ingress_cidrs_is_refused_no_http_fallback" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

# ---- Neptune tunnel ----------------------------------------------------------------------------------------------------------------------

run "the_tunnel_is_absent_by_default_even_with_the_runtime" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }

  assert {
    condition     = output.phase14b_controls.tunnel_role == null && length(output.phase14b_controls.tunnel_task) == 0 && output.neptune_tunnel == null
    error_message = "neptune_tunnel_enabled defaults to false: no role, no task definition, no output."
  }
}

run "the_tunnel_needs_the_runtime_with_an_image_revision" {
  command = plan
  variables {
    neptune_tunnel_enabled = true
    image_revision         = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }

  assert {
    condition     = output.phase14b_controls.tunnel_role == null && length(output.phase14b_controls.tunnel_task) == 0 && output.neptune_tunnel == null
    error_message = "With the runtime disabled the tunnel is not created even when requested (base-apply is unchanged)."
  }
}

run "the_tunnel_role_has_the_runtime_boundary_and_the_ecs_task_trust" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
  }

  assert {
    condition     = output.phase14b_controls.tunnel_role.role_name == "scholarchain-course-neptune-tunnel-task"
    error_message = "Role name per the deployer naming contract: scholarchain-<env>-neptune-tunnel-task (matches the *-task patterns)."
  }
  assert {
    condition     = output.phase14b_controls.tunnel_role.boundary == "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary" && output.iam_controls.role_boundaries["task-graph-service"] == output.phase14b_controls.tunnel_role.boundary
    error_message = "The tunnel role carries the runtime permissions boundary, the only boundary the deployer accepts for a -task role."
  }
  assert {
    condition     = output.phase14b_controls.tunnel_role.trust == output.iam_controls.task_trust["graph-service"] && jsondecode(output.phase14b_controls.tunnel_role.trust).Statement[0].Principal.Service == "ecs-tasks.amazonaws.com" && jsondecode(output.phase14b_controls.tunnel_role.trust).Statement[0].Condition.StringEquals["aws:SourceAccount"] == "111122223333"
    error_message = "Same trust as the other task roles: ecs-tasks.amazonaws.com with the source account and ECS source ARN conditions."
  }
}

run "the_tunnel_role_policy_is_exactly_the_four_ssmmessages_channel_actions" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
  }

  assert {
    condition     = length(jsondecode(output.phase14b_controls.tunnel_role.policy).Statement) == 1 && toset(jsondecode(output.phase14b_controls.tunnel_role.policy).Statement[0].Action) == toset(["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"]) && length(jsondecode(output.phase14b_controls.tunnel_role.policy).Statement[0].Action) == 4
    error_message = "One statement, exactly the four ssmmessages channel actions, no other action."
  }
  assert {
    condition     = jsondecode(output.phase14b_controls.tunnel_role.policy).Statement[0].Effect == "Allow" && jsondecode(output.phase14b_controls.tunnel_role.policy).Statement[0].Resource == "*" && output.phase14b_controls.tunnel_role.policy_name == "ecs-exec-channels"
    error_message = "The channel actions have no resource type, so Resource is * (and nothing else is granted)."
  }
  assert {
    condition     = !strcontains(output.phase14b_controls.tunnel_role.policy, "neptune-db") && !strcontains(output.phase14b_controls.tunnel_role.policy, "s3:") && !strcontains(output.phase14b_controls.tunnel_role.policy, "kms:") && !strcontains(output.phase14b_controls.tunnel_role.policy, "secretsmanager") && !strcontains(output.phase14b_controls.tunnel_role.policy, "iam:")
    error_message = "The tunnel role has no data, key, secret or IAM access."
  }
}

run "the_tunnel_task_definition_has_the_contracted_family_size_and_roles" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
  }

  assert {
    condition     = length(output.phase14b_controls.tunnel_task) == 1 && output.phase14b_controls.tunnel_task[0].family == "scholarchain-course-neptune-tunnel"
    error_message = "One task definition with family scholarchain-<env>-neptune-tunnel (matches task-definition/scholarchain-<env>-*:*)."
  }
  assert {
    condition     = output.phase14b_controls.tunnel_task[0].cpu == "256" && output.phase14b_controls.tunnel_task[0].memory == "512" && output.phase14b_controls.tunnel_task[0].network_mode == "awsvpc" && output.phase14b_controls.tunnel_task[0].requires_compatibilities == toset(["FARGATE"])
    error_message = "Fargate awsvpc 256 CPU / 512 MiB, the smallest valid size."
  }
  assert {
    condition     = one(output.phase14b_controls.tunnel_task[0].runtime_platform).cpu_architecture == "X86_64" && one(output.phase14b_controls.tunnel_task[0].runtime_platform).operating_system_family == "LINUX"
    error_message = "linux/amd64 like the graph-service image it runs."
  }
  assert {
    condition     = output.phase14b_controls.tunnel_task[0].task_role_arn == "arn:aws:iam::111122223333:role/synthetic-neptune-tunnel-task" && output.phase14b_controls.tunnel_task[0].execution_role_arn == "arn:aws:iam::111122223333:role/synthetic-graph-service-execution"
    error_message = "Task role = the tunnel task role; execution role = scholarchain-<env>-graph-service-execution (it can pull the image and log to the graph-service group)."
  }
}

run "the_tunnel_container_only_sleeps_logs_to_the_graph_service_group_and_supports_ecs_exec" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
  }

  assert {
    condition     = length(jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)) == 1 && jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].name == "neptune-tunnel" && jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].essential == true
    error_message = "A single essential container."
  }
  assert {
    condition     = jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].entryPoint == ["sleep"] && jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].command == ["14400"]
    error_message = "The container just sleeps for a bounded 14400 s (4 h, the operator session maximum) and does nothing else."
  }
  assert {
    condition     = jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].image == "${output.repository_urls["graph-service"]}:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    error_message = "The graph-service image at the immutable image revision."
  }
  assert {
    condition     = jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].readonlyRootFilesystem == false && jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].linuxParameters.initProcessEnabled == true
    error_message = "ECS Exec needs a writable root file system (AWS documents it cannot work read-only) and an init process."
  }
  assert {
    condition     = jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].logConfiguration.options["awslogs-group"] == "/scholarchain-course/graph-service" && jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0].logConfiguration.options["awslogs-stream-prefix"] == "neptune-tunnel"
    error_message = "Logs go to the graph-service log group only (the execution role cannot write elsewhere)."
  }
  assert {
    condition     = !contains(keys(jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0]), "secrets") && !contains(keys(jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0]), "environment") && !contains(keys(jsondecode(output.phase14b_controls.tunnel_task[0].container_definitions)[0]), "portMappings")
    error_message = "No secrets, no environment, no listening port: the container carries nothing."
  }
}

run "there_is_no_ecs_service_for_the_tunnel" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
  }

  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.services)) == toset(["query-api", "graph-service", "semantic-service", "embedding-worker"])
    error_message = "The four runtime services only: the tunnel is a one-off task, not a service, so nothing runs or bills between loads."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.task_definitions)) == toset(["query-api", "graph-service", "semantic-service", "embedding-worker"]) && length(output.phase14b_controls.tunnel_task) == 1
    error_message = "The service task definitions are unchanged; the tunnel task definition is separate."
  }
}

run "the_tunnel_output_has_what_the_run_task_command_needs" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
  }

  assert {
    condition     = output.neptune_tunnel.cluster_name == "scholarchain-course" && output.neptune_tunnel.family == "scholarchain-course-neptune-tunnel" && output.neptune_tunnel.container_name == "neptune-tunnel"
    error_message = "Cluster name, family and container name for run-task, execute-command and the port-forward target."
  }
  assert {
    condition     = output.neptune_tunnel.task_definition_arn == output.phase14b_controls.tunnel_task[0].arn && output.neptune_tunnel.security_group_id == "sg-synthetic-graph-service" && output.neptune_tunnel.security_group_id == output.network_ids.security_group_ids["graph-service"] && jsonencode(output.neptune_tunnel.subnet_ids) == jsonencode(["subnet-synthetic-app-0", "subnet-synthetic-app-1"])
    error_message = "The graph-service security group (the only one Neptune admits) and the two application subnets."
  }
}

# ---- Neptune outputs ---------------------------------------------------------------------------------------------------------------------

run "neptune_writer_endpoint_port_and_resource_id_are_outputs" {
  command = plan

  assert {
    condition     = output.neptune_writer_endpoint == "synthetic.cluster.neptune.amazonaws.com" && output.neptune_port == 8182 && output.neptune_cluster_resource_id == "cluster-synthetic-graph"
    error_message = "Writer (cluster) endpoint hostname, port and cluster resource id come from the cluster."
  }
  assert {
    condition     = output.phase12b_controls.deployment_contract.neptune_endpoint == "https://synthetic.cluster-ro.neptune.amazonaws.com:8182" && output.neptune_writer_endpoint != "synthetic.cluster-ro.neptune.amazonaws.com"
    error_message = "The runtime services keep the READER endpoint; the writer endpoint is a separate output."
  }
}

run "neptune_outputs_are_null_while_neptune_is_disabled" {
  command = plan
  variables {
    neptune_enabled = false
  }

  assert {
    condition     = output.neptune_writer_endpoint == null && output.neptune_port == null && output.neptune_cluster_resource_id == null
    error_message = "No cluster, no endpoint, no port, no resource id."
  }
}

# ---- W4: purge-ready data stores ------------------------------------------------------------------------------------------------------------

run "the_data_buckets_and_vector_stores_have_no_prevent_destroy" {
  command = plan

  assert {
    condition     = length(output.data_controls.buckets) == 7 && !can(regex("prevent_destroy\\s*=", file("modules/datalake/main.tf"))) && !can(regex("prevent_destroy\\s*=", file("modules/s3vectors/main.tf")))
    error_message = "W4: neither the S3 buckets nor the S3 Vectors bucket and indexes carry a prevent_destroy lifecycle guard any more."
  }
  assert {
    condition     = length(output.data_controls.buckets) == 7 && can(regex("prevent_destroy\\s*=\\s*true", file("modules/foundation/bootstrap/main.tf")))
    error_message = "The optional state-backend bootstrap module keeps its prevent_destroy guards (the backend is preserved)."
  }
}

run "force_destroy_is_off_by_default_for_every_bucket_and_the_vector_bucket" {
  command = plan

  assert {
    condition     = alltrue([for b in output.data_controls.buckets : b.force_destroy == false]) && length(output.data_controls.buckets) == 7 && output.phase12b_controls.vectors.bucket.force_destroy == false
    error_message = "Outside cleanup mode the seven buckets and the vector bucket cannot be force-emptied."
  }
}

run "force_destroy_is_on_only_in_cleanup_mode_for_every_bucket_and_the_vector_bucket" {
  command = plan
  variables {
    cleanup_mode = true
  }

  assert {
    condition     = alltrue([for b in output.data_controls.buckets : b.force_destroy == true]) && length(output.data_controls.buckets) == 7 && output.phase12b_controls.vectors.bucket.force_destroy == true
    error_message = "cleanup_mode = true is the only way force_destroy becomes true (S3 versions and the vector bucket contents are then deleted with the resource)."
  }
}
