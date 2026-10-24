# 8B command record

All sbt commands use:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Preflight: `git status --short --branch` clean phase-8 tracking origin/phase-8; `git rev-parse HEAD` 3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e. Actual Google Drive plan copied to phase8-plan.md; `cmp` exit0. `java -version` exit0,17.0.20.1.

First `sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/testOnly *EmbeddingContractSpec'` exited1 before compilation: sandbox blocked ~/.sbt/boot/sbt.boot.lock. Retained core-1.txt. Same exact command rerun with native sandbox escalation, core-2.txt: exit0,13passed0failed. Coordinator executes owner-requested format/gates; module owner authors code.

Read-only preflight attempted a non-existent Phase6Loaders.scala path, exit1; corrected file discovery found ManifestRows.scala and existing completed export reader. No file changes resulted.

Early combined command:
```sh
sbt -batch 'storage/Compile/scalafmt' 'storage/Compile/compile' 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'rag/Test/compile' 'independentTests/Test/scalafmt' 'independentTests/Test/compile' 'independentTests/Test/runMain edu.uic.cs441.scholarchain.independent.IndependentEmbeddingG1ExportMain target/phase8b-g1-export'
```
compile-g1-1.txt, exit1: failed first storage formatter on nested tuple pattern syntax in LocalEmbeddingState.scala:76; compile and G1 harness did not execute. Routed to storage owner.

`sbt -batch 'storage/Compile/scalafmt' 'storage/Compile/compile'` → storage-compile-2.txt exit0 after storage owner syntax correction.

`sbt -batch 'storage/Compile/scalafmt' 'storage/Test/scalafmt' 'storage/testOnly *EmbeddingStorageSpec *EmbeddingGroupStateSpec'` → storage-targeted-1.txt exit0,19passed/0failed (13+6).

`sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'rag/Test/compile' 'independentTests/Test/scalafmt' 'independentTests/Test/compile' 'independentTests/Test/runMain edu.uic.cs441.scholarchain.independent.IndependentEmbeddingG1ExportMain target/phase8b-g1-export'` → compile-g1-2.txt exit1, RAG compilation: ambiguous core/storage StorageConfig import in LiveEmbeddingIngestMain.scala:233. Independent compile/G1 generation did not run. Routed to RAG owner.

After usage-limit interruption and user “continue”, storage owner separated admin fake class/alias (implementation unchanged). `sbt -batch 'storage/Compile/scalafmt' 'storage/Test/scalafmt' 'storage/testOnly *EmbeddingStorageSpec *EmbeddingGroupStateSpec'` → storage-targeted-2.txt exit0,19passed0failed after extraction.

Latest affected+G1 command:
```sh
sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'rag/testOnly *EmbeddingRagSpec *EmbeddingRetrievalSpec *LiveEmbeddingGuardSpec' 'independentTests/Test/scalafmt' 'independentTests/Test/compile' 'independentTests/testOnly *IndependentEmbedding*Spec *IndependentStorageRuntimeFenceSpec' 'independentTests/Test/runMain edu.uic.cs441.scholarchain.independent.IndependentEmbeddingG1ExportMain target/phase8b-g1-export'
```
Exit0. RAG25passed0failed; independent39passed0failed. Actual fence5 runtime/20 inspected files, no findings; fence unchanged. G1 producer exact10researchers/9canonicalworks/18windowededges,28tables published. RawoutsideGit /tmp/phase8b-targeted-g1-3.txt; hash/size and line-numbered leanexcerpt retained. Warnings prefixed [error] by forked JVM are Spark plan truncation/native Hadoop warnings, not gate failures.

Local acceptance:
```sh
sbt -batch 'independentTests/Test/runMain edu.uic.cs441.scholarchain.independent.IndependentEmbeddingLocalReplayMain target/phase8b-g1-export target/phase8b-g1-local-acceptance' 'independentTests/Test/runMain edu.uic.cs441.scholarchain.independent.IndependentEmbeddingLocalReplayMain target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49 target/phase8b-real-local-acceptance'
```
local-acceptance-1.txt exit0. G1 12written→12unchanged/0embeddingcalls; real16written→16unchanged/0embeddingcalls. Real12summaries+3topic+1institution span all5types. Fresh counters and manifest hashes equal; all12/16persisted pointers/hash resolve, qualifications hash verified. The completed real source verifies100765summaries+3topics+1institution under scan cap; only16documents embedded withfake. Outputs/state stay ignored under target; lean reports retained here.

Direct documented CLI separate sbt-process replay, exact arguments retained in cli-process-replay-1.txt:
`sbt -batch 'rag/Compile/runMain edu.uic.cs441.scholarchain.rag.EmbeddingIngestMain --export target/phase8b-g1-export --work-manifest target/phase8b-g1-export/load-manifests/s3vectors.json --config target/phase8b-g1-local-acceptance/local-config.json --state target/phase8b-g1-local-acceptance/state-a.json --report target/phase8b-g1-local-acceptance/process-replay-report.json --manifest-output target/phase8b-g1-local-acceptance/process-replay-manifest.json --run-id g1-process-replay' 'rag/Compile/runMain edu.uic.cs441.scholarchain.rag.EmbeddingIngestMain --export target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49 --work-manifest target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49/load-manifests/s3vectors.json --config target/phase8b-real-local-acceptance/local-config.json --state target/phase8b-real-local-acceptance/state-a.json --report target/phase8b-real-local-acceptance/process-replay-report.json --manifest-output target/phase8b-real-local-acceptance/process-replay-manifest.json --run-id real-process-replay'`
Exit0 and correct12/16unchanged0calls, but Hadoop shutdown threads threw NoSuchFileException against sbt target/bg-jobs copied jars after command success. Not treated as clean final CLI validation. Routed minimal forked RAG run setting to build owner; no source workaround or hidden suppression.

Forked directCLI retry: `sbt -batch scalafmtSbt` followed by the same G1/real directCLI arguments, output labels `fork-replay`, runIDs g1-fork-replay/real-fork-replay. cli-process-replay-2.json/rawlog/excerpt retain exact command and observed exit0/counts12/16unchanged0calls. Forking fixed deleted-JAR shutdown exceptions, but childJVM lacked the explicit parent's logback property, producing235MB DEBUG output. Raw stays outsideGit; only count/command excerpts retained. Routed forwarding of the explicitly supplied logback property to build owner before final clean CLI replay.

Final directCLI replay: `sbt -batch scalafmtSbt` followed by same G1/real documented directCLI arguments with output labels final-process and runIDs g1-final-process/real-final-process. Exact invocation lines/rawoutput retained cli-process-replay-3.txt, exit0: forkedJVM,12/16unchanged,0embeddingcalls, stablemanifesthashes, no missing-JAR shutdown exceptions and no DEBUG output. Forwarding only optional logback.configurationFile from explicit required environment.

Frozen-source scope/hash in frozen-source.json; full command started on that snapshot:
```sh
/usr/bin/time -p sbt -batch check > /tmp/phase8b-final-check-1.txt 2>&1
```
Exit/results pending at this checkpoint; no extra full run unless this one fails or code changes.

Final full gate completed exit0,756passed0failed,678.84s real. Module totals157/64/39/38/51/25/374/8. Raw size1381548 and SHA25691ef687108bcb2ec6083b1033197a6373477e49130bb68ec464659e34149ea59; final-check.json and final-check-excerpt.txt retain observed evidence. Expected injected build failure-path self-test present. Post-gate frozen-file audit verifies254 files unchanged and30 source records against source-files.json; plan cmp0 and source diff --check0.
