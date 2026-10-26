# Subphase 9C commands and observed results

Every sbt command uses:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Preflight git status/HEAD/branch reads exited0: initial tree clean, phase-9, HEAD2527de01252286080e6db776b9cc0199a9353e1e. All22approved9B source blobs match the committed review manifest.
java -version > /tmp/phase9c-java-version.txt 2>&1: exit0, Homebrew OpenJDK17.0.20.1. No sbt gate run yet. Root serializes every build; owners author feature tests without concurrent builds.

Core targeted1: `/usr/bin/time -p sbt -batch 'core/Compile/scalafmt' 'core/Test/scalafmt' 'core/testOnly *RuntimeContractSpec *RuntimeBundlePartitionSpec *RuntimeEvidenceIdSpec *Runtime9CContractSpec' > /tmp/phase9c-core-targeted-1.log 2>&1`; exit0,50passed0failed,16.10seconds. Formatting ran before tests; raw SHA-256 5c834634f91ef13041e33c7c3281042c815e9c73eee264e1a806da8703cbf507.

storage-targeted-1: `/usr/bin/time -p sbt -batch 'storage/Compile/scalafmt' 'storage/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' > /tmp/phase9c-storage-targeted-1.log 2>&1`; exit1,13passed/1failed,10.85seconds. Storage test-only pointer-size assumption corrected; production unchanged.

rag-compile-1: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/compile' > /tmp/phase9c-rag-compile-1.log 2>&1`; exit0,0passed/0failed,13.34seconds. Production compile passed; existing/new non-local-return warnings retained.

Evidence-only helper correction: first result-record Python script had a syntax error before execution, no writes; corrected script succeeded. No source/build change or test rerun resulted.

Integrated targeted1: `/usr/bin/time -p sbt -batch 'storage/Test/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' 'rag/testOnly *Runtime9CSpec' 'independentTests/testOnly *Runtime9C*' > /tmp/phase9c-targeted-1.log 2>&1`; exit1,storage14passed/RAG14passed1failed,11.36seconds; independent target not reached. Full raw/hash retained; long assertion excerpt explicitly clipped. Owners repair benchmark positives without weakening expectations.

Independent targeted1: `/usr/bin/time -p sbt -batch 'independentTests/testOnly *Runtime9CVerificationSpec *Runtime9CSynthesisSpec *Runtime9CTrustSpec *Runtime9CWorkflowSpec' > /tmp/phase9c-independent-targeted-1.log 2>&1`; exit1,63passed1failed,10.78seconds. Natural compare-community phrase unsupported; owner repairs. RAG edits completed immediately before diagnostic freeze; final frozen gate will rerun after repairs.

Integrated targeted2: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' 'rag/testOnly *Runtime9CSpec *Runtime9ASpec *Runtime9ARepairSpec *Runtime9BSpec' 'independentTests/testOnly *Runtime9C* *Runtime9B* *Runtime9APlannerSpec *Runtime9AResolverSpec *Runtime9ARepairPlannerSpec *Runtime9ARepairResolverSpec *Runtime9AEvidenceSpec' > /tmp/phase9c-targeted-2.log 2>&1`; exit1,storage14passed,6.58seconds; RAG compile invalidregexescape, other targets not reached. Owner corrects Scala regex quoting; assertion coverage retained.

Integrated targeted3: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' 'rag/testOnly *Runtime9CSpec *Runtime9ASpec *Runtime9ARepairSpec *Runtime9BSpec' 'independentTests/testOnly *Runtime9C* *Runtime9B* *Runtime9APlannerSpec *Runtime9AResolverSpec *Runtime9ARepairPlannerSpec *Runtime9ARepairResolverSpec *Runtime9AEvidenceSpec' > /tmp/phase9c-targeted-3.log 2>&1`; exit1,storage14/RAG72passed,independent208passed1failed,12.90seconds. All new9Ccases/benchmark positives passed; old9B byte-bound assertion updated to approved effective persisted cap; original context/whole-path assertions retained.

