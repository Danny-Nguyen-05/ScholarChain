# Subphase7C repair round1 command ledger

User specifically authorized7C-M1 after external7CAPPROVE. No questions. Preflight phase-7 HEADc911b236f2a8c02b7422df56f8c334d47fff7ad3; existing7Cuncommittedtree retained. Exact Git status in preflight.json.

Every sbt command uses exactly:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

AwsIntegration configuration compile only. No integration test entry point, live body, actual cleanup, AWS/provider account call, staging/commit/push or reviewer. Full localcheck required after repair.

## Affected repair targets — attempt1

```bash
java -version
/usr/bin/time -p sbt -batch 'storage / Test / scalafmt' 'storage / AwsIntegration / compile' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec'
```

Exit0 real14.30s. Normalstorage32/32 and independentStorage73/73. Java17.0.20.1 Homebrew/sbt1.10.7. Live sources compiled only; sole tagged body not executed; cleanup regression uses SDK proxies, not live clients. Complete raw output targeted-1.txt with bytes/SHA metadata targeted-1.json. No repair invocation failed.

## Fresh full gate

```bash
java -version
/usr/bin/time -p sbt -batch check
```

Started on final-source-snapshot.json (308source/build/test/README files). Raw /tmp/phase7c-repair1-final-check.txt, marker REPAIR1_EXIT_CODE recorded after completion. Result pending at this entry. Existing integration execution guards unchanged; no live test entry point invoked.

Fresh full gate exit0: 664passed/0failed, groups144/64/39/38/32/339/8, real681.26s; Java17.0.20.1/sbt1.10.7. Full log final-check.txt 1,370,465bytes SHA256 `f225a4ecaa93d920ae1476211ab638bc1f36b0120bf2e078eb5d0308820773b3`. All308 source/build/test/README hashes and mtimes unchanged. Expected injected format-stage error belongs to passing self-test. Live body and actual cleanup never executed.
