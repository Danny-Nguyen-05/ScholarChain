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

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

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


## Subphase 12B work order and Step 0 answer

User start instruction (verbatim): `alright let do phase 12b`

User acceptance (verbatim): `use all recommendations`

The complete accepted recommendations are retained in `evidence/12b/step-0-answers.md`. Follow the complete user-supplied NEXT PROMPT in `review.md` under Subphase 12A repair round 1, Steps D–G, after its completed review-record and commit-confirmation steps. Base/HEAD `a83f62e9af56058a170075f98c4e027d039567ec`, branch `phase-12`, clean before the first 12B edit. Implement ONLY 12B via infra-engineer; run all required local gates and a post-freeze full JDK 17 check via build-engineer. No reviewer is invoked, no cloud action/spend or commit/push is authorized. Stop with a complete independent reviewer prompt after 12B.


## Subphase 12C — authorized 2026-10-30

Source: the complete independently supplied 12C next prompt already preserved in review.md, current external phase12.md copied to evidence/12c/phase12-plan-at-start.md, and user answers in the current conversation. The approved 12B source/repair/review records are committed at 3b0855b9657a72b30e8ac43bd484161a9b886c79.

The coordinator presented all remaining defaults (account/profile/Ohio/AZs/deployment trust, N9/N10/N11/N12/N14/N17, inactive primary plan, manual security plus static checks) and asked for provider downloads, read-only AWS checks and Terraform plan only. User answered verbatim: “All right, let's do it.” No apply, cloud writes, paid model calls or paid Cost Explorer calls were included.

Preflight found four untracked human-owned gates for Phases 08–11. The user answered verbatim: “Leave them untouched and continue 12C (Recommended)”. Their baseline hashes are retained. Do not modify, stage or commit them.

Budget USD200 before credits is shared across all cloud phases including optional9C, 12D, ingestion, experiments, evaluation and retained evidence. Cost Nov15 00:00CST to Nov24 23:00CST (239h) as base and Nov11 00:00CST to Nov24 23:00CST (335h) as upper duration; dates are costing assumptions, not live approval. Follow the updated shared plan for privacy, delayed cost reporting, independently approved cleanup, instructor archival approval and early monitoring. The exact notification email is private; budget bootstrap/activation remains pending and outside12C.

Implement only12C via the assigned infra/test owners, retain red/green evidence, pinned native gates, a real plan outside Git with checksum and sanitized summary, security/cost summaries, and the full JDK17 post-freeze check by build-engineer. Never launch a reviewer or start12D. Detailed inputs and limitations: evidence/12c/step-0-answers.md.


## Subphase12D — offline preparation work order

User requests verbatim: “so lets do 12D now”; “use recommendations”. The proposed USD10/two-hour EMR-on-EC2 scope and separate billing bootstrap preparation are recorded in evidence/12d-preparation/step-0-answers.md. This is a coordinator transcription, not a human-owned live approval. Main environment remains untouched. See evidence/12d-preparation/work-order.md for exact ownership and gates. No AWS account calls, real plan/apply/destroy/import, paid calls, reviewer, commit or push authorized in this preparation.


## Subphase 12D preparation — repair round 1 work order

Phase 12D PREPARATION — repair round 1 (offline only). Fresh session.
Repository /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-12, base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f, working tree carries the uncommitted 12D preparation.

0. Coordinator: append the independent 12D preparation review (verdict REQUEST-CHANGES, findings F1–F7 and Info) VERBATIM to docs/agent-runs/phase-12/review.md under "## Subphase 12D preparation — independent review", append routed items to repairs.md, and append this work order to prompt.md. Append only; never rewrite earlier text or human records.

Step 0 — ask the human, with recommended defaults, and wait:
  a. Tag values for the account-wide budget (course, project, environment, owner, expiration). Recommend an expiration that matches the budget's retention/reconciliation end, not the stack's 2026-11-25.
  b. F2: accept that USD 10 of 12C's USD 15 all-EMR reserve goes to 12D, leaving ~USD 5 for Phase 13/15 EMR (upper-window margin was USD 5.09)? Or lower the spike allocation? Record the answer as a coordinator transcription, not an approval.
  c. F7: how to handle the Gmail-bearing Drive path in 69 tracked files (accept / redact going forward / human-performed history rewrite). Agents only record the decision.

