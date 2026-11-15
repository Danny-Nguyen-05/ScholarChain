# Phase 14 repairs

## Subphase 14A — repair round 1 (from review 1, REQUEST-CHANGES)

Source: the user-supplied external review in `review.md` (Subphase 14A, review 1). Severity, owner and acceptance checks are kept as the reviewer gave them.

| ID | Severity / blocking | Owner | Paths named by the reviewer | Acceptance check (reviewer) | Repair status |
|---|---|---|---|---|---|
| F1 | High / yes | coordinator (request); human (path); service-engineer + infra-engineer (code, as the human decides) | `approval-request-14a.md:84,89`, §1; `modules/runtime/compute.tf:58,94-96,124-127`; `ServiceMains.scala:42-44`; `phase12b-variables.tf:158-161`; `phase12b.tf:42` | A §1 row "Live service composition" marked M, with evidence and owner. Steps 8 and 10 corrected. The request never tells the human to set `runtime_composition_verified=true` before the composition is replaced and tested. `prompt.md` records the human's decision. | fixed offline (repair round 1) |
| F2 | Medium / yes | infra-engineer; test-engineer if the guard changes | `deployer/phase14_main.tf:125-139,158-166,298-361`; `deployer/README.md:108-109` | Either narrow the statements (key administration in the key policy naming the deployer role, with a negative test that a foreign tagged key or security group gains no mutation rights), or rewrite the honest-list rows exactly, pin the reachable set with a test and record a new human acceptance. | fixed (narrowed) |
| F3 | Low / no | coordinator | `approval-request-14a.md:99,105,106` | Record-template lines carry no trailing `# …` comments. | fixed |
| F4 | Low / no | coordinator | `approval-request-14a.md:159,166` | The Haiku line is no longer marked unpriced; the authored maxima include metrics (about 0.773/h, USD 18.55/day). | fixed (0.7726/h, USD 18.54/day; Haiku 4.5 reserve stated as a cap) |
| F5 | Low / no | infra-engineer | `deployer-apply-proposal.md` | A rule: on `LimitExceeded`, re-plan, expect only the remaining creates, re-apply. | fixed (proposal and deployer README) |
| F6 | Observation / no | — | runtime boundary `GetSecretValue` on `secret:*` | Note only; a possible later tightening is `secret:scholarchain-course-*` plus that naming for human-created secrets. | noted |

### User decision for repair round 1 (2026-11-07)

The user said: "fix all blocking bugs for me". The coordinator recorded it as follows:
- **F1:** option (1), a live-composition work order before the 14A commit:
  - `service-engineer` for the service code;
  - `infra-engineer` for the task environment, including passing the synthesis inference-profile ID as the model ID.
- **F2:** the reviewer's recommended narrowing:
  - key administration moves into the key policy, which names the deployer role;
  - adopted-group mutation reach is removed.

### Repair evidence (round 1)

Agent-reported results are in `owner-report.md`, "Repair round 1". The coordinator's own results are in `test-report.md`, "Repair round 1".

- **F1:**
  - `modules/services`: AwsConfig, AwsPorts, AwsComposition, ReadinessGate and LiveAdapters, with 5 new specs plus LiveGraphSnapshotSpec;
  - `modules/storage`: `NeptuneGraphReader.connect`, `DirectedGraphReader` and DirectedGraphReaderSpec;
  - `modules/runtime/compute.tf` and its variables and outputs: the per-role aws environment, gated by `runtime_composition_verified`;
  - `modules/identity/main.tf`: `ReservationInQuerySessionTableAndIndex`, `ListRagBucketPrefixes` and `HeadAbsentRagKeyAs404NotListing`;
  - approval request rows 17 and 18 and steps 8 and 10.
- **F2:**
  - `deployer/phase14_main.tf`: 5 statements removed;
  - `modules/identity/main.tf`: a 5-statement key policy;
  - `modules/network/main.tf`: `aws_default_security_group` removed;
  - D6 exception removed from `scripts/phase12d-spike/tests/test_terraform_static.py`;
  - new negative tests in the deployer and root suites and in `tests/infra` (`Phase14F2InMemory`);
  - evidence in `evidence/14a/r1/`.
