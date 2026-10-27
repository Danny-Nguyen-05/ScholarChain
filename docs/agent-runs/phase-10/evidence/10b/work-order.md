# Subphase 10B work order

User authorized starting 10B after the prior stop. 10A including repair is committed at c85da7365927a1f7d8ee5ab1f67c5c1a128391b3. No unresolved Step 0 questions: previously approved defaults persist.

Defaults: include F2–F5 through their listed owners; graph direction both, depth 1 (maximum 3), limit 50 (maximum 200), course edge allowlist, opaque cursor bound to request filters and snapshot, configurable 5000 ms hard timeout; evidence/explain course fields backed by stored provenance/audits and add links.evidence; poison threshold 3 configurable with DLQ enqueue before acknowledgement and DLQ failures left unacknowledged; rebuild and smoke all four local Docker images, no push.

Service engineer owns modules/services/**, build engineer owns packaging/build paths, test engineer owns tests/**; root assembles evidence. Production downstream composition must use DownstreamClient with registered per-dependency breakers. No cloud/provider calls, human-gate edits, commits, pushes or reviewer invocation. Full JDK 17 sbt check is required. Stop after 10B handoff.
