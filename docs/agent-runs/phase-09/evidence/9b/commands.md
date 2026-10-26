# Subphase 9B exact execution record

Every sbt invocation uses:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Preflight: `git status --short` (empty before delegation), `git rev-parse HEAD`
(f139f9c925b4925864a2c9a33734d869a1929cd2), `git branch --show-current` (phase-9); all exit0.
`java -version > /tmp/phase9b-java-version.txt 2>&1`: exit0; Homebrew OpenJDK17.0.20.1.
No sbt gates run yet. Root serializes execution; specialists do not start concurrent builds.

Core targeted1: `/usr/bin/time -p sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/testOnly *RuntimeContractSpec *RuntimeBundlePartitionSpec *RuntimeEvidenceIdSpec' > /tmp/phase9b-core-targeted-1.log 2>&1`; exit 0,36 passed/0 failed,13.82seconds. Formatting ran before tests. SHA256 in core-targeted-1-result.json.

RAG compile1: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/compile' > /tmp/phase9b-rag-compile-1.log 2>&1`; exit0,6.33seconds,7sourcescompiled, no testsrun. Hashinrag-compile-1-result.json.

Integrated target1: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'rag/testOnly *Runtime9BSpec' 'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec' > /tmp/phase9b-targeted-1.log 2>&1`; exit1,7.02seconds. Module test compilation failed on fixture run name collision;0testsrun. Independent target not reached. Owner repair routed; retained target1 result/excerpt.

Integrated target2: `/usr/bin/time -p sbt -batch 'rag/Test/scalafmt' 'rag/testOnly *Runtime9BSpec' 'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec' > /tmp/phase9b-targeted-2.log 2>&1`; exit1,6.19seconds. RAG14run12passed2failed: default four-hop context4234>4096 leads required builder/workflow abstention; independent target not reached. Routed compact rendering repair; no assertion weakened.

rag-targeted-3: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'rag/testOnly *Runtime9BSpec' > /tmp/phase9b-rag-targeted-3.log 2>&1`; exit0,14passed/0failed,6.14seconds. Exacthashes in correspondingresultJSON.

independent-targeted-1: `/usr/bin/time -p sbt -batch 'independentTests/Test/scalafmt' 'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec' > /tmp/phase9b-independent-targeted-1.log 2>&1`; exit1,62passed/1failed,9.71seconds. Exacthashes in correspondingresultJSON.

Core targeted2: `/usr/bin/time -p sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/testOnly *RuntimeContractSpec *RuntimeBundlePartitionSpec *RuntimeEvidenceIdSpec' > /tmp/phase9b-core-targeted-2.log 2>&1`; exit0,39passed/0failed,11.95seconds, includes3identity-contractcases.

Final integrated target4: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeArtifactStorageSpec' 'rag/testOnly *Runtime9BSpec' 'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec' > /tmp/phase9b-targeted-4.log 2>&1`; exit0, storage15/RAG15/independent66=96passed0failed,12.78seconds. Corefinaltarget2adds39for135combinedtargetedpasses.

Full gate1: `/usr/bin/time -p sbt -batch check > /tmp/phase9b-check-1.log 2>&1`; exit0,707.18seconds,1001passed0failed. Modules core196/Hadoop64/ER39/Spark38/storage66/RAG88/independent502/build8. Expected injected format-stage failure is the passing build self-test; final TestRunMarker ran. Full raw remains outside Git, SHA256 4a3835389a36c942220ca8650876b04d2b8e69087f8a1b8522bb3fd670077fea. No tests rerun afterward.
