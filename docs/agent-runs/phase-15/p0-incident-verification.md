# P0 incident linkage verification (modify-20261116-01), 2026-11-17

Coordinator record, assembled from the human's pasted outputs. The account ID is redacted as `<account>`, and no recipient appears. The human ran every step in their own Terminal from `target/phase15/p0/p0-steps.md`, section "Incident linkage verification (modify-20261116-01)". The main checkout was clean at the frozen session commit `9e881a2e595328c5d3a4a9fc45827cb6b4a6367f`.

| Step | What ran | Observed result |
|---|---|---|
| I1 (offline, no AWS) | Evidence pre-check of the preserved incident artifacts | All checks `ok` (groups A-H: backup and op folder file sets; recovery-000 = current state `92a7ba42…0e6d` / 40834 B; recovery-001 = current `.backup`; pre-apply copy = initial `271fe888…3f67` / 40818 B; journal and apply-log shape; receipt sizes 469 / 490 B and line counts; no wrapper lock; verify op folder absent; modes 0700/0600, single link, owner; no symlink; state/lock scan). `MGATE_SHA=7279b775ba7e9696b8fba46bbedfe6601213edbff1f40a3629ad21084f2b339f`, `PRES_SHA=1dcfeaa77bb90f5fedd69a4450a9009063fb67142407b06301a3c2942ee2bc68`. **`I1-result: differences=0`** |
| I2 (AWS login, STS, gate) | `aws login` (finished 09:39:11 CST), `aws sts get-caller-identity` (09:39:22 CST; role `scholarchain-billing-deployer`, session `scholarchain-billing-operator`), clean-checkout check (`HEAD=9e881a2…`, no status lines), `p0_gate.py verify --linkage incident`, window start `2026-11-17T09:39` (America/Chicago) | Gate written privately as `$PRIMARY/approval-20261116-verify-incident.json`; **`VGATE_SHA=54507124d993a6ee89ebd197e0fab455c292c55afba42073ba43feba9317786f`**. Human answers: retention yes; read-only verification yes; G1 affirmation "I confirm this is a read-only verification of the USD 25 budget after incident modify-20261116-01." |
| I3 (read-only verify, AWS reads) | `budget_verification.py verify-modified --operation verify-usd25-incident-01` | **`exit=0`**. Observed at 2026-11-17T15:42:05Z. Output below |

I3 output (one JSON line, account redacted):

```json
{"actor_arn": "arn:aws:sts::<account>:assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator", "gate_sha256": "54507124d993a6ee89ebd197e0fab455c292c55afba42073ba43feba9317786f", "linkage": {"incident_cause_recorded": null, "mode": "incident", "modify_gate_sha256": "7279b775ba7e9696b8fba46bbedfe6601213edbff1f40a3629ad21084f2b339f", "modify_operation": "modify-20261116-01", "preservation_receipt_sha256": "1dcfeaa77bb90f5fedd69a4450a9009063fb67142407b06301a3c2942ee2bc68", "state_backup_verified": true, "state_unchanged_since_incident": true}, "observed_at": "2026-11-17T15:42:05.023697+00:00", "operation": "verify-usd25-incident-01", "option": "M", "plan_sha256": "01c74ac90e44614c0df0aba500fed33fe94b1c49bd989ec1a1b185c02193d529", "result": {"account_request_matches": true, "budget_fields_match": true, "cost_scope_match": true, "dates_match": true, "delivery_verified": false, "email_subscribers_each": 1, "health_healthy_if_reported": true, "health_reported": true, "notification_count": 3, "phase12d_complete": false, "private_recipients_match": true, "scope_filters_absent": true, "sns_subscribers": 0, "tags_match": true}, "stage": "verify"}
```

Private log (gitignored): `target/phase14/evidence/14b/budget-modify-incident-verify.log`, 1174 bytes, sha256 `ff32112ca90476c79717c91f90c1960023ecfe6bffce2bdf5942f2a98650520b`. That hash is of the unredacted file.

**Result.** The live budget matches the approved USD 25 shape:
- 3 actual-cost notifications, each with one e-mail subscriber; no SNS subscriber;
- cost scope, budget fields, dates, tags and private recipients match; no scope filters.

The state has not changed since the incident, and the preserved state backup is verified. This closes the P0 API readback that was pending in `docs/runbooks/session-2-plan.md` (P0 row, "Amended 2026-11-16" block) and in incident `docs/incidents/2026-11-16-p0-budget-modify-backup-check.md`. Per the wrapper's design, `delivery_verified` is `false`: e-mail delivery is not checked by an API read.

The optional `post-freeze-scan-modified` publication scan was not run.
