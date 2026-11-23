<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Build-engineer handoff

STATUS: COMPLETE for the owned build repairs. Not a Phase 2 acceptance.

OWNER: `build-engineer` (`composer-2.5-fast`)

WORK ORDER: Phase 2 skeleton, then the two review repairs, then the two human repairs in `prompt.md`.

FILES CREATED: `build.sbt`, `Dockerfile`, `.gitignore`, `.sbtopts`, `.scalafmt.conf`, `project/build.properties`, `project/plugins.sbt`, `project/Versions.scala`, `project/Dependencies.scala`, `project/ScholarChainBuild.scala`, `project/verification/src/main/scala/scholarchain/build/TestRunMarker.scala`, `project/verification/src/main/scala/scholarchain/build/TestRunMarkerPolicy.scala`, `project/verification/src/test/scala/scholarchain/build/TestRunMarkerSpec.scala`, `project/verification/src/test/scala/scholarchain/build/CheckFailurePathSpec.scala`, and the approved `.gitkeep` files. `build-verification/` is an sbt project anchor; only its gitignored `target/` exists.

FILES MODIFIED: The repair passes edited `build.sbt`, `project/Versions.scala`, `project/Dependencies.scala`, `project/ScholarChainBuild.scala`, and `TestRunMarkerSpec.scala`. No tracked Phase 1 file was modified. `git diff --stat` against HEAD is empty because the Phase 2 tree is untracked.

COMMANDS RUN: Reported by the build-engineer; see the coordinator validation supplement below. The coordinator at handoff did not re-run `sbt`.

TEST RESULTS: Final reported `sbt check` ran `CheckFailurePathSpec` and `TestRunMarkerSpec` (2 tests) and then `TestRunMarker`. The failure-path spec passed when run with `testOnly`.

VALIDATION RESULTS: `Test/compile`, `fmt`, `check`, and `packageJobs` were reported passing on the repair path. `dockerLocal` remains unverified. The current marker file is `success=true` and `timestamp=1791170024115`.

ASSUMPTIONS: Empty modules compile without sources. `build-verification/` may exist as an untracked sbt base while marker sources stay under `project/verification/`. The probe property is set only by `CheckFailurePathSpec`.

RISKS: Spark 3.5.4 is published as `spark-sql_2.13` only. Scala 3 sources must use Java and `org.apache.spark.sql.*` entry points. The repaired check that produced the current marker ran on Homebrew Java 27; an earlier check ran on Java 17. Class file major version observed by the second reviewer for `TestRunMarker.class` was 52. Spark's transitive Hadoop artifacts are 3.3.4 while the Hadoop module pins `hadoop-client` 3.3.6. `CheckFailurePathSpec` treats any non-zero `sbt` status as the expected failure, including a missing `sbt` on `PATH`.

MANUAL ACTION REQUIRED: Human acceptance gate. Start Docker and re-run `sbt dockerLocal` if an image build is required before acceptance.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: none for the owned repairs. `dockerLocal` has no successful run.

NEXT GATE: Human architect reads `review.md` and this tree. This report does not accept Phase 2.

## Coordinator validation supplement

This section preserves the separate validation record after the human requested its consolidation. It distinguishes the build-engineer's reports, the earlier coordinator's observations, and the later independent double-check. It does not change the build-engineer's final report above. The statement above that `dockerLocal` was unverified describes the build-engineer handoff; the later independent run below succeeded. The consolidation also modifies the tracked `docs/agent-runs/README.md` rule after the earlier clean-diff observation.

Toolchain reported by the build-engineer: Homebrew `openjdk@17` 17.0.20.1, sbt launcher 2.0.10 loading sbt 1.10.7 from `project/build.properties`. The later repair logs name Homebrew Java 27. Docker CLI 29.5.3 was present, but its daemon was unavailable during the build-engineer's run.

Earlier coordinator observation on 2026-10-04, not an sbt re-run:

```text
git rev-parse HEAD
5a1a3d80ee1006cb47045027085cafbaef28ddc2

git diff --stat 5a1a3d80ee1006cb47045027085cafbaef28ddc2 -- AGENTS.md CLAUDE.md docs .claude .mcp.json
(empty)

git diff --stat
(empty)

git status -sb
## main...origin/main
untracked Phase 2 build files and .gitkeep skeleton
```

