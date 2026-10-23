# Subphase7A repair round1 handoff

STATUS: COMPLETE local F1/F2 repairs and required checks; recheck pending.
OWNER: Coordinator /root; storage/test owners unchanged.
WORK ORDER: Fix only blockers F1/F2. No questions; original Step0 defaults persist. No7B/reviewer/cloud/commit.
FILES CREATED: Phase7ManifestSmokeMain.scala plus repair evidence;23.log->.txt byte-preserving renames.
FILES MODIFIED: ManifestRows.scala, ParquetManifestSpec.scala, IndependentStorageParquetSpec.scala and coordinator metadata/reports. Exact files.json.
COMMANDS RUN: Section2JDK17, exact commands.md. java-version17.0.20.1; targeted10/27/4passed; clean real smoke0; freshfullcheck0.
TEST RESULTS:596passed/0failed,144/64/39/38/10/293/8,real681.20s. Full raw hash26f7ad074aa1db1028558326d8826e30fd6e07937ed8ad511a2d5870f12e2497.
VALIDATION RESULTS:F1 exact producer strings/malformed counts+real bounded reader smoke. F2 all23 byte hashes/Git visibility/live retained references pass, .gitignore unchanged. All110 source hashes/mtimes stable; protected inputs/review/source metadata preserved.
ASSUMPTIONS: Actual smoke is bounded, not a full dataset/cache audit. Git-visible files await human commit; none staged.
RISKS:N1–N8 OPEN and unchanged; no live AWS or real CSV replay. Earlier smoke launch errors are retained with clean corrected probe.
MANUAL ACTION REQUIRED: User launches recheck with rechecker-prompt.md, then commits only after APPROVE.
BLOCKED-ON OWNER:None local.
BLOCKED-ON EVIDENCE:None required local; later/live gates unverified.
NEXT GATE:User-launched7A repair1 recheck. All jobs and specialists ended. Stop; no next subphase.

Branch phase-7; base/currentHEAD98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2.
The complete copyable recheck prompt is rechecker-prompt.md in this directory.
