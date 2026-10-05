# Phase 2 repairs

## Review round 1

Reviewer `5775ce38-29b5-46bd-82ff-6a9c0a384df2` returned `REQUEST-CHANGES`.

1. `project/Dependencies.scala` and `project/Versions.scala`: `spark-sql_2.13` 3.5.4 was `% Provided` with `.intransitive()` and no compatibility statement.
2. `sbt fmt` read missing `TestRunMarker.scala` paths under `modules/core/project/verification/` and `project/verification/project/verification/`.

Repair owner: `build-engineer` `cb6e6493-8d9c-4268-bcbb-3c3a5855428a`.

Repair: ledger comment states Spark 3.5.4 has no Scala 3 artifact. `.intransitive()` was removed. Excludes are `scala-library`, `scala-reflect`, and `scala-xml_2.13`. `buildVerification` is based at `build-verification/` with Scala sources still under `project/verification/src/`. Reported `sbt fmt` and `sbt check` passed. Empty `modules/*/project` trees were removed.

## Review round 2

Reviewer `984c0cee-1565-4a30-8642-769f071f3633` returned `APPROVE` for those two repairs. `dockerLocal` stayed unverified. The live failure probe was not retained.

## Human double-check

The human architect required two more repairs before acceptance.

1. `sbt check` format stage was `Compile / scalafmtCheck` only. A badly formatted test file passed `check` while `core / Test / scalafmtCheck` failed.
2. `TestRunMarkerSpec` used a simulated guard and a hard-coded task list. It did not run a failed `sbt check`. A manual contract-test failure left the marker unchanged.

Repair owner: `build-engineer` `d33b635d-78a2-4463-958a-2567f2d1f703`.

Repair: `build.sbt` lines 95–110 add `Test / scalafmtCheck` for all seven modules and `buildVerification`. `CheckFailurePathSpec` runs `sbt -Dscholarchain.checkProbe.fail=true checkTask` and asserts the marker is not created or modified. The simulated-guard and hard-coded-list tests were removed.

## Final review

Reviewer `0321eee1-566c-475b-a189-b25949e7575f` returned `APPROVE` for both human repairs. No further build repair was routed.
