# Repair errata and historical evidence

F2: The old USD 10 proposal consumed USD 10 of the existing USD 15 all-EMR planning reserve, leaving USD 5. The user now chose a USD 5 proposed spike cap, leaving USD 10 of that reserve if spent in full. This does not add a new reserve or change the shared USD 200 ceiling. The 12C upper-window scenario's USD 5.09 margin remains small; later EMR runs require a new allocation and exact all-resource cost decision. Neither the chosen cap nor USD 0.96 compute-only subtotal proves a live run fits.

F5: Original infra/final-commands.json contains 14 historical command records without an environment field. The original prose names TF_CLI_CONFIG_FILE, but that is not a captured per-command environment record. This omission cannot be repaired retroactively as observed metadata. Preserve those records byte-for-byte. New repair command records capture selected non-secret environment variables explicitly; never capture an entire environment or credentials.

F6: The preparation packet's notes and four appended tracked report/work-order sections contained missing spaces. The original note bytes and manifest are retained in original-notes/ with original-note-provenance.json. Readability corrections to the original untracked notes are authorized by this repair work order; their earlier gate claims remain historical. Correct tracked records only by appending readable errata and repair sections. Preserve every prior byte, human record and historical log.

F4: The proposal's constant-output assertions do not prove absence of AWS resources. Its zero-resource claim rests on source inspection. No optional test-engineer static check has been assigned.

Stale XML: The original full gate excluded one old TestRunMarkerSpec report under project/verification/target. Its 157 fresh reports contain 1,255 tests with zero failures/errors/skips. This is historical evidence; the new post-freeze gate has its own fresh report inventory.

F7: The user chose neutral references going forward and preservation of existing records/history. No historical redaction or history rewrite is authorized. The repository plan copy under evidence/12c is the neutral authority reference; original historical content is not rewritten.

The required new full gate rewrites normal ignored XML outputs. Original build XML manifests remain historical records; they are not claimed to match the current target files after a new run. The new gate independently inventories and verifies all of its own fresh reports. Original build logs and manifests remain byte-identical.