- **F3 and F4:** `approval-request-14a.md` Sections 4 and 5.
- **F5:** `evidence/14a/deployer-apply-proposal.md` and the deployer README.
- **Also routed:** test-engineer updated 5 stale `tests/infra` tests.

## Subphase 14A — review 2 (repair round 1 recheck): APPROVE

These are nonblocking findings from `review.md`, review 2.

| ID | Severity | Owner | Status |
|---|---|---|---|
| N1 | Low | coordinator | fixed (docs only): the passing-snapshot line in approval-request-14a.md §7 now names `c4dbd00` and `evidence/14a/gates/check-full-r1.txt` |
| N2 | Low | coordinator + deploy-engineer | carried to 14B Step 0: before runtime-apply, the 14B record states the expected 14B smoke result. A no-data `smoke-query` stop is not a rollback trigger. |
| N3 | Low | infra-engineer (only through a routed repair and a recheck) | carried as a 14B watch item: no `health_check_grace_period_seconds`, and query-api readiness waits for both peer services |
| N4 | Observation | infra-engineer | carried: stale wording at compute.tf:105, phase12b.tf:43 and phase12b-variables.tf:161, to fix the next time these files are touched |

## Subphase 14B — review 1 (Step 0 and the Q6 repair): REQUEST-CHANGES

From `review.md`, "Subphase 14B", review 1. The user said: "fix all blocking bugs" (2026-11-07).

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| B1 | Medium | yes | infra-engineer, then test-engineer | routed in repair round 1, option (a): grace default 300 s, a validated root variable, explicit target-group thresholds from configuration, threshold arithmetic in the README; tests updated and mutations repeated |
| N1 | Medium | no (before the base-apply record) | coordinator records; user decides | arithmetic recorded in `prompt.md`; the date choice (Nov 11 with a named reserve cut, or Nov 15) is the user's, still open |
| N2 | Medium | no (start condition; before the commit and base-apply) | user decides; infra-engineer only on explicit instruction | dated 14B addendum to `approval-request-14a.md`; the certificate source is the user's decision, still open |
| N3 | Low | no | coordinator | fixed: the deployer-apply dates in `prompt.md` |
| N4 | Low | no | coordinator | fixed: snapshot identity counts and infra-engineer mutation results retained as evidence files |
| N5 | Observation | no | infra-engineer | carried: stale text at `phase12b.tf:43` and `phase12b-variables.tf:161` |
| /healthz vs /readyz | note | no | — | no change, per the reviewer; risk on record: a peer failure replaces query-api tasks that a restart cannot fix |

## Subphase 14B — review 2 (repair round 1 recheck and replan): REQUEST-CHANGES

Source: the reviewer's verdict and follow-up, both appended verbatim to `review.md`. The user's decisions and answers are in `prompt.md`, "Subphase 14B — repair round 2".

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| B2 | Medium | yes | infra-engineer (`scripts/config/release.conf`, `scripts/deploy.sh`, `scripts/lib/verify.py`, `scripts/README.md`); test-engineer (cleanup-prepare tests); documentation-engineer (runbook C2); coordinator (approval request §4, §7) | routed in repair round 2: cleanup-prepare has no headroom floor (user answer: yes); runbook done |
| N1 | Medium | no (decide before the approval record) | user decides; coordinator writes | user: tax counts, assume 11% (Chicago); done in approval request §3.2. The USD 3 floor fails at 42 h (1.37); options listed for the user; no cap changed |
| N2 | Low | no | coordinator | done: `review.md:378` plan path replaced by `<plan path>`, noted as the only change to verbatim text. Lines 136 and 263, in the committed 14A reviews, still hold the path; this is the user's decision |
| N3 | Low | no | owners | deferred by user decision 1: fixed after the recheck approves and before the pin refresh, together with the four tracked files |
| N4 | Low | no | coordinator | done: approval request §3.4 reworded. The 0.30 is fully allocated, there is no reserve and no service-side Titan cap; the user must accept this or set a reserve |
| N5 | Low | no | coordinator | done: approval request §5 billing row reworded (new and changed files hold no raw account ID; the pre-existing executor literal at `budget_execution.py:26` stays under decision 3 and is used by the modify path) |
| N6 | Low | no | coordinator | done: deploy-engineer provenance recorded in `owner-report.md` |
| N7 | Observation | no | infra-engineer (future 14C scope) | carried: `upload-slice.sh --execute` has no machine-checked approval record |
| N8 | Observation | no | coordinator after the commit | carried: confirm the committed Spark exporter matches `codeVersion b6d030eb`. Note: the plan figures "≈170 answers" and "≈19.60" differ from the repository's (about 130 at 0.01155; 19.44); the plan file is the user's |
| Exception gaps (follow-up) | — | no | test-engineer | done: named entry `aws-documentation-example-account` (exact value, exact path, no pattern); tests (i)–(v); mutations caught |
| Whitespace (reviewer: route now) | — | no | owners | deferred by user decision 1, which overrides the reviewer's "route now" |

