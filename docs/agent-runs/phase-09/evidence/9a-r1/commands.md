#9A repair round1 command ledger

Preflight: git status --short, git branch --show-current, git rev-parse HEAD → exit0;
phase-9, HEAD/base5fee9ffc607cf802e4aaddf4a261c21f1f232fec; preserve uncommitted9A tree.
All31 previous source hashes matched prior source-files.json before repair writes.

First gate toolchain:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
```
Exit0: openjdk17.0.20.1 2026-08-18, Homebrew17.0.20.1+0.
Every sbt command below uses exactly those environment exports.

External review retained verbatim and SHA-bound; B1–B4 routed, N1–N7 logged/deferred.
User instruction "Fix all blockings for me" selects B4 FIX NOW. No additional questions.

Core target1:
```sh
sbt -batch 'core / Test / testOnly *RuntimeContractSpec *SerializationContractSpec' > /tmp/phase9a-r1-core-targeted-1.log 2>&1
```
Exit0;21passed0failed (16runtime contract cases +5 frozen serialization cases).
No legacy wire example changed. No production fix required by this gate.

Storage target1:
```sh
sbt -batch 'storage / testOnly *RuntimeArtifactStorageSpec' > /tmp/phase9a-r1-storage-targeted-1.log 2>&1
```
Exit0;15passed0failed. Includes B3 stored-window absence and B4 mixed warm reads,
concurrent cold reads (one GET), first-load corruption and failed-load retry.
These are structural reuse/correctness tests, not measured production latency.

Independent target1:
```sh
sbt -batch 'independentTests / Test / testOnly *IndependentRuntime9A*' > /tmp/phase9a-r1-independent-targeted-1.log 2>&1
```
Exit0;64passed0failed,6suites. Includes42new hand-derived repair cases and22originalruntime
cases, including fresh actualG1 producer/export→artifact materialization. RAG main sources
were frozen during this gate; owner authored RAGTest files separately, which this target does
not compile or execute. No unsupported case was weakened to obtain the pass.

RAG/format target1:
```sh
sbt -batch 'rag / Test / testOnly *Runtime9ASpec *Runtime9ARepairSpec' 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'rag / Compile / scalafmt' 'rag / Test / scalafmt' 'independentTests / Test / scalafmt' > /tmp/phase9a-r1-rag-format-targeted-1.log 2>&1
```
Exit1;test compile failed before tests/formatting: helper execute with a default third argument
collided with inherited ScalaTest execute default getter. RAG owner renamed test helper to
planOutput; production unchanged. Raw small failure log retained.

RAG/format target2 (same exact sbt arguments as target1, output /tmp/phase9a-r1-rag-format-targeted-2.log):
Exit0;RAG40passed0failed (20original+20repair); all7 requested touched-project formatter tasks
completed successfully. Core21/storage15/RAG40/independent64 =140targeted passed cases.
Only mechanical formatting followed the passing targeted tests; final full check uses frozen
formatted source-files.json and repair-files.json.

Full gate1:
```sh
/usr/bin/time -p sbt -batch check > /tmp/phase9a-r1-check-1.log 2>&1
```
Exit0;725.07s wall;901passed0failed: core173/Hadoop64/ER39/Spark38/storage66/RAG73/
independent440/build8. Expected injected format-stage failure is the passing build self-test;
final TestRunMarker success observed. Raw log path/hash and meaningful excerpts retained.

Final integrity:34source/config/test/prompt hashes unchanged since pre-full-gate snapshot,
git diff --check exit0, bounded credential-literal scan0findings, no secret locations accessed.
External review retained verbatim in review.md and SHA-bound file. No source changes after gate.


User-authorized commit packaging (2026-10-26): global *.log ignore required explicit staging
of17lean evidence logs/excerpts. Staged check exposed terminal trailing spaces in3small
compiler-output copies. Display copies had only trailing spaces/tabs removed; original raw
/tmp files remain byte-identical. Exact raw/display hashes and transformation are recorded
in commit-log-normalization.json. Source hashes/full-gate result records/reviews unchanged.
No tests rerun for evidence-display whitespace cleanup.
