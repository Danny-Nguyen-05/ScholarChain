# Phase 15 test reports

## Work order 1: P0 budget guard (2026-11-15)

All runs offline; no AWS, Anthropic or Voyage call. Lines marked "agent-reported; log not retained" come from the agent's final report (`owner-report.md`); no log file was kept for them. Lines with a sha256 have a retained git-ignored log.

- infra-engineer, `infra/terraform/billing-bootstrap` (Terraform 1.13.5, mock provider): init, `fmt -check -recursive`, `validate` and `terraform test` all exit 0, **12 passed, 0 failed** (agent-reported; log not retained; the same 12 are in the coordinator's clean-snapshot log below). Mutation check on scratch copies ([10,15,20], [18,20,25], [18,20], [15,20,22], [18,20,22,24], [50,80,100], PERCENTAGE, FORECASTED, LESS_THAN): each failed exactly the intended run (agent-reported; log not retained).
- infra-engineer, `scripts/billing`: `test_budget_execution.py` **115 OK** (113 before, plus 2), `test_budget_verification.py` **62 OK**, `test_publication_evidence.py` **39 OK** (agent-reported; the same counts are in the clean-snapshot log below). Python mutation back to (10, 15, 20): 12 failures and 11 errors, and 6 failures and 3 errors (agent-reported; log not retained).
- infra-engineer, failed run recorded: `scripts/check.sh --only terraform` in the working tree, **exit 4 (gate FAIL)**. billing-bootstrap 12, deployer 113, spikes/emr-spark-isolated 40 and infra/terraform 272 passed; the failures were local-only (fmt of the private `course.local.tfvars`, which was not opened, and init of `billing-execution` and `spikes/emr-spark` through broken provider links), not caused by P0. At that time `tests/infra/test_billing_replan_14b` failed 2 of 28 (exit 1) before the test-engineer's fix (agent-reported; log not retained). The coordinator's clean-snapshot run below replaces this gate.
- test-engineer: `test_billing_replan_14b` **33 OK** (agent-reported; log not retained); the whole `tests/infra` suite **465 executed, 0 skipped, 0 failures, 0 errors** (agent-reported; the same count is in the clean-snapshot log below). Scan-base mutation (HEAD as base; main's tip as base): 2 and 3 failures (agent-reported; log not retained).
- documentation-engineer: link check of the runbook and the demo script, 65 links, 0 broken (agent-reported; log not retained; superseded by the repair-round-1 clean-worktree check below, because that run included the untracked drafts).
- Coordinator, `sbt -batch check` on the P0 working tree (JDK 17): **exit 0**, 772 s, ScalaTest **1567 succeeded, 0 failed, 1 canceled**; the tree did not change during the run. Log sha256 `6c2f5e7e3a9e2df572e5ae12deee1c3163850e7bc54619015ebc56a688bf4960` (git-ignored `target/phase15/p0/sbt-check-p0.log`).
- Coordinator, clean snapshot (a detached worktree of HEAD `a576878` plus the P0 patch, sha256 `def2c2817b2f32b60a8a2f369bb259d61b03aaa031d6b01b748fd91389176d4f`, plus the untracked drafts), JDK 17, AWS credential variables unset, `scripts/check.sh --skip sbt`: **exit 5, `RESULT: PARTIAL passed=6 skipped: sbt`**. Gates: constitution, hooks, shell and python PASS; terraform PASS (`terraform test` 12, 19, 113, 40, 6 and 272 passed, 0 failed); script-tests PASS (scripts/tests 1061 with the required classes 7 and 6; phase12d-spike 78; billing 115, 62 and 39; tests/scripts 463; tests/infra 465; 0 skipped). Log sha256 `5ec773a2611e9e08c88cc8ad2d0fe97d170d95da8543fa53f0e6de8d99130821` (git-ignored `target/phase15/p0/check-skip-sbt-p0.log`). terraform init contacted the public Terraform registry (logged); no AWS call.
- Not verified offline: the live plan, apply and readback. The human's 2026-11-17 modify run is the proof.

## Work order 1: P0 repair round 1 (2026-11-15)

Coordinator runs, offline, no AWS, Anthropic or Voyage call. Log: git-ignored `target/phase15/p0/r1/verify-r1.log`, sha256 `755f145a4f34f9d85fce75d3c944879f68debfec41e3aa76d4ab112c4a4738d3`.

- New P0 patch: `git diff a576878 | shasum -a 256` = **`ede0052faf4f066eea436b67c5e75b76bff22807fa2ee27040d806123055d6fb`** (saved as git-ignored `target/phase15/p0/r1/p0-patch-r1.diff`). Same 12 tracked files; the runbook stays `7 0` (additions only).
- Only change since the round-0 patch: in a worktree of `a576878` with the new patch applied, putting line 264 of `docs/runbooks/phase-14-live-session.md` back to its round-0 text gives `git diff | shasum -a 256` = `def2c2817b2f32b60a8a2f369bb259d61b03aaa031d6b01b748fd91389176d4f`, the round-0 patch hash. So the round-1 tracked change is that one line and nothing else.
- Link check, clean worktree of `a576878` plus the new patch only (no untracked files; `session-2-plan.md` and `demo-script.md` absent), scratch checker `linkcheck.py` (relative links and GitHub heading anchors; lychee and markdown-link-check are not installed): `docs/runbooks/phase-14-live-session.md` **links=62, broken=0**, exit 0. Also run on the other changed Markdown files: `infra/terraform/billing-bootstrap/README.md` 10 links, 0 broken; `scripts/billing/VERIFICATION.md` and `tests/infra/README.md` 0 links; `scripts/billing/README.md` 19 links, **1 broken**: the absolute local-path link to `infra/terraform/billing-bootstrap/main.tf:28` on line 38. That link is unchanged since `a576878` (present there, not in the P0 diff); recorded as coordinator observation O1 in `repairs.md`, not fixed in this round.
- `sbt check` skipped in this round: no Scala, Java, build or test source changed (only `docs/runbooks/phase-14-live-session.md` and `docs/agent-runs/phase-15/**`), per the user's standing rule. The P0 `sbt check` evidence stands: exit 0, 1567 / 0 / 1 canceled, log sha256 `6c2f5e7e3a9e2df572e5ae12deee1c3163850e7bc54619015ebc56a688bf4960`. `check.sh --skip sbt` was not rerun: no test or gate under `tests/`, `scripts/`, `modules/` or `infra/` reads `docs/runbooks/phase-14-live-session.md` (grep: no match), and `check.sh` reads Markdown only for the constitution files, which are unchanged.

## Work order 2: P40 public semantic route and query-embedding cache (2026-11-15/16)

All runs offline; no AWS, Anthropic or Voyage call. Lines marked "agent-reported; log not retained" come from the agents' final reports, quoted in `owner-report.md` ("Work order 2"). Lines with a sha256 have a retained git-ignored log under `target/phase15/p40/`.

### Agent-reported (logs not retained)

- rag-engineer: `rag/test` **228 succeeded, 0 failed** (18 suites), including the 17 `CachingEmbeddingClientSpec` tests.
- service-engineer repair 1 (final state): `services/test` **165 succeeded, 0 failed** (17 suites, including `PublicSemanticRouteSpec`, `SemanticCacheWiringSpec` and the new `RequestNestingSpec` with 10 tests); `AdversarialPublicSemanticHttpSpec` **14 succeeded, 0 failed**, with no "StackOverflow" in its log; `IndependentServices*` (8 suites) plus `AdversarialRuntimeHttpSpec` **51 succeeded, 0 failed**.
- test-engineer, before the repair: `AdversarialPublicSemanticHttpSpec` **13 of 14 passed**. The failing test was deep-nested JSON inside 8 KiB, which gave HTTP 500 and a printed StackOverflowError. That production defect was routed to the service-engineer (repair 1) and is recorded in `repairs.md`.
- infra-engineer: `scripts/tests/test_smoke.py` **48 run, 48 OK** (31 before, 17 new). Also `tests/scripts` `test_smoke*.py` 38 OK, `test_regression_13a.py` 20 OK, `test_13b_repairs.py` 22 OK and `test_syntax.py` 20 OK.

### Coordinator runs

- **Snapshot of the bundle under test.** HEAD `d5e74aa`.
  - Tracked diff: `git diff HEAD`, sha256 `f88095220a13d78d208d7b8cebf17f261723cede827412a69d7e866189327137` (git-ignored `p40-tracked.diff`).
  - Untracked files: tar sha256 `bb68fe0868d015d799b5b52cc1aac648060040c09105a7aebe207adbc08d084e` (`p40-untracked.tar`, 12 files).
  - The tar also holds `docs/demo-script.md`, the documentation-engineer's untracked work-order-1 draft. It is not part of P40.
  - The `git status` before and after `sbt check` and at the snapshot are identical.
- **`sbt -batch check` (JDK 17) on the working tree.**
  - Result: **exit 0**, 754 s (2026-11-16T01:57:12Z to 02:09:49Z).
  - ScalaTest summed over all modules: **1639 succeeded, 0 failed, 1 canceled**.
  - The tree did not change during the run, and `markTestRun` updated the marker.
  - The log has one `[error] (checkProbeInjectFailure)` block. It comes from the build's own failure-path probe (`CheckFailurePathSpec`), which injects it deliberately, and it is expected.
  - Log sha256 `07e845ce566291fc37b2b20033a975c617f375de76ae91ec5f2dbff6e2085d93` (`sbt-check-p40.log`).
- **Clean snapshot, `scripts/check.sh --skip sbt`.** The run used a detached worktree of `d5e74aa` with the tracked diff and the untracked tar applied, JDK 17, and AWS credential variables unset.
  - Result: **exit 5, `RESULT: PARTIAL passed=6 skipped: sbt`**.
  - Gates:
    - constitution, hooks, shell and python: PASS;
    - terraform: PASS (`terraform test` 12, 19, 113, 40, 6 and 272 passed, 0 failed);
    - script-tests: PASS (3867 s), with 0 skipped in every suite:

      | Suite | Tests run |
      |---|---|
      | `scripts/tests` | 1078, including the required classes with 7 and 6 tests (1061 at P0; the 17 new smoke tests explain the difference) |
      | `phase12d-spike` | 78 |
      | billing | 115, 62 and 39 |
      | `tests/scripts` | 463 |
      | `tests/infra` | 465 |

  - `terraform init` downloaded providers from the public registry (logged); there was no AWS call.
  - Log sha256 `92d5435452646e56b3a016e2373f43121842d5d7edbbc03f3b10d5707b10acdf` (`check-skip-sbt-p40.log`). The worktree was removed afterwards.
- **`scripts/smoke-local.sh --build`, run 1: FAIL (recorded).**
  - The script reused an existing `modules/services/target/distribution` built before P40 (services.jar sha256 `a2d04be1…2895d`), because `--build` packages only when the distribution is missing.
  - The six base checks passed. `smoke-semantic` failed with `POST /v1/semantic/retrieve returned 404, expected 200`, so smoke-test.sh exited 4 and the run ended with **exit=4**.
  - Cause: a stale build, not a P40 code defect. A follow-up is recorded in `repairs.md` (S1).
  - Log sha256 `9362723ecee1c43f89a2e1780b5255cfc75c83e3adf982b1e4545df2671755e1` (`smoke-local-p40.log`).
- **`sbt -batch packageServices`, then `scripts/smoke-local.sh --build`, run 2: PASS.**
  - Package: exit 0; new services.jar sha256 `64d1d190b2668733ff3291206b059c786f02675f4ef39c9aeb372c7a4ef8c7a2`.
  - The semantic rate limit used the service code defaults (no override).
  - Throwaway API key: not printed; only its sha256 reached the service.
  - Checks:
    - `CHECK-OK: semantic`: 200, exactly `{hits, model}`, and without a key 401 `UNAUTHORIZED`;
    - `CHECK-OK: semantic-cache`: `embedding_cache_hits_total` went from 0 to 1 when the same question was repeated.
  - Result: `RESULT: PASS all 6 checks plus 2 semantic check(s)`, **smoke-exit=0**.
  - Log sha256 `60261eebf8911e48ae2f8fe15835477cc7e0a80f06729ed348cf69ea20df635d` (`smoke-local-p40-r2.log`).
  - The run used local loopback only.
- **Not verified offline:**
  - the route on the deployed query-api, the Terraform env wiring (P41) and the rebuilt images (P15);
  - the rate limiter under the real load profile (P35 must show zero 429s at the heaviest level, with r_S2 ≥ 2× the measured peak served rate per task);
  - the real Voyage embedding through the cache.

## Work order 3: P41 request-count scaling and rate-limit env wiring (2026-11-16)

All runs offline; no AWS, Anthropic or Voyage call. Lines marked "agent-reported; log not retained" come from the infra-engineer's reports (`owner-report.md`, "Work order 3"). Lines with a sha256 have a retained git-ignored log under `target/phase15/p41/`.

### Agent-reported (logs not retained)

- infra-engineer, first build:
  - `terraform test` **301 passed, 0 failed** (272 existing + 29 new);
  - fmt-check and validate pass;
  - default planned address sets unchanged (0 differing lines over 42,633);
  - plan-delta derivation byte-identical;
  - 8 of 8 mutations killed;
  - `tests/infra` **465 OK**; `scripts/tests` `test_runtime_base_apply` + `test_plan_deltas` **46 OK**.
- infra-engineer, repair 1 (moved the three variables into `phase12b-variables.tf` and deleted `phase15-variables.tf`):
  - `terraform test` **304 passed, 0 failed**. That count includes 3 runs from lane B's untracked `phase15_stagea.tftest.hcl`, which is not part of P41.
  - `scripts/tests` `test_terraform_*` **17 OK**, `test_terraform_r1` 10 OK, `test_runtime_base_apply` 31 OK;
  - `tests/infra` `test_runtime_shape_14b` **19 OK**.

### Coordinator runs

- **Run 1: FAIL (recorded).**
  - Snapshot of HEAD `cceb1f5` + tracked diff sha256 `df7d542a956088acaa5ebb1601ab3dcc0ae53d0c53cb90e31412690f9491aa95` + untracked tar sha256 `e7f9e93e470cc7e3ab5d8309d3aeeae982149d2ac09152c412973e56ad7a5d9f`, clean worktree, AWS variables unset, `scripts/check.sh --skip sbt`.
  - Result: **exit 4, `RESULT: FAIL failed: script-tests skipped: sbt`**.
    - constitution, hooks, shell, python: PASS;
    - terraform: PASS (12, 19, 113, 40, 6 and 301 passed);
    - `phase12d-spike` 78, billing 115/62/39, `tests/scripts` 463 and `tests/infra` 465: OK;
    - **`scripts/tests`: 1078 run, 7 failures.**
  - Log sha256 `ee2b4a03a327ff9ec9e2e363d5e507648530c5b4c97d8b71b5c49739d183d99b` (`check-skip-sbt-p41.log`).
  - The per-suite log was lost when the coordinator removed the worktree too early.
  - Reproduced on the same snapshot: `test_terraform_r1` had 10 run, **7 FAIL**. Its fixture copies only `git ls-files infra/terraform`, so the untracked new root file `phase15-variables.tf` was missing, and `main.tf` lines 140-142 referred to undeclared variables. Routed to the infra-engineer (repair 1, `repairs.md`).
  - The other candidate files passed on that snapshot: `test_runtime_guard` 24, `test_runtime_rollback` 51, `test_check` 54, `test_package` 28.
- **Run 2 (after repair 1): PASS (gate).**
  - Result: **exit 5, `RESULT: PARTIAL passed=6 skipped: sbt`**.
    - constitution, hooks, shell, python: PASS;
    - terraform: PASS (12, 19, 113, 40, 6 and 301 passed, 0 failed);
    - script-tests: PASS, 0 skipped in every suite:

      | Suite | Tests run |
      |---|---|
      | `scripts/tests` | **1078 OK**, including the required classes RealStateBindingTests 7 and RouteOwnershipTest 6 |
      | `phase12d-spike` | 78 |
      | billing | 115, 62 and 39 |
      | `tests/scripts` | 463 |
      | `tests/infra` | 465 |

  - Log sha256 `22abe7b0bf5f461318b38bd612b0123f81e1cd8e7071dd55cb1315d7e8aa35e2` (`target/phase15/p41/r1/check-skip-sbt-p41-r1.log`).
  - P41-only snapshot: `git diff HEAD -- infra/terraform docs/agent-runs/phase-15` sha256 `100e31634ea8b05d3834b6b86b6d28fbbd3bc758e05fb057fc189cbe43f82705`, plus the two P41 test files, tar sha256 `58573b0dbe213fd00eeac4c52e6dccbe490cb261435ccd6cb1082304746ab0c1`.
  - The pipeline lanes' in-progress files are excluded from it.
  - Log: `target/phase15/p41/r1/check-skip-sbt-p41-r1.log`; per-suite logs copied to `target/phase15/p41/r1/check-logs/`.
- `sbt check`: not run for P41 (no Scala, build or test-source change under `modules/**`).

## Pipeline bundle (Session 2 prerequisites), coordinator-observed gate results (2026-11-16)

| Gate | Command | Result | Evidence |
|---|---|---|---|
| sbt check (JDK 17), run 1 | `sbt -batch check` | exit 0, 15 min 7 s (before the rag account-ID fix and D3) | target/phase15/pipeline/sbt-check2.log, sha256 b9422828…5c65 |
| sbt check (JDK 17), final | `sbt -batch check` | exit 0, 14 min 21 s. Suites: 207, 64, 39, 53, storage 160, rag 251, 165, independent 707, 30 (1 canceled: the deliberate check probe) | target/phase15/pipeline/sbt-check3.log, sha256 b75e37e9…0b09 |
| P6 local chain, S | `python3 -I scripts/lib/p6_local_chain.py run --size S --er-xmx 12g` (no hadoop-CLI workaround) | all 6 steps exit 0: hadoop 47.4 s, ER 165.4 s, Spark 489.8 s, copy-out 4.7 s (1,104,381,932 B) | target/phase15/p6/work/p6-S-20261116T171431Z/evidence/summary.json |
| P6 local chain, L | same with --size L | hadoop-prep exit 0 (132 s; OVERSIZE_TEAM 210, largestTeam 79, maxLocalSampleRecords rejects 0); ER refused by the pinned config, then out of memory at 22g after 963 s | target/phase15/lanes/p6-progress.md |
| L Spark, ER identity bypass (local only) | experiments/scripts/run_spark_bypass.py --label L | exit 0, 1110 s; 48,188 works, 76,623 researchers, 320,690 edges; hard invariants 0/0; sidecar max 8,565,999 B | target/phase15/p6/l-bypass/spark-L/summary.json |
| Agent-run suites (final, as reported) | python3 -I unittest discover | tests/scripts 482/482; tests/infra 468/468; experiments 84/84; datasets/scripts/phase15 13/13; scripts/tests per-module runs (verbatim in owner-report.md); terraform test scratch roots: phase12b 18, phase12c 9, phase13c 37, phase14a 40, phase14b_plan_deltas 3, phase15_stagea 3, phase15_elasticity 5, phase15_emr_primary 12, gdeployer 13, all 0 failed | owner-report.md, pipeline bundle section |
| Clean-snapshot check.sh | `scripts/check.sh --skip sbt` on a HEAD worktree plus the full tracked diff plus untracked files | exit 5, `RESULT: PARTIAL passed=6 skipped: sbt` (expected; sbt gated separately). constitution, hooks, shell, python PASS; terraform PASS 155 s (tests 12, 19, 113, 40, 6, 333 passed, 0 failed); script-tests PASS 4049 s (Python suites ran 1196, 482, 468, 115, 78, 62, 39 tests, all OK, one with skipped=3). Snapshot: tracked.diff sha256 d6ddf1f3…1010, untracked.tar sha256 778335b3…7e2 (41 untracked files; 101 is the porcelain status line count of the snapshot worktree, `check-snapshot-status-count.txt`); check.log sha256 5973636b…b90b6; run 20261116T193009Z-41305, finished 2026-11-16T20:40:21Z | target/phase15/pipeline/r1/ |
| Final sbt check (JDK 17, main checkout, after review 1) | `sbt check` with the phase-04 logback config, AWS env unset | exit 0; `All tests passed`; `[success] Total time: 811 s`, completed 2026-11-16 14:54:35 CST; the `[error]` lines are the expected `checkProbeInjectFailure` probe; marker updated 14:54:35. Log sha256 608d08eb…5969 | target/phase15/pipeline/r1/sbt/sbt-check4.log |
| D1/D2 parser test on the built tree (review finding 5) | `python3 -m unittest -v test_hadoop_prep_args_15` from `tests/scripts`, JDK 17, after sbt-check4 built the JARs | `Ran 3 tests in 13.038s`, `OK` (the real-parser acceptance test and both mutants D1 and D2 executed; in the clean snapshot these were the 3 skipped tests because the JARs and the P6 classpath are absent there) | target/phase15/pipeline/r1/hadoop-prep-args-15.log |
| Clean-snapshot check.sh, repair round + P42 + P35 (after reviews 2 and 3 APPROVE) | `scripts/check.sh --skip sbt` on a worktree of HEAD f801d28 plus the full tracked diff plus untracked files | exit 5, `RESULT: PARTIAL passed=6 skipped: sbt` (expected; sbt gated separately). constitution, hooks, shell, python PASS; terraform PASS 149 s (tests 12, 19, 113, 40, 6, 333 passed, 0 failed); script-tests PASS 4021 s (Python suites ran 1199, 485, 468, 115, 78, 62, 39 tests, all OK; tests/scripts skipped=3, the JAR-dependent D1/D2 parser tests). Snapshot: tracked.diff sha256 89fc92fc…f017 (25 files, +1797/-181), untracked.tar sha256 e8927097…c3b7 (29 untracked files); check.log sha256 2b18a215…70d7; run 20261116T222533Z-13933, finished 2026-11-16T23:35:12Z | target/phase15/pipeline/r2/ |
| Final sbt check (JDK 17, main checkout, after reviews 2 and 3) | `sbt check` with the phase-04 logback config, AWS env unset | exit 0; `All tests passed`; `[success] Total time: 807 s`, completed 2026-11-16 17:48:41 CST; the `[error]` lines are the expected `checkProbeInjectFailure` probe; marker updated 17:48:41. Log sha256 06a1aded…29c1 | target/phase15/pipeline/r2/sbt/sbt-check5.log |
| P15 A1.7 full check, main checkout (P0 wrapper fix, incident record, runbooks, after P0 reviews 1 and 2 APPROVE) | `scripts/check.sh` (all gates) on the main checkout at HEAD 2611cc6 with the uncommitted tracked diff, JDK 17, AWS env unset | exit 4, `RESULT: FAIL failed: terraform`. constitution, hooks, shell, python PASS; script-tests PASS 3984 s; sbt PASS 814 s (Tests: succeeded 165, 707, 30; failed 0; one canceled). terraform FAIL 79 s for two local-checkout causes, not code: (1) `terraform fmt -check -recursive` listed `environments/course.local.tfvars`, the human's ignored private tfvars, which agents do not read or edit; (2) `init` in `billing-execution` and `spikes/emr-spark` failed with `mkdir … darwin_arm64: file exists`, because those ignored `.terraform/providers` entries are symlinks into a deleted /tmp provider mirror from Phase 12B. The other terraform roots passed (tests 12, 113, 40, 333 passed, 0 failed). git status before = after; diff sha256 before = after = 35915fbc…0197. Run 20261117T024422Z-71922; log sha256 bf319382…9e66. Rerun as a clean snapshot (next row) | target/phase15/p15/a1-check-full.log |
| P15 A1.7 / P20 full check, clean snapshot (frozen code commit content) | `scripts/check.sh` (all 7 gates, no skip) on a detached worktree of HEAD 2611cc6 plus the full tracked diff plus untracked files, JDK 17, AWS env unset | exit 0, `RESULT: PASS gates=7`. constitution, hooks, shell, python PASS; terraform PASS 177 s (tests 12, 19, 113, 40, 6, 333 passed, 0 failed); script-tests PASS 3958 s (scripts/tests 1199 OK, phase12d-spike 78 OK, tests/scripts 485 OK with skipped=3, the JAR-dependent D1/D2 parser tests, tests/infra 468 OK; required classes RealStateBindingTests 7 and RouteOwnershipTest 6 executed); sbt PASS 860 s (Tests: succeeded 165, 707, 30; failed 0; one canceled). Snapshot: tracked.diff sha256 35915fbc…0197 (11 files, +1453/-34; identical to the main-checkout run's diff), untracked.tar sha256 038a5d39…430f (1 file, the incident record). The committed tree differs from the snapshot only by this file's two record rows. Run 20261117T040654Z-64834; check.log sha256 439e88c3…8419 | target/phase15/p15/snap/ |
| P6 local chain, S, on the frozen commit 9e881a2, attempt 1 | `python3 -I scripts/lib/p6_local_chain.py run --size S --er-xmx 12g --retain`, JDK 17, AWS env unset, clean tree at 9e881a2 | exit 1. stage-in, hadoop-prep, entity-resolution, spark-class-origin exit 0; spark-job exit 1 after 232 s: task 0 of ShuffleMapStage 4297 (`checkpoint at Phase6DEJobs.scala:1007`) failed with `java.io.IOException: java.lang.ArrayIndexOutOfBoundsException: Index 0 out of bounds for length 0` in `TorrentBroadcast.readBlocks` under `ReliableCheckpointRDD.readCheckpointFile`; `spark.task.maxFailures=1` aborted the job. The EMR configuration also sets `spark.task.maxFailures=1` (`infra/terraform/modules/emr/variables.tf:169`). Read-only diagnosis routed to the spark-engineer | target/phase15/p6/work/p6-S-20261117T053104Z/ (spark-job.stderr.log line 87481) |
| P6 local chain, S, on the frozen commit 9e881a2, attempt 2 (identical rerun) | same command | exit 0, all 6 steps exit 0 (stage-in 0s; hadoop-prep 34s; entity-resolution 88s; spark-class-origin 3s; spark-job 339s; copy-out 3s). All 61 Spark counters equal those of the passing run p6-S-20261116T171431Z (for example canonicalWorks 10578, canonicalResearchers 21819, allYearsEdges 81181, components 3942). Export run:cfd5c7d1-89f2-4889-a679-be1f7b43053b, 433 files, 605,713,492 B; retained with SHA256SUMS (433 lines, `shasum -a 256 -c` all OK; SHA256SUMS sha256 1d6890a5…0fb9) for the step-7b fallback. Of the 6 local S runs that reached a full spark-job (4 at 7a02de2, 2 at 9e881a2), this was the only spark-job failure | target/phase15/p6/work/p6-S-20261117T053800Z/evidence/summary.json; target/phase15/p6/size-S/run:cfd5c7d1-89f2-4889-a679-be1f7b43053b/ |
| spark.task.maxFailures 1 -> 2, full check, clean snapshot (after review APPROVE) | `scripts/check.sh` (all 7 gates, no skip) on a detached worktree of 9e881a2 plus the branch phase-15-maxfail tracked diff, JDK 17, AWS env unset | exit 0, `RESULT: PASS gates=7`. constitution, hooks, shell, python PASS; terraform PASS 156 s (tests 12, 19, 113, 40, 6, 333 passed, 0 failed); script-tests PASS 3977 s (scripts/tests 1200 OK, phase12d-spike 78 OK, tests/scripts 485 OK with skipped=3, tests/infra 468 OK); sbt PASS 869 s (Tests: succeeded 165, 707, 30; failed 0; one canceled). Snapshot: tracked.diff sha256 26a8849e…c698 (10 files, +319/-5), no untracked files. The commit adds only this record row on top of the snapshot. Run 20261117T150435Z-28163; check.log sha256 a07f7d2c…9d71 | phase15-maxfail worktree: target/phase15/p15/snap-maxfail/ |
| spark.task.maxFailures 2, local P6 S on branch commit 0b37c9d, attempt 1 | worktree `sbt -batch packageEmr` (exit 0), then `python3 -I scripts/lib/p6_local_chain.py run --size S --er-xmx 12g --retain` | exit 3, refused before any step: `P6-REFUSED: the built er-jar does not have the manifest sha256 e8df4ee2…2768`. The clean worktree build gives er-jar ba9c7e24… and job-jar 75a17d92… (hadoop-submit and hadoop-libjars equal the pins). There is no Scala source or build change between 9e881a2 and 0b37c9d (`git diff --stat 9e881a2 0b37c9d -- modules build.sbt project` is empty). Same entries in the same order; 36 er-jar and 4 job-jar entries differ, all `.class`/`.tasty` pairs. Each `.class` differs only in its trailing TASTy UUID bytes; the `.tasty` files differ by a few bytes with the same string table. The pinned hashes come from the main checkout's incremental build, so a clean rebuild does not reproduce them byte for byte (build reproducibility finding, build-engineer follow-up) | phase15-maxfail worktree: target/phase15/p15/s-maxfail/ |
| spark.task.maxFailures 2, local P6 S on branch commit 0b37c9d, attempt 2 (pinned JARs) | the four pinned JARs and `emr-artifact-manifest.json` copied from the main checkout's `target/` (same source), same command | exit 0, all 6 steps exit 0 (stage-in 1 s, hadoop-prep 34 s, ER 92 s, class-origin 3 s, spark-job 346 s, copy-out 2 s); clean tree at 0b37c9d, `pipelineRelevantChangesVsHead` empty; plan carries `spark.task.maxFailures=2`. **All 61 counters equal** the reference run p6-S-20261116T171431Z; pins equal. No task failure and no same-host disk read in this run. Export run:6136b574-aa5c-432f-b1f8-29b199e00ed5, 435 files, 605,715,916 B, retained with SHA256SUMS (all OK; sha256 942b4658…). Versus the 9e881a2 export (433 files), only `edges/type=coauthored_with` has 3 Parquet parts instead of 2, a layout-only difference with equal counters; `counters.json` values are equal, only run IDs and lineage IDs differ | phase15-maxfail worktree: target/phase15/p6/work/p6-S-20261117T163043Z/evidence/summary.json |