## Subphase 14B — review 3 (repair round 2 recheck): APPROVE

B2 is closed. All findings are nonblocking.

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| F1 | Medium | no (decide before the commit) | user decides; coordinator (§1, §3.2, §11); documentation-engineer (runbook times); infra-engineer and test-engineer only if a pin or the Neptune maximum changes | decided 2026-11-09: option 1, 37 h hard stop, cleanup by H35; approval request §1, §3.2 and §11 updated; runbook times routed to documentation-engineer |
| F2 | Low | no | coordinator | partly done: the 0.31/h line is labelled pre-tax, the §5 header is fixed, and §8 states that the full check is pending; §8 is refreshed after the post-approval full check. Original: the §5 header and §8 get refreshed after the post-approval full check; the USD 0.31/h line gets labelled pre-tax |
| F3 | Observation | no | coordinator, on the user's yes | done: user said yes; lines 136 and 263 redacted to `<plan path>`, with a note |
| Whitespace (six items) | — | no | infra-engineer, storage-engineer, test-engineer, documentation-engineer | done: all six fixed, whitespace only |

## Subphase 14B — review 4 (post-approval delta): REQUEST-CHANGES

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| D1 | Low | yes | experiment-engineer | done (cap 2.52; scale-out 2.94 > 2.52; experiments 24 OK; check_manifests exit 0). Routed as: `experiments/README.md:23` and `experiments/scripts/render_manifests.py:23` to say 2.52, and the scale-out sentence to say 2.94 > 2.52 (needs a recorded human cap decision) |
| N1 | Nit | no | infra-engineer | done (test_pipeline 69 OK). Routed as: the `scripts/tests/test_pipeline.py:580` comment to read "would exceed" |
| N2 | Nit | no | documentation-engineer | done (N3 margin sentence added too). Routed as: R.1 to use 0.3096 (about 0.31), matching the 11.15 example |
| N3 | Observation | no | coordinator | recorded: later receipts need a margin of at least about USD 0.35 to cover H36–H37; the coordinator states it when giving values |
| N4 | Observation | no | user (plan text); coordinator (round 3) | user: "Re-derive in round 3". The plan's "Update 2026-11-09" block says 1.50 and the decision is 1.33 |
| N5 | Observation | no | user | user: "Yes, keep it" (decision 3). `scripts/billing/budget_execution.py:26` constant from Phase 12D; user decision 3 (2026-11-08) left existing Phase 12 mentions in place |

## Subphase 14B — review 5 (post-approval delta repair recheck): APPROVE

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| D1, N1, N2 | — | — | — | closed by review 5 |
| O1 | Observation | no | documentation-engineer, only if the user wants exact wording | no change required. The N3 margin of "at least about USD 0.35" sits before tax and is about 0.04 more than needed, which is the safe side |

## Subphase 14B — repair round 3 (planned provider switch, not a review finding)

Plan "Update 2026-11-09": implement the Anthropic API and Voyage AI switch after the 14B commit. Routed per `prompt.md` "Repair round 3 work order".

