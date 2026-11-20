# Phase 15 P9 (docs/runbooks/session-2-plan.md rows F5 and P9), MODULE level: modules/observability's elasticity dashboard holds only
# free native AWS metrics and at most 50 metrics (CloudWatch free tier: 3 dashboards of up to 50 metrics each) in EVERY combination of its
# three optional sources: the ALB (alb_metric_dimensions), Neptune (neptune_identifier) and EMR (emr_cluster_id). Root-level counts are in
# phase15_elasticity.tftest.hcl and phase15_p41.tftest.hcl.
# Hand count from modules/observability/main.tf (six tables, as the root's modules/dynamodb):
#  - base 23 = 6 AWS/ECS utilization (query-api, graph-service, semantic-service x CPUUtilization, MemoryUtilization) + 2 SQS depth
#    (queue, DLQ) + 1 SQS oldest age + 2 Step Functions (failed, timed out) + 12 DynamoDB throttle (6 tables x read, write);
#  - ALB +9 = 1 HealthyHostCount + 3 (RequestCount, HTTPCode_Target_5XX_Count, HTTPCode_ELB_5XX_Count) + 3 TargetResponseTime
#    (p50, p95, p99) + 2 P41 panel (RequestCountPerTarget, HTTPCode_Target_4XX_Count);
#  - Neptune +5 = 3 capacity/utilization (CPUUtilization, ServerlessDatabaseCapacity, NCUUtilization) + 2 errors per second;
#  - EMR +6 = node counts (CoreNodesRunning, TaskNodesRunning, CoreNodesPending, TaskNodesPending, TotalNodesRequested, TotalNodesRunning).
# So: base 23, ALB 32, Neptune 28, EMR 29, ALB+Neptune 37, ALB+EMR 38, Neptune+EMR 34, all three 43 (before P9: 109, 111, 114, 115, 116,
# 117, 120, 122). All identifiers are synthetic. No AWS client runs. Plan-only: never remove the mock_provider or run apply.
mock_provider "aws" {
  override_during = plan
}

variables {
  name_prefix           = "scholarchain-course"
  aws_region            = "us-east-2"
  retention_days        = 7
  notification_arns     = []
  application_namespace = "ScholarChain/Application"
  api_error_percent     = 5
  latency_seconds       = 5
  queue_age_seconds     = 300
  queue_name            = "scholarchain-course-embedding"
  table_names           = { RunLedger = "t1", EntityLinkCache = "t2", QuerySession = "t3", EvidenceBundle = "t4", ArtifactRegistry = "t5", ResearcherMetricCache = "t6" }
  neptune_identifier    = null
  emr_cluster_id        = null
  alb_metric_dimensions = null
  tags                  = {}
  workflow_arn          = "arn:aws:states:us-east-2:111122223333:stateMachine:scholarchain-course-embedding-dispatch"
}

run "base_has_23_metrics" {
  command = plan
  module {
    source = "./modules/observability"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 23
    error_message = "Base (no ALB, Neptune or EMR): 23 metrics."
  }
  assert {
    condition     = alltrue([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : try(length(w.properties.metrics) > 0, true)]) && !strcontains(aws_cloudwatch_dashboard.elasticity[0].dashboard_body, "AWS/ApplicationELB")
    error_message = "No ALB: no ALB panel and no empty metric widget."
  }
  assert {
    condition     = toset([for m in one([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : w.properties.metrics if try(w.properties.title, "") == "ECS CPU and memory utilization (%), HTTP services"]) : "${m[0]} ${m[1]} ${m[2]}=${m[3]} ${m[4]}=${m[5]}"]) == toset(flatten([for s in ["query-api", "graph-service", "semantic-service"] : [for n in ["CPUUtilization", "MemoryUtilization"] : "AWS/ECS ${n} ClusterName=scholarchain-course ServiceName=${s}"]]))
    error_message = "AWS/ECS CPUUtilization and MemoryUtilization for the three HTTP services (ClusterName + ServiceName), nothing else in that panel."
  }
  assert {
    condition     = alltrue(flatten([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : [for m in try(w.properties.metrics, []) : startswith(m[0], "AWS/")]])) && !strcontains(aws_cloudwatch_dashboard.elasticity[0].dashboard_body, "ECS/ContainerInsights") && !strcontains(aws_cloudwatch_dashboard.elasticity[0].dashboard_body, "ScholarChain/Application")
    error_message = "Free native AWS/* metrics only: no ECS/ContainerInsights series and no custom-namespace series."
  }
  assert {
    condition     = strcontains(aws_cloudwatch_dashboard.elasticity[0].dashboard_body, "publisher required")
    error_message = "The text widget still discloses that custom application metrics need a publisher."
  }
}