Routing (one writer each; no delegation by children; no reviewer launch):
  - infra-engineer, only infra/terraform/billing-bootstrap/** and infra/terraform/spikes/emr-spark/**:
    F1: add the five required tags with validation, plus a mock-plan assertion that checks them; give the 50/80/100 thresholds a rationale comment.
    F3: disclose the CostTypes deprecation and add a post-apply readback check that credits/refunds are excluded.
    F4: state in the spike README that the zero-resource claim rests on source inspection (the test-engineer static check is optional and only if the human assigns it).
    Run the same pinned binary and TF_CLI_CONFIG_FILE in all three roots: init -backend=false -input=false -no-color -lockfile=readonly; fmt -check -recursive; validate -no-color; test -no-color. Retain one RED that removes a required tag and fails at the new assertion.
  - coordinator, evidence only:
    F2: state the remaining EMR reserve explicitly in cost-proposal.md and handoff.md.
    F5: record non-secret environment variables in new command records.
    F6: restore spacing in untracked evidence; add an appended erratum to tracked records.
    Then run the static guard, the guard self-test and git diff --check, and take a new freeze.
  - build-engineer: full JDK 17 sbt check after the new freeze; return logs and XML; no source edits.

Retain every live blocker unchanged: active account-wide monitor and recipient delivery proof; human-enabled Cost Explorer and conservative remaining budget; separate non-root temporary deployment identity (scholarchain-planner stays read-only); portable G1 bundle; same-assembled-JAR local baseline; driver/executor class-origin probe; shared-filesystem proof; independent elapsed-time deadline mechanism; genuine isolated launch plan with checksum and independent review; human-written approval of cap/region/types/counts/runtime/teardown. B1/B2/B3/R1 and N19/N20 are carried unchanged.

Forbidden: AWS account or paid calls, real plan/apply/destroy/import, credential/state/plan/private-input reads, writing human-gate.md/accepted-commit.md/approvals, inferring apply or live approval, launching reviewers, commits, pushes, Phase 13.

Handoff: updated packet plus a reviewer prompt for an independent preparation-only recheck. Then ask the human, without assuming an answer, which bounded 12D continuation (if any) to authorise after a recheck APPROVE — for example, read-only real plan of the billing bootstrap, or the Spark/build technical-readiness work order. End with: "Subphase 12D preparation repair round 1 is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."

User request: “FIx all blockings for me”.


## Subphase 12D preparation repair round 1 — readable erratum

The earlier 12D preparation text is preserved byte-for-byte. Read its joined words as ordinary spaced prose: for example, “203 frozen files at 2026-10-30”, “main foundation budget”, “before inventory”, “assembled JAR” and “13 files”. These spacing corrections change no observed gate result.

The original preparation had 51 passing Terraform runs, 69 assertions, 26 expected-failure runs, a 203-file freeze and a full JDK 17 check with 1,255 tests in 157 fresh XML reports. One stale TestRunMarkerSpec report under project/verification/target was excluded. Those results describe the original source state; use the repair-round evidence for the repaired source and new gate results.

F2 allocation clarification: the original USD 15 reserve covers ALL EMR spikes and experiments. The former USD 10 spike proposal would leave USD 5 for later EMR. The user now chose a USD 5 proposed spike cap, leaving USD 10 if fully spent. The 12C upper-window margin remains USD 5.09. Later EMR runs require a new allocation decision and exact all-resource costing. Nothing increases the shared USD 200 before-credit ceiling or authorizes spending.

F5 metadata clarification: historical Terraform records omit their environment field. The original prose names TF_CLI_CONFIG_FILE, but the missing per-command observation is not reconstructed as fact. New repair records explicitly retain selected non-secret environment variables. Original logs and metadata remain unchanged.

F7 decision transcription: use neutral references in new material and preserve existing records/history. No historical redaction, human-record rewrite or history rewrite is authorized. The neutral authority reference is the repository copy at docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md.


## Subphase 12D — preparation recheck recording work order

Phase 12D — record preparation recheck and obtain the next bounded continuation. Fresh session. No implementation in this turn.
Repository /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-12, base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f (working tree carries the uncommitted 12D preparation plus repair round 1).

1. Coordinator: append the independent recheck review (verdict APPROVE for preparation only, N1 Low, I1–I3 Info) VERBATIM to docs/agent-runs/phase-12/review.md under "## Subphase 12D preparation repair round 1 — independent recheck". Append N1 to repairs.md as a carried non-blocking item owned by infra-engineer, to be resolved at the next billing-bootstrap or deployment-identity touch. Append this work order to prompt.md. Append only; preserve every earlier byte and all human records.

2. Retain unchanged: every live prerequisite (active monitor and recipient delivery proof; usable cost data and conservative remaining allowance; separate non-root temporary deployment identity; portable G1 bundle; same-assembled-JAR baseline; real driver/executor class origins; shared-filesystem proof; independent elapsed-time deadline; genuine isolated plan, checksum and review; human-written execution and teardown approval). B1/B2/B3/R1 and N19/N20 carried. Planner stays read-only.

3. Ask the human, wait, and record the answer only as a coordinator transcription (not an approval):
   Which bounded 12D continuation, if any, should be authorised next?
   (a) Billing monitor: a read-only real plan of infra/terraform/billing-bootstrap. Needs a confirmed read-only planning identity, private recipient input, explicit project start/end timestamps and a budget name. Fold in the N1 README fix first. Plan stays outside Git; record summary and checksum only; no apply.
   (b) Technical readiness: an offline Spark/build work order (portable G1 bundle, same-assembled-JAR local baseline, class-origin probe design, filesystem mapping). No AWS calls.
   (c) Stop here / defer.
   Do not infer apply approval, budget creation, live execution or Serverless fallback from any answer.

Forbidden in this turn: source or infra edits, AWS/account/paid calls, real plan/apply/destroy/import, credential/state/private-input reads, writing human-gate.md/accepted-commit.md/approvals, launching reviewers, commits, pushes, Phase 13.
End with: "Subphase 12D preparation recheck is recorded. I have stopped and will not start the next continuation until I receive the next prompt."


## Subphase 12D — billing monitor read-only plan continuation

User request: “alright let do it. If you need any thing that i do manually tell me”. The user confirmed the named profile/account/region, scholarchain-project-budget name, and October 1, 2026 through January 1, 2027 UTC monitoring period. Detailed transcription and boundaries: evidence/12d-billing-plan/step-0-answers.md. Route only N1 documentation to infra-engineer; prepare a real read-only budget plan with private recipient input supplied manually, plan/state outside Git, summary/checksum retained, then independent review and stop. No apply, AWS write, paid calls, live spike, reviewer launch, commit, push or Phase 13.


## Subphase 12D — billing-plan review recording work order

Phase 12D — record billing-plan review and obtain the next bounded continuation. Fresh session. No implementation, AWS or Terraform calls in this turn.
Repository /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-12, base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f (uncommitted 12D preparation, repair round 1 and billing-plan work present).

1. Coordinator: append the independent billing-plan review (verdict APPROVE for the read-only billing plan only; B1 Low, B2 Low, Info) VERBATIM to docs/agent-runs/phase-12/review.md under "## Subphase 12D billing-monitor read-only plan — independent review". Append B1 to repairs.md (infra-engineer, carried non-blocking, to be resolved before any deployment-identity policy or execution plan) and B2 as a pending human decision. Append this work order to prompt.md. Append only; preserve every earlier byte and all human records.

2. Retain unchanged: the saved plan is bound to the read-only planner and is NOT an execution plan; no budget exists; live CUSTOM/CostTypes/tag acceptance, alert delivery, usable cost data and remaining allowance are unverified; USD 5 proposed spike cap and USD 10 remaining all-EMR reserve unchanged and unapproved; every EMR/G1/probe/filesystem/deadline/teardown prerequisite open; B1/B2/B3/R1 (12B/12C) and N19/N20 carried. Planner never elevated or repurposed.

3. Ask the human, wait, and record answers only as coordinator transcriptions (never approvals):
   a. B2: delete the /tmp/scholarchain-phase12d-billing-plan private artifacts after this review (human performs it), or retain them (where and why)?
   b. Next bounded continuation:
      (i) Billing execution preparation: decide how the separate non-root, temporary-credential deployment identity is established in a way consistent with the Terraform-only rule (if any console step is proposed, it needs an explicit documented human exception). Then infra-engineer fixes B1 and drafts the reviewed least-privilege policy. A fresh plan with that identity, an independent review and a human-written apply approval are each separate later gates. Nothing is created or applied in this step.
      (ii) Offline Spark/build technical readiness (portable G1 bundle, same-assembled-JAR baseline, class-origin probe design, filesystem mapping). No AWS calls.
      (iii) Stop / defer.
   Do not infer apply approval, IAM creation, budget creation or live execution from any answer.

Forbidden in this turn: source or infra edits, AWS/account/paid calls, Terraform plan/apply/destroy/import, credential/state/private-input/raw-plan reads, deleting private artifacts, writing human-gate.md/accepted-commit.md/approvals, launching reviewers, commits, pushes, Phase 13.
End with: "The billing-plan review is recorded. I have stopped and will not start the next continuation until I receive the next prompt."


## Subphase 12D billing execution preparation — work order

User request: “Deleted; start billing execution preparation.”

Coordinator transcription: the user reports deleting the previous private billing-plan directory. A metadata-only check confirmed its absence; no deleted private input was read or recovered. Prepare only the identity-establishment strategy and least-privilege billing policy draft, resolving the billing review’s B1 action/scoping documentation. The actual trusted principal and bootstrap authorization remain unset. Keep scholarchain-planner read-only. No AWS/account or paid calls, real Terraform plan/apply/destroy/import, IAM creation/grant, budget creation, credential/state/private-input reads, approvals, reviewer launches, commits, pushes or Phase 13.

Ownership: infra-engineer writes only scoped infra/terraform policy drafts and billing README corrections; coordinator assembles phase evidence and append-only records. After local native tests and static checks, freeze sources before the build-engineer runs the full JDK 17 sbt check without source edits. Return an independent preparation-only reviewer prompt and stop. The human chooses the bootstrap route after reviewing the concrete proposal. No console exception or live approval is inferred.

Authority: AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/infra-engineer.md, .claude/agents/build-engineer.md, docs/agent-runs/README.md and the neutral plan snapshot docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md. Prior approved preparation, repair and billing-plan packets are immutable. Carried B1/B2/B3/R1 from earlier phases and N19/N20 are unchanged.


## Subphase 12D — billing execution preparation review recording work order

User-supplied work order; verbatim.

Phase 12D — record billing execution preparation review and obtain the human's identity-establishment choice. Fresh session. No implementation, AWS, Terraform or IAM actions in this turn.
Repository /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-12, base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f (uncommitted 12D preparation, repair-1, billing-plan and billing-execution-prep work present).
1. Coordinator: append this independent review (verdict APPROVE for offline billing execution preparation only; E1 Low, E2/E3 Info) VERBATIM to docs/agent-runs/phase-12/review.md under "## Subphase 12D billing execution preparation — independent review". In repairs.md append: billing B1 resolved by this round; E1 carried non-blocking (infra-engineer, next touch of billing-execution); E3 noted for the human decision. Append this work order to prompt.md. Append only; preserve every earlier byte and all human records.
2. Retain unchanged: no identity, role, policy, budget, execution plan, active monitor, alert delivery, usable cost data or remaining allowance exists or is verified; the old planner-bound plan was deleted and is not reusable; USD 5 proposed spike cap, USD 10 remaining all-EMR reserve and USD 5.09 upper-window margin unchanged and unapproved; every G1/same-JAR/class-origin/filesystem/elapsed-deadline/isolated-plan/teardown gate open; B1/B2/B3/R1 (12B/12C) and N19/N20 carried. Planner stays read-only and is never trusted or elevated.
3. Ask the human, wait, and record answers only as coordinator transcriptions (never approvals):
   a. Identity-establishment route:
      (i) Terraform-first: name an already-authorized, privileged NON-ROOT bootstrap identity and its temporary-credential login method; or
      (ii) consider the proposed one-time human-performed root-console account-access bootstrap exception (dedicated operator user + MFA + the single reviewed billing role/trust/caller documents only; no root keys, no AdministratorAccess, no planner change, no budget creation). This would be a deviation from Terraform-only authorship that the human must record personally; agents never write it; or
      (iii) stop / defer.
   b. Credential path for the operator, given E3: browser-based aws login (MFA-context compatibility unverified), MFA-protected AssumeRole from an IAM user access key (long-lived key, needs explicit justification), or an Identity Center design (separate review). Which should the next work order evaluate?
   c. The actual operator user name/ARN once chosen (non-root, not the planner, same account).
   Do not infer IAM creation, a console exception, a plan, an apply, budget creation or live execution from any answer.
Forbidden in this turn: source or infra edits, AWS/account/paid/IAM calls, Terraform plan/apply/destroy/import, credential/state/private-input reads, console actions, writing human-gate.md/accepted-commit.md/approvals or exception records, launching reviewers, commits, pushes, Phase 13.
End with: "The billing execution preparation review is recorded. I have stopped and will not start the next work order until I receive the next prompt."


## Subphase 12D — offline browser-login path evaluation

User request: “use those recommendations and evaluate the login path”.

Coordinator transcription: evaluate browser-based aws login first; use scholarchain-billing-operator as a proposed name only; consider the prior narrowly scoped human bootstrap exception as a future design option. No actual operator ARN or existing privileged non-root bootstrap identity is verified. This is not a human exception, IAM, plan/apply or spending approval. No remaining questions for this offline evaluation.

Bounded scope: public primary AWS documentation/source and safely isolated installed CLI help/version. Determine what supports strict MultiFactorAuthPresent MFA-conditioned trust, identify undocumented assumptions, separately audit login permissions and propose the next reviewable setup work order. Evaluate the source-profile path and, if supported, console MFA role switching followed by browser login as distinct candidates. Do not weaken trust, select long-lived keys or Identity Center, or create a fallback without a new reviewed decision.

Specialist: infra-engineer, read-only research, no child agents, source edits or production artifact changes; return scratch report and public-source provenance. Coordinator owns phase evidence and append-only records. No Terraform/build rerun for this documentation-only evaluation; all older gate results are historical. Retain approved source/evidence/pins/locks and E1 unchanged. Never launch a reviewer.

Forbidden: login/session/account/AWS/IAM/paid calls, credential/config/cache/state/private-input/raw-plan reads, source or infra edits, console action, root keys, planner elevation, human-gate/accepted-commit/approval/exception writes, commits, pushes and Phase 13. Public web fetches are not account calls. Local help must not read user AWS config or credentials. All live billing and EMR prerequisites remain open, including the USD 5 proposed cap/USD 10 remaining EMR reserve/USD 5.09 upper-window margin.

Authority: AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/infra-engineer.md, docs/agent-runs/README.md and neutral plan docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md. Return a complete evidence-backed evaluation and independent read-only reviewer prompt, then stop before any setup.


## Subphase 12D — login-path review and proposed offline amendment work order

User-supplied work order; verbatim.

Phase 12D — record login-path review, then (only if the human authorizes it) an OFFLINE billing-execution policy amendment for candidate B and E1. Fresh session.
Repository /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-12, base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f (uncommitted 12D work present).

0. Coordinator: append this independent review (verdict APPROVE for the offline login-path evaluation only; Info L1–L3) VERBATIM to docs/agent-runs/phase-12/review.md under "## Subphase 12D offline login-path evaluation — independent review". Append L1–L3 to repairs.md as design inputs for the amendment. Append this work order to prompt.md. Append only; preserve every earlier byte and all human records.

Step 0 — ask the human, with recommended defaults, and wait:
  a. Authorize the offline amendment below? (Recommended: yes; offline only.)
  b. Pin signin:OAuthClientId to arn:aws:signin:::devtools/same-device in the login statement (L1)? (Recommended: yes, disclosed as an extra live-verification risk.)
  c. Operator console setup (L2): password reset on first sign-in (needs a reviewed iam:ChangePassword grant) or a bootstrap-set password with no reset; MFA assigned by the bootstrap actor with no self-management grant? (Recommended: no reset grant; bootstrap-assigned MFA.)
  Record answers only as coordinator transcriptions, never as an IAM, exception, login or apply approval.

If authorized — infra-engineer, only infra/terraform/billing-execution/**:
  1. Add a separate rendered login policy for the billing role only: Allow signin:AuthorizeOAuth2Access and signin:CreateOAuth2Token on exactly arn:aws:signin:<region>:<account>:oauth2/public-client/localhost, with configurable validated region (default us-east-2, rejecting wildcards) and account, plus the OAuthClientId condition if chosen. Never add Sign-In actions to the five-action budget statement; no remote client, console resource or wildcard. Keep the trust and caller policies byte-for-byte equivalent in behaviour; give the planner nothing.
  2. Fix E1: compare lower(operator_user_arn) and add a mixed-case planner rejection test.
  3. Tests with independent synthetic values: exact login-policy JSON; region/account binding changes; wildcard region/account rejected; budget statement unchanged; trust/caller unchanged; mixed-case planner rejected. Retain one RED (e.g., scratch login Resource widened to oauth2/public-client/*) that fails the exact assertion with a real value diff; tests identical; repository hashes unchanged.
  4. README: document candidate B, the L1 managed-policy-scope inference and stop-on-denial rule, the L2 operator console prerequisites as chosen, L3 session-expiry fail-closed behaviour, and that nothing is installed. Zero-resource claim stays based on source inspection.
  Gates: pinned Terraform 1.13.5/AWS 6.44.0 init -backend=false -input=false -no-color -lockfile=readonly, fmt -check -recursive, validate -no-color, test -no-color in all four roots with selected non-secret environment recorded; static guard and self-tests; git diff --check; new source freeze; full JDK 17 sbt check after the freeze (build-engineer, no source edits). Retain native logs, hashes and manifests.

Retain unchanged: no identity, role, login grant, budget, execution plan, active monitor, delivery, usable cost data or remaining allowance exists or is verified; candidate B is unverified live; no automatic fallback to candidate A, a permanent key or Identity Center; USD 5 proposed cap, USD 10 remaining EMR reserve and USD 5.09 margin unchanged and unapproved; every G1/same-JAR/class-origin/filesystem/elapsed-deadline/isolated-plan/teardown gate open; B1/B2/B3/R1 and N19/N20 carried.

Forbidden: AWS/account/login/IAM/paid calls, console actions, Terraform plan/apply/destroy/import against an account, credential/config/cache/state/private-input reads, writing human-gate.md/accepted-commit.md/approvals or exception records, launching reviewers, commits, pushes, Phase 13.
Handoff: packet plus a complete reviewer prompt for an independent read-only review of the amendment. End with: "The billing-execution policy amendment is ready for review. I have stopped and will not start the next work order until I receive the next prompt."


## Subphase 12D — authorized OFFLINE billing-execution policy amendment

User request: “use all recommended defaults. Also where are we up to ?”

Coordinator transcription: all three Step 0 defaults accepted: offline amendment only; exact same-device OAuthClientId pin; bootstrap-set password without forced reset/ChangePassword grant, bootstrap-assigned MFA without self-management. This is not an IAM, console exception, login, plan/apply or spending approval. Actual operator ARN remains unset; no additional questions for this offline work order.

Implement only the already recorded reviewer work order for candidate B and E1, through infra-engineer in infra/terraform/billing-execution/**. Render separate exact two-action account/region/localhost login policy with client-ID pin; preserve existing budget/trust/caller semantics; reject mixed-case planner. Independent synthetic feature/negative tests plus genuine scratch RED with unchanged repository. Document L1 scope inference/stop-on-denial, L2 password/MFA setup choice, L3 expiry fail-closed. Keep zero-resource claim inspection-based. Pinned four-root init/fmt-check/validate/mock tests, static guard+self-test, diff-check, final source freeze, then build-engineer full JDK 17 sbt check without source edits. Retain exact commands/env/exits/counts/log hashes and manifests; append 14-field reports and return independent read-only reviewer prompt. Never launch reviewer or start setup automatically.

Authority: AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/infra-engineer.md, .claude/agents/build-engineer.md, docs/agent-runs/README.md and neutral plan docs/agent-runs/phase-12/evidence/12c/phase12-plan-at-start.md. Forbidden/live-boundary and carried findings are exactly those in the recorded review work order.


## Subphase 12D — billing policy amendment review recording work order

User-supplied work order; verbatim.

Phase 12D — record billing policy amendment review and obtain the human's identity-establishment decision. Fresh session. No implementation, AWS, IAM, login, console or Terraform actions in this turn.
Repository /Users/danny/Documents/UIC/CS441/ScholarChain, branch phase-12, base/HEAD 5ca8406bad5fe55f732458fa0cbd5d561ac83d8f (uncommitted 12D work present).
1. Coordinator: append this independent review (verdict APPROVE for the offline billing-execution policy amendment only; one Info note on RED coverage) VERBATIM to docs/agent-runs/phase-12/review.md under "## Subphase 12D offline billing-execution policy amendment — independent review". In repairs.md append: E1 resolved; L1–L3 addressed in README; Info RED-coverage note carried as optional. Append this work order to prompt.md. Append only; preserve every earlier byte and all human records.
2. Retain unchanged: no operator, billing role, login grant, budget, execution plan, active monitor, delivery, accounting acceptance, usable cost data or remaining allowance exists or is verified; candidate B (console MFA → strict Switch Role → role-selected aws login → native login_session) is inferred, not verified; the narrowed Sign-In scope and client-ID pin may be denied live and must then stop for review; no automatic fallback to root, planner, candidate A, a permanent key or Identity Center; the old planner plan is deleted; USD 5 proposed cap, USD 10 remaining EMR reserve and USD 5.09 margin unchanged and unapproved; every G1/same-JAR/class-origin/filesystem/elapsed-deadline/isolated-plan/teardown gate open; B1/B2/B3/R1 and N19/N20 carried.
3. Ask the human, wait, and record answers only as coordinator transcriptions (never approvals or exception records):
   a. Identity-establishment route:
      (i) Terraform-first: name an existing, already-authorized, privileged NON-ROOT bootstrap identity and its temporary-credential method. A later work order would author Terraform for the operator, role, trust, caller, execution and login attachments with the five required tags; its plan, checksum, independent review and a human-written security-change approval are separate gates. Root never runs Terraform.
      (ii) One-time human-performed root-console bootstrap exception, limited to: the dedicated operator user with a bootstrap-set password (no forced reset), bootstrap-assigned MFA (no self-management), and the single billing role with exactly the reviewed trust, caller, execution and login documents. No root keys, AdministratorAccess, planner change, Organizations/Identity Center enablement, budget creation or other resources. Only the human may write and record this exception, personally, before any action; agents never draft it as an approval.
      (iii) Stop / defer.
   b. Confirm the operator user name (proposed scholarchain-billing-operator) and the role name (proposed scholarchain-billing-deployer). Do not supply passwords, MFA seeds or codes to the agent.
   c. When the chosen route's prerequisites exist, which bounded next work order: (i) Terraform IAM bootstrap authoring (offline, then plan/review/approval gates), or (ii) a post-exception read-only verification checklist for the human-performed setup (no agent console actions)?
   Do not infer IAM creation, a console exception, login, a plan, an apply, budget creation or live execution from any answer.
Forbidden in this turn: source or infra edits, AWS/account/login/IAM/paid calls, console actions, Terraform plan/apply/destroy/import, credential/config/cache/state/private-input reads, writing human-gate.md/accepted-commit.md/approvals or exception records, launching reviewers, commits, pushes, Phase 13.
End with: "The billing policy amendment review is recorded. I have stopped and will not start the next work order until I receive the next prompt."

## Subphase 12D — human identity-route choices (coordinator transcription)

The user answered the pending questions:

1. “Consider the limited human console-bootstrap route (Recommended if root and planner are your only identities)”.
2. “Keep both names (Recommended)”: proposed user scholarchain-billing-operator and role scholarchain-billing-deployer. These names are proposals, not verified identities.
3. “Post-exception read-only verification checklist for your manual setup (Recommended for the console route)”. This follow-up is conditional on the chosen route’s prerequisites.

This is a coordinator transcription of planning choices only. It is not an exception, security-change approval, IAM creation authorization, login authorization, budget/plan/apply approval or spending approval. The human-owned console exception has not been supplied or verified. Do not write human-gate.md, accepted-commit.md, approvals or exception records on the human’s behalf. No console or AWS action occurred.

Next gate: the human personally records the exact limited account-access exception before any action, then supplies a separately bounded checklist work order when prerequisites exist. The proposed scope remains the dedicated operator with bootstrap-set password/no forced reset, bootstrap-assigned MFA/no self-management, and the one billing role with reviewed exact trust/caller/execution/same-device login policies and required governance tags. No root access keys, AdministratorAccess, planner change, Organizations/Identity Center enablement, budget creation or unrelated resources. Actual operator ARN and live login chain remain unverified. No automatic setup or checklist execution starts from these answers.

All live billing/EMR gates remain open; old planner plan remains deleted; proposed USD 5 cap/USD 10 EMR reserve/USD 5.09 margin and B1/B2/B3/R1/N19/N20 unchanged.


## Subphase 12D — human IAM bootstrap and authentication-only verification

Coordinator record of the human-performed setup and separately selected authentication check. Exact authentication go-ahead: “alright let's do it. guide me step by step how to do it”. User later reported “yes login succeeds”, then pasted the identity-only command and the expected billing-role Account/Arn JSON. See evidence/12d-authentication-verification/user-go-ahead-transcription.json, human-command-records.json and caller-identity.user-supplied.json. This record does not authorize a plan/apply or spending. Earlier personal setup exception and exact user-requested window append are preserved. Source was not changed during guidance. Actual setup start/end were not supplied and are not invented.


## Subphase 12D — fresh billing execution-identity read-only plan

User work order, verbatim: “alright let's continue”. Context: assistant identified the immediate next step as the fresh read-only Terraform plan for the USD 200 budget monitor using the verified billing role. User then confirmed the existing inputs: “everything is good”.

Selected scope: isolated billing-bootstrap init/local checks/read-only plan/protected show and sanitized summary/checksum; dedicated scholarchain-billing-deployer profile in account 530332961125, us-east-2, existing selected budget name/period and five tags. The human privately re-enters the notification recipient outside Git. No direct credential/config/cache inspection or private-input contents are exposed. No apply/destroy/import, IAM change, paid calls, EMR, reviewer launch, commit/push or Phase 13. See evidence/12d-billing-execution-plan/work-order.json and confirmed-inputs.json.

Coordinator retains phase evidence. Infra-engineer /root/infra_12d_execution_plan owns the protected scratch planning helpers and execution; no children, reviewers or production-source edits. A fresh execution-identity plan is not approval to apply.


## Subphase 12D — billing apply-gate blocker repair preparation

User work order, verbatim: “Fix all blocking bugs”. The pasted review APPROVES the prior read-only plan only; P1/P2 block apply and P3 is required in the later handoff. The review is retained verbatim in review.md and evidence/12d-billing-apply-gate-repair-prep/user-supplied-external-review.txt. Attached recommendations are review data; no apply, IAM change or spending authority inferred.

Scope: record verdict/findings, prepare the user-launched identity-packet review prompt, obtain the human's own timing clarification and durable-storage/retention choices, and prepare public offline P2/P3 proposals. No actual apply handoff or replacement plan until P1 timing/independent identity review and storage prerequisites pass. Human selected recommended local paths/retention and conditionally authorized read-only regeneration after prerequisites. Coordinator transcribes choices only; never writes human timing/exception/approval records.

Infra-engineer /root/infra_12d_durable_storage_prep owns public scratch technical preparation only under /tmp/scholarchain-phase12d-durable-storage-prep; no children/reviewer launch, repo source edit, protected artifact reads or AWS/Terraform execution. Coordinator owns phase evidence. Existing uncommitted work preserved. No mutations, private recipient request, plan regeneration, commit/push or Phase13 in preparation.


## Subphase 12D — human actual-timing clarification

User statement, verbatim: “that is my real time I have updated it”. User confirms the9–10PM Chicago October31 window in the human-owned exception file is the actual setup time. Record as user-supplied evidence only; no agent edit of human record, independent approval, plan regeneration, apply or spending. See evidence/12d-timing-clarification/user-statement.json.


## Subphase 12D — P1 timing reconciliation repair

User work order: “Fix all blocking bugs please”. New independent review is REQUEST-CHANGES for F1 timing only; technical identity/authentication evidence verified. Record review verbatim, route F1–F4, add F3 retrospective manifest and preserve original three files, record F2 original request as unavailable unless retained verbatim, prepare narrow user-launched recheck. No AWS/IAM/login/Terraform/build call, durable plan, apply or spending.

User subsequently explicitly requested: “oh yeh can you update that window for me, I enter the wrong time”. Asked for their own exact correction, user dictated: “I don't really remember it was around 8-9pm I think”. This specific instruction authorizes only verbatim append of their statement to the human record, preserving all prior bytes. No replacement time selected, retrospective acceptance, attribution of old replacement paragraph, approval or signature is supplied by the agent. See evidence/12d-p1-timing-reconciliation/append-provenance.json and human-file-check.json.


Human replies received during this repair, in response to the retained questions: “accept” for retrospective window/60-minute deviation acknowledging AWS20:01–20:23 activity, and “yes it is mine” for original replacement paragraph attribution. Under the user's explicit edit instruction and the stated verbatim-append procedure, both questions/answers were appended to the personal record without changing any earlier byte. See evidence/12d-p1-timing-reconciliation/human-replies.json. No agent-selected times, compliance certification, backdated approval, or prospective apply/spending authority.


## Subphase 12D — fresh durable-path read-only billing plan

User supplies P1 timing/provenance APPROVE and explicitly invokes the attached NEXT PROMPT as their request. Exact attachment is evidence/12d-billing-durable-plan/user-supplied-p1-approval.txt. F1/F2/F3 closed by independent review; technical identity evidence already verified. Selected scope: protected durable local setup, fresh human role-session login and sanitized identity, fresh hidden recipient input, pinned offline gates and read-only init/plan/show/sanitization. No apply/import/destroy, IAM/resource mutation, paid calls/spending, human-record writes, reviewer launch, commit/push or Phase13.

Reuse confirmed USD200 COST/CUSTOM budget scholarchain-project-budget, account530332961125/profile scholarchain-billing-deployer/regionus-east-2, UTC2026-10-01 through2027-01-01, existing cost basis/five tags/three alerts. Human selected primary /Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap and sibling billing-bootstrap-backups, modes0700/0600 (executables0700), selected retention until reviewed teardown/final reconciliation and human-approved cleanup; same-disk backup limitation retained. State primary/billing.execution.tfstate, plan primary/billing.execution.tfplan, TF_DATA_DIR primary/tf-data, cwd primary/config. All toolchain/config/provider targets durable; do not copy old private plan or inputs.

Coordinator owns phase evidence; infra-engineer /root/infra_12d_durable_plan owns selected durable/safe scratch artifacts only, no source edits/children/reviewers. Live plan waits for fresh verified human identity and hidden Saved. Prior uncommitted work preserved; no approval file or human-record edit. Old /tmp plan kept, marked superseded after successful new plan. G1 pre-apply personal affirmation, P3 checks and exact-plan apply approval remain separate later gates.


## Subphase 12D — operator password recovery proposal

User reports “I think I didn't save it” after password-recovery question. Prepare proposal only for existing operator password reset; no human authorization is inferred. Original durable read-only plan task remains active but waits for access recovery, fresh identity and private input. See evidence/12d-password-recovery-proposal/proposal.md. No console/IAM mutation or human-record write.


## Subphase 12D — record durable-plan APPROVE; bounded apply proposal only

User expressly invokes the attached durable-plan review NEXT PROMPT as their request. Full attachment retained verbatim at evidence/12d-billing-durable-plan-review-record/user-supplied-review.txt. Scope: record APPROVE/P2 plan-stage satisfaction, append D1 sequencing erratum distinguishing record write from unknown user receipt time, prepare ONLY a bounded apply proposal and user-launched reviewer prompt. Nothing executed; no Terraform/AWS/IAM/login/console/build/paid calls, protected plan/private input/state/config/cache reads, durable writes, human-record/approval writes, reviewer launch, commit/push or Phase13.

Infra-engineer /root/infra_12d_apply_proposal owns public scratch proposal/source research/manifest only; coordinator assembles phase evidence. Plan bound to6631bytes/SHAab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855 with exact existing durable paths/toolchain. Future human G1 and exact-plan/window/actor/P3/backup/readback authorization remains pending and human-owned. No questions or extra approval sought for current offline authoring. Preserve all earlier bytes and uncommitted work.


## Subphase 12D — apply-proposal APPROVE; wrapper and offline tests only

User-invoked complete NEXT PROMPT retained verbatim in evidence/12d-billing-apply-proposal-review-record/user-supplied-review.txt and review.md. No new questions. Route infra-engineer to scripts/billing/** for the bounded execution/backup/sanitizer wrapper and offline feature tests including A1 pinned credential-free terraform_data scratch test and A2 config/errored.tfstate preservation. Coordinator assembles evidence and user-launch reviewer prompt. No live calls, durable/private access, human record/approval writes, reviewer launch, commit/push or Phase13.


## Subphase 12D — bounded wrapper repair W1/W2

User-supplied REQUEST-CHANGES and NEXT GATE retained verbatim in evidence/12d-billing-wrapper-review-record/user-supplied-review.txt. Route infra-engineer, sole writer scripts/billing/**: SIGINT-first apply termination, dedicated apply timeout, unconditional local backup/preservation, meaningful offline tests, full wrapper suite and isolated pinned Terraform A1 regression. W3 remains an execution-gate scan-scope requirement; no unrequested broad code change. W4 Info has no detailed finding in supplied report and is carried without invented content. A1/A2 independently accepted/CLOSED. No new questions. Coordinator owns evidence and a user-launched recheck prompt. No live calls, actual durable/private/state/plan/credential/config/cache access, human-record/approval writes, reviewer launch, commit/push or Phase13.


## Subphase 12D — bundled human execution-gate handoff only

User-supplied APPROVE recheck/NEXT GATE retained verbatim in evidence/12d-billing-execution-gate-handoff/user-supplied-review.txt. Record verdict and prepare handoff only: concrete reviewed hashes, human source-control/clean canonical checkout/G1/CLIhash+version/identity/window decisions, W3 final-publication coverage and R1 persistent-terminal procedure. No new questions needed for authoring. No scripts changed, test/build/live commands, installed CLI/durable/private inspection, personal record/approval writes, reviewer launch, commit/push or Phase13.


## Subphase 12D — record handoff APPROVE; present bundled human decisions

User-supplied review retained verbatim in evidence/12d-billing-execution-gate-review-record/user-supplied-review.txt. Record verdict and present release/clean canonical checkout, G1 ownwords, local-only CLI preflight authorization, H1 actor/mechanism, H2 window/W3tooling and R1residualrisk decisions together. No dependent work until human answers. No local CLI invocation, helper authorship/delegation, live work, login, installed toolchain/durable/private inspection, approval writing, commit/push or reviewer launch. This is a human-decision wait within the approved handoff, not a new implementation/review round.


## Subphase 12D — user-selected offline publication helper

Human answered “yes” to preparing/testing the offline evidence assembly/comparison helper; exact question/reply in evidence/12d-billing-publication-helper/human-choice.json. Delegate infra-engineer /root/infra_12d_publication_helper to new scripts/billing/publication helper/test/documentation files only. Implement W3publicpacket/five exact suffix copies/base+suffix publication equality and compatible freeze manifest; no publication/record mutations, real private scanning or broader execution. Existing5script files unchanged. Test only public synthetic tempfixtures with python3 -I; no wrapper/A1/Terraform/AWS/CLI/build/login/durable/private/credential/config/cache calls. Coordinator assembles evidence and complete user-launch reviewer prompt; no reviewer launch/commit/push/human approval writing. No window selected or live permission. No further questions needed for this bounded authoring task.


## Subphase 12D — record helper APPROVE; remaining human decisions

User-supplied review/NEXT GATE retained verbatim in evidence/12d-billing-publication-helper-review-record/user-supplied-review.txt. Record verdict and present sourcecontrol/clean canonical checkout covering all8billingfiles, R1residualrisk acceptance, datedwindow/personal-gate decisions. No automatic helper/private scan/publication/live work. Human remains gate author. No new implementation/reviewer/test/CLI/login/Terraform/AWS/durable/private access/commit/push.


## Subphase 12D — stopped P3 format diagnosis and offline repair

User reported approved human-run p3-check stopped with P3_NOT_EXACT_NOT_FOUND/exit2. Apply/readback never started, no local state/backup, no P3successreceipt. Incident-responder performed local-only in-memory fixed-category parsing of exact saved stderr; no raw body/IDs/addresses/loginURL persisted, no AWSretry. Exact observed known header is aws: [ERROR]: An error occurred (NotFoundException) when calling the DescribeBudget operation (reached max retries: 0): <opaque body>. Evidence sanitized in evidence/12d-billing-p3-format-repair/diagnosis/. Route infra-engineer /root/infra_12d_p3_format_repair for narrow two-header parser/offline feature repair and A1scratchregression, no originaljournal/gate/state modification or newlivecalls. Existing plainformat retained; unknown/prefix-only/plain-annotation/positivecount/mixederrors remain rejected. User-launched independent recheck before any newcommit/newgate/newoperation. No originalapproval extension inferred.


## Subphase 12D — F1 saved-stderr layout check authorization

User-supplied REQUEST-CHANGES/NEXT PROMPT retained verbatim in evidence/12d-billing-p3-format-repair-review-record/user-supplied-review.txt. Record review and ask one human question before any private access: authorize incident-responder one bounded local in-memory final absence() check on exact existing stderr, output accepted/blockedcode/leadingtrailingnewlinebuckets/CRLFflag only. No raw text/AWS/CLI/login/Terraform/wrapperstage/retry/gatejournalwrites. Wait for answer. If acceptedtrue later infraaddsconfirmedlayoutfixture/fullsuite only; iffalse narrowly adjustslayout plusfixtures/fullsuite/A1; ifdeclinedrecordriskandstop. No branch started now.


## Subphase 12D — authorized F1 exact saved-stderr check and conditional repair

Human answered “yes” to one bounded local in-memory finalabsence() check; exact context in evidence/12d-billing-p3-layout-recheck/user-authorization.json. Route incident-responder /root/incident_12d_p3_diagnosis to one evaluation using wrapperSHA297830d4… and exactexistingstderr, outputonlyaccepted/blockedcode/newlinebuckets/CRLFflag; source retained, rawbytesneverpublished. No productionmode/Policyinstantiation/privatebeyondstderr/livecall/oldgatejournalmutation. Conditionalreviewpromptbranch only after actualboolean; coordinatorassemblesevidence. No renewedexecutionapproval orwindowextension.


## Subphase 12D — record F1 APPROVE; present new release/gate choices only

User-supplied F1APPROVE/NEXT PROMPT retained verbatim in evidence/12d-billing-p3-layout-review-record/user-supplied-review.txt. Record/preserve all public evidence and prepare factual new-gate handoff (no gatewritten). Present together humancommit/defer, L1riskacceptance versus one more bounded2fieldprivatecheck authorization, R1ownwordsnewattemptdecision, distinctoperation/datedwindow/personalgate. Stop for answers. No privatecheck/read, agentcommit/push/staging, newgate/journal/approval write, login/CLI/Terraform/AWS/livecall/reviewer/Phase13. G1/H1/retention/helperchoices historical evidence preserved; no answer inferred for newattempt.


## Subphase 12D — L1 finalparser check authorized and completed

Human answered yes to one incident-responder finala31852d4…savedstderr in-memory check, outputonlyaccepted/blockedcode; exactcontext in evidence/12d-billing-final-parser-check/user-authorization.json. Incident performedoneboundednofollowread/oneunstrippedabsencecall, no Policy/Execution/stage/otherprivate/livecalls. Resultacceptedtrue/blockedcodenull. Record safeproof; resume one-at-a-time humanrelease/gate decisions, no codechange or extra privatecheck/reviewer/agentcommit/login/retry. User phase-statusquestion answered during work without replacingobjective.


## Subphase 12D — fresh budget verification and frozen W3 publication

WORK ORDER: Continue human-authorized Option B fresh read-only verification and same-window frozen privacy scan/checked exact publication. Human personally saved gate; coordinator assembled public packet and five suffixes; human foreground runs production modes. No AWS mutation/new budget/apply/IAM/EMR/spending/cleanup/source-control action is included.

Packet: evidence/12d-publication-output-verify-billing-20261103-02/. Gate SHA256: 6e1e20c10049f6440f81d7aaccfb4e08600a3bd7d495027c7fa67b0af3062b84. Operation: verify-billing-20261103-02. Source: 1aa13d71489ebd605cee9b9931bf12de61c18bc3. Verification receipt SHA256: 42a74eee8a6202598b2175e67d8914d2cf4eeacefb000844e32f7df38438eb90. Delivery and Phase12D completion remain unverified/false. This suffix is published only after genuine zero-match same-window scan and verify-before, with verify-after proving exact final bytes.


## Subphase 12D — offline Spark readiness and same-JAR local proof

# Phase12D — offline Spark technical readiness

User work order: “alright let's move on” after explicit completion of commit/push4232ed12a7941c6c15d6f562f4f61fdd6928ebca and identification of offline EMR readiness as the next step. Branch phase-12. This is a coordinator transcription of bounded offline work, not a human live approval or a renewed billing gate.

Owners and allowed paths:
- spark-engineer /root/spark_12d_readiness: additive modules/spark readiness CLI/probe/comparator, synthetic G1 resources, module tests and README. Existing Phase6 pipeline/readers/export semantics and shared contracts remain unchanged. No child delegation.
- build-engineer /root/build_12d_readiness: JDK17 packaging, bounded local toolchain/classpath checks and final deterministic gate. Build source changes only if a demonstrated owned prerequisite is routed; no dependency-version changes are presumed. Do not run concurrent sbt processes. No child delegation.
- coordinator /root: this evidence directory, exact operational local input/config instantiation, existing CLI runs after packaging, evidence and final review handoff. Human records immutable; frozen billing packet and its existing exact record suffix history are preserved.

Acceptance targets:
1. Explicitly synthetic portable G1 A–J/w1…w9 inputs. Produce completed Hadoop and offline ER inputs through unchanged public pipeline entry points; never fabricate upstream completion markers or substitute historical real data. Retain source/config/hash/complete-run lineage and package/file inventory.
2. Rebuild current Spark job JAR using existing verified task. Audit found old generated2026-10-22 JAR stale and without Phase6Main.class; it must not be used. Run full Phase6 CLI baseline using actual assembled JAR, not loose project class directories. Bind artifact SHA and actual loaded driver/runtime libraries. Use identical assembled bytes for any later comparator/runtime.
3. Add bounded class-origin/shared-path probe which reports actually loaded Spark, scala-library, scala-reflect and scala3-library versions/origins on driver and task JVM. A local[*] task is one process and cannot pass a distributed-required gate. A local-cluster executor may demonstrate process separation locally, but cannot demonstrate multi-host EMR/YARN compatibility or shared mounts. No unsupported distributed claim.
4. Full28-table comparison from actual completed Parquet runs with exact runId/codeVersion/upstream manifest hashes/logical configuration, schema, row counts and content hashes; no silent context.runId normalization, table omission or part-file-name comparison. Same assembled JAR and copied immutable upstream manifests avoid historical class-directory fingerprint differences.
5. Document the common absolute POSIX mount needed by current NIO paths and Spark default-filesystem mapping. Actual remote/shared-filesystem proof remains a later deployment prerequisite. Do not change production path semantics to make the demonstration pass.
6. Meaningful module feature tests for rejection paths and actual bounded local probe/comparison. Build owner runs targeted gates and final source-frozen JDK17 sbt check, then packages/tests artifact as appropriate. Report failures/retries exactly. Do not claim anything unrun.

No AWS/account/CostExplorer/paid API, download of research data, private/recipient/state/plan/credential reads, Terraform plan/apply/destroy, IAM change, EMR resource, reviewer launch, commit/push or Phase13 work is authorized here. Public dependency/tool documentation may be read; prefer cached dependencies/offline sbt. Any missing tool/dependency is reported before changing external state.

Billing state carried forward: independent publication/candidate review APPROVE and exact105-file commit/push are complete. Budget configured/verified and actual98-file scan passed with zero matches; human later reported recipient “verified”. That is activation testimony, not a proven spending-alert delivery. Same-disk backup limit and F4 inventory/conservative allowance remain open. Proposed USD5 spike cap, USD10 remaining all-EMR reserve and USD5.09 margin are planning constraints, not spending permission. Separate non-root deployment identity, isolated genuine plan, independent elapsed-lifetime termination mechanism and personal cap/region/types/counts/runtime/teardown gate remain mandatory. Original verification window is not renewed and started operations are never replayed.

The prior publication review N1 (post-freeze runtime/source-control metadata archival) remains for the next separately authorized actual-recipient-scanned publication round. This offline readiness work does not retroactively scan that metadata or overwrite the98-file frozen packet. N2 older account-identifying path components remain a separate optional human decision; N3was satisfied by explicit inclusion of15ignored logs in4232ed1.

Stop at an independent read-only readiness review handoff after implementing and verifying this bounded local work. Do not chain into live EMR authoring/execution or infer full Phase12D/Phase12 completion.

## Owned integration repair and local scheduling clarification

The first full source-frozen check completed with1253current log-counted tests and one failure in the unchanged independent Spark source fence; the new probe used direct JavaRDD collect outside BoundedActions and option isEmpty tokens. The Spark owner may add a capped JavaRDD helper to owned BoundedActions while preserving existing methods, route the probe through cap1, change the master-option spelling and add bounded-cap/overflow feature tests. The independent guard and historical Phase6 algorithms remain unchanged. Run targeted module plus exact independent safety suite before the fresh full check; preserve the first full failure and distinguish old XML files from tests actually run.

The local machine's physical memory was read via /usr/sbin/sysctl -n hw.memsize as34359738368bytes (32GiB), with no source/data/config/credential reads. After repaired fast gates and a source freeze, packaging/runtime-classpath export may precede the full repository check to allow one bounded local[2] baseline process to overlap that check. The candidate JAR does not gain acceptance until the full final-source check succeeds. No concurrent sbt processes or source edits are allowed. At most one baseline, the full check and a small1executor probe may overlap; preserve each timeout/failure without substituting another source artifact under the same claimed evidence.


## Subphase 12D — independent offline readiness APPROVE recorded

Record the supplied independent offline-readiness APPROVE verdict verbatim and preserve its scope. Prepare the concrete source-control decision; no source-control or live action is authorized.


## Subphase 12D — public EMR design and complete cost proposal

# Phase12D — EMR design and public cost proposal

User authorized “Yeah, let's do it” in reply to preparing the EMR test design and cost proposal. Base2d637c6707ecc66a489561dd179406b6ac622e93, branch phase-12. This authorizes public documentation/pricing research and offline proposal assembly. It supplies no account access, private processing, deployment, security change, spend, source-control or new live window.

Preserve the reviewed six Spark files, packaged JAR/baseline lineage, prior budget packet, historical proposal, all existing Terraform/application/build sources and human decisions. Do not flip old preparation-time flags. No login, AWS account/API/paid Cost Explorer request, credential/state/plan/recipient read, Terraform init/plan/apply/destroy, infrastructure resource authoring, deployment, reviewer launch, cleanup, commit/push or Phase13 is part of this work.

Routing per AGENTS.md/docs/agents.md: infra-engineer /root/infra_12d_emr_design owns its new public scratch design/research/report only at /tmp/scholarchain-phase12d-emr-design-infra-20261103. It must not edit canonical sources or delegate. Coordinator /root owns public pricing research/calculation/evidence in this directory and append-only phase records plus a human-launched independent proposal review handoff. No reviewer is launched by the implementation agents.

Retain prior proposed choices: EMR on EC2, exactly one primary and one core m5.xlarge in us-east-2, no task/Spot nodes, one attempt, at most two hours total including startup/retries/termination. The proposed USD5 allocation is contained within the existing USD15 all-EMR reserve/shared USD200 ceiling; USD10 remains for later EMR if that allocation is spent. None is a current remaining-balance observation or spending approval.

Deliver a concrete, source-cited design: current EMR/Java17/YARN candidate and separate Spark3.5.4/Scala2.13 strategy; same-JAR/full28-table comparison; real common absolute POSIX storage; private network and artifact egress; encryption/TLS and separated deployment/service/node/watchdog IAM roles; elapsed-lifetime watchdog armed independently of the terminal before cluster creation; staged isolated Terraform authoring/review and teardown inventory dependencies.

Public prices must carry exact source URL, retrieval time, raw/decoded hashes and selected SKU/range/region/unit where available. Separate observed published rates, proposed bounded quantities, arithmetic and unresolved account facts. Include EC2+EMR, root/data EBS, shared filesystem/storage/throughput, NAT/publicIPv4 or endpoints/data, S3 requests/retention, KMS/key retention, deadline controller, logs/metrics, transfer, taxes and uncertainty. No free-tier/credits/monthly-reset inference. A conditional modeled fit cannot establish account funds, exact plan cost, region/quota/capacity or technical compatibility. If bounds remain unknown or exceed the allowance, fail the launch recommendation without silently widening scope.

Stop at an independently reviewable design/cost proposal and the next bounded work order. No live action follows automatically. Document-only work does not require another full source build; validate arithmetic/provenance/preservation and report unrun gates honestly.


## Subphase 12D — EMR cost scenario L1 wording repair

User returned REQUEST-CHANGES for one L1 wording defect. Apply the reviewer’s offered relabeling option: ancillary resources active 24 h total (21 h beyond nominal), USD7.52. Keep model quantities/arithmetic, all launch flags and live gates unchanged. Refresh evidence and return a narrow recheck prompt in chat only.
