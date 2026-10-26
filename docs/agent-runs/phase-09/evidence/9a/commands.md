# Subphase 9A command ledger

Preflight (before edits): `git status --short` → exit 0, empty; `git branch --show-current` → exit 0, phase-8; `git rev-parse HEAD` → exit 0, 5fee9ffc607cf802e4aaddf4a261c21f1f232fec.

JDK first gate: `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml java -version` → exit 0; openjdk 17.0.20.1 2026-08-18, Homebrew build17.0.20.1+0.

Read-only inventory attempts: `rg --files -g 'AGENTS.md' modules tests prompts docs project` returned exit1 (no nested matching files), preventing chained role read; roles subsequently read successfully. `ls -ld docs/agent-runs/phase-09 '/Users/danny/Documents/plan/phase9.md'` returned exit1 because phase-09 did not yet exist; local plan existed. No build failures occurred in these reads.

`git switch -c phase-9` → exit128 in sandbox (cannot create refs/heads/phase-9.lock, operation not permitted). Same exact command rerun with native escalation, user approved → exit0, switched to new branch phase-9. No commit or push.

All sbt commands below use exactly:
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Targeted core gate:
```sh
sbt -batch 'core / Test / testOnly *RuntimeContractSpec *SerializationContractSpec' > /tmp/phase9a-core-targeted-1.log 2>&1
```
Sandbox attempt exit1 before sbt startup (sbt.boot.lock outside writable roots); retained core-targeted-1-sandbox.log. Exact same sbt command rerun via native escalation after user approval, output /tmp/phase9a-core-targeted-1-approved.log → exit0;17 passed,0failed,2suites. Raw approved output retained core-targeted-1.log. No test or source repair needed.

Storage target1: `sbt -batch 'storage / testOnly *RuntimeArtifactStorageSpec' > /tmp/phase9a-storage-targeted-1.log 2>&1` → exit1; production compiled; testcompile ambiguous iterator (no tests executed). Owner renamed local sourceIterator.

Storage target2: same exact sbt arguments, output /tmp/phase9a-storage-targeted-2.log → exit1;11run,4passed,7failed. Synthetic graph evidence failed strict source/ID validation.

Storage target3: same exact sbt arguments, output /tmp/phase9a-storage-targeted-3.log → exit1;11run,4passed,7failed. Remaining synthetic topic/venue/institution IDs used invalid namespaces. Owner corrected fixture IDs and source work bindings, added fixture self-validation; production validation retained. Independently identified sourceRefs row-key issue corrected by storage owner with regression assertion.

RAG/independent target1:
```sh
sbt -batch 'rag / testOnly *Runtime9ASpec' 'independentTests / Test / testOnly *IndependentRuntime9APlannerSpec *IndependentRuntime9AResolverSpec *IndependentRuntime9AEvidenceSpec' > /tmp/phase9a-rag-independent-targeted-1.log 2>&1
```
Exit1 overall;RAG17passed0failed. Independent testcompile failed on generic enum type in ArtifactPipelineSpec (although not selected, all test sources compile). Test owner added wildcard; no independent tests ran.

Final combined targeted gate (post repairs):
```sh
sbt -batch 'core / Test / testOnly *RuntimeContractSpec *SerializationContractSpec' 'storage / testOnly *RuntimeArtifactStorageSpec' 'rag / testOnly *Runtime9ASpec' 'independentTests / Test / testOnly *IndependentRuntime9A*' > /tmp/phase9a-targeted-all-1.log 2>&1
```
Exit0;core17/storage11/RAG20/independent22;70passed0failed. Independent fresh G1 producer integration passed (10researchers,9works,18windowededges,28tables). Raw log bound by targeted-all-1-result.json, meaningful excerpts retained.

Formatting:
```sh
sbt -batch 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'rag / Compile / scalafmt' 'rag / Test / scalafmt' 'independentTests / Test / scalafmt' > /tmp/phase9a-format-1.log 2>&1
```
Exit0;formatter output retained. Mechanical formatting only, centralized by coordinator.

Full gate1:
```sh
/usr/bin/time -p sbt -batch check > /tmp/phase9a-check-1.log 2>&1
```
Exit1;724.36s wall. Core169/Hadoop64/ER39/Spark38/storage62/RAG53passed; independent398run397passed1failed. Existing IndependentStorageLoaderSpec expected3 cachewrites but approved base-namealias now makes4. No buildVerification run or success-marker claim. Failure raw binding/excerpts retained in check-1-result.json/check-1-excerpts.log. Routed to test-engineer to update hand-derived write/replay4 expectations and assert alias identity/provenance; production unchanged.

Legacy-loader repair target:
```sh
sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly *IndependentStorageLoaderSpec' > /tmp/phase9a-loader-repair-targeted-1.log 2>&1
```
Exit0;formatting success;5passed0failed. Expected4write/replay and explicit alias provenance assertions passed; production unchanged.

Final full gate2:
```sh
/usr/bin/time -p sbt -batch check > /tmp/phase9a-check-2.log 2>&1
```
Exit0;705.87s wall;831passed0failed: core169/Hadoop64/ER39/Spark38/storage62/RAG53/independent398/build8. Expected injected format-stage failure is the passing build failure-path self-test; final TestRunMarker ran after successful gate. Meaningful excerpts and raw log hash retained in check-2-excerpts.log/check-2-result.json.

Final integrity: git diff --check exit0; all31 changed source/config/test/prompt hashes unchanged from pre-final-gate snapshot; bounded high-confidence credential-literal scan0findings. No credential locations accessed. No further build/test reruns needed after these passing gates.
