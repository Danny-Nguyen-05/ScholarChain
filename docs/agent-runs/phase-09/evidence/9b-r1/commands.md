# Subphase 9B repair round 1 commands

Every sbt invocation uses exactly:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Preflight git status/branch/rev-parse reads exit0: branchphase-9,base/HEAD f139f9c925b4925864a2c9a33734d869a1929cd2; reviewed9B uncommitted,22/22sourcehashesverified beforerepair. No reset/discard/staging.
java -version > /tmp/phase9b-r1-java-version.txt 2>&1: exit0,Homebrew OpenJDK17.0.20.1. Builds not run yet; root serializes every gate.

Targeted1: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeArtifactStorageSpec' 'rag/testOnly *Runtime9BSpec' 'independentTests/testOnly *Runtime9B* *Runtime9AEvidenceSpec' > /tmp/phase9b-r1-targeted-1.log 2>&1`; exit0,storage15/RAG17/independent67=99passed0failed,11.66seconds. No failed repair-round attempt. RawSHA256 6ab60e10fbb8af910f580827ae3411b8c52bf2f75ea031170324146e0bbeec3d.

Fullcheck1: `/usr/bin/time -p sbt -batch check > /tmp/phase9b-r1-check-1.log 2>&1`; exit0,1004passed/0failed,717.84seconds. Counts core196/Hadoop64/ER39/Spark38/storage66/RAG90/independent503/build8. Expected injectedformatprobe is the passingbuildselftest; finalTestRunMarker ran. RawSHA256 6b4755d9be0c7449f27d1d4ace7c1942bd6728a0b39f7935823e5a8f373ef42a. No repair-round failedattempt.

Evidence-only assembly note: an initial Python report-append helper had a syntax error before execution (exit1, no file writes); corrected helper succeeded. No build/source change or extra test run resulted.
