# Subphase 7B work order

User: “alright let implement phase 7b”

Step 0 answers: “accept all recommended defaults”

- N1: Store source-run qualifications once, referenced by run ID and SHA-256 from each metric item, preserving all qualifications.
- N2: Verify CSV sidecar hashes in loader and run bounded local replay from retained real data into new temporary output; original export untouched.
- N3: Use fixed ClientRequestToken per logical DynamoDB transaction.
- N4-N9: Defer nonblocking items; N6 remains 7C.
- existing: Fakes/SDK stubs; no Docker dependency; no AWS/provider calls; no reviewer; only 7B; no stage/commit/push.

Implement only plan Section 8 Subphase 7B using the accepted snapshot. Native storage/test owners, and scoped Spark bounded replay only. No reviewer, cloud/provider calls, staging, commit or push; stop before 7C. Exact JDK 17 environment required for every sbt command. Evidence uses Git-visible files, no *.log.