| Item | Owner | Status |
|---|---|---|
| Anthropic and Voyage clients, switches, vector consistency, embedding cost bound | rag-engineer | done |
| Service wiring, key handling, startup consistency check | service-engineer | done |
| Model ids and limits as configuration with rationale (plan rule 6.7; coordinator re-read of the plan) | rag-engineer, service-engineer | done |
| Terraform switches, two secrets, scoped grants, receipts, cleanup, cost report | infra-engineer | done |
| Per-answer unit at Haiku 5.5 prices; embeddings cap; cost reporting | experiment-engineer | done |
| README, report section, runbook (key entry, receipts, revocation, monitoring) | documentation-engineer | done |
| Fixture repairs and independent tests | test-engineer | done |
| Close the 10 pre-session items | coordinator | after round 3 is approved (plan) |

## Subphase 14B — review 6 (repair round 3): REQUEST-CHANGES

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| B1 | Medium | yes | rag-engineer | routed: build the Voyage config only on the Voyage branch and the Bedrock config only on the Bedrock branch in `LiveEmbeddingIngestMain.scala:384` and `LiveEmbeddingSmokeMain.scala:284`; tests through the `awsPorts` path for a Titan config (no Voyage key, Bedrock client) and a Voyage config (fake key, no Bedrock client) |
| B2 | Medium | yes | documentation-engineer | routed: README, `docs/report/provider-fallback.md` §4 and runbook A0/A4 state that a Bedrock run also sets `main_synthesis_provider` / `main_embedding_provider` = "bedrock" in `infra/terraform/deployer/deployer.local.tfvars` and re-applies the deployer before the base plan |
| N1 | Nonblocking | no | rag-engineer | listed, not routed (counter may under-count on ambiguous outcomes; inside the 200M free tokens) |
| N2 | Nonblocking | no | service-engineer | listed, not routed (startup consistency check is self-referential; README wording) |
| N3 | Nonblocking | no | infra-engineer | listed, not routed (model ids as non-overridable locals in `phase14b-providers.tf`) |
| N4 | Nonblocking | no | experiment-engineer | listed, not routed (hardcoded model literal in `llm_budget.cost_report`) |
| N5 | Nonblocking | no | documentation-engineer | routed with B2 because it touches the same runbook: B3b.2 must not tell the user to click "Retrieve secret value"; A4 Case B counts re-derived or marked stale |
| N6 | Decision | no | user | asked (reviewer recommends keeping `PRESPEND_PROJECT_CEILING_USD=25`) |

## Subphase 14B — review 7 (repair round 3 recheck): APPROVE

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| B1 | Medium | was yes | rag-engineer | closed (review 7) |
| B2 | Medium | was yes | documentation-engineer | closed (review 7) |
| N5 | Nonblocking | no | documentation-engineer | closed (review 7) |
| O1 | Observation | no | rag-engineer | recorded, not routed: Voyage at 2048 dimensions is refused in both live preflights (`LiveEmbeddingIngestMain.scala:282`, `LiveEmbeddingSmokeMain.scala:133`); no impact while 256 is pinned |
| O2 | Observation | no | documentation-engineer | recorded, not routed: runbook A4 STOP rule (`:345`) still refers to the reference-only lists |
| N1–N4 | Nonblocking | no | various | listed in review 6, not routed |
| N6 | Decision | no | user | asked again with the commit (reviewer recommends keeping it) |

## Subphase 14B — pre-session items, review 8: REQUEST-CHANGES (repair round pre-session R1)

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| B1 | Medium | yes | experiment-engineer, then rag-engineer | routed: replace question 28 ("… strongest bridges in window since-2015?", refused by `QueryPlannerAgent.coveredQuestion`, `QueryPlannerAgent.scala:547-549,354`) with "… strongest bridges since 2015?"; regenerate all five 14C files with `include-ids.txt` byte-identical (sha256 `5d4d99a0…`); update the derive test grammar and `experiments/README.md:121`; rag spec asserting all 40 committed questions are `Planned` through the fallback |
| B2 | Medium | yes | coordinator | routed: rerun the three billing files one process each as `scripts/check.sh` runs them, `terraform validate`, `git diff --check` and the privacy scan with retained raw logs; retain or drop the clean-clone comparison; restate the `suite_run` failure as an undiagnosed harness difference |
| N1 | Low | no | experiment-engineer | routed with B1: `load-tests/README.md:116` test count |
| N2 | Low | no | experiment-engineer | routed as optional: test for `eval16b` `plan_state` shared-cap refusal |
| N3 | Low | no | coordinator | routed: cost-to-date in owner-report |
| N4 | Future scope | no | rag-engineer | recorded, not routed: planner coverage regex fails any "in window since-…" phrasing |
| N5 | Future scope | no | infra-engineer | recorded (already noted): `archive.py` name filter misses `*.plan.txt` |
| N6 | Accepted deviation | no | — | item 5 wording "to be confirmed live in the session" accepted |

