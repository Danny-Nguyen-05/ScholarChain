# Candidate-B policy amendment — coordinator transcription

User request: “use all recommended defaults. Also where are we up to ?”

- Authorize the bounded OFFLINE candidate-B policy amendment and E1 fix, with local mock tests/gates only.
- Pin signin:OAuthClientId to arn:aws:signin:::devtools/same-device. Disclose that this extra restriction could cause a live denial; stop for review rather than widen.
- Document a bootstrap-set console password with no forced password reset and no ChangePassword grant; bootstrap-assigned MFA with no self-management grant. Private password/MFA material remains with the human. This is a proposed future setup, not permission to create it.
- Region default us-east-2 with validated configurable region/account; proposed operator name scholarchain-billing-operator, actual ARN unset/unverified. No additional questions for this offline amendment.
- Scope: infra-engineer only infra/terraform/billing-execution/**; coordinator owns evidence; build-engineer runs full JDK 17 gate after final source freeze with no source edits.
- No AWS/account/login/IAM/paid call, console action, real account plan/apply/destroy/import, credential/config/cache/state/private-input read, human-gate/accepted-commit/approval/exception write, reviewer launch, commit/push or Phase 13. No actual identity, role, login grant or budget is installed by this step.
- Candidate B remains live-unverified. No automatic A/permanent-key/Identity Center fallback. Every billing and EMR live gate remains open; USD 5 proposed cap/USD 10 reserve/USD 5.09 margin unchanged and unapproved.
