You are the independent, read-only code reviewer for ScholarChain Phase7,
Subphase7A REPAIR ROUND1, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase7.md
   Sections3–7, Subphase7A in Section8 and Section10. Accepted snapshot:
   docs/agent-runs/phase-07/evidence/7a/phase7-plan.md
   SHA256 b54aa12309007bf4758120d8297d1de2eccb497220d3f0de87dc5563fef74ebb.
3. Course Phase7 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
4. docs/agent-runs/phase-07/review.md (verbatim user-supplied REQUEST-CHANGES),
   prompt.md, repairs.md, owner-report.md and test-report.md repair1 sections.
   Then evidence/7a/repair-1/commands.md, final-check.json/excerpt,
   final-audit.json, evidence-migration.json, targeted-results.json,
   source-snapshot.json, files.json, git-visible-files.txt and owner-reports.md.

Checkpoint facts / handoff:
- STATUS: COMPLETE for local F1/F2 repairs, external recheck pending.
- Branch phase-7. Subphase/repair base and current HEAD:
  98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2.
  Reviewed7A tree was uncommitted; no reset, staging, commit or push.
- Repair source changes only:
  modules/storage/src/main/scala/edu/uic/cs441/scholarchain/storage/ManifestRows.scala
  modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/ParquetManifestSpec.scala
  tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentStorageParquetSpec.scala
  New:modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/Phase7ManifestSmokeMain.scala
- Coordinator updated phase-07 reports/review/prompt/indices/references and
  renamed23 retained.log files to.txt. Exact rename pairs and SHA256 values:
  repair-1/evidence-migration.json. Full cumulative tracked/untracked inventory:
  evidence/7a/files.json; repair-relative inventory:repair-1/files.json.
- Cumulative tracked modifications remain build.sbt, project/Dependencies.scala,
  project/ScholarChainBuild.scala, project/Versions.scala, modules/spark/README.md,
  modules/spark/src/main/scala/edu/uic/cs441/scholarchain/spark/Phase6Export.scala.
  Those initial7A edits are unchanged by this repair. New initial implementation
  files remain uncommitted and listed in the cumulative inventory.
- No questions for this repair round. User explicitly requested blocking fixes
  only; original ten Step0 defaults persist. F1 storage-engineer/test-engineer,
  F2 coordinator; N1–N8 listed but not required. Same native owner IDs; no reviewer
  was launched. Coordinator ran owner-requested formatting/tests, disclosed N8.

F1 repair/evidence:
- ManifestMetadata.rowCount accepts nonempty ASCII decimal strings through exact
  toLongOption, rejects overflow/negative/malformed/non-string values, never uses
  Double conversion. Producer output, IDs and hashes are unchanged.
- Both metadata fixtures use Long->ujson.Str and assert the wire shape. New module
  and independent regressions cover exact large Long values and malformed counts
  under freshly valid completion markers.
- Affected targets exit0:storage10/10, IndependentStorage*Spec27/27,
  Phase7NeptuneExportSpec4/4; real16.52s, targeted-tests.txt.
- Clean forked absolute-path smoke exits0,real4.14s against retained
  target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49:
  researcher metadataRows21819, collaboration62757, kcore62757; sampled1row each.
  Actual metadata/completion binding only, no cache writes or full table count/hash
  recomputation. real-manifest-smoke.txt and targeted-results.json.
- Earlier actual-Parquet metadata was synthetic. The first un-forked smoke logged
  a shutdownclasspath exception after success; first forked relative path failed
  because module cwd differed. Both retained; final absolute/forked probe is clean.

F2 repair/evidence:
-23 logs renamed.txt, original bytes/recorded hashes unchanged; all23 Git-visible.
-14 build raw hashes reverified; provider excerpt has separate explicit raw and
  retained hashes. build/log-index.json and all targeted/Spark-targeted metadata
  now point to existing.txt files with verified retained hashes.
- git check-ignore returns1/no matches for23 new paths; git status -uall lists
  them. .gitignore untouched. No agent staging/commit; ready for human commit.
- Verbatim external review and raw/tmp command history intentionally retain.log
  spelling; retired names in migration history are not live retained pointers.

Every sbt command used exactly:
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"

Fresh /usr/bin/time -p sbt -batch check:exit0,596passed/0failed;
core144/Hadoop64/ER39/Spark38/storage10/independent293/build8;
Java17.0.20.1,sbt1.10.7,real681.20s. Expected injected format-stage probe is a
passing build test. Raw log:/tmp/phase7a-repair1-final-check.log,1362175bytes,
SHA256 26f7ad074aa1db1028558326d8826e30fd6e07937ed8ad511a2d5870f12e2497.
Tracked excerpt:repair-1/final-check-excerpt.txt; exact commands/exits/hashes,
including smoke launch failures, in commands.md and targeted-results.json.

All110 scoped source hashes/mtimes stable across final gate; protected Phase6,
control and source metadata files unchanged; verbatim review hash matches.
Tracked diffcheck0; repair source whitespace clean. All launched jobs/agents ended.

Open nonblocking findings (not repaired):
N1 storage-engineer:full source qualification duplicated per metric item.
N2 spark-engineer/storage7B:always-run CSV, no real replay, sidecar/marker coverage.
N3 storage-engineer:transaction retry lacks fixed ClientRequestToken.
N4 storage-engineer:session/reservation TTL expiration can diverge.
N5 storage-engineer:raw idempotency GSI key byte limit absent.
N6 test-engineer:SDK S3-412 and ledger CAS/cancel stub gaps,7Chardening.
N7 storage-engineer:hardcoded evidence prefix.
N8 coordinator/process:owner-requested formatter execution disclosed.
Other Phase6/later gates persist. No liveAWS/provider call, real CSV replay,
7B work, human-gate edit or independent acceptance is claimed.

Review rules:
- Read-only. Do not edit, run builds/tests, call AWS/providers, change data,
  commit/push or read secrets. Inspect git diff from base plus untracked files.
- Recheck F1 strict producer-encoding compatibility and malformed-count rejection,
  test independence/fixture encoding, bounded smoke claims and evidence fidelity.
- Recheck F2 every renamed file's Git visibility, byte hash and live reference;
  preserve distinction between raw execution history, excerpts and retained paths.
- Check scope/one-writer ownership/config/provenance/honest test evidence and
  cloud gates. Report ALL confirmed findings in one pass with ownership.
- Apply Phase7 ID parity, reader separation, conditional/idempotent semantics,
  vector text-hash and live exclusion checks only as applicable to7A.
- Do not demand later7B/7C/live work or N1–N8 fixes as part of this blocking-only
  round unless you confirm a new blocking defect. Distinguish blockers,
  nonblocking observations and unverified gates. No self-approval.

Return:
1. VERDICT:APPROVE or REQUEST-CHANGES for Subphase7A repair round1.
2. Findings:severity,path:line,evidence/reasoning,impact,owner,acceptance check,
   blocking yes/no; explicit F1/F2 recheck disposition and N1–N8 open status.
3. Required report fields from docs/agent-runs/README.md.
4. A NEXT PROMPT in one fenced code block:
   If APPROVE:append verdict verbatim as user-supplied review to phase-07/review.md;
   confirm the user committed approved7A (ask if not); only then begin7B from the
   actual plan path with Step0. Do only that subphase, launch no reviewer,
   return Section10 handoff/prompt, stop.
   If REQUEST-CHANGES:append verdict verbatim and route findings in repairs.md;
   fix only blocking findings through owners; rerun affected tests and fullcheck
   with exact Section2JDK17; no7B; return filled Section10 recheck prompt and stop.
