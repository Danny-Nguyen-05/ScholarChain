# Coordinator command register — 7A

Every sbt command ran from `/Users/danny/Documents/UIC/CS441/ScholarChain` with:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

`java -version` observed OpenJDK17.0.20.1. Commands below ran through `/usr/bin/time -p`, with output redirected to `/tmp/phase7a-<name>.log`. Coordinator executes owner-requested formatting/targets while retaining one shared sbt slot; source ownership remains with specialists. Build-owner command register is `build/commands.md`. Initial git branch create sandbox failed128, identical escalated `git switch -c phase-7` passed0.

| Name | sbt arguments (after `sbt -batch`) | Observed result |
|---|---|---|
| targeted-1 | `'storage / Compile / scalafmt' 'sparkAnalytics / Compile / scalafmt' 'sparkAnalytics / Test / scalafmt' 'independentTests / Test / scalafmt' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec' 'storage / Test / compile' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStoragePortsSpec edu.uic.cs441.scholarchain.independent.IndependentStorageSdkSpec'` | exit1 Spark2/3, sidecarLong assertion; later tasks not reached |
| targeted-2 | `'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'sparkAnalytics / Test / scalafmt' 'storage / Test / compile' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'` | exit1 storage syntax compile, no tests |
| spark-targeted-2 | `'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'` | exit1 Spark2/3 CRLF changed to CRCRLF |
| targeted-3 | `'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec'` | exit1 moduletest compile iterator ambiguity, no tests |
| spark-targeted-3 | `'sparkAnalytics / Compile / scalafmt' 'sparkAnalytics / Test / scalafmt' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'` | exit1 Spark2/3 reader normalized CRLF; writer repair compiled |
| targeted-4 | `'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec'` | exit0 storage8/8 independent26/26, real13.34s |
| spark-targeted-4 | `'sparkAnalytics / Compile / scalafmt' 'sparkAnalytics / Test / scalafmt' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'` | exit1 testcompile varargs call, no tests |
| targeted-5 | `'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'sparkAnalytics / Compile / scalafmt' 'sparkAnalytics / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'` | exit0 storage9/9 independent26/26 Spark4/4, real15.22s |

Read-only commands include `git status --short --branch`, `git rev-parse HEAD`, `git diff --check`, `git diff --stat`, `rg --files`, scoped `cat`/`sed`, official AWS/course web reads, Python JSON/hash/evidence assembly. No AWS resource API, paid provider, commit, push, historical evidence rewrite or human-gate edit.

## First full repository gate

```sh
java -version > /tmp/phase7a-final-check.log 2>&1
/usr/bin/time -p sbt -batch check >> /tmp/phase7a-final-check.log 2>&1
```

Section 2 JDK 17 environment applied. Exit 1, real 676.92s, 585 passed/1 failed; build verification not reached. `PHASE7A_EXIT_CODE=1` appended by the wrapper. Exact raw hash/size and bounded line-numbered excerpt: first-full-check.json and first-full-check-excerpt.txt. Source snapshot did not change during the gate. Sole source-fence failure routed to Spark owner; scanner unchanged.

## Source-fence repair target

Section 2 JDK 17 environment; `/usr/bin/time -p sbt -batch 'sparkAnalytics / Compile / scalafmt' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentPhase6SafetySpec' > /tmp/phase7a-source-fence-targeted.log 2>&1`.

Exit 0, Spark CSV4/4, unchanged independent safety7/7; real10.63s. Spark owner changed exactly three production expressions; scanner/test unchanged. New source snapshot captured before the second full check; first snapshot preserved separately.

## Second full repository gate

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version > /tmp/phase7a-final-check-2.log 2>&1
/usr/bin/time -p sbt -batch check >> /tmp/phase7a-final-check-2.log 2>&1
```

Fresh invocation after the passing source-fence target. The wrapper appends `PHASE7A_EXIT_CODE` after process completion. Final exit, counts, timing and raw hash will be retained in final-check.json with a line-numbered excerpt. Source snapshot refreshed after repair, before this invocation. No source edits during the gate.

Final observed result: second full check exit0,594 passed/0failed, real680.62s, sbt679s. Expected injected build-probe failure is part of a passing verification test. Exact counts/line references/rawSHA and source/protected-input stability are in final-check.json/excerpt and final-audit.json. `git diff --check` exit0; independent whitespace scan over new implementation files found0 entries. No more implementation or test commands are needed after the passing stable-tree gate.
