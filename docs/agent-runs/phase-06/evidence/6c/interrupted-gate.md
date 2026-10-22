# Interrupted intermediate 6C gate

Coordinator observation, October 22, 2026. This was an intermediate run, not the final gate.

Command from repository root, with JDK 17 and the Phase 4 logging config:

```bash
env JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home PATH=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:$PATH SBT_OPTS=-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml /usr/bin/time -p sbt -batch check > /private/tmp/scholarchain-phase6c-final-check-bound.txt 2>&1
```

The coordinator interrupted this run with Ctrl-C; process exit **130**. The partial log had core **142/142** and no final check result. During the run, source audit found that published `input_rejects` and several other tables lacked top-level `runId` and `schemaVersion`. The `spark-engineer` repaired the publication boundary and added module tests. A fresh module suite, local smoke and full JDK 17 `sbt -batch check` then passed; only `final-check.txt` is the final gate evidence.