Repair evidence (pre-session R1, awaiting recheck):

| ID | Status | Evidence |
|---|---|---|
| B1 | repaired, awaiting recheck | `questions.txt:28` = "Which researchers are the strongest bridges since 2015?"; `include-ids.txt` sha256 `5d4d99a0…` unchanged; `Phase14QuestionSetPlannerSpec` (all 40 `Planned`; rag 196); `evidence/14b/presession/r1/experiment-gates.txt`, `sbt-check-r1-summary.txt` |
| B2 | repaired, awaiting recheck | retained logs `evidence/14b/presession/r1/{billing-per-file,suite-run-comparison,terraform-validate,diffcheck-privacy}.txt`; cause restated as undiagnosed in `gates-summary.txt` and `test-report.md` X |
| N1 | repaired | `load-tests/README.md` counts (71 / 17) |
| N2 | repaired | `test_plan_and_run_refuse_when_the_shared_cap_would_be_passed` |
| N3 | repaired | `owner-report.md` pre-session R1: cost-to-date USD 0.34 (AWS), Anthropic 0, Voyage 0 |

## Subphase 14B — pre-session R1 recheck, review 9: APPROVE

| ID | Severity | Blocking | Owner | Status |
|---|---|---|---|---|
| B1, B2, N1–N3 (review 8) | — | — | — | closed by review 9 |
| R1 | Low | no | experiment-engineer | repaired: `experiments/README.md:121` now says the 40 questions are checked by the shape test in `experiments/tests/test_derive_14c_inputs.py` and by `Phase14QuestionSetPlannerSpec` (all 40 `Planned` through the fallback); experiments/tests rerun: Ran 51 tests, OK |
| O1 | Info | no | rag-engineer (future scope, with N4) | recorded: `Phase14QuestionSetPlannerSpec` "regression (N4)" asserts the "in window since-2015" phrasing is refused; it will fail on purpose when N4 is fixed and must then be flipped |

## Phase 14 live session 1 — live repairs 6-11 (2026-11-14)

Found in the live session and fixed in place; each commit was made on the user's explicit yes. Source: the decision log (`evidence/14b/session-1/00-timeline/decision-log.md`); commit metadata: `evidence/14b/session-1/live-repairs/commits-6-11.txt`. Test counts are as the decision log records them (coordinator- or agent-run); the raw test logs for these runs were not retained. No independent review is recorded for any of these commits.

Earlier in the session (2026-11-13): E1 repair `24bf49d` (deployer Cloud Map and Step Functions grants), E1 repair 2 `155562d` (ELB companion EC2 reads; state machine KMS data key reuse 300), repair 3 `bc81afd` (empty Cloud Map `health_check_custom_config`), repair 4 `9ee5bbe` (image files readable by the runtime user) and repair 5 `83a4168` (`StorageLoadMain --graph-only`). They are recorded in `14b-deploy/deployer-e1*-decision.md`, the 14B results excerpt and the decision log, and are not expanded here.

