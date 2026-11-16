# ScholarChain demonstration video script

**Status: DRAFT, not approved.** Drafted 2026-11-15 by the documentation-engineer for the human's review. No command below was replayed while writing this draft. Commands marked "(rehearse)" must be run once offline, or in the stage where they are recorded, before you record. The live items depend on Session 2, planned in [session-2-plan.md](runbooks/session-2-plan.md), which is also a draft.

Amended 2026-11-16 (P34 impossible, then option (i) in the plan, section 6.4): Neptune runs at min 1 / max 2.5 NCU with a 5.8 h hard stop (this script said "Neptune capped at 1 NCU"), and R-c is dropped, so the "With R-c" column in section 4 is a record only. Item rows 11 and 14-16 in section 1 said "live with R-c"; they now read "Session 1 result only; R-c dropped". Amended 2026-11-16 (L dropped on EMR): items 9 and 10 show S on EMR plus the measured L local evidence, replacing "two real DBLP sizes on the same cluster".

**Target length:** 10 to 15 minutes. This script totals **14 min 15 s** (section 2).
**Recording rule from the course:** the demonstration must show every item "without relying only on prerecorded screenshots". Every item below is a screen recording of a real command, console page or file being opened, never a still image. Live items are recorded while the AWS stack exists; they cannot be re-shot after cleanup.
**Privacy rule:** never show an account ID, a bucket name (bucket names contain the account ID), the API domain, a key, a secret or an e-mail address. Blur the console header and any ARN. Put the API key in a temporary header file, as in the runbook's smoke steps; never type it on the command line. The Session 1 video showed the account ID in two ARN lines, so do not reuse that footage.

---

## 1. Item list and how it matches the course

**Source:** course README, section "Demonstration requirements", https://raw.githubusercontent.com/0x1DOCD00D/ScholarChain/main/README.md, read 2026-11-15T16:51:58Z. The course lists **22 numbered items**. This script uses the course's numbering and wording.

**Mismatch to note:** the Phase 17 plan (section 7.2, "Demonstration script (20 items from the course)") lists 20 items. Its list ends at "scale-out and scale-in evidence" and leaves out course item 21 ("One failure and recovery example") and item 22 ("Cleanup or resource inventory evidence"). The course README is authoritative, and the human's count of 22 agrees with it.

The course also requires, in its hooks section, "at least three safe probes showing that the guard blocks prohibited commands". Item 4 therefore shows three probes.

**The human's offline/live split, checked:**

