# 6F+6G repair round 1 commands and scope

Base/HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`, branch `phase-6`.
User scope: **F1–F3 only**; F4–F12 deferred. Optional README edits were
owner-reverted to the exact original snapshot SHA; no production file changed.

Every sbt command used:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch 'independentTests/Test/scalafmt' 'independentTests/testOnly *IndependentPhase6SafetySpec'
/usr/bin/time -p sbt -batch check
git diff --check
```

The targeted command was wrapped with `/usr/bin/time -p` and explicit exit-code
capture, output to `safety-targeted.txt`: **7/7**, exit0, real5.79seconds.
The full check is retained separately in `final-check.txt`, with final observed
counts/timing/size/hash in `final-gate-metadata.json` after completion.

## Evidence-only derivations

Coordinator ran `python3 -I -` inline inspections (no Spark, production edit,
provider or network). Exact input files/hashes and derivation fields are retained
in `stage-dag.json`; values and source report hashes are in
`analytics-report-comparison.json`. The derivation is:

1. Stream the successful first run's `.event-logs` JSON files. Read Stage Info
   from StageSubmitted/StageCompleted and JobStart's Stage Infos. Key by stage ID
   and attempt; retain Stage Name, Parent IDs and Number of Tasks. Read TaskEnd
   events and sum task count/failures, finish-minus-launch duration, executor run
   time, remote+local shuffle-read bytes, read records, written bytes/records.
2. Compare every executed stage-attempt total and partition count to the original
   retained event summary. Resolve every parent ID and run Kahn's topological
   traversal. Results: 5,667 stage IDs, 4,532 parent edges, all names/partitions,
   no missing parents/cycles; all 2,004 executed attempts match. Retain referenced
   ancestor stages with zero tasks. Full DAG plus an actual bounded ancestor
   subgraph are saved; no claim that the small diagram is the whole DAG.
3. Recursively compare parsed first/replay analytics report dictionaries, arrays
   and scalar values; retain full paths, both values, absolute numeric deltas and
   both byte hashes. Observed 12 differing fields: one P90, eleven means. Add this
   artifact comparison to the existing replay JSON. Keep logical-table equality
   true, explicitly set all-compared-artifact equality false, and disclose report
   approximation/float-order dependence plus latent estimate-P90 limitations.

No retained Parquet, counter array, operational report or run manifest was
rewritten. The required report/comparison evidence and handoff are updated. Raw
logs and prior full gate are preserved; there is no optional retention cleanup.
The user did not approve a new retention policy by saying blocking-only.
