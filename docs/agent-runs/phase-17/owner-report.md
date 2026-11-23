# Phase 17 owner reports (assembled by the coordinator)

Each section summarises one owner's report for this phase in the fields of `docs/agent-runs/README.md`. Commands and outputs are those the owner reported; the coordinator re-ran the ones marked "coordinator". Workers ran on Claude Sonnet 5.5, effort high; the code-reviewer on Claude Opus 5.5, effort high (human instruction of 2026-11-16, quoted in `docs/agent-runs/phase-15/q12-rerun-addendum.md`).

## documentation-engineer, instance 1 (17A-1)

STATUS: COMPLETE (initial write-up; review round 1 repairs: see `repairs.md`)
OWNER: documentation-engineer
WORK ORDER: `docs/agent-runs/phase-17/prompt.md`, package 17A-1
FILES CREATED: `docs/architecture.md`, `docs/data-lineage.md`, `docs/threat-model.md`, `docs/service-limits.md`, `docs/runbook.md`, `docs/api.md`
FILES MODIFIED: none
COMMANDS RUN (observed, offline, read-only):
- `bash scripts/<name>.sh --help` for check, package, plan, deploy, rollback, cleanup, smoke-test, smoke-local, run-bounded-pipeline, run-experiment, archive-evidence, upload-slice, upload-emr-artifacts: all 13 exit 0, usage text of 43 to 190 lines
- `python3 -I scripts/lib/p6_local_chain.py --help`: usage printed
- route count: 12 extended-route cases in `ApiApplication.scala` plus 7 routes matched in `handle` = 19 paths in `openapi/scholarchain.v1.yaml`
- `git ls-files infra | grep -c tfstate`: 0; `git check-ignore -v` on the `*.local.tfvars` files: ignored by `.gitignore:52`
TEST RESULTS: none run (documentation only)
VALIDATION RESULTS: 298 relative links, 0 broken; 0 twelve-digit runs; 0 '@'; 244 numbers checked, 242 in the linked sources and 2 rounded p95 values (4732 and 7077, from 4731.616 and 7076.662) whose exact values are in the source; after round 1 repairs 304 links, 0 broken
RISKS: Neptune bulk load in Session 2, Step Functions, SQS and most DynamoDB tables marked "not verified"; Mermaid not rendered; live rollback not exercised
NEXT GATE: review

## documentation-engineer, instance 2 (17A-2 and 17F)

STATUS: COMPLETE (initial write-up; review round 1 repairs: see `repairs.md`)
OWNER: documentation-engineer
WORK ORDER: `docs/agent-runs/phase-17/prompt.md`, packages 17A-2 and 17F
FILES CREATED: `docs/evaluation.md`, `reports/final-report.md`, `reports/release-manifest.md`
FILES MODIFIED: `README.md`, `docs/demo-script.md`
COMMANDS RUN (observed, offline):
- `python3 -I experiments/scripts/eval16_repro.py --verify`: `REGENERATION: PASS pass=24 fail=0 skipped_scripts=0`, exit 0
- `(cd datasets && shasum -a 256 -c samples/SHA256SUMS)`: 4 samples OK
- `python3 -I experiments/scripts/check_manifests.py`: `RESULT: OK`, 106 file hashes verified
- `--help` of run-bounded-pipeline, smoke-local, plan, cleanup, deploy, package, smoke-test, archive-evidence, run-experiment, `p6_local_chain.py`: usage printed
- `git log --format=%s | wc -l`: 151; `| grep -c '^phase-[0-9]'`: 37; `git tag | wc -l`: 0
TEST RESULTS: none run (documentation only); the release-manifest test counts are the coordinator's full check `20261122T055838Z-17867` on `main` `55fb1b3` (`test-report.md`)
VALIDATION RESULTS: 467 relative links, 0 broken, 0 bad anchors; twelve-digit runs only inside sha256 hex strings; '@' only in `cnguye69@uic.edu` and in `openjdk@17` and curl syntax in README; numbers found in the committed sources except pre-existing README text
RISKS: commands marked "not replayed in 17A (replay in 17G)"; README query examples need a running service; the video link and a release tag are still to be added by the human
BLOCKED-ON EVIDENCE: final release SHA and tag; release build hashes
NEXT GATE: review

## incident-responder (17B)

STATUS: COMPLETE (initial records; review round 1 repairs)
OWNER: incident-responder
WORK ORDER: `docs/agent-runs/phase-17/prompt.md`, package 17B
FILES CREATED: `docs/incidents/README.md` and seven `docs/incidents/2026-11-18-*.md` records (EMR spark-job step, vectors ingest 1 HTTP 401, runtime-archive upload timeout, load-test abort and 5xx burst, deployer session drops, console permission gaps, kit missing the a7/b3b/c5 policies)
FILES MODIFIED: none (the 2026-11-16 record is unchanged)
COMMANDS RUN (observed): read-only reads of the Session 2 decision log, evidence index and logs; link and privacy check script: `files 8 paths_checked 84 unresolved 0 12digit 0 at 0` (initial and after repairs)
VALIDATION RESULTS: evidence differences recorded inside the records (abort time 20:52:44.209Z first failure vs 20:52:49.770Z abort event; poll-file blank stretches; decision-log ordering; derived ingest times; no quoted human decision for the c5 policy; exit codes 255 and 4 at different layers)
RISKS: root cause "not determined" for the EMR class error and the 5xx burst; two records rest on the decision log because the raw logs are private or excluded
NEXT GATE: review

