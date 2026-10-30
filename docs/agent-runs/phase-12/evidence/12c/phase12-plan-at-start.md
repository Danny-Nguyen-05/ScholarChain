# ScholarChain Phase 12 — AWS infrastructure in Terraform: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** start now in a **second session**, in parallel with Phase 7. Phase 6 finished early (Oct 22), so target Oct 23 – Nov 2, 2026, including the optional EMR spike in 12D.

## Shared AWS budget and deployment window

Budget/window decisions agreed with the user on 2026-10-29; review corrections incorporated on 2026-10-30. This is the common planning reference for Phase 8C, the optional Phase 9C live smoke, and Phases 12–17. It supersedes the earlier provisional 7–10-day lifetime. Dates and estimates are planning inputs, not cloud execution approval or human-owned gate records.

- **One project budget: USD 200 total before credits.** Infrastructure, any approved early billing bootstrap costs, the separately approved 12D spike, Phase 8C/14 live checks, optional Phase 9C live LLM smoke, Phase 15 experiments, Phase 16 model/evaluation calls, Cost Explorer API requests and retained storage/evidence draw from this same ceiling. Per-run caps are suballocations, never extra budgets. Count usage across calendar months; a monthly AWS Budget reset does not reset the project ceiling. Estimate applicable taxes and retention costs; report credits separately and do not assume the advertised credit balance is available.
- **Costing scenarios and deployment timing:** Phase 12C must cost November 15–24, 2026 as the base case and November 11–24 as the upper-duration case, using explicit start/end timestamps. November 15 is the preferred start if Phase 12/13 acceptance and deployment prerequisites are ready; November 11 is an earlier comparison, not permission to bypass those gates. The wider November 11–25 envelope is only an outer planning limit; target cleanup by November 24 before the release freeze. Neither scenario authorizes deployment or requires continuous hosting until submission.
- **Cost fit remains unverified.** Estimate the default 12C plan shape separately from later activation costs, and price both windows against the USD 200 project ceiling. Use the accepted Neptune Serverless 1–2.5 NCU configuration; a provisioned-instance comparison is an alternative requiring a separate user choice, not a silent sizing change. Include NAT processing/public IPv4, any justified per-AZ interface endpoints, storage, model calls and retention. Application HTTPS egress uses the existing NAT design by default; extra interface endpoints need a concrete security/function requirement and cost justification. Data-tier isolation remains required. EMR runs only inside approved bounded windows. Return an over-budget estimate to the user; never silently raise the ceiling or assume credits fix it.
- **Private notification input:** use the user's AWS signup Gmail, checked daily, but keep its exact address out of the graded repository. The user supplies `TF_VAR_budget_notification_emails` or an ignored local tfvars file; never put the address in committed `course.tfvars`, command transcripts, reports or approval templates. Confirm the recipient privately and report only that it is configured. Terraform can retain the value in state and saved plans, so keep state, plan binaries/JSON and unredacted outputs outside Git and evidence. Notifications may be delayed and do not impose a hard spending stop.
- **Preferred cleanup target: November 24, before the final release freeze**, after required experiments, evaluation, demo recording, final smoke check and evidence archival. Capture before/after inventories and explain retained resources. November 25 at 11 PM CST is the submission deadline and the outer planning limit, not a requirement to keep the application live until then. Confirm exact cleanup timing with the user in Phase 14/17; never automatically destroy on a date.
- **Archive evidence without blocking unrelated cleanup:** before cleanup, make verified copies with SHA-256 manifests: small curated grading artifacts in the private repository, larger outputs/video/metrics in the user's Drive or another instructor-approved archive. Never commit secrets, notification addresses, Terraform state/plans, full datasets or unsuitable large raw outputs. Copies in Git/Drive do not constitute instructor approval of the archival location. Until that approval exists, retain any S3 originals required for grading and their necessary KMS keys/access dependencies, with an inventory and retention-cost allowance. Approved compute/network cleanup can proceed independently of those retained resources; never delete the originals merely to meet the November 24 target.
- **Later live demonstrations or extensions require a new user decision.** If the instructor/TA requests access after the planned cleanup or deadline, obtain a revised runtime/cost decision and the relevant live approval before extending or recreating the stack. The total budget does not increase automatically.
- **Separate execution gates remain mandatory.** Phase 12C still needs explicit read-only planning authorization and confirmed account/profile/region/AZ inputs. Establish and verify the pre-spend monitoring gate below before any paid run, even one scheduled before Phase 14. The billing bootstrap, Phase 12D, Phase 14 deployment, Phase 8C ingest/smoke, optional Phase 9C live smoke, Phase 15 experiments, Phase 16 live evaluation and destructive cleanup each retain explicit human-written approval requirements. Do not write or rewrite those human records.
- **Account setup status:** the user has created the AWS account, enabled root MFA, created the read-only `scholarchain-planner` IAM user and reported successful browser-based CLI login. Planner MFA was deferred by the user. This status is not an API verification, a grant of deployment permissions, or authorization to inspect credential files. Reconfirm usable access at the relevant phase gate instead of asking the user to create another account.
- **Pre-spend monitoring gate:** before any paid spike, live model smoke or deployment, verify an active account-wide USD 200 cost budget with actual-spend email alerts at 50%, 80% and 100% (USD 100/160/200). Do not depend on project-tag filters being active; configure the tracked costs consistently with the before-credit ceiling and cover the full project interval. Under the Terraform-only rule, author a tiny separate billing-bootstrap Terraform root and obtain its own reviewed plan and human approval for apply; it is outside 12C's read-only execution scope. Reconcile ownership with the main foundation budget explicitly so the later deployment does not unknowingly create a duplicate or attempt to manage the same budget from two states. A console-created budget is only an option after an explicit documented human exception, not an agent shortcut. Monitoring and standard notifications are free; paid Budgets Reports/actions are separate features. These plan edits create no budget or exception.
- **Enable Cost Explorer before paid work:** the human performs the account-level console activation and records the result; AWS does not offer API activation. Initial current-month data usually takes about 24 hours. Its delayed data is not a precondition for authoring an offline configuration or completing an otherwise authorized read-only 12C plan, but missing/lagged costs must not be treated as zero. Do not enable optional paid hourly/resource-level data collection without a separate need and approval.
- **Cost reports are delayed estimates, not enforcement:** record the queried period, retrieval time and latest available usage period. Data is generally refreshed daily and some charges can arrive later; do not promise a strict maximum 24-hour lag. Compute a conservative remaining allowance from reported charges plus nonoverlapping estimates of unreported usage and reserved baseline/retention costs. Enforce each run with maximum runtime/auto-termination, instance/task capacity, concurrency, request/token/vector counts and bounded retries using reviewed prices and headroom. Reconcile actual charges afterward. If headroom cannot be established, stop before the paid run.
- **Cost Explorer API access and fees:** check `ce:GetCostAndUsage` on the selected non-root identity before API reporting; add permissions only if required through the approved owner/gate. Each primary-billing-view API request costs USD 0.01, including paginated requests. Budget and authorize the bounded query count, cache results and avoid per-request or tight-loop polling. Prefer human console snapshots when that is sufficient. Read-only does not mean cost-free; 12C planning authorization does not silently authorize paid Cost Explorer polling.
- **Account plan and service pre-flight:** the signup guidance selected Paid, but the actual plan status has not been independently verified. Confirm the Billing plan type before real 12C planning, along with documented regional support and available read-only checks for Neptune, S3 Vectors, EMR and the configured Bedrock models. Paid plan access does not prove service quotas, IAM/model permissions or a compatible EMR runtime. Free accounts have restricted services and close at the earlier of six months or exhausted credits unless upgraded; a normal Paid upgrade carries remaining eligible credits, while AWS Organizations has separate credit consequences. Do not create a cluster or invoke a model merely to prove usability during a read-only pre-flight. Record unverified live gates honestly.