Integrated targeted 4: `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' 'rag/testOnly *Runtime9CSpec *Runtime9ASpec *Runtime9ARepairSpec *Runtime9BSpec' 'independentTests/testOnly *Runtime9C* *Runtime9B* *Runtime9APlannerSpec *Runtime9AResolverSpec *Runtime9ARepairPlannerSpec *Runtime9ARepairResolverSpec *Runtime9AEvidenceSpec' > /tmp/phase9c-targeted-4.log 2>&1`; exit 0; storage 14, RAG 73, independent 211 passed (298 total), zero failures; 14.71 seconds. All 85 independent 9C cases passed. Raw SHA-256 4e27b6d1ca269408c09e42399a780b8036d59b609f4ef4575e2d33bd9dbdbb4d.

CLI benchmark 1: `/usr/bin/time -p sbt -batch 'rag/runMain edu.uic.cs441.scholarchain.rag.RuntimeWorkflowMain --benchmark' > /tmp/phase9c-cli-benchmark-1.log 2>&1`; exit 0; all 15 cases passed literal expected fields and outcomes; 4.76 seconds. Raw SHA-256 ca2b47b883cecbae4becde5f4ed494cfe487596f9e7d5c172531b70c95a74d17. Full generated audits stay in /tmp only.

Evidence helper correction: initial CLI JSON parser omitted sbt fork log prefix and exited before writing records; corrected by stripping `[info] `. Full check had already started serially after the successful CLI process. No source edits or overlapping builds resulted.

Full check 1: `/usr/bin/time -p sbt -batch check > /tmp/phase9c-check-1.log 2>&1`; intentionally terminated via TERM to its sbt JVM; exit 143, 112.1 seconds. The final ambiguity response discarded candidates, found during packet inspection. This run is not a pass; owners repair and coordinator reruns targeted/full. Raw SHA-256 296a41b4cf4ab78dd35dcb299d77e152546a810f785a7a86e618ce9e0b400ea3.

Integrated targeted 5 (after ambiguity repair): `/usr/bin/time -p sbt -batch 'rag/Compile/scalafmt' 'rag/Test/scalafmt' 'independentTests/Test/scalafmt' 'storage/testOnly *RuntimeAuditStorageSpec' 'rag/testOnly *Runtime9CSpec *Runtime9ASpec *Runtime9ARepairSpec *Runtime9BSpec' 'independentTests/testOnly *Runtime9C* *Runtime9B* *Runtime9APlannerSpec *Runtime9AResolverSpec *Runtime9ARepairPlannerSpec *Runtime9ARepairResolverSpec *Runtime9AEvidenceSpec' > /tmp/phase9c-targeted-5.log 2>&1`; exit 0; storage 14, RAG 74, independent 211 passed (299 total), zero failures; 16.31 seconds. Raw SHA-256 03be3286d55e126145eb6b864216cb10042b17eaaaed84d13b5903cd159e7200.

CLI benchmark 2 after ambiguity repair: `/usr/bin/time -p sbt -batch 'rag/runMain edu.uic.cs441.scholarchain.rag.RuntimeWorkflowMain --benchmark' > /tmp/phase9c-cli-benchmark-2.log 2>&1`; exit 0; all 15 literal benchmark cases passed and both unselected homonyms returned; 4.45 seconds. Raw SHA-256 b08d7aa37c9dfcaa3ea6b278760e974b430b7f7baf01c3d82961082744b88986.

Full check 2: `/usr/bin/time -p sbt -batch check > /tmp/phase9c-check-2.log 2>&1`; exit 0; 1,131 passed, zero failed; 780.69 seconds. Module counts: core 207, Hadoop 64, entity-resolution 39, Spark 38, storage 80, RAG 107, independent 588, build 8. Expected injected format-stage probe ran as a passing build self-test; final TestRunMarker observed. Raw SHA-256 830bb94d47e4d122f44013f5a42f82fc45fed696df4020afba395511cbd0bc37.

Final read-only validation: git diff --check exit 0; untracked-file git diff --no-index --check emitted no findings; all 38 source hashes and 13 raw-log SHA-256 bindings verified. Drive plan hash, original decisions and prior reviews unchanged; HEAD remains base. No active Java/sbt build found; all specialists completed. Details: final-validation.json.

Final prompt helper correction: first inventory comprehension passed a record instead of its path to git and exited before any file writes; corrected to record.path. No source/build changes or test reruns.