run "alb_only_has_32_metrics_and_the_plan_panels" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    alb_metric_dimensions = { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 32
    error_message = "ALB only: 23 + 9 = 32 metrics."
  }
  assert {
    condition = length([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : w if try(w.properties.title, "") == "ALB healthy query-api targets" && w.properties.period == 60 && w.properties.stat == "Minimum" && w.properties.metrics == [
      ["AWS/ApplicationELB", "HealthyHostCount", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321"]
    ]]) == 1
    error_message = "HealthyHostCount by LoadBalancer + TargetGroup, Minimum, period 60."
  }
  assert {
    condition = length([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : w if try(w.properties.title, "") == "ALB requests and 5XX (query-api)" && w.properties.period == 60 && w.properties.stat == "Sum" && w.properties.metrics == [
      ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321"],
      ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321"],
      ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", "app/synthetic/1234567890123456"]
    ]]) == 1
    error_message = "RequestCount and HTTPCode_Target_5XX_Count by LoadBalancer + TargetGroup, HTTPCode_ELB_5XX_Count by LoadBalancer, Sum, period 60."
  }
  assert {
    condition = length([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : w if try(w.properties.title, "") == "ALB target response time p50/p95/p99 (seconds, query-api)" && w.properties.period == 60 && w.properties.metrics == [
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321", { stat = "p50" }],
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321", { stat = "p95" }],
      ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321", { stat = "p99" }]
    ]]) == 1
    error_message = "TargetResponseTime p50, p95 and p99 by LoadBalancer + TargetGroup, period 60."
  }
  assert {
    condition = length([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : w if try(w.properties.title, "") == "ALB requests per target and target 4XX (query-api)" && w.properties.period == 60 && w.properties.stat == "Sum" && w.properties.metrics == [
      ["AWS/ApplicationELB", "RequestCountPerTarget", "TargetGroup", "targetgroup/synthetic/6543210987654321"],
      ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321"]
    ]]) == 1
    error_message = "The P41 panel is unchanged: RequestCountPerTarget (TargetGroup) and HTTPCode_Target_4XX_Count (LoadBalancer + TargetGroup), Sum."
  }
  assert {
    condition     = length([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : w if strcontains(jsonencode(w), "AWS/ApplicationELB")]) == 4
    error_message = "Exactly four ALB panels."
  }
}

run "neptune_only_has_28_metrics" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    neptune_identifier = "scholarchain-course-graph"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 28
    error_message = "Neptune only: 23 + 5 = 28 metrics."
  }
}

run "emr_only_has_29_metrics" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    emr_cluster_id = "j-SYNTHETICP9"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 29
    error_message = "EMR only: 23 + 6 = 29 metrics."
  }
}

run "alb_and_neptune_have_37_metrics" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    alb_metric_dimensions = { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
    neptune_identifier    = "scholarchain-course-graph"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 37
    error_message = "ALB and Neptune (the Session 2 R-b shape): 23 + 9 + 5 = 37 metrics."
  }
}

run "alb_and_emr_have_38_metrics" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    alb_metric_dimensions = { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
    emr_cluster_id        = "j-SYNTHETICP9"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 38
    error_message = "ALB and EMR: 23 + 9 + 6 = 38 metrics."
  }
}

run "neptune_and_emr_have_34_metrics" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    neptune_identifier = "scholarchain-course-graph"
    emr_cluster_id     = "j-SYNTHETICP9"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 34
    error_message = "Neptune and EMR: 23 + 5 + 6 = 34 metrics."
  }
}

run "all_three_sources_have_43_metrics_at_most_50" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    alb_metric_dimensions = { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
    neptune_identifier    = "scholarchain-course-graph"
    emr_cluster_id        = "j-SYNTHETICP9"
  }

  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) == 43
    error_message = "All three optional sources: 23 + 9 + 5 + 6 = 43 metrics, the maximum."
  }
  assert {
    condition     = sum([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : length(try(w.properties.metrics, []))]) <= 50
    error_message = "P9: at most 50 metrics even with every optional source (the CloudWatch free-tier dashboard size)."
  }
  assert {
    condition     = alltrue(flatten([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : [for m in try(w.properties.metrics, []) : startswith(m[0], "AWS/")]])) && alltrue([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : try(length(w.properties.metrics) > 0, true)])
    error_message = "Free native AWS/* metrics only, no empty metric widget."
  }
  assert {
    condition     = length(distinct([for w in jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets : "${w.x},${w.y}"])) == length(jsondecode(aws_cloudwatch_dashboard.elasticity[0].dashboard_body).widgets)
    error_message = "No two widgets share a grid origin."
  }
}

run "dashboard_off_creates_no_dashboard" {
  command = plan
  module {
    source = "./modules/observability"
  }
  variables {
    dashboard_enabled     = false
    alb_metric_dimensions = { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
  }

  assert {
    condition     = length(aws_cloudwatch_dashboard.elasticity) == 0 && length(aws_cloudwatch_metric_alarm.latency) == 2
    error_message = "dashboard_enabled = false: no dashboard; the alarms stay."
  }
}