References checked for this planning correction: [AWS Budgets pricing](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/), [Cost Explorer activation](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-enable.html), [Cost Explorer API pricing](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/pricing/), [API permissions, caching and pagination](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-api-best-practices.html), [AWS account plans](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html), and the course [cleanup requirements](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#cleanup-requirements). Public documentation checks are not account or live-service verification.


> **⛔ WORK ONE SUBPHASE AT A TIME, THEN STOP.** Do exactly one subphase per prompt. When it is done or blocked, return the reviewer prompt and **end your turn**. Do not start, prepare or "get ahead on" the next subphase, even if you have time or the next step looks obvious. The user reviews every subphase before the next begins. Doing several subphases in one run is a failure of this work order, even when the code is correct.

## 1. Your assignment

Implement Phase 12, **AWS infrastructure in Terraform**, in `/Users/danny/Documents/UIC/CS441/ScholarChain`.

You are the coordinator. Launch specialist subagents with your tool's native delegation, give each a bounded work order, route dependencies and repairs, collect observed evidence, and produce the review handoff prompt for the user. Do not write specialist production code yourself. Subagents must not launch more subagents.

Four rules apply to every subphase:

1. **Ask before implementing.** At the start of every subphase you may ask the user any question, and the user wants you to. Ask everything at once, give a recommended default for each question, and wait for answers before editing files. If you have no questions, say so explicitly, then proceed.
2. **One subphase at a time, then stop for the user's review.** Implement only the subphase named in the prompt you were given. When it is done or blocked, stop and end your turn. Do not begin the next subphase in the same run and do not draft its code ahead of time. The next subphase starts only when the user pastes a new prompt, normally the one the reviewer wrote. This also applies to repair rounds: fix only the listed findings, then stop.
3. **Do not trigger a code reviewer.** Never launch, invoke or auto-select the `code-reviewer` agent or any other reviewer. The user handles review outside your session.
4. **End every subphase with a copyable reviewer prompt.** Your final message for a subphase must contain the complete reviewer prompt in one fenced code block (Section 10). The user pastes it into a separate reviewer agent. That reviewer reviews read-only, then writes the next prompt for you: either the next subphase or a repair round. Then stop and wait.

This document is an implementation work order. It is not proof of human acceptance, instructor approval, a completed run, or permission to spend money on AWS.

## 2. Project context and verified starting point

- **Nothing is applied in this phase.** `infra-engineer` authors Terraform under `infra/terraform/**` and produces a reviewed, non-destructive **plan**. Applying it is Phase 14 and requires the human gate. The agent never runs `terraform apply`, `destroy`, `import`, or any AWS write command.
- **Today** `infra/terraform/` is empty and `scripts/` holds only `phase4-emr-smoke.sh` and a README. Operational scripts (`plan.sh`, `deploy.sh`, and so on) are Phase 13; here only the Terraform is authored and plans are produced with direct `terraform` commands recorded in evidence.
- **The Terraform-only rule.** Every cloud resource the project needs must be declared in Terraform, including S3 Vectors, EMR, ECS autoscaling and the observability resources the Phase 15 experiments depend on. An ephemeral resource created by a script is not allowed.
- **AWS access.** `terraform init` downloads providers (network). `terraform plan` calls AWS read APIs and needs credentials. The user supplies a profile name, account ID, region and permission to run the plan in Step 0. Never read or print credential files or environment values; refer to the profile by name only.
- **MCP note.** The `terraform-registry` and `aws-api-readonly` MCP servers failed to connect in the planning session. `aws-knowledge` is available for documentation. If a registry lookup is needed and unavailable, read the provider documentation at the registry website instead and cite the URL and provider version.
- **Dependencies from earlier phases:** table and key designs in `modules/storage/README.md` (Phase 7); index names, dimension and metric (Phase 8); the four service artifacts and ports/scaling needs (Phase 10); the Phase 6 EMR compatibility memo (`docs/agent-runs/phase-06/evidence/6a/`) for the EMR release and Spark/Scala decision.
- **Schedule slot:** Oct 29 – Nov 5, 2026 (about 7 days). Run in a **second session** in parallel with Phase 7: paths do not overlap. Starting early is deliberate; real AWS problems (permissions, quotas, provider gaps) should appear in the first week, not the last.

Environment for every sbt command (copy exactly):

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch check        # about 7+ minutes; the "checkProbeInjectFailure ... injected format-stage failure" line is an expected self-test
```

## 3. Source of authority and required reading

1. `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/agents/infra-engineer.md`, `docs/agent-runs/README.md`.
2. The course Phase 12 section (all thirteen areas, script requirements, gate), "Required technology stack", "Cost controls", "Security requirements", "Observability requirements" and the scaling-rule table in Phase 15: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform
3. `scripts/phase4-emr-smoke.sh` and `scripts/README.md` (the existing EMR conventions and how the Phase 4 smoke expects an existing cluster ID), the EMR memo from Phase 6A, and the Phase 7/8/10 READMEs named above.
4. Current documentation for the AWS provider resources used (cite provider version and page URLs), especially Neptune, S3 Vectors, EMR managed scaling, ECS Application Auto Scaling, VPC endpoints.

## 4. Decisions and open questions that apply to the whole phase

- **Open questions for the phase (ask in Step 0 of 12A; the user answers once and the answers apply to 12B–12C):**
  - **12-1. Account, profile, region, environment name.** No default; the user supplies them. Region must support Neptune, S3 Vectors, Bedrock (chosen model) and EMR.
  - **12-2. Budget and lifetime.** USD 200 total before credits is selected. Cost November 15–24 as the base case and November 11–24 as the upper-duration case; target separately approved November 24 cleanup with retained evidence as described above. Exact live timestamps and per-run suballocations remain human-gated. Supply the AWS signup Gmail notification input privately; no exact recipient goes into committed tfvars or records. Verify account-wide alerts before any paid work, including 12D and optional 9C.
  - **12-3. Remote state.** Recommended: document the S3 + DynamoDB lock design and a tiny bootstrap module, but use **local state** for the course environment, kept out of git and out of evidence (state can hold sensitive values). Confirm.
  - **12-4. Egress.** Recommended: one NAT gateway (cost-aware, destroyed in cleanup) plus gateway endpoints for S3 and DynamoDB, and interface endpoints only where a service needs private access. Required if the LLM provider is outside AWS.
  - **12-5. Step Functions and EventBridge.** The course lists them as "when used". Recommended: omit for lean scope; the scripts submit EMR steps directly; document the omission and the reason. Confirm.
  - **12-6. Neptune sizing.** The agent reports current Neptune options and hourly cost from documentation; recommended: the smallest serverless or instance option that supports the bulk loader and openCypher.
  - **12-7. EMR shape.** From the 6A memo: the release label, Spark/Scala decision, instance types, minimum and maximum capacity (recommended: 1 primary + 1 core + task capacity up to a stated maximum, managed scaling, no Spot unless failure handling is shown).
  - **12-8. Security scanner.** Which scanner is installed (for example `trivy config` or `checkov`)? If none, recommended: a documented manual IAM/encryption checklist plus `terraform validate`, and a disclosure.
  - **12-9. S3 Vectors in Terraform.** Confirm the AWS provider version that has native S3 Vectors resources. If none does, present options (a CloudFormation stack wrapped by Terraform, or a documented exception) and **do not choose**; ask the user.
  - **12-10. EMR Spark runtime: the largest schedule risk, decided here and early.** Phase 6 recorded that stock EMR 7.x Spark 3.5.x is built for Scala 2.12 while this repository is Scala 3 using `spark-sql_2.13`. No compatible runtime has been selected or tested. Recommended: run the timeboxed feasibility spike in 12D (at most two working days) before authoring the final EMR module, and write the EMR module for the option that passes. The 6A memo (`docs/agent-runs/phase-06/evidence/6a/emr-compatibility.md`) lists the candidates: EMR on EC2 with a bootstrap-installed Spark 3.5.4 / Scala 2.13 distribution, EMR Serverless custom image, EMR on EKS custom image. Hadoop MapReduce on EMR on EC2 already works (Phase 4 smoke), so only the Spark side is at risk.
- **Tags on every resource:** course, project, environment, owner and expiration date, plus cost-allocation tags where the account allows.

## 5. Delegation and ownership

Follow `docs/agents.md`. One writer per artifact class. Record each launched agent's native ID, role, model, assigned paths and handoffs. You alone assemble `docs/agent-runs/phase-12/**` from agent reports.

| Agent | Owns | Subphases |
|---|---|---|
| `infra-engineer` | `infra/terraform/**` (modules, environment variable files without secrets, README) and nothing else in this phase | 12A–12C |
| `build-engineer` | `.gitignore` entries for Terraform local state, plan files and `.terraform/` | 12A, on demand |
| `test-engineer` | `tests/**`: optional independent static checks over the Terraform text (no wildcard IAM, no public bucket, no secrets) | 12C |
| `deploy-engineer` | Not used. Apply is Phase 14 | — |

## 6. Global rules for every subphase

1. **Ask first.** Step 0 of every subphase: list your questions, including the subphase's "Open questions" that are still open, each with a recommended default. Wait for the user's answers. If none, write "No questions for this subphase" and proceed.
2. **Preflight.** Record `git status --short`, the branch and HEAD as this subphase's **base SHA**. If the previous subphase's changes are still uncommitted, ask the user whether to proceed or wait for their commit. Never reset or discard changes you did not make.
3. **JDK 17 for every sbt command** (Section 2). Report `java -version` in the first gate of each subphase.
4. **One writer per artifact.** Route every edit to the owner in Section 5 and `docs/agents.md`. An unlisted path is an orphan: stop and ask the user. Out-of-scope work is returned as `BLOCKED-ON <owner>` with evidence.
5. **Secrets.** Never read or print `.env`, private keys, tokens, generated credentials or secret directories. Secrets live in AWS Secrets Manager or approved local placeholders, never in tracked files, logs, prompts, Terraform source or plans.
6. **Cloud and money gates.** All AWS infrastructure is authored in Terraform. Live apply, deployment, costly scale changes, data destruction, security changes and rollback require the human gate recorded in the phase evidence. Do not run any command that creates, changes or deletes a cloud resource, or that calls a paid model provider, unless this subphase's text and the user's recorded approval allow it. Unit and contract tests use fakes.
7. **Configuration, not constants.** No hardcoded bucket names, endpoints, account IDs, regions, thresholds or model IDs without a configuration entry and a short rationale (the course deducts for this).
8. **Observability.** Structured logs with trace/run IDs; no secrets or full sensitive payloads in logs.
9. **Every behavior change has tests**, written from the stated requirement, not by re-running the implementation's own logic. Module owners add tests under their module's `src/test/**`; `test-engineer` adds independent tests under `tests/**`.
10. **Provenance.** Data transformations and runtime claims keep source and run provenance. An LLM may never invent a researcher identity, path, score or evidence.
11. **Evidence stays lean.** Put exact commands, exit codes, test counts and meaningful log excerpts under `docs/agent-runs/phase-12/evidence/<subphase>/`; summarize in `owner-report.md` and `test-report.md`. Do not commit full datasets, run outputs or large inventories. Human decisions (`human-gate.md`, `commit.txt`, any approval record) are written only by the user; never write or rewrite them.
12. **Reports** use exactly these fields: `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. Never report an unobserved pass; list unrun commands as unverified.
13. **No commits or pushes by agents.** The user commits, normally once per approved subphase on a `phase-12` branch.
14. **Lean scope (about 30 days remain before the 2026-11-25 deadline).** Implement what the baseline and rubric require. Do not add optional components (OpenSearch, CI workflows, extra indexes or services) unless the user asks. Record each omission in the owner report so the final report can disclose it.
15. **Stop at the boundary.** When the subphase is done or blocked: ensure no subagents, builds or jobs are still running; return the handoff packet and the reviewer prompt (Section 10); end the turn with **"Subphase 12X is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."**

## 7. Design (binding unless a subphase question changes it)

### 7.1 Layout

```text
infra/terraform/
  README.md                      how to init/validate/plan, variables, cleanup mode, remote-state design
  modules/
    foundation/   provider pins, required tags, budget
    network/      VPC, 2 AZs, public/private subnets, routes, NAT, VPC endpoints, security groups by role
    identity/     roles and policies per component, KMS keys, Secrets Manager references (ARNs only)
    datalake/     S3 buckets or prefixes: raw, curated, graph, rag, artifacts, logs, reports
    dynamodb/     the six tables, GSIs, PITR where appropriate
    neptune/      cluster, subnet and parameter groups, loader role, read-only runtime role
    s3vectors/    vector bucket and the five indexes
    emr/          cluster, managed scaling, logging, bootstrap, bounded capacity
    runtime/      ECR (immutable tags, scan on push), ECS cluster, Fargate services, service discovery, ALB for query-api
    messaging/    SQS queue + DLQ for embedding work
    observability/ log groups, dashboards, alarms, metrics for the experiments
  environments/
    course.tfvars                no secrets
```

### 7.2 Requirements per area (from the course, with the lean decisions applied)

1. **Foundation:** pinned provider versions; required tags; remote-state design documented (question 12-3); budget resource where the account permits.
2. **Network:** VPC in two AZs; public subnets only for approved ingress (the ALB and NAT); private application and data subnets; security groups **chained by service role** (ALB → query-api → graph-service/semantic-service → Neptune/endpoints), never broad CIDR ingress to data stores.
3. **Identity and encryption:** least-privilege roles for EMR, each ECS service and task, embedding worker, the Neptune loader and the runtime reader; separate runtime and deployment permissions; encryption with KMS or approved AWS-managed keys; secrets referenced by ARN only. The graph reader role has **no write action**.
4. **Data lake:** versioning where needed, encryption, public-access block, lifecycle rules for intermediates, deletion safeguards on persistent buckets, an explicit course-environment cleanup mode.
5. **EMR:** Hadoop and Spark applications, managed scaling with bounded minimum and maximum, log URI, bootstrap actions from the 6A memo, bounded default capacity, auto-termination or an explicit variable that disables the cluster outside experiments.
6. **DynamoDB:** exactly the Phase 7 tables and keys; on-demand unless justified; PITR where appropriate.
7. **Neptune:** per question 12-6; encryption; backups; deletion protection for non-ephemeral environments with an explicit cleanup-mode override; loader role and read-only runtime role.
8. **S3 Vectors:** vector bucket plus the five indexes with the dimension and metric from Phase 8; encryption, tags, access policies.
9. **Runtime compute:** ECR with immutable Git-SHA tags and scan on push; ECS cluster and Fargate task definitions for `query-api`, `graph-service`, `semantic-service`, `embedding-worker`; internal service discovery; ALB only for external ingress; HTTPS where the account provides a certificate, otherwise documented as a limitation.
10. **Messaging:** SQS queue and DLQ with redrive policy for embedding work.
11. **Observability:** log groups with retention; a dashboard that makes an elasticity run readable without raw logs; alarms; the metrics the Phase 15 experiments need (EMR capacity, ECS desired/running tasks, SQS depth and oldest-message age, Neptune and DynamoDB metrics, API latency, LLM usage via application metrics).
12. **Autoscaling (required for Phase 15):**

| Component | Policy |
|---|---|
| EMR | Managed scaling with bounded min and max |
| Embedding workers | ECS step or target tracking on SQS backlog per task, bounded maximum |
| Graph retriever | Target tracking on CPU or request count, bounded maximum, latency alarm |
| Vector retriever | Target tracking on CPU or request count, bounded maximum |
| Query API | Request- or CPU-based scaling with a bounded maximum |
| DynamoDB | On-demand |

13. **Cost and safety:** bounded defaults everywhere; environment-specific variable files with no secrets; deletion protection on stateful resources in persistent environments; an explicit cleanup mode.

### 7.3 Plan summary the user must receive (12C)

Add/change/destroy counts; resources by module; estimated high-cost resources with hourly and total-for-duration estimates against the user's budget; any stateful replacement; every IAM role and policy change; required human actions before apply; tool versions used. **No unexplained destroy or replacement of stateful resources.**

### 7.4 Plan hygiene

The plan file and its outputs must not contain secret values. Plan files stay out of git; commit only the summary, counts and the plan **checksum** in the evidence. Do not paste raw plan JSON containing account-sensitive values into evidence beyond what the user approves.

## 8. Subphases

Execute the subphases in order: 12A → 12B → 12C → 12D (12D is the optional but strongly recommended EMR spike; the user may run it right after 12A instead). Each subphase starts only from a prompt produced by the reviewer of the previous one, or from the user. **One subphase per run:** after a subphase's handoff you stop, and the user reviews it before anything else happens. Never chain subphases together. Every subphase has the same frame:

> **Step 0 — Questions.** You may ask the user any question before implementing. Ask the open questions below that are still open, plus any of your own, each with a recommended default. Wait for answers.
> **Step N — Handoff and stop.** Do not trigger any code reviewer. Return the handoff packet and the copyable reviewer prompt (Section 10), then end your turn. Do not start the next subphase.

### Subphase 12A — Foundation, network, identity, data lake, DynamoDB, messaging, ECR

**Owners:** `infra-engineer`, `build-engineer` (`.gitignore` only).

**Open questions:** 12-1 through 12-9 (ask them all now).

**Tasks:**

1. Scaffold `infra/terraform/` per Section 7.1 with the README, provider pins and required tags.
2. Author the foundation, network, identity (roles, KMS, secret references), data lake, DynamoDB, messaging and ECR modules.
3. Ignore local state, `.terraform/` and plan files in `.gitignore` (through `build-engineer`).
4. Run `terraform fmt -check` and `terraform validate` (with `init -backend=false` if no profile has been approved yet).
5. Record exact provider versions, commands and exit codes under `evidence/12a/`.

**Done when:** these modules format and validate; IAM policies are scoped to concrete resources and actions (no `*` actions or resources without a written justification); no secret value exists in any file.

> **⛔ STOP after 12A.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 12B until the user sends a new prompt.

### Subphase 12B — Neptune, S3 Vectors, EMR, runtime compute, autoscaling, observability

**Owners:** `infra-engineer`.

**Tasks:**

1. Author the Neptune, S3 Vectors (per 12-9), EMR (per the 6A memo and 12-7), runtime compute (ECR already in 12A; ECS, Fargate task definitions, service discovery, ALB) and observability modules.
2. Author every autoscaling policy in Section 7.2 item 12, and the dashboard and alarms.
3. Wire environment variables or secret references into task definitions by ARN and name only.
4. `terraform fmt -check` and `terraform validate` for the whole tree.

**Done when:** the whole tree validates; every module the course lists is present or its omission is justified and recorded (Step Functions, OpenSearch); no public data store; default capacity is bounded.

> **⛔ STOP after 12B.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 12C until the user sends a new prompt.

### Subphase 12C — Security review prep, non-destructive plan and summary

**Owners:** `infra-engineer`; `test-engineer` (optional static checks).

**Tasks:**

1. With the user's approved profile, run `terraform plan` (never `apply`) for the course environment; save the plan outside git; record its SHA-256 checksum.
2. Produce the plan summary in Section 7.3, including both dated cost scenarios, the authored Neptune Serverless capacity range, baseline plus per-run/retention allowances, cost-data lag and any missing monitoring/account-plan gates; add the course security self-review (least privilege, encryption, no public access, separate runtime/deployment roles, bounded capacity, no secrets).
3. Run the selected scanner (question 12-8) or the documented manual checklist; retain output.
4. `test-engineer` (optional): static assertions over the Terraform text (no wildcard IAM actions, no public bucket ACLs, no secret-looking strings).
5. Return **BLOCKED-ON user** for any unexplained destroy or stateful replacement instead of working around it.
6. Do not apply. State the human actions required before Phase 14.

**Done when:** the plan exists with a recorded checksum; the summary is complete; scanner output (or the disclosed manual checklist) is retained; the reviewer can compare the plan summary against the code.

> **⛔ STOP after 12C.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 12D until the user sends a new prompt.

### Subphase 12D — Timeboxed EMR Spark feasibility spike (needs the user's approval record)

**Start condition:** the user wrote an approval record with a small dollar cap, region, instance types, maximum runtime (hours, not days) and teardown. The pre-spend monitoring gate must be verified first. The cap must be a suballocation of the conservative estimated remaining USD 200 shared project budget, including any spike before the main deployment window; enforce it through approved runtime/capacity limits and report delayed cost-to-date plus unreported-usage estimates for later phases. Without the record, do nothing live. The spike uses a **separate** Terraform root (for example `infra/terraform/spikes/emr-spark/`) so it never touches the main environment, and it is destroyed right after the test. Every resource is Terraform-authored; nothing is created by hand or by a script.

**Owners:** `infra-engineer` (Terraform for the spike), `deploy-engineer` (applies, runs the test, destroys, after approval), coordinator (evidence).

**Goal:** answer one question with evidence: can the existing Spark job (the Phase 6 CLI on the G1 fixture) run on a real Spark cluster on AWS with Scala 2.13 libraries on both driver and executors?

**Tasks:**

1. Test candidates in this order and stop at the first that works: (a) EMR on EC2 with a bootstrap-installed Spark 3.5.4 / Scala 2.13 distribution; (b) EMR Serverless with a custom image. Use the 6A memo's guidance on class-origin checks.
2. Submit the Phase 6 Spark job on the G1 fixture and verify: it completes; driver and executor class-origin evidence shows the Scala 2.13 library versions the job expects (not 2.12); DataFrame and Parquet read/write work; output tables equal the local run's rows.
3. Record cost and elapsed time. Destroy everything and capture the after-inventory.
4. If no candidate works within the timebox, **do not improvise**: return the options with consequences and let the user decide, for example (i) a standalone Spark 3.5.4 / Scala 2.13 cluster on EC2 (still distributed), (ii) Spark in local mode on one machine for the demonstration with a clear disclosure of reduced "distributed execution" evidence, (iii) a build change to Scala 2.13 (large). Each option carries a grading and schedule risk the user must weigh.

**Done when:** one runtime is proven (with evidence) or the failure and the options are reported; all spike resources are destroyed and inventoried; the 12-10 decision is recorded so the EMR module in 12B/12C and the Phase 13 and 15 Spark steps use it.

> **⛔ STOP after 12D.** Return the handoff packet and reviewer prompt, then end your turn. The phase closes only after the user's own review and `human-gate.md`.

## 9. Required test matrix

| Area | Minimum meaningful checks |
|---|---|
| Static | `terraform fmt -check`, `terraform validate` pass on the full tree; provider versions pinned |
| Plan | A non-destructive plan completes; add/change/destroy counts reported; no unexplained destroy or replacement of stateful resources; checksum recorded |
| IAM | No wildcard actions or resources without justification; runtime reader has no write action; deployment and runtime roles are separate; secrets referenced by ARN |
| Data stores | No public bucket or database; encryption on; Neptune and DynamoDB protections for persistent environments; cleanup mode explicit |
| Capacity | Defaults bounded (EMR, ECS maximums, SQS worker maximum); estimated cost within the user's budget |
| Scaling | Every policy in Section 7.2 item 12 exists with a bounded maximum |
| Secrets | A search of source, variable files and plan summary finds no secret values |
| Scanner | Selected scanner output retained, or manual checklist and disclosure |

Tests assert required behavior from hand-derived expectations, not by re-running the implementation's own logic.

## 10. Handoff protocol and reviewer prompt

At the end of **every subphase and every repair round**, return a handoff packet to the user containing:

- Status (complete or blocked).
- Base SHA, branch and HEAD.
- Changed and untracked files.
- Exact commands with exit codes and test counts.
- Evidence paths.
- Answers the user gave in Step 0.
- Limitations and manual actions.
- **The complete reviewer prompt in one fenced code block**, with every placeholder filled with real values.

Then stop. **Never launch a reviewer.** The user pastes the prompt into a separate reviewer agent. That reviewer returns its verdict **and** the next prompt for you.

When you receive a prompt that came from the reviewer, first append the reviewer's verdict verbatim to `docs/agent-runs/phase-12/review.md` under the subphase heading, marked "user-supplied external review". On REQUEST-CHANGES, log the routed findings in `repairs.md`. Then do what the prompt asks.

**Template you must complete and give to the user:**

````text
You are the independent, read-only code reviewer for ScholarChain Phase 12,
Subphase [12X] [repair round N, if any], in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md — Sections 3–7 and
   Subphase [12X] in Section 8 (scope, owners, open questions, tasks,
   "Done when").
3. The course Phase 12 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform
4. docs/agent-runs/phase-12/prompt.md, owner-report.md and test-report.md
   (Subphase [12X] sections), and evidence under
   docs/agent-runs/phase-12/evidence/[12x]/.

Checkpoint facts (filled in by the manager):
- Branch: [branch]   Subphase base SHA: [sha]   Current HEAD: [sha]
- Changed tracked files: [list]   Untracked files: [list]
- User answers to Step 0 questions: [answers]
- Commands run, exit codes, test counts: [exact results]
- Evidence paths: [paths]
- Known limitations / items deferred to later subphases: [list]
- Prior findings and repair evidence (repair rounds only): [list]

Review rules:
- Read-only. Do not edit files, run builds or tests, call AWS or any
  provider, change data, commit or push. Do not read secrets.
- Inspect `git diff [base]` plus untracked files. Report ALL confirmed
  findings in one pass.
- Check, as applicable to Subphase [12X]: ownership (one writer per path,
  per docs/agents.md and the plan's Section 5); no hardcoded
  buckets/endpoints/account IDs/models; no secrets in files, logs or
  evidence; honest evidence (claimed results match retained logs);
  required tests exist and assert hand-derived expectations;
  cloud/spend gates respected; lean-scope omissions recorded.
- Also check for Phase 12: nothing applied or destroyed; no secrets in `.tf`, tfvars, plan summary or evidence; wildcard IAM; public access; a runtime role that can write the graph; unbounded capacity; stateful resources without protection in persistent environments; autoscaling maxima; that omitted modules (Step Functions, OpenSearch) are disclosed; that the plan summary matches the code.
- Do not demand work the plan assigns to a later subphase; list it as
  future scope. Distinguish blockers, nonblocking observations and
  unverified gates.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase [12X].
2. Findings: severity, path:line, evidence/reasoning, impact, owning agent,
   acceptance check, blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A NEXT PROMPT for the main agent, in one fenced code block, that I can
   paste directly:
   - If APPROVE: tell the main agent to (a) append this verdict verbatim to
     docs/agent-runs/phase-12/review.md under "Subphase [12X]",
     (b) confirm the user has committed Subphase [12X] (if not, ask the user),
     (c) start Subphase [next] of /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md
     (or, after the last subphase, tell the user Phase 12 is ready for their
     human-gate and that Phase 13 is next), beginning with Step 0 questions,
     (d) end with a new reviewer prompt per Section 10 without triggering
     any reviewer, and (e) do ONLY that one subphase, then stop and end the
     turn; do not start the subphase after it.
   - If REQUEST-CHANGES: tell the main agent to (a) append this verdict
     verbatim to review.md and the findings to repairs.md, (b) route each
     blocking finding to its owning agent (listed), (c) rerun the affected
     tests and the full sbt check on JDK 17, (d) not start the next
     subphase, (e) return a recheck reviewer prompt per Section 10 without
     triggering any reviewer, and (f) stop and end the turn after the
     repair. Nonblocking findings are listed but not required.
````

## 11. Final checklist (Phase 12 complete)

- [ ] Each subphase was reviewed by a user-launched reviewer; verdicts are retained in `review.md`.
- [ ] The full Terraform tree formats and validates; provider versions are pinned.
- [ ] The plan contains no unexplained destroy or replacement of stateful resources.
- [ ] IAM policies are scoped to actual resources and actions; runtime and deployment permissions are separate.
- [ ] Buckets and databases are not public; encryption is on.
- [ ] Default capacity is bounded; the cost estimate against the user's budget is stated.
- [ ] Secrets do not appear in source, plan summary or evidence.
- [ ] Autoscaling policies required by Phase 15 are present.
- [ ] The plan checksum is recorded and **nothing in the main environment was applied**. The only live action in this phase is the approved, destroyed-afterward 12D spike.
- [ ] The EMR Spark runtime decision (12-10) is recorded with evidence or with the options the user chose between.
- [ ] The human reviewed the plan summary; the reviewer returned APPROVE; the human wrote `human-gate.md` and `commit.txt`.
