# Repair round 1 command ledger

Preflight read Git branch/HEAD/status and captured source/evidence hashes. Expected branch phase-7 and HEAD08e3d21233dbaf8c3d6283fc3bb9bce7f7fb1276 matched. The existing uncommitted 7B changes are explicitly authorized to remain.

Every sbt invocation uses exactly:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

No questions for this repair round. No reviewer, cloud/provider call, staging, commit or push. Only F3/F4 are in scope; N4–N14 stay open/nonblocking.

## Affected repair targets — attempt 1

```bash
java -version
/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'
```

Exit0; real19.40 seconds. Storage23/23, independentStorage54/54, NeptuneCSV4/4. Java17.0.20.1 Homebrew, sbt1.10.7. Complete unmodified output retained as targeted-1.txt; raw path/bytes/SHA in targeted-1.json. No failed repair invocation occurred. Owner-requested formatting does not transfer path ownership.

## Fresh full gate

```bash
java -version
/usr/bin/time -p sbt -batch check
```

Started against final-source-snapshot.json (298 source/build/test/README files, including unchanged module placeholders). Raw output /tmp/phase7b-repair1-final-check.txt. Exit marker REPAIR1_EXIT_CODE will be recorded after completion. Full gate pending at this ledger entry.

Full gate completed: exit0, 636 passed /0failed; groups 144/64/39/38/23/320/8, real680.86s. Java17.0.20.1 / sbt1.10.7. Full output retained final-check.txt (1,366,798bytes, SHA256 `0d8fb3ecc98dddf264ccba022a7941e49fff44c21e404357fa580daf3f715ef1`). All298 frozen source/build/test/README hashes and mtimes unchanged. Expected build-probe injected error is part of its passing self-test.
