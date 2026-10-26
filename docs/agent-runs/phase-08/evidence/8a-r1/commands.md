# 8A repair round 1 — exact gates

All commands run from /Users/danny/Documents/UIC/CS441/ScholarChain.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Preflight: git status --short, git branch --show-current, git rev-parse HEAD all exit 0. Existing uncommitted 8A retained on phase-8 at 8503e1715cbcaf043fd68213c5b08731e9de9ba7. No reset, staging, commit or push.

`java -version` exit 0; java-version.txt (17.0.20.1). Native sandbox escalation used for sbt external cache; no auto-review rejection occurred.

## Affected gate 1

```text
sbt -batch 'core / Compile / scalafmt' 'core / Test / scalafmt' 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'core / Test / testOnly *EmbeddingContractSpec' 'storage / Test / testOnly *EmbeddingStorageSpec'
```

Exit 0; core 11/11 and storage 13/13. targeted-1.txt and .exit retain output/result. Module owners requested these formatting/test tasks; coordinator executed shared slot only.

## Affected gate 2

```text
sbt -batch 'rag / Compile / scalafmt' 'rag / Test / scalafmt' 'independentTests / Test / scalafmt' 'rag / Test / test' 'independentTests / Test / testOnly *IndependentEmbedding* *IndependentStorageRuntimeFenceSpec'
```

Exit 0; RAG 18/18 and independent 29/29 across five independent suites; runtime roots 3. targeted-2.txt and .exit retain output/result. Owners requested formatting/test tasks. No failed affected attempts.

## Full gate

```text
/usr/bin/time -p sbt -batch check > /tmp/phase8a-r1-final-check-1.txt 2>&1
```

Exit0: 731 tests passed / 0 failed; groups155/64/39/38/45/18/364/8, real703.88 seconds. All303 frozen files unchanged. final-check-1.exit/final-check.json retain result; line-numbered excerpt/hash/size retained; raw log outside repo. Expected injected format-stage failure is a passing build self-test. Live tests excluded by unchanged build policy.

Final checks: git diff --check exit0; Python compares303 frozen SHA/mtimes with0changes; new-source whitespace check0violations; original plan matches snapshot; protected control/human/upstream tracked paths unchanged. Deferred provider/queue/runtime-fence source hashes match original8A. All build sessions completed. No failed repair test attempts.
