# 6D+6E repair round 1 commands

Working directory: `/Users/danny/Documents/UIC/CS441/ScholarChain`.

All successful sbt runs used:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Core owner:

```bash
sbt -batch 'core/scalafmtAll' 'core/Compile/scalafmtCheck' 'core/Test/scalafmtCheck'
sbt -batch 'core/testOnly *SparkAnalyticsContractSpec'
git diff --check -- modules/core
```

All exit 0; targeted **14/14**. Stdout retained in `core-format.txt` and `core-targeted.txt`; the latter prints old/new full and logical fingerprints through ScalaTest `info`.

The Spark owner's initial local command exited **1 before compilation** because its sandbox could not open `/Users/danny/.sbt/boot/sbt.boot.lock`; `module-sandbox-denial.txt` retains that error. The coordinator executed the owner's supplied formatter/check/test command on the owner's test source:

```bash
sbt -batch 'sparkAnalytics/Test/scalafmt' 'sparkAnalytics/Test/scalafmtCheck' 'sparkAnalytics/testOnly *Phase6DEJobsSpec' > docs/agent-runs/phase-06/evidence/6de/repair-1/module-targeted.txt 2>&1
phase6de_exit=$?
printf '\nexit=%s\n' "$phase6de_exit" >> docs/agent-runs/phase-06/evidence/6de/repair-1/module-targeted.txt
exit "$phase6de_exit"
```

Exit **0**, **10/10**; the new oscillation/core-record validation case passed. No production algorithm changed.

Final full gate on the stable repair tree:

```bash
/usr/bin/time -p sbt -batch check > docs/agent-runs/phase-06/evidence/6de/repair-1/final-check.txt 2>&1
phase6de_exit=$?
printf '\nexit=%s\n' "$phase6de_exit" >> docs/agent-runs/phase-06/evidence/6de/repair-1/final-check.txt
exit "$phase6de_exit"
```

Direct JDK evidence:

```bash
/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version
```

Exit 0; retained in `java-version.txt`. `source-check.txt` records file mtimes, the production driver/API scan, plan hash and `git diff --check` exit 0. Final full-gate counts, exit, size and SHA-256 are reported in the repair sections of `owner-report.md` and `test-report.md` and in `final-gate-metadata.json` for the completed run.

Observed full gate: **exit 0**, **528/528**, sbt **561 s**, real **563.44 s**; metadata contains exact bytes/hash/counts.
