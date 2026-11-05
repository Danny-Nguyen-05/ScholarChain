# B1/L1 repair addendum — design only

This addendum supplements the immutable design at `/tmp/scholarchain-phase12d-costscope-repair/post-create-verification-design.md`. No continuation implementation, option selection, private processing or execution is supplied here. The review accepted that proposal only as a design; its execution gates remain.

Whichever option is later chosen, the post-create verifier must enforce the repaired whole-Budget contract as well as the accepted cost representation:

- `BillingViewArn` must be absent. Reject every presence, including null/empty and a primary-looking ARN; this round proves no primary ARN's scope. Do not infer the saved response's value, which neither prior diagnostic projected.
- Accept only the documented Budget key set. Reject unknown fields, and reject any presence of `AutoAdjustData` or `PlannedBudgetLimits` including null/empty. Observational metadata must never be confused with a new limit or scope.
- Preserve exact legacy flags when present, the strict modern metric/exclusion pair, all other budget/date/tag/alert/subscriber/health guards, and safe output/privacy rules.

Future verification and W3 receipts must use `cost_scope_match` and `scope_filters_absent`. The latter means there is no scope restriction beyond the approved charge-type exclusion, including no billing-view restriction. Old result fields `cost_types_match`/`filters_absent` are not interchangeable receipts. Receipt provenance, the accepted source, distinct new namespace and linkage to original successful apply/state/backup remain explicit gates; no original readback success receipt may be fabricated.

I3 remains a human decision: Option A verifies captured observations only, and its six successful subprocess exits remain a source-path inference rather than six standalone recorded exit receipts. Option B needs a fresh bounded read-only gate/window/session. Neither option is selected, implemented or automatically substituted for the other. The old raw apply-receipt SHA remains unknown. Original gates, failed journals, state, backup and immutable prior evidence remain untouched.