| Repair | Cause (observed) | Fix | Owner | Tests observed (decision log) | Commit (UTC) | Live result |
|---|---|---|---|---|---|---|
| 6 | B8.8 queries abstained with 0 claims: `stageFailures path=stage-deadline`. query-api loads the 9.6 MB runtime artifact on first use; the load takes about 28 s against the 4 s path budget (`pathMs 4000`), and a cancelled load is not cached, so every request starts again (Logs Insights: artifact fetched again at 04:42:39Z and 04:46:16Z). Also found: containers logged at DEBUG, so SDK wire logs in CloudWatch carried SigV4 headers and the task role's temporary session token | background warm-up of the runtime artifact at query-api startup; `logback.xml` at INFO with SDK and HTTP wire logging at WARN | service-engineer | `sbt check` exit 0 (services 124/124, 693 total); new `RuntimeArtifactWarmupSpec` | `bfa393a` 16:19:46 | push PASS, runtime apply 5 PASS; warm-up `attempt=1/3 outcome=loaded elapsedMs=28107` at 16:31:02Z; r6a path stage OK (1002 ms) |
| 7 | r6c: Haiku called once; the one claim was rejected (`unsupported-claim-template`, `subject-window-or-trust-mismatch`, `unsupported-claim-field`, `identity-not-resolved`). The synthesis-v1 prompt and schema never stated the verifier's contract | `ClaimContract` (the verifier's shared rules), `ClaimScaffold` (a `claimScaffold` key in the synthesis input), synthesis-v1 prompt edited in place (no version bump) | rag-engineer | `sbt check` exit 0 (rag 206 incl. 10 new; 693 total) | `0656dc4` 17:47:02 | push PASS, runtime apply 6 PASS; r7b failed at the synthesis deadline (`synthesisMs 5000`): copying scaffold claims with long ids was too slow; smoke-real-9 query 504 |
| 8 | synthesis stage deadline after repair 7 | the model returns `selectedClaimIds`; code expands them into scaffold claims before the unchanged verifier; `selectedClaimIds` optional in the schema | rag-engineer | `sbt check` exit 0 (rag 211; 693 total) | `ae14593` 18:18:37 | images rolled out within the combined EMR apply (serial 16); r8a ANSWERED 3 attempted / 3 verified / 0 rejected (4102 ms); smoke-real-11 `RESULT: PASS all 6 checks` |
| 9 | EMR run 1 attempt B: `aws emr describe-cluster` also calls `elasticmapreduce:ListBootstrapActions`, which the operator-pipeline role lacked (AccessDenied, exit 254) | deployer `operator_pipeline` policy adds `ListBootstrapActions` on the project cluster | infra-engineer (Terraform); the commit also changes `tests/infra` files | tftest 113/113; tests/infra operator roles 33/33; `sbt check` exit 0 | `2b2d263` 19:00:30 | user "Yes, apply" 19:00:30Z; deployer plan `0 to add, 1 to change, 0 to destroy`; apply `0 added, 1 changed, 0 destroyed` |
| 10 | EMR run 2: `aws emr list-instance-groups` does not exist in AWS CLI 2.35.4 (ParamValidation invalid choice, exit 252) | cluster-check reads `Cluster.InstanceGroups` from `describe-cluster` | infra-engineer (scripts), test-engineer (`tests/scripts` fakes) | `sbt check` exit 0; tests/scripts execute 14/14, dryrun 16/16, refusals 58/58; scripts/tests `test_pipeline` 68/69, then fixed (a 5-test subset OK; full 69/69 recorded with repair 11), `test_experiment` 39/39 | `7ecc572` 20:20:35 | EMR run 3: `CLUSTER-CHECK: ok state=WAITING` |
| 11 | EMR run 3: `aws emr add-steps` refused `HadoopJarStep` (the CLI takes `Type`, `Name`, `ActionOnFailure`, `Jar`, `Args`, ...); the ledger slot was reserved and counts | `pipeline.py` `step_json` sends `{Type: CUSTOM_JAR, Jar: command-runner.jar, Args}` (also `phase4-emr-smoke.sh`); fakes reject `HadoopJarStep` with the real CLI message; the other EMR calls were checked against the CLI 2.35.4 source | infra-engineer (scripts), test-engineer (`tests/scripts`) | scripts/tests c1 25/25, experiment 39/39, pipeline 69/69; tests/scripts execute 14, arg-limit 20, dryrun 16, refusals 58, all OK; `sbt check` started 20:45Z, result not recorded before the commit | `b6dc94d` 20:58:10 | EMR run 4: stage-in `COMPLETED`; hadoop-prep `FAILED` (not a repair-11 defect: unuploaded prep-config reference) |

