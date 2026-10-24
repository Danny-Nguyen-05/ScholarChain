# Repair round 1 command register

Working directory: /Users/danny/Documents/UIC/CS441/ScholarChain.
Every sbt command used exactly:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

1. `java -version` — exit0, Java17.0.20.1, at beginning of targeted-tests.txt.
2. `/usr/bin/time -p sbt -batch 'storage / Compile / scalafmt' 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec' 'sparkAnalytics / Test / testOnly edu.uic.cs441.scholarchain.spark.Phase7NeptuneExportSpec' 'storage / Test / runMain edu.uic.cs441.scholarchain.storage.Phase7ManifestSmokeMain target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49'` — exit0, real16.52s; storage10/10, independent27/27, SparkCSV4/4. Log targeted-tests.txt includes successful real-source smoke followed by a Hadoop shutdown hook missing sbt temporary classpath JAR. Retained honestly; not counted as a failed test, and subsequent isolated smoke resolves launch-context problem.
3. `/usr/bin/time -p sbt -batch 'set storage / Test / fork := true' 'storage / Test / runMain edu.uic.cs441.scholarchain.storage.Phase7ManifestSmokeMain target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49'` — exit1, real3.72s. Forked JVM starts in module directory; relative root missing. Log real-manifest-smoke-relative-failure.txt. Ephemeral setting only, no build file edit.
4. `/usr/bin/time -p sbt -batch 'set storage / Test / fork := true' 'storage / Test / runMain edu.uic.cs441.scholarchain.storage.Phase7ManifestSmokeMain /Users/danny/Documents/UIC/CS441/ScholarChain/target/phase6-runs/6fg-spark-first-v2/run:f02acf56-4bea-4009-adaf-b11d5afceb49'` — exit0, real4.14s, clean shutdown. Three real manifests bound and <=1row/table read. No cache writes/full dataset count/hash scan. Raw debug output /tmp/phase7a-repair1-real-manifest-smoke.log; bounded tracked excerpt real-manifest-smoke.txt; raw/retained SHA256 in targeted-results.json. Debug verbosity is the reason for retaining an excerpt; source row payloads are omitted.
5. `java -version > /tmp/phase7a-repair1-final-check.log 2>&1` and `/usr/bin/time -p sbt -batch check >> /tmp/phase7a-repair1-final-check.log 2>&1` — fresh fullgate running. Final result goes to final-check.json and line-numbered final-check-excerpt.txt. Wrapper appends REPAIR1_EXIT_CODE after completion.
6. Coordinator F2 Python audit: rename23 .log to.txt preserving bytes; verify14 build raw hashes and23 renamed hashes; add explicit retained hashes/paths to metadata; check Git visibility. `git check-ignore -v -- <23 concrete new paths in evidence-migration.json>` — exit1, no matches. `git status --short -uall -- docs/agent-runs/phase-07` — exit0, output git-visible-files.txt. No .gitignore edit or staging.
7. `git diff --check` — exit0 before fullgate; final audit repeats after completion.

Verbatim external review/work order retain their historical .log spelling. Actual retained-file references use.txt; raw/tmp execution paths remain.log. F2 renamed bytes were never trimmed or edited. Full command/path mapping is evidence-migration.json.


Final result: full gate exit0,596passed/0failed, real681.20s, sbt679s;144/64/39/38/10/293/8. Raw hash/bytes and retained line-numbered excerpt are in final-check.json. The expected injected build-probe failure belongs to a passing test. Final audit repeats source hashes/mtimes, protected inputs, .gitignore, real-source metadata, verbatim review,23 migrated log hashes,14 build raw hashes and retained-reference resolution; all pass. `git diff --check` exits0. No further implementation/test commands after this passing stable-tree gate.
