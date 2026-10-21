# Human review checkpoint for Phase 5D

The user confirmed “Not yet” when asked for saved annotation files. No real human labels have been imported.

1. Open the unchanged local page at `modules/entity-resolution/src/main/resources/review/index.html`.
2. Load `docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json`. Use the repaired queue, not an archived pre-repair copy.
3. Enter your reviewer ID and use the initial review tasks. There are 240 initial reviews: 40 development and 200 held out; 60 reserves are separate. The page keeps predictions hidden.
4. Review the source evidence and choose Same, Different or Uncertain. OpenAlex IDs and supplied ORCIDs are provider hypotheses, not proof of identity. Do not guess when the evidence is insufficient.
5. Save the original checkpoint JSON frequently outside `target/`, keep a backup and resume with the same queue. Do not edit or merge the JSON manually.
6. Return the local path of the saved original checkpoint when ready. The importer will validate its population/evidence bindings and revision history before counting labels.

The technical adapter tests, any future model output, and synthetic browser/test fixtures do not count as human reviews. No held-out scoring or Phase 5E work has begun.