### Open after the session (not routed yet)

| ID | Item | Owner |
|---|---|---|
| S1-F1 | 15A manifests set `hadoop_config` to a repo-relative local path (`experiments/inputs/15a/prep-config.json`); every other reference is an s3 URI, so the node cannot localize it | experiment-engineer (manifest), infra-engineer (`upload-emr-artifacts.sh --hadoop-config` option and test) |
| S1-F2 | EMR bootstrap race: the cluster was created in parallel with the EFS mount target (serial 16 `BOOTSTRAP_FAILURE`, "EFS mount failed") | infra-engineer (`depends_on` the mount target) |
| S1-F3 | Destroy policy refused `terraform_data.phase12b_guard` (not in `CLEANUP_TEARDOWN_ADDRESS_RULES`); removed from state by human decision | infra-engineer (rule plus tests) |
| S1-F4 | `LiveGraphFixture.handle()` roots at a non-real temp path; `NeptuneExportValidator` compares real paths and rejects it on macOS (test-only; workaround `-Djava.io.tmpdir`) | storage-engineer |
| S1-F5 | A new query-api task serves cold until the warm-up finishes (28 s; 45 s on the next task); the first query after idle can 504 at the graph stage | service-engineer (readiness gate or faster load); storage-engineer for the graph-stage diagnosis |
| S1-F6 | Context budget 4096 makes every 22-coauthor direct-coauthor question abstain (16B 0/14); path questions 0/10 undiagnosed; `synthesis-v2` label for provenance; coauthor names instead of ids | rag-engineer |
| S1-F7 | Repair 11 `sbt check` result not recorded; no independent review of the in-session commits. **Closed** by the closeout `sbt check` on b6dc94d and the B2 `scripts/check.sh --skip sbt` run (test-report.md, "Session 1 closeout" entries) and the external closeout review and its recheck (review.md, "Subphase 14B — Session 1 closeout") | coordinator (rerun `sbt check`), code-reviewer |
| S1-F8 | Runbook note: never run `aws login` while the browser is signed in as root | documentation-engineer |

## Session 1 closeout review (2026-11-15): findings routed

External review verdict REQUEST-CHANGES (appended verbatim to `review.md`, "Subphase 14B — Session 1 closeout"). Repair round 1 is records-only.

