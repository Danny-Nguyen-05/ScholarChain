build-engineer 13A report (Sonnet 5.5, effort high; native agent ID ab501a4a617dd57dc) — key facts, verified by orchestrator:
STATUS COMPLETE. Files: M build.sbt, M project/ScholarChainBuild.scala, M project/HadoopPackaging.md, A project/verification/src/test/scala/scholarchain/build/PackagingJava17GuardSpec.scala. Dockerfile unchanged.
- ThisBuild/checkJava17 (Java17Guard) guards serviceDistribution, sparkJobJar, hadoopDependencyBundle, hadoopSubmitJar, assembly, assemblyPackageDependency, every Compile/packageBin, dockerLocalImage; aliases packageJobs and new packageRelease start with ;checkJava17.
- JDK 27 negative probe: packageRelease and 12 other packaging tasks exit 1 with "ScholarChain check requires Java 17; found Java 27..."; jar mtimes/sizes unchanged.
- JDK 17 packageRelease exit 0 (twice, per-module clean). Submit jar not byte-reproducible (timestamps).
- PackagingJava17GuardSpec: 5 static + 1 live probe (SCHOLARCHAIN_NON17_JAVA_HOME); live run: succeeded 6, failed 0.
- sbt -batch check JDK 17: first run failed at scalafmtSbtCheck (ScholarChainBuild.scala unformatted) exit 1; fixed with scalafmtSbt; second run exit 0, 759 s; core 207, hadoop 64, ER 39, spark 50, storage 80, rag 107, services 40, independentTests 667, buildVerification 18 succeeded + 1 canceled (live probe, env unset).
- amd64 probe build of QueryApiMain: exit 0, image linux/amd64; probe tag removed. Base index includes linux/amd64.
