# Login-path evaluation — coordinator transcription

User request: “use those recommendations and evaluate the login path”.

- Evaluate browser-based aws login first using public documentation, public source and safe local help/version only. No login, session, account, credential, IAM, paid or real Terraform call.
- Proposed operator name: scholarchain-billing-operator. No operator exists or actual ARN is verified by this evaluation. No privileged non-root bootstrap identity is confirmed. Consider the previously proposed one-time human-performed console exception only as a design option; this answer is not an exception record or security-change approval.
- Keep the MFA trust strict and the planner read-only. No long-lived key or Identity Center fallback selected. Any alternate design needs review and an explicit bounded human decision.
- No source edits; E1 remains carried until the next implementation touch of billing-execution. No new full build or Terraform gate needed for evidence-only evaluation; earlier results remain historical.
- No remaining questions for this offline evaluation. New authentication or permission changes, identity setup, plans/applies, budget creation, spending, live 12D and Phase 13 remain separate gates.
