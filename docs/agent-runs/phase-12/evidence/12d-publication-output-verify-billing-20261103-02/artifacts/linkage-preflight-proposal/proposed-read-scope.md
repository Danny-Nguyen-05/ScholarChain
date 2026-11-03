# Proposed local linkage preflight — permission required before execution

Exact proposed command:

```sh
python3 -I /tmp/scholarchain-phase12d-linkage-preflight-proposal/preflight.py --original-gate-filename approval-20261102-attempt02.json
```

This command has NOT been run against actual private storage, even for help. Authoring ran only the separate synthetic test suite. No real gate, stage or operation directory is created. Filename has no default and must match the reviewed direct-child pattern. The fixed canonical repo must be clean at commit a9a52a91c1edaf5a584bd5b1f1affa2985795899 and all11approved billing files must match pinned hashes before any actual private access. Source checks repeat before output. Python bytecode writing is disabled.

## Proposed successful-read scope (fixed paths only)

Under `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/`:

1. `operations/billing-budget-attempt-02/apply.receipt.json`: bounded no-follow secure read TWICE. First read computes its raw metadata-receipt hash in memory but emits nothing; the second read is the accepted verifier's unchanged `Verification.linkage()` validation. The raw hash is printed only if exact receipt schema, successful apply/backup, fixed historical context, original gate and state/backup checks all pass. If the file contains wrong/private/unrecognized data, the helper emits only a fixed failure code and NO hash.
2. Human-pinned `approval-20261102-attempt02.json`: bounded no-follow read ONCE by the accepted linkage method, verifying exact known old hash/context and original time window. The filename comes from the earlier human-pasted Gate saved output; current presence/location/bytes remain unverified until permission is granted and this command runs.
3. `billing.execution.tfstate` and selected backup sibling `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap-backups/initial-ab9f141e83058209/billing.execution.tfstate`: each opaque streamed hash ONCE, compared to fixed reported hash/size. Neither is parsed, printed, copied or edited.
4. `apply.started` and `readback.started` under the fixed original operation: secure zero-byte journal metadata checks. Original `readback.receipt.json` is checked for absence. No journal/log is opened or changed beyond the two specified gate/receipt JSON reads.
5. Fixed primary/backups/operations/original-operation/config directory ownership/mode/ancestor-symlink checks; fixed possible Terraform lock paths are checked for absence without removal.
6. Resolved `/opt/homebrew/bin/aws` launcher: opaque hash ONCE against previously accepted a0124776b581826399171820e7812f2965486e79605c07fc3e86dbe798baf3f9. No CLI/version/subcommand, AWS request or credential/profile/config/cache inspection.
7. Shared `.billing-wrapper-active.lock`: absence checked before and after linkage. No lock is created or removed. These are endpoint absence checks, NOT continuous locking or an atomic filesystem snapshot. Keep other infrastructure operations stopped; later actual verification still requires authoritative under-lock rechecks.

Successful output contains only fixed status/booleans, fixed source commit/old operation/old gate hash, and the newly validated raw APPLY METADATA receipt hash. It never contains recipient data, recipient-file identity/size/hash, spending values, state contents/hash output, arbitrary private strings, raw errors or object bodies. No private notification input is read or statted. No other response logs, plan or toolchain files are accessed.

The helper constructs four narrow in-memory linkage arguments (human filename, measured receipt hash, previously accepted CLI launcher hash and current UTC comparison boundary). They are NOT the32-field execution gate, contain no approval booleans and are never saved as a gate. It invokes only the reviewed `Verification.linkage()`, not load_gate/verify/scan or any production mode. The current UTC boundary only requires the historical apply to precede this preflight; it does not start or renew an execution window.

A successful local check establishes only metadata/hash linkage at the checked times. It does not authenticate human/source provenance, prove current AWS settings or MFA, create a budget, authorize the later verifier, complete W3, or close F4/EMR/delivery/Phase12. The human must separately approve a new real gate/window/session and supervise future read-only verification. Failure stops; no broader inspection, retry, cleanup or recovery is automatic.
