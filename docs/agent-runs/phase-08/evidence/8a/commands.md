# 8A observed commands

Preflight: `git status --short` exit0 empty; `git branch --show-current` exit0 main; `git rev-parse HEAD` exit0 8503e1715cbcaf043fd68213c5b08731e9de9ba7. `git switch -c phase-8` initially exit128 (sandbox), native approved identical retry exit0.

All sbt commands use:
```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```
`java -version` exit0; output java-version.txt.

Prerequisite, before rag production source:
```text
sbt -batch 'independentTests / Test / scalafmt' scalafmtSbt 'independentTests / Test / testOnly *IndependentStorageRuntimeFenceSpec'
```
First attempt exit1: sbt cache boot-lock sandbox denial, prerequisite-1.txt/.exit. Identical command with native sandbox escalation exit0, prerequisite-2.txt/.exit, 8 tests succeeded/0 failed, 0 runtime roots at this checkpoint. Repair fixes character literals/interpolated executable code in the test heuristic; does not prove IAM or full Scala semantics. Build owner requested scalafmtSbt; test owner requested tests scalafmt. No live test/provider call.

Interface gate (owner-requested formatting):
```text
sbt -batch 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'core / Test / testOnly *EmbeddingContractSpec' 'storage / Compile / compile'
```
Output interfaces-1.txt/.exit; result recorded after completion. Native cache escalation used.

Interface gate observed exit0: core contract8/8; storage production compiled. New storage guarded-match exhaustivity warning routed to storage owner (not suppressed). Core/storage formatter execution was explicitly requested by owners.

RAG early compile:
```text
sbt -batch 'rag / Compile / scalafmt' 'rag / Compile / compile'
```
rag-compile-1.txt/.exit, exit0, three RAG production sources compiled. Storage updated sources also compiled without prior exhaustivity warning.

Focused gate:
```text
sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / testOnly *EmbeddingStorageSpec' 'independentTests / Test / testOnly *IndependentEmbeddingContractSpec *IndependentEmbeddingStorageSpec *IndependentEmbeddingRenderingSpec *IndependentStorageRuntimeFenceSpec'
```
targeted-1.txt/.exit, exit0; storage11/11 and independent23/23; actual runtime fence scans3 sources. Subsequent logging/completion replay and RAG module test work still pending at this checkpoint.

Final core/storage affected gate:
```text
sbt -batch 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'core / Test / testOnly *EmbeddingContractSpec' 'storage / Test / testOnly *EmbeddingStorageSpec'
```
targeted-2.txt/.exit exit0, core9/9 storage12/12. Unicode boundary, completion-checkpoint replay and safe JSON summary tests included.

Final RAG/independent affected gate:
```text
sbt -batch 'rag / Compile / scalafmt' 'rag / Test / scalafmt' 'rag / Test / test' 'independentTests / Test / testOnly *IndependentEmbeddingContractSpec *IndependentEmbeddingStorageSpec *IndependentEmbeddingRenderingSpec *IndependentStorageRuntimeFenceSpec'
```
targeted-3.txt/.exit exit0, RAG14/14 independent23/23.

Full gate (frozen302-source/build/test/doc snapshot; no owner edits while running):
```text
/usr/bin/time -p sbt -batch check > /tmp/phase8a-final-check-1.txt 2>&1
```
Exit recorded in final-check-1.exit; result unverified until completion. Same JDK17 environment. Live test remains excluded.

Full gate FINAL: exit0,718 passed/0failed; groups153/64/39/38/44/14/358/8. Real683.81s. Expected injected checkProbeInjectFailure observed; build verification8/8 passed. Final-check.json and line-numbered excerpt retain summary/raw hash. Raw log1,379,298bytes outside repo at /tmp/phase8a-final-check-1.txt.

Final audit commands: git diff --check exit0; Python SHA256/mtime comparison of302 frozen files finds0changes; newly created source whitespace check0violations; original plan byte comparison matches snapshot. Human/control/upstream tracked paths absent from git diff. Exact branch/head and file inventories retained in final-audit.json/files.json. All launched build sessions have returned completion; specialist agents returned final reports.
