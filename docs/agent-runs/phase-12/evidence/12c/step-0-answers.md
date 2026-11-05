# Subphase 12C — coordinator transcription of user choices

This is a coordinator work-order record, not a human-owned approval/gate file. Source: the current conversation, culminating in “All right, let's do it.” after the complete remaining-defaults and read-only authorization request. The user separately authorized leaving the four pre-existing Phase 08–11 human-gate.md files untouched and continuing 12C.

- Base: phase-12 at 3b0855b9657a72b30e8ac43bd484161a9b886c79; approved 12B and repair committed/pushed already.
- Account 530332961125; named CLI profile scholarchain-planner; environment course; region us-east-2; proposed AZs us-east-2a/us-east-2b, subject to actual read-only availability checks.
- Deployment trusted principal: arn:aws:iam::530332961125:user/scholarchain-planner (trust configuration only; the planner remains read-only).
- Authorized: recommended local repairs/tests, provider downloads, read-only account/service checks and terraform plan only. No apply/destroy/import, AWS writes, paid model calls, paid Cost Explorer calls, credential file/environment inspection, commit or push.
- Selected repairs: N17 vector KMS SourceArn bucket/index coverage; N9 EMR service-role key use; N10 control-policy wildcard ARN guard; N11 omit widgets for disabled EMR/Neptune; N12 native Neptune/DynamoDB panels; N14 missing workflow input guard. Preserve all other items unless separately selected. N15 internal HTTP and N16 missing loader/writer identities are disclosures only.
- Plan the default course shape: Neptune, EMR and runtime disabled; do not choose an EMR runtime or Neptune engine/version implicitly.
- One USD 200 project ceiling before credits across all cloud phases, including optional 9C, 12D, 8C/14, experiments/evaluation and retention. Cost Nov 15–24 as base and Nov 11–24 as upper-duration case, using explicit timestamps. Preferred separately approved cleanup Nov 24; submission Nov 25 at 23:00 CST; retain grading evidence as required.
- Notification preference: AWS signup Gmail, exact address private and absent from evidence. Primary plan keeps enable_budget_resource=false because the separately approved pre-spend account-wide budget bootstrap and private subscriber setup are not complete; disclose this gate. Do not implement or apply that bootstrap in 12C.
- Neither trivy nor checkov was found on PATH. Use the disclosed manual IAM/encryption/public-access checklist plus independent static checks under tests/**.
- Plan binary/JSON outside Git, local state ignored and excluded from evidence; retain only summaries/counts/checksum. No TF_LOG debug dumps. No secret or recipient values in command transcripts/reports.
- Root MFA configured; planner MFA deferred by user. CLI login reported, actual identity and Paid/Free plan still need read-only verification. Do not assume successful live service availability from account signup.
- Early live work requires verified budget notifications and human-enabled Cost Explorer; neither is created/activated by this work order. Delayed billing is reconciliation, not runtime enforcement.
- After final source edits and timestamped source freeze, build-engineer runs JDK17 sbt -batch check; retain exact logs/hashes/XML counts and source snapshots. No reviewer is launched. Finish only 12C and return its complete read-only reviewer prompt.
