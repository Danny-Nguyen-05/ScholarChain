# Subphase 7C command ledger

Preflight: branch phase-7, HEAD c911b236f2a8c02b7422df56f8c334d47fff7ad3, git status --short empty before delegation. Approved7B commit and repair evidence confirmed tracked. No edits or agents launched before Step0 answers.

Every sbt invocation uses exactly:

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

Only compile the AwsIntegration configuration. Never invoke its test/testOnly/testQuick/executeTests entry points here, even for a negative probe. Normal Test targets and sbt check exclude the live tag. Read-only show of testOptions is permitted to retain exact selection evidence.

No AWS/provider calls, staging, commit/push, reviewer or Phase8 work.

## Independent first targets

```bash
java -version
/usr/bin/time -p sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorageHardeningSpec edu.uic.cs441.scholarchain.independent.IndependentStorageRuntimeFenceSpec edu.uic.cs441.scholarchain.independent.IndependentStorageSdkSpec'
```

Exit1 real7.86s,27passed/1failed across28. New ledgerCAS test incorrectly expected revision Str rather than Num5; owner corrected assertion only. Hardening8 and runtimeFence4 passed. Complete raw output retained independent-targeted-1.txt, hash metadata .json. Java17.0.20.1/sbt1.10.7. No live sources were compiled or executed by this independent-only target.

## Compile-only live configuration and affected normal tests — attempt2

```bash
java -version
/usr/bin/time -p sbt -batch 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / AwsIntegration / compile' 'show storage / Test / testOptions' 'show storage / AwsIntegration / testOptions' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec'
```

Result pending. AwsIntegration compile does not execute tests; show only reads selection settings. Normal Test excludes the live tag. No AwsIntegration test/testOnly/testQuick/executeTests task invoked.

Attempt2 exit1 real9.04s: AwsIntegration compile succeeded; Test options show -l exact live tag and integration options show -n same tag. Normal storage26/27 passed; offline journal policy expected explicit planned state, but default serializer omitted it. Storage owner fixed journal serialization to retain explicit ownership states/fields. Independent target not reached. Live test body excluded. Full output targeted-2.txt and hash metadata targeted-2.json retained.

## Final affected targets — attempt3

```bash
/usr/bin/time -p sbt -batch 'storage / Test / scalafmt' 'independentTests / Test / scalafmt' 'storage / AwsIntegration / compile' 'storage / Test / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentStorage*Spec'
```

Result pending. Still compile-only for AwsIntegration; default Test excludes live body.

Attempt3 completed exit0 real14.87s: final AwsIntegration sources compiled; normal storage27/27 and independentStorage73/73 passed. No live body ran. Runtime scan reports0runtime source files; fixture tests demonstrate detector behavior. Full output targeted-3.txt, metadata/hash targeted-3.json; selection evidence references read-only settings output in targeted-2.txt. C1/C2 fixes validated.

## Final synthetic support-path consistency check — attempt4

```bash
/usr/bin/time -p sbt -batch 'storage / Test / scalafmt' 'storage / AwsIntegration / compile' 'storage / Test / testOnly edu.uic.cs441.scholarchain.storage.AwsLivePolicySpec'
```

Exit0 real7.19s. Corrected synthetic ordinary support path matches production loader manifest; final live configuration sources compile. Offline policy4/4 passed. Live body never run. Exact output fixture-targeted-4.txt and hash metadata .json.

## Fresh full gate

```bash
java -version
/usr/bin/time -p sbt -batch check
```

Started against frozen306 source/build/test/README files in final-source-snapshot.json. Raw output /tmp/phase7c-final-check.txt; exit marker PHASE7C_EXIT_CODE appended after completion. No AwsIntegration test entry point invoked. Result pending at this entry.

Fresh full gate completed exit0: 659 passed/0failed, groups 144/64/39/38/27/339/8, real684.21s; Java17.0.20.1/sbt1.10.7. Complete retained final-check.txt 1,373,089bytes, SHA256 `3da90e0bd60d8948809f3159f4ab24ab85a46d58ddb5ba0a47d46982368e8e2f`. Expected injected format-stage error is a passing build self-test. Storage27offline cases ran; the sole live tagged body did not. Runtime scan0application source files, with detector behavior covered by fixtures. All306 source/build/test/README hashes and mtimes unchanged.