## coordinator (17C, 17D)

FILES CREATED: `docs/agent-runs/phase-15/q12-rerun-addendum.md`; `docs/agent-runs/phase-NN/agent-report.md` for NN = 01-16 (a one-line note plus a copy of that folder's `owner-report.md`; byte-identical below the note except phase 12, where the AWS account ID is replaced by `<acct>`); `docs/agent-runs/phase-{05,08,09,10,11,15}/commit.txt` (from `git log <merge>^1..<merge>^2` of the pull-request merges: 4, 2, 3, 2, 3 and 48 commits); `docs/agent-runs/phase-17/{prompt,owner-report,review,repairs}.md`
COMMANDS RUN (observed): `diff` of each copy against its original below the note (phases 01 and 16 shown identical; all 16 are 2 lines longer than the original); `python3 -m unittest test_billing_replan_14b.NoRealAccountIdIsAdded` in `tests/infra`: Ran 2 tests, OK (after 17D and after the B1 repair)

## hadoop-engineer (17I, work order 2)

STATUS: DONE
OWNER: hadoop-engineer
WORK ORDER: `docs/agent-runs/phase-17/work-order-2-stray-files.md`, package 17I
FILES DELETED: 24 tracked files under the top-level `file:` directory (J05, J07, J08 job-statistics files and their `.crc` files from `HadoopPrepReviewSpec` temp folders `review-block*` and `review-repeat*`), staged with `git rm -r -q -- 'file:'`
FILES CREATED / MODIFIED: none
COMMANDS RUN (observed): `git ls-files 'file:*' | wc -l`: 24; `git diff 3ccd61c HEAD --stat -- modules/hadoop/src/main`: empty; `sbt -batch "hadoop/testOnly edu.uic.cs441.scholarchain.hadoop.HadoopPrepReviewSpec"` (JDK 17): `Tests: succeeded 30, failed 0, canceled 0, ignored 0, pending 0`, `All tests passed.`; afterwards `ls -d file:` prints nothing
CAUSE: a one-slash `file:/<tmp>` stats directory string passed to `FsPaths.file` would resolve `file:` relative to the working directory without the `isFileUri` check (`HadoopIO.scala:27-35`); the current code has that check and a round-trip test (`HadoopPrepReviewSpec.scala:159-171`), so the junk came from an earlier pre-fix working-tree run
RISKS: no test asserts that a `file:` directory is absent; no `.gitignore` entry (build-engineer's file)
NEXT GATE: review, full check

## documentation-engineer, instance 1 (17I follow-up)

FILES MODIFIED: `docs/threat-model.md` lines 63 and 136: the account-ID and e-mail question is stated as decided (keep; no history rewrite) with the coordinator's counts and a link to `human-decision-privacy.md`
VALIDATION RESULTS (owner-reported): threat-model.md 69 relative links, 0 broken, 0 twelve-digit numbers, 0 '@'; all six files 306 links, 0 broken

## factory-engineer (package 17E, work order 3)

STATUS: DONE (draft; ratified by the human, see `ratification-17e.md`)
FILES MODIFIED: `.claude/settings.json` (the four hook `command` values in the form `"$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh`), `.mcp.json` (`github-readonly` header `Authorization: ${GITHUB_MCP_AUTHORIZATION}`), `.claude/MCP-TRUST.md:7` (names the new variable)
VALIDATION RESULTS (owner-reported): JSON parse OK for both files; `bash -n` OK for the four hooks; `validate-agent-files.sh`: "Validated 18 unique agents, reviewer fence, 32 representative ownership paths and 18 routes", exit 0; `scripts/tests` `test_check.py`: Ran 54 tests, OK
NEXT GATE: review, ratification, fresh-session probes, full check

## documentation-engineer (package 17E follow-ups)

FILES MODIFIED: `README.md:57`, `:405`, `:417` (name `GITHUB_MCP_AUTHORIZATION`, whose value includes `Bearer `); `docs/threat-model.md:118` (the change is ratified, with links to the ratification record)
VALIDATION: covered by the coordinator's account-ID scan and full check 3 (`test-report.md`)

## documentation-engineer (17E, after full check 3)

FILES MODIFIED: `docs/threat-model.md:118` only: the hook probes are stated as run on 2026-11-22 (four PASS, one INCONCLUSIVE, file unchanged) with a link to `hook-probes-17e.md`; no stronger claim than the probe record
VALIDATION RESULTS (owner-reported): 71 relative links, 0 broken; 0 twelve-digit numbers, 0 '@', 0 home paths. Coordinator: line 118 links the probe record and no longer says "pending"; `NoRealAccountIdIsAdded` OK. Text-only change after full check 3; no further full check run
