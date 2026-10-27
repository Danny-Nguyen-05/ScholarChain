# Subphase 10B exact commands

Every sbt invocation ran from /Users/danny/Documents/UIC/CS441/ScholarChain with this environment (supplied exactly by run-gate.py):

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
```

Observed Java: Homebrew 17.0.20.1. java -version exited 0. Source hashes are snapshotted before each gate; formatting can alter the pre-command snapshot. Final source-files.json and post-check-source-comparison.json bind the final files. Every full raw log remains in /tmp with an exact hash in the corresponding result JSON; meaningful excerpts are retained here.

- `sbt -batch 'services / Test / compile'` — exit 1, 7.844 s; `compile-1-result.json`.
- `sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'independentTests / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10B*'` — exit 1, 6.012 s; `targeted-1-result.json`.
- `sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'independentTests / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10B*'` — exit 1, 11.996 s; `targeted-2-result.json`.
- `sbt -batch scalafmtSbt 'buildVerification / Compile / scalafmt' 'buildVerification / Test / scalafmt' 'buildVerification / test'` — exit 0, 15.620 s; `packaging-tests-result.json`.
- `sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'independentTests / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A* edu.uic.cs441.scholarchain.independent.IndependentServices10B*'` — exit 0, 11.579 s; `targeted-3-result.json`.
- `sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10B*' packageServices` — exit 0, 8.119 s; `targeted-final-package-result.json`.
- `sbt -batch check` — exit 0, 709.995 s; `check-result.json`.

Focused results: targeted-2 services25/25 and independent10B13/16 (three failures); targeted-3 services26/26 in4suites and independent10A/B36/36 in6suites; targeted-final-package final independent10B17/17 in4suites plus packageServices; packaging-tests13/13 in8suites. Full check1199/1199 in145suites, no failures, sbt708s (11:48), wall709.995s. The intentional nested checkProbeInjectFailure belongs to CheckFailurePathSpec; parent test and outer gate passed.

Docker: DOCKER_CONFIG=/tmp/phase10b-docker-config DOCKER_HOST=unix:///Users/danny/.docker/run/docker.sock python3 /tmp/phase10b-docker.py — exit0,13.530s. Same environment python3 /tmp/phase10b-docker-remote.py — exit0,2.805s. Exact per-command Docker argv, exits, durations, startup probes, hashes and cleanup are in the two successful Docker result JSON files. Earlier credential-helper cancellation and all three integration harness failures are retained separately. Optional-field actual HTTP probe exited0 in0.999s.

Final read-only checks: git diff --check; git branch --show-current; git rev-parse HEAD; git status --short; source SHA-256 rehash; Ruby YAML parse and Python local-ref/JSON-example validation; Docker task-container/network cleanup checks. Their final observed results are in final-validation.json and openapi-validation.json.
