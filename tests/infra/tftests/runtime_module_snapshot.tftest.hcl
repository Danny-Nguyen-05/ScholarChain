# Test-engineer snapshot (copied into the SCRATCH wrapper root of modules/runtime as tests/zz_runtime_module_snapshot.tftest.hcl).
# It asserts nothing: it applies the wrapper (module name "m") against mock_provider (no AWS call is possible) so the Python tests can
# read values that the real provider leaves unknown in an offline plan, for example the rendered container definitions that embed the
# ECR repository URLs. Each repository gets a distinct synthetic URL so that "which image" is observable.
mock_provider "aws" {
  mock_resource "aws_lb" {
    defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:loadbalancer/app/synthetic/1234567890123456", dns_name = "synthetic-alb.us-east-2.elb.amazonaws.com" }
  }
  mock_resource "aws_lb_target_group" {
    defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:targetgroup/synthetic/1234567890123456" }
  }
  mock_resource "aws_ecs_cluster" {
    defaults = { arn = "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course", id = "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course" }
  }
  mock_resource "aws_ecs_task_definition" {
    defaults = { arn = "arn:aws:ecs:us-east-2:111122223333:task-definition/synthetic:1" }
  }
  mock_resource "aws_ecr_repository" {
    defaults = { arn = "arn:aws:ecr:us-east-2:111122223333:repository/synthetic" }
  }
  mock_resource "aws_service_discovery_service" {
    defaults = { arn = "arn:aws:servicediscovery:us-east-2:111122223333:service/srv-synthetic" }
  }
  mock_resource "aws_service_discovery_private_dns_namespace" {
    defaults = { arn = "arn:aws:servicediscovery:us-east-2:111122223333:namespace/ns-synthetic" }
  }
}

override_resource {
  target = module.m.aws_ecr_repository.service["query-api"]
  values = { repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/scholarchain-course/query-api" }
}
override_resource {
  target = module.m.aws_ecr_repository.service["graph-service"]
  values = { repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/scholarchain-course/graph-service" }
}
override_resource {
  target = module.m.aws_ecr_repository.service["semantic-service"]
  values = { repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/scholarchain-course/semantic-service" }
}
override_resource {
  target = module.m.aws_ecr_repository.service["embedding-worker"]
  values = { repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/scholarchain-course/embedding-worker" }
}

run "snapshot" {
  command = apply
}
