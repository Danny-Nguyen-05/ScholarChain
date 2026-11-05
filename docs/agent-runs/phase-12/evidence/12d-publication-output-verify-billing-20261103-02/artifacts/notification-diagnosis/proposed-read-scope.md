# Proposed one-time local notification projection

Execute only after separate human authorization:

`python3 -I /tmp/scholarchain-phase12d-notification-diagnosis/check_notifications.py`

The helper first reads and SHA-checks exactly two public source files. It then traverses the fixed saved-response path using no-follow directory descriptors and opens exactly one protected file: `operations/verify-billing-20261102-01/verify-notifications.stdout` below the selected durable primary. The three protected leaf directories must be uid501/0700; the file must be regular, single-link, uid501/0600, at most8MiB and stable before/after its single bounded read. No other private file is read or statted. JSON duplicate keys are rejected, list length is capped at10, and all errors are fixed constants with no traceback.

Only notification count and fixed per-item projections are printed: recognized50/80/100 threshold or null and presence/type/match flags; recognized public NotificationType/ComparisonOperator/ThresholdType enums or null and flags; unknown-key count. NotificationState and its value, unknown strings/keys/values, email/subscribers, spend, IDs and raw objects/hashes are omitted. Missing ThresholdType stays missing; no default is assumed.

No AWS/CLI/Terraform, recipient input, state, plan, gate, other log, mutation, retry, operation creation or receipt fabrication. Both runtime verification and this diagnostic's actual protected read remain unexecuted by this authoring task. The previous failed verification is not replayed.