Phase 1 paths had no diff against HEAD. The Phase 2 diff was untracked.

### Commands reported by the build-engineer

| Command | Reported result | Reviewer check of retained logs |
|---|---|---|
| `sbt Test/compile` | Pass, about 2 s, after the first clean build | No separate timing log found |
| `sbt fmt` | Exit 0 on the fmt-path repair (19:52:45 CDT) and again on the human-repair pass | First fmt task logs accepted. No fmt transcript retained for the final human-repair pass |
| `sbt check` | Pass. Final claimed run 2026-10-04 22:13:44, 2 tests, then `TestRunMarker` | Marker file matched `timestamp=1791170024115` (22:13:44.115 CDT). A single retained stdout showing both specs and only then the marker was not found |
| `sbt -Dscholarchain.checkProbe.fail=true checkTask` | Exit 1, `(checkProbeInjectFailure) scholarchain check probe: injected format-stage failure` | Error text is in `target/streams/_global/checkProbeInjectFailure/_global/streams/out`. No shell exit line retained. The spec asserts exit code `!= 0` |
| `sbt "buildVerification/testOnly scholarchain.build.CheckFailurePathSpec"` | Exit 0, 1 test | XML `failures="0"` `errors="0"` timestamp `2026-10-04T22:13:52`. Shell exit 0 is not in that file |
| `sbt packageJobs` | Jars for `hadoop` and `sparkAnalytics` | Jars and manifest titles accepted on the earlier review |
| `sbt dockerLocal` | Failed then: `docker build` exit 1, daemon unavailable | Stale stream recorded exit 1; the build-engineer did not re-run it after the repair |

### Later independent double-check

On 2026-10-04, an independent reviewer ran `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch 'Test/compile' check packageJobs` in the ScholarChain tree. Exit code was 0. `Test/compile` passed; `check` ran `CheckFailurePathSpec` and `TestRunMarkerSpec` (2 passed, 0 failed), then ran `TestRunMarker`; both `packageJobs` tasks passed. The nested failure probe printed `(checkProbeInjectFailure) scholarchain check probe: injected format-stage failure`, and its parent test passed after confirming the marker was unchanged.

The reviewer also copied the current `build.sbt` and `project/ScholarChainBuild.scala` into an isolated Phase 2 copy containing `modules/core/src/test/scala/FormatProbe.scala` with invalid formatting. `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch check` exited 1 with `(core / Test / scalafmtCheck) scalafmt: 1 files must be formatted`. The malformed file was never added to the ScholarChain tree.

After Docker Desktop was started, `docker info --format '{{.ServerVersion}} {{.OSType}} {{.Architecture}}'` returned `29.5.3 linux aarch64`. `JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home sbt -batch dockerLocal` exited 0 at 22:26:56 CDT and created `scholarchain-local:latest`. `docker image inspect scholarchain-local:latest --format '{{.Id}} user={{.Config.User}} entrypoint={{json .Config.Entrypoint}}'` returned image ID `sha256:770a890d0be662225ff17efa99937448a0bbddc1e47ef88b66b9338d3caa3ecc`, user `scholarchain`, and entrypoint `["java","-jar","/app/services.jar"]`. `docker run --rm scholarchain-local:latest` exited 1 with `no main manifest attribute, in /app/services.jar`; Phase 2 has no service application entry point.

### Current check definition and marker

`build.sbt` lines 91–134 contain one `Def.sequential`. The format stage checks both `Compile` and `Test` sources for all seven modules and `buildVerification`, then checks sbt sources. Compilation, module tests, `contractTest`, and `markTestRun` follow. `checkProbeInjectFailure` is first and errors only when `-Dscholarchain.checkProbe.fail=true`.

`.gitignore` ignores `.claude/.last-test-run`. At the build-engineer handoff it contained `success=true` and `timestamp=1791170024115`. A later successful check rewrote that ignored marker. `CheckFailurePathSpec` launches a failing `checkTask` and asserts the marker bytes and mtime are unchanged. The earlier manual failure probe was not retained because a later success overwrote the marker.