- Offline: items 1-8, 17 and 22. Live: items 9-16 and 18-21.
- This matches the course list, with three nuances:
  - **Items 9 and 10** are produced in **stage a** (EMR), not stage c. Record them while the EMR run happens. Stage c can only show the terminated cluster's Steps page and the copied-out files.
  - **Item 16** is live (an answer's claim verdicts) plus an **offline** unit-test clip for "one unsupported claim test".
  - **Item 22** is recorded after cleanup (stage d and the next day). The inventory files are offline. The empty console pages are a live, read-only check of AWS after the destroy.

| # | Course item (verbatim) | Offline or live | Produced in | Seconds | Running total |
|---|---|---|---|---:|---:|
| - | Opening | offline | any time | 15 | 0:15 |
| 1 | Private repository structure. | offline | before freeze | 20 | 0:35 |
| 2 | Agent ownership map. | offline | before freeze | 25 | 1:00 |
| 3 | At least one agent role file. | offline | before freeze | 20 | 1:20 |
| 4 | A dangerous-command hook safely blocking a probe. | offline | before freeze | 45 | 2:05 |
| 5 | A test-stop hook or equivalent deterministic gate. | offline | before freeze | 30 | 2:35 |
| 6 | A phase report and repair record. | offline | before freeze | 30 | 3:05 |
| 7 | A clean `sbt check` result. | offline | before freeze | 35 | 3:40 |
| 8 | A dataset manifest and actual source samples. | offline | before freeze | 30 | 4:10 |
| 9 | Hadoop job execution evidence and counters. | live (S on EMR) + L local evidence | **stage a** + P6 local | 45 | 4:55 |
| 10 | Spark job execution evidence and graph outputs. | live (S on EMR) + L local evidence (ER bypassed, disclosed) | **stage a** + P6 local | 45 | 5:40 |
| 11 | Neptune graph query. | **Session 1 result only; R-c dropped** | Session 1 | 35 | 6:15 |
| 12 | DynamoDB run or query record. | live | stage a (ingest run-ledger record) | 25 | 6:40 |
| 13 | S3 Vectors query returning source pointers. | live | stage a (query smoke on about 10,000 vectors) | 35 | 7:15 |
| 14 | A complete user query through the API. | **Session 1 result only; R-c dropped** (plus the local fixture run) | Session 1 + local fixture | 45 | 8:00 |
| 15 | Evidence and explain endpoints for the answer. | **Session 1 result only; R-c dropped** | Session 1 | 40 | 8:40 |
| 16 | Claim verification behavior, including one unsupported claim test. | **Session 1 result only; R-c dropped** + offline test clip | Session 1 + offline | 45 | 9:25 |
| 17 | Reproduction scripts, agent replay instructions, and a clean-checkout bounded run. | offline | after Phase 17A README | 45 | 10:10 |
| 18 | Terraform plan or deployed-resource evidence. | live | stage a and the R-b window | 30 | 10:40 |
| 19 | CloudWatch elasticity dashboard. | live | R-b window | 35 | 11:15 |
| 20 | Scale-out and scale-in evidence. | live | R-b window | 55 | 12:10 |
| 21 | One failure and recovery example. | live (stop one query-api task, P11) | R-b window | 50 | 13:00 |
| 22 | Cleanup or resource inventory evidence. | offline (+ live read-only console after the destroy) | stage d / next day | 35 | 13:35 |
| - | Closing: costs and disclosures | offline | after the C11-style check | 40 | **14:15** |

Edit the clips into this course order. Recording order under plan R0 + R-b: items 9, 10, 12, 13 and 18 in stage a; items 18-21 in the R-b window; item 22 after the destroy; items 11 and 14-16 from Session 1 evidence (section 4); the rest offline.

---

## 2. Per-item script

Terminal setup for every offline clip: the runbook's "T1 setup" block (JDK 17, `cd` to the repository). For live clips, the stage's own setup (runbook B8.0 or B10.1). `<domain>`, `<run-prefix>`, `<run-id>` and the other angle-bracket names are placeholders: fill them in the terminal only, never in a file.

### Opening (15 s, 0:15)
- **Show:** the repository README title in the editor.
- **Say:** "This is ScholarChain. It turns DBLP and linked open scholarly data into a researcher collaboration graph with Hadoop and Spark, stores it in Neptune, DynamoDB, S3 and S3 Vectors on AWS, and answers questions with evidence that every claim is checked against."

### 1. Private repository structure (20 s, 0:35), offline
- **Show:** the GitHub repository page with its **Private** label. Then in the terminal: `git ls-files | cut -d/ -f1 | sort | uniq -c` and `ls modules`.
- **Say:** "Core holds the shared contracts. Hadoop prepares the data, entity resolution decides identities, Spark builds the graph, storage adapts the AWS stores, rag retrieves and verifies, and services expose the API. Dependencies point toward core."

### 2. Agent ownership map (25 s, 1:00), offline
- **Show:** `sed -n '1,30p' docs/agents.md` (the artifact ownership table).
- **Say:** "Every class of file has exactly one writer. Reviewers report findings but never edit. I, the human, own the phase gates and ratification."

### 3. Agent role file (20 s, 1:20), offline
- **Show:** `sed -n '1,40p' .claude/agents/hadoop-engineer.md`
- **Say:** "A role file states the agent's territory, what it must decline, its ordered procedure and its report fields."

### 4. Dangerous-command hook blocking probes (45 s, 2:05), offline
- **Show (three safe probes; the hook only reads the JSON and never runs the command):**
  ```
  printf '%s' '{"tool_name":"Bash","tool_input":{"command":"echo terraform destroy"}}' | .claude/hooks/guard-dangerous.sh; echo "exit=$?"
  printf '%s' '{"tool_name":"Bash","tool_input":{"command":"aws s3 rm --recursive s3://example-bucket/x"}}' | .claude/hooks/guard-dangerous.sh; echo "exit=$?"
  printf '%s' '{"tool_name":"Bash","tool_input":{"command":"aws emr terminate-clusters --cluster-ids j-EXAMPLE"}}' | .claude/hooks/guard-dangerous.sh; echo "exit=$?"
  ```
  Expected (derived from the hook source, rehearse): `Blocked: terraform apply or destroy…`, `Blocked: recursive S3 deletion…` and `Blocked: destructive AWS operation…`, each followed by `exit=2`.
  Then a short clip in a fresh Claude Code session of probe 3 in `.claude/PROBES.md`: the guard rejects a proposed `echo 'terraform destroy'` Bash call.
- **Say:** "The hook is executable policy. It blocks Terraform destroy, recursive S3 deletion and EMR termination before anything runs. In Codex and Cursor this hook does not run, so there the same rules are enforced by process and review."

### 5. Test-stop hook or deterministic gate (30 s, 2:35), offline
- **Show:** in a Claude Code session, probe 5 of `.claude/PROBES.md`: change a harmless Scala file, try to finish, and the Stop hook refuses until `sbt check` refreshes `.claude/.last-test-run`. Alternatively, `scripts/check.sh` ending in `RESULT: PASS gates=7` (rehearse).
- **Say:** "An agent cannot claim it is done after a source change unless the tests ran and passed."

### 6. Phase report and repair record (30 s, 3:05), offline
- **Show:** `sed -n '1,25p' docs/agent-runs/phase-14/owner-report.md`, `sed -n '1,25p' docs/agent-runs/phase-14/repairs.md` and `git log --oneline | grep -i 'live repair' | head -11`.
- **Say:** "Each phase has a prompt, an owner report, a test report, an independent review and my gate. Live failures in Session 1 became numbered repairs, each with tests and a commit I approved."

### 7. Clean `sbt check` (35 s, 3:40), offline
- **Show:** the JDK 17 setup, then `sbt -batch check`. Show the start, cut the middle (the run takes about 7 minutes or more) and show the final summary with the test counts and exit 0. Say on camera that the cut was made.
- **Say:** "This is the repository's definition of done: formatting, compilation and every module's tests."

### 8. Dataset manifest and actual source samples (30 s, 4:10), offline
- **Show:** `sed -n '1,40p' datasets/dataset-manifest.yaml`, then `head -c 800 datasets/samples/dblp/linked-records.xml`, then `(cd datasets/samples && shasum -a 256 -c SHA256SUMS)` (rehearse: check the path format in `SHA256SUMS`).
- **Say:** "Every source has a snapshot, a retrieval date, a license and checksums. The DBLP input is a bounded slice of about 10,577 papers, not the full dump."

### 9. Hadoop execution evidence and counters (45 s, 4:55), live, stage a
- **Show (record during the stage-a EMR run):**
  - The `run-experiment.sh … --execute` output, with the `hadoop-prep` step completing.
  - The EMR console **Steps** tab of the cluster (header blurred).
  - After copy-out, the Hadoop counters and rejects files from the downloaded `hadoop/` part, for example `ls <download>/hadoop/` and `python3 -I -m json.tool <download>/hadoop/<run>/counters.json | head -40` (rehearse: confirm the file names with the P6 dry run).
- **Also show (local evidence, labelled "local P6 run, 2026-11-16"):** the L Hadoop pass from the P6 logs: 132 s, 210 works dropped by the team limit, maximum team 79.
- **Say:** "Hadoop MapReduce parses and normalises the records on the EMR cluster. On EMR we ran S, 10,577 real DBLP works. The counters show records in, records out and rejects, the rejects are kept, and here are the step times. The larger size, about 50,000 works, was dropped on EMR: locally its Hadoop step passes in 132 seconds, but entity resolution ran out of memory at 22 GB, so we show L from the local run only." (Replaces "We ran two real DBLP sizes on the same cluster"; L is dropped on EMR, plan section 5.2.)

### 10. Spark execution evidence and graph outputs (45 s, 5:40), live, stage a
- **Show:**
  - The `spark-class-origin` and `spark-job` steps completing (S on EMR).
  - Local L next to S, labelled on screen "ER bypassed: identity pass-through, local only, not the EMR path": L Spark 1,110 s, 48,188 works, 76,623 researchers, 320,690 all-years edges, against S 460 s, 10,578 works, 21,819 researchers, 81,181 edges with the same bypass (`target/phase15/lanes/l-bypass-progress.md`; evidence `target/phase15/p6/l-bypass/`, including its `ER-BYPASSED.txt` files).
  - Then in the downloaded `spark/run:<id>/`: `ls` (nodes, edges, metrics, path-evidence, `neptune-opencypher-csv`, `_SCHOLARCHAIN_SPARK_COMPLETE`) and `python3 -I -m json.tool analytics-report.json | head -40`.
- **Say:** "Spark builds the temporal weighted coauthorship graph and computes components, communities, bridges, k-core and paths in a distributed way, never by collecting the graph to one machine."

### 11. Neptune graph query (35 s, 6:15), Session 1 evidence under plan R-b (live only if the graph is loaded)
- **Show:**
  - With the tunnel up (runbook B7), the reader role queries Neptune:
    ```
    aws neptunedata execute-open-cypher-query --endpoint-url "https://$WRITER:8182" --open-cypher-query 'MATCH (r)-[e]-(c) WHERE id(r) = "<researcher-id>" AND type(e) = "coauthored_with" RETURN id(c) LIMIT 5' --profile scholarchain-reader --region us-east-2
    ```
  - (rehearse: confirm the label and property names against the sidecar CSV headers.) Never echo `$WRITER`.
- **Say:** "The graph lives in Neptune. This query returns five direct coauthors of one canonical researcher."

### 12. DynamoDB run or query record (25 s, 6:40), live, stage a
- **Show:** the DynamoDB console (reader role, header blurred): the run-ledger table, then **Explore items**, then the record of the stage-b load run, whose run id links back to the stage-a EMR run. Or `aws dynamodb query` with the reader profile, using the key names given in `modules/storage/README.md`.
- **Say:** "DynamoDB holds the run ledger, caches and query sessions, so every load and answer has a provenance record."

### 13. S3 Vectors query returning source pointers (35 s, 7:15), live, stage a
- **Show:** one query of the runbook's B8.7 smoke (`LiveEmbeddingSmokeMain`, with a query cap of 1), then the report's source pointers: `python3 -I -m json.tool target/session2/evidence/c/query-report.json | head -40`. This makes one Voyage embedding call, inside the free allowance.
- **Say:** "About `<N>` vectors were embedded with Voyage voyage-4-lite at 256 dimensions from the Spark semantic summaries of the real slice. S3 Vectors returns the nearest items, each with a pointer back to its source text." Use the real ingested count from the ingest report, never a target.

### 14. Complete user query through the API (45 s, 8:00), Session 1 evidence under plan R-b (see section 4)
- **Show:** first one warm-up query (Session 1: the first query after idle could return 504). Then:
  ```
  python3 -I load-tests/llm_budget.py reserve --bucket <approved bucket> --answers 2
  H="$(mktemp)"; printf 'Authorization: Bearer %s\n' "$SCHOLARCHAIN_SMOKE_API_KEY" > "$H"
  curl -sS -H @"$H" -H 'Content-Type: application/json' -H 'Idempotency-Key: demo-14-1' -X POST "https://api.<domain>/v1/query" -d @<question file> | python3 -I -m json.tool
  ```
  Use a question that answered in 16B (component or ranking), or a coauthor question once P3 is fixed.
- **Say:** "One HTTPS call: the planner resolves the researcher, retrieves graph and semantic evidence, and the model writes claims that cite evidence IDs."

### 15. Evidence and explain endpoints (40 s, 8:40), Session 1 evidence under plan R-b (see section 4)
- **Show:**
  ```
  curl -sS -H @"$H" "https://api.<domain>/v1/evidence/<evidenceId from item 14>" | python3 -I -m json.tool | head -40
  curl -sS -H @"$H" "https://api.<domain>/v1/explain/<queryId from item 14>" | python3 -I -m json.tool | head -40
  rm -f "$H"
  ```
  Route names are from `modules/services/README.md`; rehearse them.
- **Say:** "Every cited ID resolves to stored evidence. Explain shows the stages, prompt and model versions and the verifier's verdicts, not hidden model reasoning."

### 16. Claim verification, including one unsupported claim test (45 s, 9:25), live + offline clip
- **Show (live):** in the item 15 explain output, the claim counts (attempted, verified, rejected).
- **Show (offline clip):** the rag test that feeds the verifier an unsupported claim and sees it rejected, run with `sbt -batch "rag / testOnly <verifier spec>"` (rehearse: fill in the exact spec name from `modules/rag/src/test`).
- **Say:** "The verifier checks every claim against the evidence. A claim with no supporting evidence is rejected, and the system abstains instead of guessing."

### 17. Reproduction scripts, agent replay instructions, clean-checkout bounded run (45 s, 10:10), offline
- **Show:**
  - The README section "Reproducing the agentic workflow" (a Phase 17A deliverable that does not exist yet).
  - Then a fresh clone in a new directory, and the bounded local run chosen in Phase 17A (for example `scripts/smoke-local.sh --build`, which starts the real query-api offline and runs the smoke checks; rehearse).
- **Say:** "A grader can replay one bounded phase and the test gates without rebuilding the cloud."

### 18. Terraform plan or deployed-resource evidence (30 s, 10:40), live, stage a and R-b window
- **Show:**
  - The ECS console with the four services running and the ALB target healthy (header blurred).
  - The plan log's action list, `grep '^PLAN-ACTION:' <stage-b runtime-plan.log> | head -20`.
- **Say:** "Everything on AWS was created by Terraform from reviewed plans, each applied only after my approval record."

### 19. CloudWatch elasticity dashboard (35 s, 11:15), live, R-b window
- **Show:** CloudWatch, then **Dashboards**, then `scholarchain-course-elasticity`, with the time range set to the elasticity run.
- **Say:** "The dashboard shows load balancer requests and latency percentiles, healthy query-api tasks and CPU on one synchronized time axis."

### 20. Scale-out and scale-in evidence (55 s, 12:10), live, R-b window
- **Show:**
  - The dashboard's healthy-host and CPU panels going from 1 task to 2 and back to 1.
  - The poll log lines with UTC times, for example `grep -E ' [12] [12] ' <poll log> | head`.
  - The scaling activities: `aws application-autoscaling describe-scaling-activities --service-namespace ecs --resource-id service/scholarchain-course/query-api --region us-east-2 --profile "$ADMIN" --query 'ScalingActivities[].[StartTime,Description]' --output text`.
  - `python3 -I load-tests/loadgen.py summarize <run dir>`.
- **Say:** "Under 50 concurrent users CPU passed the 60 percent target and ECS added a task. After about 15 quiet minutes and a 5-minute cooldown it scaled back in." If no scale-out happened, say so and show the CPU values; that is the honest result.

### 21. One failure and recovery example (50 s, 13:00), live, R-b window
- **Show:** the scenario chosen in session-2-plan P11. For "stop one query-api task" (needs the approved permission):
  1. The service events.
  2. The task replacement.
  3. Smoke `healthz` and `readyz` recovering.
  4. Timestamps from the failure-run record.
- **Say:** what failed, what detected it, how long recovery took, and that nothing was edited by hand.

### 22. Cleanup or resource inventory evidence (35 s, 13:35), offline after stage d
- **Show:**
  - The final `RESULT:` line of destroy pass 2.
  - `wc -l` of the before-cleanup and after-cleanup inventory files.
  - The after-cleanup inventory listing only expected leftovers.
  - Then, read-only, in a private window, as the IAM user: the console pages with no NAT gateway, load balancer, Neptune cluster, running EMR cluster or EFS in us-east-2.
- **Say:** "Everything was destroyed in two passes after the evidence was archived. Both provider keys were revoked."

### Closing (40 s, 14:15)
- **Show:** the cost report from runbook step C11b (AWS, Anthropic, Voyage and the combined total).
- **Say:** the oral points in section 3, briefly.

---

## 3. Things you must explain orally

- **Tool-policy disclosure:**
  - The course describes a Claude Code orchestrator; the main workflow used Codex and Cursor, with Claude Code for compatibility.
  - The instructor's 2026-09-29 chat reply allowed Claude, Codex and Cursor. It did not address the orchestrator and hook enforcement model, so do not claim more than it says.
  - The `.claude/` hooks run only in Claude Code. In Codex and Cursor the same rules were followed by process and human review.
- **Provider deviation:**
  - AWS Bedrock quotas were 0, so on 2026-11-09 the instructor approved the Anthropic API (`claude-haiku-5-5`) for answers and Voyage AI (`voyage-4-lite`, 256 dimensions) for embeddings.
  - Question text, evidence snippets and document text leave AWS.
  - The Anthropic path cannot use temperature 0, so repeated answers can vary.
- **Session 1 outcomes (say them plainly):**
  - EMR was PARTIAL: cluster, permissions, step submission and stage-in were proven, but hadoop-prep failed because a config file was never uploaded.
  - The 15B elasticity experiments were dropped for budget.
  - In 16B, 40 questions were asked: component 7/8, ranking 7/8, direct coauthors 0/14 (context budget), path 0/10 (cause not diagnosed during the session; the offline diagnosis and fix are Session 2 prerequisite P4; report what P4 actually found).
  - The first video was 63 s and exposed the account ID; this video replaces it.
- **What Session 2 changed:** the repairs P1-P14 in the Session 2 plan, each tested and reviewed before going live.
- **Cost:**
  - The project ceiling is USD 25 across AWS, Anthropic and Voyage together, tax included. AWS budget alerts at 18, 20 and 22 are e-mails only, so our own caps did the protecting.
  - Give each bill separately, then the total. The final AWS figure comes from the bill, not the model.
- **Dataset limitations:**
  - A bounded DBLP slice (dblp-2026-10-03, about 10,577 papers).
  - The OpenAlex, Crossref and ORCID inputs are small committed samples and were not scaled with the DBLP subsets.
  - Ranking questions rank only the researchers included in the runtime artifact, not the whole corpus.
- **Identity resolution:** say which ER mode produced the loaded graph (session-2-plan P10). The Session 1 graph came from the ER-disabled run.
- **Elasticity limits:**
  - HTTP services scale between 1 and 2 tasks.
  - Container Insights was off for cost, so task counts come from ALB healthy hosts and a once-a-minute poll.
  - The embedding worker stayed at one task.
- **Schedule deviations:** Phase 12 Terraform was written in parallel with Phase 7, and the Phase 6 EMR gate and the Phase 7/8 live gates ran in Phases 14-15 (Phase 17 plan, section 2).
- **Offline versus live:** which clips were recorded live and which come from archived evidence; the stack was destroyed before the video was edited.
- **Agent-generated code:** be ready to explain any file the instructor picks: why Hadoop and then Spark, how each metric is defined, how ER decides, how the verifier works, what each store is for, and what scaled and why.

---

## 4. What is live under the approved Session 2 plan (R0 + R-b; R-c dropped 2026-11-16) and what comes from Session 1

[session-2-plan.md](runbooks/session-2-plan.md), sections 5 and 6: firm USD 25, floor 2 (project at most 23.00; option (i), 2026-11-16). One day, in this order:

- **Stage a:** EMR at S, about 10.5k works (L, about 50k, dropped on EMR 2026-11-16 and shown from local evidence); about 10,000 voyage-4-lite vectors with a live retrieval smoke.
- **R-b (gate 1 and the pre-R-b check):** elasticity on the production runtime with an **empty** graph and Neptune at min 1 / max 2.5 NCU, with a 5.8 h hard stop on the Neptune window (record items 18-21 early in that window). The load is semantic retrieval through `POST /v1/semantic/retrieve`; scaling is ALB request count per target, plus CPU.
- **R-c: dropped** (plan option (i), 2026-11-16). Formerly optional behind gate 2: graph load and the 24-question rerun. Items 11, 14, 15 and 16 therefore come from Session 1 evidence (and the offline test for 16).

Items that cannot be recorded live are shown from real Session 1 evidence, opened on screen as files and logs (not still images). **Say on camera** which session each clip is from and that the stack was destroyed afterwards.

| # | R0 + R-b | With R-c (dropped; record only) | Fallback evidence if not live |
|---|---|---|---|
| 9, 10 | **live** (stage a, S on EMR) + L local evidence (ER bypassed at L, disclosed) | same | — |
| 11 Neptune query | Session 1 | **live** (reader role through the tunnel, on the S graph) | `target/phase14/evidence/14b/tunnel-test.log`; `14c-results.txt` (`graphState=LOAD_COMPLETED`, 78,104 nodes, 328,967 edges) |
| 12 DynamoDB record | **live** (stage a ingest run-ledger record) | also the cache-load run record | Session 1: 166,088 cache writes |
| 13 S3 Vectors query | **live** (stage a query smoke; also the R-b semantic route) | same | `target/phase14/evidence/14c/query-report.json` |
| 14, 15 API query, evidence, explain | Session 1 + local fixture | **live** (one of the 24 rerun answers: query, `/v1/evidence/{id}`, `/v1/explain/{queryId}`) | `query-response-r8a.json`, `query-explain-r8a.json`, `final-smoke.log`; optional `scripts/smoke-local.sh` labelled "fixture data" |
| 16 Claim verification | Session 1 + offline test | **live** explain verdicts + offline test | `query-explain-r8a.json` |
| 18 Terraform or resources | **live** | same | — |
| 19, 20 Dashboard, scale-out and scale-in | **live** (R-b) | same | Without R-b none exists; say so |
| 21 Failure and recovery | **live** (stop one query-api task) | same | Session 1's tunnel-drop recovery (`--graph-only` rerun) and EMR bootstrap-race recovery, with timestamps |
| 22 Cleanup and inventory | **live** (read-only console after the destroy, including no deployer role, P39) + inventory files | same | Session 1 `cleanup-evidence/after-inventory.txt` |

**Items 19 and 20, what to say:** "The load was semantic search: each request looks up the embedding for one of a fixed set of real topic questions (cached after its first use) and queries about 10,000 real vectors in S3 Vectors. Query-api scaled on requests per task, with CPU as a second signal. The graph was empty during this run, so this measures the retrieval tier, not graph or LLM work."

The running time stays about 14 minutes. Replace the "Say" lines for Session 1 items with the provenance sentence above.
