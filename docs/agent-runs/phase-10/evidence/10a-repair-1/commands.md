# Subphase 10A repair round 1 commands

Working directory /Users/danny/Documents/UIC/CS441/ScholarChain. Exact child attempt and initial tool restriction are retained in service-owner-report.md. Root used the current unrestricted tool environment after confirming no child sbt process existed. No approval parameter was used by root.

Every sbt command uses:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
```

## Pre-fix regression

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version > /tmp/phase10a-r1-regression-red.log 2>&1
sbt -batch 'services / Test / testOnly edu.uic.cs441.scholarchain.services.RetriedSessionCreationSpec' >> /tmp/phase10a-r1-regression-red.log 2>&1
phase10a_r1_result=$?
tail -45 /tmp/phase10a-r1-regression-red.log
exit "$phase10a_r1_result"
```

Exit1,3tests:2passed/1failed. RetriedWritten returned503; both noncreator cases passed. sbt elapsed3s. JDK17.0.20.1. Exact output phase10a-r1-regression-red.txt.

## Required focused gates

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version > /tmp/phase10a-r1-targeted.log 2>&1
sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A*' >> /tmp/phase10a-r1-targeted.log 2>&1
phase10a_r1_result=$?
tail -70 /tmp/phase10a-r1-targeted.log
exit "$phase10a_r1_result"
```

Exit0. Formatter tasks elapsed1s/0s; service19passed/0failed/3suites,4s; independent10A20passed/0failed/2suites,3s. Required service and independent scopes were executed sequentially in one sbt invocation without changing selectors.

## Required full gate

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version > /tmp/phase10a-r1-check.log 2>&1
sbt -batch check >> /tmp/phase10a-r1-check.log 2>&1
phase10a_r1_result=$?
tail -65 /tmp/phase10a-r1-check.log
exit "$phase10a_r1_result"
```

Final exit/counts/elapsed/log hash are recorded in check-result.json after completion, with lean output in check-excerpts.txt. The injected format-stage failure is an expected nested build self-test, not an outer gate failure. No unobserved result is claimed.

## Read-only preflight/scope validation

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git diff --check
```

Preflight status/branch/HEAD in preflight.json. git diff --check exit0 before full gate; final repeat recorded after gate. Source hashes are refreshed in source-files.json; original10A source-files.json remains historical checkpoint evidence. Scope diff is repair-source.diff; reconstructed prior production/README bytes are verified against pre-repair SHA256 values before diff generation. Only the three expected F1 paths differ,20original source artifacts unchanged.

## Artifacts and lifecycle

No packaging change, Docker rebuild or container smoke during this repair. Original local images predate F1 and do not contain this fix. No cloud/provider calls,image push,commit/push,reset/discard,human-gate edits or reviewer invocation. No10B work.