| ID | Severity | Blocking | Owner | Acceptance check | Status |
|---|---|---|---|---|---|
| B1 | Medium | yes | orchestrator | Owner and test reports state C11 done-provisional, combined USD 15.83 of 25 (AWS 15.75 before credits, tax 0.00, Anthropic about 0.08 ledger estimate, Voyage 0.00), read time and bill status; ECS 0 / EMR 0 console checks recorded, EC2 Instances still unchecked; INVENTORIES.md matches; tracked decision log recopied with its C11 entries or the C11 source line corrected; c11-cost-report.md added as an INDEX row; every INDEX sha256 re-verified | in repair round 1 |
| B2 | Medium (gate not verified) | yes | coordinator runs; failures to infra-engineer / test-engineer | `scripts/check.sh --skip sbt` on a clean b6dc94d snapshot: RESULT PARTIAL, exit 5, every other gate PASS; per-gate counts, exit code and log sha256 in test-report.md; closeout sbt run cited for the sbt gate | in repair round 1 |
| N1 | Medium | no (gate before any Session 2 paid answer) | rag-engineer, domain-engineer | bump to synthesis-v2 / answer-synthesis-v2 / synthesis.v2 schema with tests, or the human accepts in writing | open |
| N2 | Medium | no (recommended this round) | orchestrator | approval-record, plan-sha and account-match lines from runtime-apply-3.log and 15/emr-apply.log, with source sha256, added to the excerpts | in repair round 1 |
| N3 | Medium | no | orchestrator | agent roster for E1 through repair 11 or "not recorded"; cross-owner edits to tests/infra/** flagged as deviations for the human | in repair round 1 |
| N4 | Low (gate not verified) | no (future) | deploy-engineer; infra-engineer for read access | Session 2 compares running task image digests with the push record | open (Session 2) |
| N5 | Low | no | service-engineer; storage-engineer, rag-engineer | logback level test; storage/rag tool logging set before Session 2; local awsintegration logs with expired tokens deleted or moved to private storage | open |
| N6 | Low | no | infra-engineer / test-engineer | test asserts phase4-emr-smoke --steps has Type=CUSTOM_JAR and no HadoopJarStep | open |
| N7 | Low | no | infra-engineer | deployer README, operator_pipeline.tf comment and gdeployer tftest no longer list list-instance-groups | open |
| N8 | Info | no | service-engineer / rag-engineer | config entry or one-line rationale for the warm-up and synthesis constants | open |
| N9 | Info | no | orchestrator / human | inventory records the remaining deployer role and phase14-main policies as a final-cleanup item | in repair round 1 (record only) |

### Repair round 1 outcome (2026-11-15, records only)

| ID | Outcome |
|---|---|
| B1 | repaired: owner-report and test-report state C11 done-provisional, combined USD 15.83 of 25 (AWS 15.75 before credits, tax 0.00, Anthropic about 0.08, Voyage 0.00), ECS 0 and EMR 0 console checks, EC2 Instances still unchecked; INVENTORIES.md corrected; decision-log copy recopied with the C11 entries (byte-identical to the frozen source, sha256 bc7254e8…2c5b; later entries go to a separate Session 2 log); c11-cost-report.md source line names the tracked copy; INDEX rows added and all hashes re-verified |
| B2 | repaired: `scripts/check.sh --skip sbt` on a clean b6dc94d worktree, exit 5 RESULT PARTIAL passed=6 skipped sbt, every other gate PASS (counts in test-report.md); closeout sbt run cited for the sbt gate; terraform init used the public registry (no AWS call) |
| N2 | repaired: `evidence/14b/session-1/approval-checks-unarchived-serials.txt` (approval-record, plan-sha, account-match lines for serials 7 and 16, with source sha256) |
| N3 | repaired: "Agent roster" in owner-report.md; native agent IDs and the roles for E1 to repair 4 not recorded; deviations for the human to accept: tests/infra/** edits in 155562d (author not recorded) and 2b2d263 (infra-engineer), and build-engineer paths in 9ee5bbe |
| N9 | recorded: INVENTORIES.md "Final-cleanup items" (deployer role, its phase14-main and boundary policies, two terraform_data guards); removal planned at the end of Session 2 by human decision |
| N1, N4-N8 | open: N1, N4 and N5 are carried into docs/runbooks/session-2-plan.md as P36, P37 and P38; N6, N7 and N8 are not yet routed and stay open for their owners |

### Recheck findings (APPROVE, 2026-11-15) and outcomes

| ID | Severity | Blocking | Owner | Outcome |
|---|---|---|---|---|
| R1 | Low | no (fix before commit) | orchestrator | fixed: test-report.md now cites the 64-character sbt log sha256 1fc21fea1fe021c6132cffc57ad2de466faba33e91319b189d6395496c882f1e; `grep -rn "1fc21fea021c" docs/agent-runs/` returns nothing |
| R2 | Low | no | orchestrator | fixed: owner-report "Open follow-ups" billing row says USD 25 with alerts at USD 18 / 20 / 22, citing the human decision of 2026-11-15T18:42Z (Q11, decision-log line 108); notes the code still defines 10/15/20 |
| R3 | Low | no | orchestrator | fixed: owner-report known gaps and follow-ups, test-report L4/L7 and S1-F7 point to the closeout sbt entry, the B2 entry and the closeout review and recheck; S1-F7 closed |
| R4 | Info | no | orchestrator | fixed: the 9ee5bbe roster row is labelled "Deviation for the human to accept" (build-engineer paths) |
| R5 | Info | no | orchestrator | not done (optional): the first closeout verdict stays as pasted; the recheck verdict was appended with its findings table in Markdown |
| R6 | Info (not verified) | no | none | noted: the clean-worktree claim rests on the record; no action |
