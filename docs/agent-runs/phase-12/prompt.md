# Phase 12A work order and user setup answers

User work order: “let start phase 12 A now”
User confirmed: “Use the recommendations; leave account, region, and budget pending.
Tell me to create it when required”

Scope: Phase 12A only, local authoring/init -backend=false/fmt/validate and mocked tests. No AWS API access, cloud mutation, real AWS plan, live test, model call, commit or push.
Accepted setup recommendations: environment course; owner danny; provisional expiration 2026-11-25 to reconfirm before deployment; local ignored state, documented remote-state/bootstrap design; one NAT and S3/DynamoDB gateway endpoints authored only, required interface endpoints only; omit Step Functions/EventBridge/OpenSearch and disclose; Neptune size and regional cost comparison deferred; EMR runtime/instances unresolved pending feasibility with bounded eventual topology and no initial Spot; manual security checklist and Terraform validation because no scanner found; verify/pin native S3 Vectors provider support; 12D approval and live work deferred. Account/profile, region, budget remain unset. Provisional stack duration 7–10 days, no spending authorized.
Account reminder: tell user to create/configure AWS account before 12C real Terraform plan, or before 12D if scheduled earlier. Phase 12A requires no AWS account.

Coordinator delegated Terraform ownership solely to /root/infra_12a; .gitignore and generated sbt test marker solely to /root/build_12a. Native subagents may not delegate; no reviewer launched. Model: inherited parent model, exact model identifier not exposed by spawn result; no override requested. Coordinator alone assembles phase evidence.

## Plan snapshot

Source: /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase12.md
SHA-256: 85f531e198d0fd6e138a5698eec1c4332807fa7e06f6b526089fb549e870d5ef

# ScholarChain Phase 12 — AWS infrastructure in Terraform: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** start now in a **second session**, in parallel with Phase 7. Phase 6 finished early (Oct 22), so target Oct 23 – Nov 2, 2026, including the optional EMR spike in 12D.

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
  - **12-2. Budget.** The user states a total budget ceiling and the duration the stack will stay up. Recommended working assumption for sizing: the stack is up for roughly 7–10 days, EMR runs only inside experiment windows, and everything is destroyed after the demo recording.
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
2. Produce the plan summary in Section 7.3 and a short security self-review against the course security requirements (least privilege, encryption, no public access, separate runtime/deployment roles, bounded capacity, no secrets).
3. Run the selected scanner (question 12-8) or the documented manual checklist; retain output.
4. `test-engineer` (optional): static assertions over the Terraform text (no wildcard IAM actions, no public bucket ACLs, no secret-looking strings).
5. Return **BLOCKED-ON user** for any unexplained destroy or stateful replacement instead of working around it.
6. Do not apply. State the human actions required before Phase 14.

**Done when:** the plan exists with a recorded checksum; the summary is complete; scanner output (or the disclosed manual checklist) is retained; the reviewer can compare the plan summary against the code.

> **⛔ STOP after 12C.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 12D until the user sends a new prompt.

### Subphase 12D — Timeboxed EMR Spark feasibility spike (needs the user's approval record)

**Start condition:** the user wrote an approval record with a small dollar cap, region, instance types, maximum runtime (hours, not days) and teardown. Without it, do nothing live. The spike uses a **separate** Terraform root (for example `infra/terraform/spikes/emr-spark/`) so it never touches the main environment, and it is destroyed right after the test. Every resource is Terraform-authored; nothing is created by hand or by a script.

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
