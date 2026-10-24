# Build-owner commands

All sbt invocations prepend exactly:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

1. `java -version` — exit0 Java17.0.20.1 (first log).
2. `sbt -batch scalafmtSbt 'buildVerification / Compile / scalafmt' 'buildVerification / Test / scalafmt' 'buildVerification / Test / testOnly scholarchain.build.AwsIntegrationPolicySpec scholarchain.build.AwsIntegrationExclusionSentinelSpec'` — sandbox exit1 cache lock; same approved retry exit0 1 test pass, sentinel excluded.
3. For each test/testOnly/testQuick/executeTests: `env -u SCHOLARCHAIN_AWS_ITEST -u AWS_PROFILE sbt -batch "buildVerification / awsIntegration / $phase7a_task"` — exit1 lowercase parser error, not guard proof.
4. For each same task: `env -u SCHOLARCHAIN_AWS_ITEST -u AWS_PROFILE sbt -batch "buildVerification / AwsIntegration / $phase7a_task"` — exit1 disabled opt-in, intended refusal.
5. `env -u AWS_PROFILE SCHOLARCHAIN_AWS_ITEST=1 sbt -batch 'buildVerification / AwsIntegration / test'` — exit1 missing explicit profile, intended refusal.
6. `sbt -batch scalafmtSbt 'buildVerification / Compile / scalafmtCheck' 'buildVerification / Test / scalafmtCheck' 'storage / update' 'show storage / Test / testOptions' 'show storage / AwsIntegration / testOptions'` — exit0.
7. `sbt -batch 'show storage / libraryDependencies' 'show independentTests / Test / dependencyClasspath'` — exit1 in-progress storage compile errors (String node indexing and lexical lambda issue), routed owner, preserved phase7a-build-classpath.txt.
8. `sbt -batch 'show independentTests / Test / externalDependencyClasspath'` — exit0, 295 entries.
9. `shasum -a 256` over logs — exit0, raw hashes log-index.json.
10. `rg -c 'Attributed\(' /tmp/phase7a-build-providers.log` — exit0,295.

Negative logs remain raw to distinguish parser failures from guarded refusals. No opt-in plus valid-profile command or live AWS suite was executed.
