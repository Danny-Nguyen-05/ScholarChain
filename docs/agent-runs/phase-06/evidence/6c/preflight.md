# Subphase 6C preflight

- Branch: `phase-6`.
- Base SHA and starting HEAD: `01d204b531d3fc72a5c49f884980a5c7c8926b18`.
- Starting tracked and untracked diff: empty (`git status --short --branch` printed only `## phase-6...origin/phase-6`).
- Last commit: `01d204b phase-06 domain-engineer: add Spark analytics contracts, stable IDs, and configuration`.
- User's Step 0 answers and corrected 6C-3 run choice are in `../../prompt.md`.
- The initially suggested `datasets/entity-resolution/prepared/f22f1a12-c7be-43af-b470-d4f4e244ca9d` root has a completed manifest naming DBLP but no retained `snapshot=dblp-*` export directory. The user accepted the corrected choice: `target/phase4-runs/ccd26111-d26d-4783-bc0f-e7106e4e617d`, which has `run-manifest.json`, `export/_SUCCESS`, and a DBLP snapshot export directory.
- No matching ER export for the corrected Hadoop run was established at preflight. 6C must verify or create one locally before claiming the smoke result.
- JDK 17 preflight: `/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin/java -version` exited 0 and printed OpenJDK `17.0.20.1` (Homebrew).
- The coordinator then ran the existing Phase 5 offline resolver with `--llm-mode disabled` against the corrected Hadoop run. Exact command and output are retained in `er-export.txt`; exit 0, 18 comparisons, fake calls 0, live calls 0. The output `target/phase6-inputs/6c-er-ccd26111-disabled` is ignored local data, has `resolution-manifest.json` with `complete=true` and a completion marker, and reports 3 accepted researcher links plus 6 accepted work links. No provider call or human label was involved.
