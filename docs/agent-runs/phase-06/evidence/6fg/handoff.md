# Subphase 6F+6G repair round 1 handoff

STATUS: COMPLETE for blockingF1–F3 and local gates; user recheck pending.
Branch phase-6; base/unchanged HEAD `6ae7378cbef90a176fd1faecae0dee0615eba9e3`.
Plan SHA-256 `6df6d856df6c4c6ee0a8f00125e78af1bce5e789666399ae48a9443aec955096`.

- User limited scope to **only blocking bugs**; F4–F12 deferred. Optional README
  changes were reverted to the original snapshot; existing evidence preserved.
- F1: complete retained-log stage DAG, names/parents/partitions and task/shuffle
  totals:5,667stageIDs/4,532edges;2,004executed totals match. See
  `repair-1/stage-dag.json` / `.md` and real-data-report references.
- F2: replay comparison includes unequal analytics-report:12numeric differences,
  one percentile/eleven means. Only28logical tables/counters match; operational
  report explicitly excluded. Approximation/float-order and latent estimateP90
  limitations disclosed. See updated replay-comparison and repair comparison.
- F3: only implementation delta is SafetySpec; parenless/isEmpty/reduce detection
  plus3synthetic self-tests. Safety target7/7, full gate**554/554**, exit0.
- Gate144/64/39/34/266/7; real676.42s; log1,358,928bytes; SHA-256
  `3e6654835296bab3be44efbdf0cd31c205dd4b34ff87b98848a4ba16623c5236`. Stable27-file snapshot, productionFP and unchangedHEAD verified.
- Production code and retained `run:f02acf56-4bea-4009-adaf-b11d5afceb49` remain
  unchanged; no new real-data run was required. Both original runs remain evidence.
- Commands, hashes, findings, limitations and exact inventories are under
  `repair-1/`; see `reviewer-prompt.md` there for the copyable recheck prompt.
- No commit/push/reviewer/AWS/liveLLM/store calls or6I. User launches recheck.
