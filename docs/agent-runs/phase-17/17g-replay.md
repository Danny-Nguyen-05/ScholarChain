# Phase 17 package 17G: clean-checkout replay and grading-agent self-check

Run by the coordinator on 2026-11-22 and 2026-11-23 (America/Chicago), after the human asked to run 17G now instead of on Tuesday ("alright instead waiting until tuesday, can you do it now ?"). Observed output only. The commands ran from a script in the coordinator's session scratchpad (not tracked); each step logged its command, its last output lines and its exit code.

## Setup

- Fresh clone of `main` with `gh repo clone` into a new sibling folder `ScholarChain-17g2`: HEAD `d1d4fe7` ("Merge pull request #15 from Danny-Nguyen-05/phase-17"), clean tree. Started 2026-11-22 23:30 CST.
- JDK 17 (`JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home`, OpenJDK 17.0.20.1), sbt 1.10.7, Terraform 1.13.5. Offline except dependency resolution, `terraform init` provider download and the AI-judge calls.
- An earlier clone of `main` at `6cf5aa8` (folder `ScholarChain-17g`, 2026-11-22 22:33 CST) gave the same `sbt clean check` result (1,773 succeeded, 0 failed, 2 canceled, sbt total time 14:34) and the first V1/V2/V3 results that led to work order 4 (`work-order-4-17g-gaps.md`). Its README replay was stopped at the human's request ("kill the current check") and restarted on the `d1d4fe7` clone below.

## Build and full check (clone at `d1d4fe7`)

| Command | Result |
|---|---|
| `sbt -batch clean check` | exit 0; `Tests: succeeded` 208, 64, 39, 53, 180 (1 canceled), 298, 194, 707, 30 (1 canceled): 1,773 succeeded, 0 failed, 2 canceled; `[success] Total time: 888 s (14:48)`. The `[error] ... injected format-stage failure` line in the log is the build's own `checkProbeInjectFailure` probe. The clone's test marker was written. |
| `bash scripts/check.sh` | run id `20261123T054553Z-70824`, started 23:45:53 CST, ended 01:12:31 CST: constitution PASS (2071 JSON files parse), hooks PASS, shell PASS, python PASS (84 files compile), terraform PASS (12, 19, 114, 40, 6, 333 passed, 0 failed), script-tests PASS (`scripts/tests` 1200 OK, `scripts/phase12d-spike/tests` 78 OK, billing 121, 84, 39 OK, `tests/scripts` 487 run, 484 executed, 3 skipped, OK, `tests/infra` 468 OK), sbt PASS (194, 707, 30 succeeded, 0 failed, 1 canceled in the last block). `RESULT: PASS gates=7`, exit 0. |

The 3 skipped tests in `tests/scripts` were 0 on the author's working tree (full checks 1-3 in `test-report.md`); a fresh clone lacks some git-ignored local inputs.

## README command replay (same clone, offline)

| README command | Exit | Observed |
|---|---|---|
| `sbt -batch fmt` | 0 | `git status --porcelain` empty afterwards (tree unchanged) |
| `sbt -batch compile` | 0 | `[success]` |
| `sbt -batch core/test` | 0 | `Tests: succeeded 208, failed 0` |
| `sbt -batch packageRelease` | 0 | Hadoop submit JAR, dependency bundle, Spark job JAR and ER job JAR verified, `[success]` |
| `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)` | 0 | 4 files `OK` |
| `python3 -I experiments/scripts/check_manifests.py` | 0 | `RESULT: OK (placeholders allowed; run with --final before the commit freeze)` |
| `python3 -I experiments/scripts/eval16_repro.py --verify` | 4 | `REGENERATION: PARTIAL pass=10 fail=0 skipped_scripts=5`; the skipped scripts need git-ignored local inputs that a fresh clone lacks (`INPUTS-UNAVAILABLE`) |
| `bash scripts/plan.sh --env course` (as then written in the README) | 2 | `RESULT: REFUSED step=usage reason=region required: --region or SCHOLARCHAIN_AWS_REGION` |
| `bash scripts/plan.sh --env course --region us-east-2` (coordinator, working tree) | 0 | `RESULT: DRY-RUN no aws or terraform command was run and no file was written; re-run with --execute (approval point 4) to plan` |
| `bash scripts/smoke-local.sh --build` | 0 | `RESULT: PASS local offline-synthetic query-api passed all smoke checks (the six plus the semantic route and its cache counter) on 127.0.0.1:<port>` |
| `python3 -I scripts/lib/p6_local_chain.py --help` | 0 | usage printed; the P6 local chain itself was not run (it needs the pinned runtime archive and the Hadoop client classpath file) |
| `git status --porcelain` before the full check | | empty |

Not replayed: `bash scripts/package.sh` (the Docker daemon was not running), every live AWS step (plan `--execute`, deploy, load, smoke against a deployed host, rollback, cleanup: human-gated and paid), and the query examples against a deployed host (no deployed stack). The README `plan.sh` line was corrected afterwards by the documentation-engineer (`--region us-east-2`).

## Grading-agent self-check (advisory; on the `d1d4fe7` clone)

Course self-check tools V1 1.0.3, V2 2.3.0, V3 3.0.0 (Claude Code adapter, `claude-sonnet-5-5`), from the coordinator's local copy of the course autograder repository; results kept outside the repository.

- V1: 36 pass, 6 fail, 7 warn, 9 info. F05 and F07 PASS (package 17E); E01 and E06 PASS (work order 4). Remaining fails: G02 (`phase-15/commit.txt`, an incident ID with a date read as a hash), G03 (commit messages of early phases), K01 and K02 (secret-shaped test fixtures), E02 (free-text OWNER lines in copied reports), E03 (early phases committed in bulk).
- V2: dataset engineering 7 met, 1 partial; Hadoop MapReduce 7 met, 5 partial (HADOOP-04, -06, -09, -10, -11); Spark analytics 11 met.
- V3: agentic factory 9 met, 1 partial (FACTORY-07, citing G02 and E02); FACTORY-01 met after work order 4.
- Cost reported in the judges' result files (API-equivalent, charged to the human's Claude usage): on `6cf5aa8`, V2 USD 0.62 and V3 USD 0.56; on `d1d4fe7`, V2 USD 0.71 and V3 USD 0.51.

## Changes after this replay (in the same push)

Not covered by the clone run above; checked by review and by the working-tree full check recorded in `test-report.md`:

- `phase-15/commit.txt` lists hashes only; the subjects moved unchanged to `phase-15/merged-subjects.md` (coordinator; matches `git log` for both merges, empty diff) for V1 G02.
- `modules/hadoop/src/test/.../CoauthorPairGenerationSpec.scala`, 37 tests (hadoop-engineer; tests only, production code unchanged) for HADOOP-10.
- README, `docs/**` and `reports/**` replay notes, the `plan.sh` command, the Hadoop per-job execution table and a known-limitations note (documentation-engineer) for HADOOP-11 and HADOOP-04, -06, -09.
- Review: code-reviewer (Claude Opus 5.5, effort high) round 1 REQUEST CHANGES (1 major: S3 access described wrongly; minors and nits), repaired, round 2 APPROVE; see `review.md`.
