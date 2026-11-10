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
