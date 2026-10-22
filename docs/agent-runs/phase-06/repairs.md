# Phase 6 routed findings and repairs

## Subphase 6A — repair round 1

The user supplied a read-only external `REQUEST-CHANGES` review, retained in `review.md`, then instructed: **"Fix F1, F2, F3 please"**. The user separately approved one minimal independent SparkSession startup probe under `tests/**`. This round is limited to those three findings. No reviewer was launched by the coordinator.

| Finding | Reviewer status and owner | Round 1 disposition |
|---|---|---|
| F1: `independentTests` cannot start Spark on JDK 17; classpath claim lacks retained proof | High, blocking. `build-engineer` for `build.sbt`/`project/**`; `test-engineer` for approved probe under `tests/**`; coordinator for evidence | **Repaired, pending external recheck.** The build owner applied shared fork/JDK 17 options and repository-root working directory. The independent probe passed; the full independent suite passed 234/234 and the full gate passed 474/474. `repair-1/independent-classpath-proof.txt` shows fork, options, Spark SQL 3.5.4 and scala-reflect 2.13.14. |
| F2: duplicate SLF4J providers and Logback bundled in job JAR | Medium, nonblocking; `build-engineer` | **Repaired, pending external recheck.** The build owner removed direct Logback from Spark test projects, added a shared WARN-level log4j2 test resource, excluded Logback from Spark packaging and added a package rejection test. The final check has no SLF4J duplicate-provider warning or DEBUG lines. The rebuilt 4,798-entry JAR listing has no Spark/Hadoop/Logback/provider paths. |
| F3: packaged Scala library patch version versus a prospective Spark Scala-2.13 runtime | Medium, nonblocking 6H feasibility; `infra-engineer` research, `build-engineer` packaging context, coordinator memo | **Research and 6H validation plan completed, pending external recheck.** `emr-compatibility.md` and `repair-1/f3-research.md` distinguish Spark's upstream 2.13.8 build profile from the local job JAR's 2.13.14. Official Scala policy says the patch difference alone is not proof of incompatibility. Inventory, alignment, class-origin and bounded-runtime checks remain a 6H gate. |
| F4: wrong-JDK evidence predates final tree | Low, nonblocking; `build-engineer`/coordinator | **Deferred by the user's F1–F3 scope.** Existing guard evidence remains dated; rerun if later requested or required for release. |
| F5: plan hash and model/tool provenance | Low, nonblocking; coordinator | **Deferred by the user's F1–F3 scope.** Reviewer-observed plan hash is recorded in the review; no new provenance claim is invented. |
| F6: packaging lacks Java 17 guard | Low, nonblocking; `build-engineer` | **Deferred by the user's F1–F3 scope.** Packaging risk remains for a later build-owned repair before release. |
| F7: 6C shared Spark harness settings | Informational future scope; `spark-engineer` | **Future 6C scope.** No 6A smoke-spec change. |
| F8: "Spark classes" wording | Informational; `build-engineer` | **Deferred by the user's F1–F3 scope.** |
| F9: evidence size | Informational; coordinator | **Deferred.** Keep the full existing final-gate log; repair output will be retained lean where possible. |

Starting repair state: branch `phase-6`, HEAD/base `03493882399e9020e6892c9f97e0ec8919365215`; previous 6A changes uncommitted. The user explicitly asked for this repair round, so work proceeds on the same tree without implying prior approval or a commit.

## External recheck disposition

The user-supplied external reviewer returned **APPROVE** for 6A repair round 1. F1 and F2 are closed with runtime/package evidence; F3 is closed as research while the 6H runtime check remains open. F4–F6 and F8 remain nonblocking/deferred, F7 is 6C scope, and F9 is mostly resolved by reduced logs. The reviewer added R1 (low, nonblocking): two report statements overstated the filtered evidence. The coordinator reworded those statements in `owner-report.md` and `test-report.md` as an editorial evidence correction after review; no implementation, test or package artifact changed. The next gate is the user's 6A commit, then a separate 6B prompt.
