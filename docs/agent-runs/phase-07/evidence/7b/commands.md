# Subphase 7B observed command ledger

Every sbt invocation uses:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

## Bounded real-data CSV replay attempt 1

Owner requested coordinator execution of formatting and explicit test main. Native sbt caches require sandbox escalation; this local build/replay does not call AWS or a model provider. Raw command output: `/tmp/phase7b-real-csv-replay-1.txt`. Result pending execution.

```bash
java -version
/usr/bin/time -p sbt -batch 'sparkAnalytics / Test / scalafmt' 'sparkAnalytics / Test / runMain edu.uic.cs441.scholarchain.spark.Phase7RealCsvReplayMain /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49 /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase7b-replay-n2-20261022-01 20 20 2000'
```

Java observed: OpenJDK 17.0.20.1 Homebrew; sbt 1.10.7. Only replay test-source formatting requested here; no production Spark change.

Observed replay attempt 1 exit **0**, real24.62s. Counts:84 nodes,20 graph edges,20 coauthor edges,29 support rows,49 community membership rows;20 unbounded-window edges. Unknown collaboration years/support years and special-character labels:0 in this real sample. Explicit main is not added to sbt test totals. Retained raw `real-csv-replay-1.txt`; metadata/hash `real-csv-replay-result.json`; bounded report `real-csv-replay-report.json`. Original run manifest, metadata, counters and completion marker bytes/mtimes rechecked unchanged.

## Early storage compile attempts 1–2

Both used exact Section2 JDK17 environment and the same command:

```bash
/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'storage / Test / compile'
```

Attempt1: exit1 real3.08s at formatter (Scala3 rejects do/while). Attempt2 after owner repair: exit1 real5.99s at compilation (explicit ujson map conversion and alternative pattern variables). No tests executed. Original output retained as `storage-compile-1.txt` and `storage-compile-2.txt`; hashes in `compile-results.json`. Both routed to storage-engineer; no coordinator source edit.

Attempt3, same compile/format command: exit1 real2.92s at formatter (reserved Scala3 `export` variable in loader). No tests ran. Owner repair requested; raw output retained `storage-compile-3.txt`, hash indexed in compile-results.json.

## Combined compile attempt4

```bash
/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / compile' 'independentTests / Test / compile'
```

Exit1 real6.38s: two storage compile errors (metadata conditional String return, core/storage config name shadowing). Independent compilation not reached and no tests ran. Routed to owner; output `storage-compile-4.txt`, indexed hash.

Attempt5, same combined compile/format command: exit1 real10.91s. Storage production and module test compilation passed; independent compilation failed for one explicit ujson metadata map conversion, routed and repaired by test-engineer. No tests executed. Raw output `storage-compile-5.txt` retained including compiler nonlocal-return warnings; hashes indexed.

## Affected targets attempt1

```bash
/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec'
```

Exit0 real20.95s. Observed storage16/16, independentStorage46/46, CSV4/4. Retained complete output `targeted-1.txt` and hash metadata `targeted-1.json`. No cloud/live suite ran.

## Actual bounded sample CLI smoke attempts 1–2

```bash
/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'set storage / Compile / fork := true' 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase7b-replay-n2-20261022-01 --config /tmp/phase7b-local-load-config.json' 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase7b-replay-n2-20261022-01 --config /tmp/phase7b-local-load-config.json --execute-fake'
```

Attempt1 exit1 real7.12s: graph validation84nodes40edges29support passed; cache validation rejected, fake command not reached. Raw log contains verbose Hadoop DEBUG row payloads; bounded excerpt retained, full raw SHA in cli-smoke-results.json.

Attempt2 used the same command after adding safe reason-code output, plus this ephemeral sbt setting after `fork := true`:

```text
'set storage / Compile / javaOptions += "-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml"'
```

Attempt2 exit1 real8.35s: typed reason `missing-resolution-endpoint`; fake not reached. Complete small output retained cli-smoke-2.txt. Both fork/quiet settings affect only the sbt invocation; build files unchanged. Config fixture local-smoke-config.json has no approved AWS environment. Storage owner diagnosed/fixing researcher index sequencing; no source dataset edit.

## Final affected targets + actual sample CLI

```bash
/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec' 'set storage / Compile / fork := true' 'set storage / Compile / javaOptions += "-Dlogback.configurationFile=/Users/danny/Documents/UIC/CS441/ScholarChain/docs/agent-runs/phase-04/xml-repair-logback.xml"' 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase7b-replay-n2-20261022-01 --config /tmp/phase7b-local-load-config.json' 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --manifest /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase7b-replay-n2-20261022-01 --config /tmp/phase7b-local-load-config.json --execute-fake'
```

Exit0 real24.10s. Storage17/17, independentStorage48/48, NeptuneCSV4/4. Dryrun84nodes40edges29support proposes68entitycandidatecachewrites; fake execution68writes0unchanged, LOAD_COMPLETED. This derivative has no collaboration/kcore metric tables; independent producer-compatible Parquet tests cover metric pointers and unchanged reload separately. Full command output retained `targeted-cli-2.txt`, SHA in `targeted-cli-2.json`. No source/output/production Spark change was needed; alias indexing repaired in storage owner territory.

## Full gate

```bash
java -version
/usr/bin/time -p sbt -batch check
```

Started on frozen291-file source/build/test/README snapshot; result pending. Exact exit marker PHASE7B_EXIT_CODE is appended by the shell. Raw output `/tmp/phase7b-final-check.txt`. No ephemeral fork/javaOptions sbt settings persisted from earlier CLI session.

Full gate completed: exit0, **624 passed /0failed**, groups 144/64/39/38/17/314/8, real703.46s. Java17.0.20.1 / sbt1.10.7. Full byte-identical output retained `final-check.txt` (1,365,402bytes, SHA256 `a149c77307a1a6f9829b5b73ae9386107707e94bdd1e353724d1cd53032e4e5f`). Build probe injected error is expected; build group passed. All291 source/build/test/README hashes and mtimes unchanged.
