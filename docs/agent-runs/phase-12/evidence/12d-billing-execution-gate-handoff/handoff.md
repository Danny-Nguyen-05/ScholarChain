# Billing execution-gate handoff — preparation only

Prepared November 1, 2026, America/Chicago. This is a decision checklist and bounded operating procedure, **not a human approval, executable work order or permission to run commands**. No production wrapper mode, login, AWS call, toolchain inspection or durable/private access was performed. The user-supplied independent recheck approves W1/W2 repair/offline regressions only; W1/W2 and A1/A2 are closed. W3 and R1 remain execution-gate requirements. W4 and R2/R3 are informational with no detailed finding supplied; none is invented here.

## Exact reviewed inputs

The only proposed cloud mutation is the initial create of `aws_budgets_budget.project[0]`, budget `scholarchain-project-budget`, account `530332961125`, profile `scholarchain-billing-deployer`, region `us-east-2`. No main-environment apply, adoption/import, IAM change, paid experiment or subsequent modification is included.

| Binding | Reviewed value |
| --- | --- |
| Saved plan | `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/billing.execution.tfplan` |
| Plan | 6631 bytes; uid501;0600; SHA256 `ab9f141e83058209263cf561eef1d102496ec7f534b88ce421620d8e0045f855` |
| Proposal | `docs/agent-runs/phase-12/evidence/12d-billing-apply-proposal/proposal.md` |
| Proposal SHA256 | `d97abf57f30f72a3c66502a998e3962c4f2b4a2f28797237fd464a5b5d8113d5` |
| Final wrapper | `scripts/billing/budget_execution.py`; SHA256 `e8876abe58a787f9753793b822140cc311863c12373e09f79b8f367ebdfa3507` |
| Complete five-file script binding | `reviewed-bindings.json` in this packet; all five files, not wrapper alone |
| Personal record (G1) | `docs/agent-runs/phase-12/billing-bootstrap-exception.md`;1334bytes; SHA256 `abe3a50ad7167fa01227c73e15e92a422a50609f6313bdcc56404cb61765d71a` |
| Exact acceptable caller | `arn:aws:sts::530332961125:assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator` |
| Resource state | `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap/billing.execution.tfstate` |
| Versioned backup | `/Users/danny/Library/Application Support/ScholarChain/terraform/billing-bootstrap-backups/initial-ab9f141e83058209/` — exclusive new directory, never reuse |

The approved budget is USD200 COST/CUSTOM, October1,2026 00:00 through January1,2027 00:00 UTC; exact11CostTypes, no filters, five governance tags and three ACTUAL/GREATER_THAN/PERCENTAGE50/80/100 alerts with one private EMAIL subscriber each and zeroSNS. The approved proposal/pins control every value; no new financial recommendation is made.

## One bundled human decision, after handoff review

The human owns and personally writes the execution decision. This packet neither supplies an affirmation in their voice nor sets approval booleans, dates or signatures. These are the remaining decisions/evidence to collect together:

1. **Source control and clean checkout.** Review the complete intended diff and choose the exact commit containing the reviewed scripts, proposal, source freeze and required public records. Current HEAD `5ca8406bad5fe55f732458fa0cbd5d561ac83d8f` does not contain the uncommitted scripts, so it is not a valid execution release. Current750-entry work must not be blindly added, discarded or treated as clean. The user controls commits; no agent commits, stashes, resets or grants an exception. The wrapper hardcodes the repository location `/Users/danny/Documents/UIC/CS441/ScholarChain` and its own path; the executable checkout must be clean **at that canonical path**. A differently located worktree cannot execute this wrapper unchanged. A separate checkout may hold human approval/evidence, but that does not change the canonical execution-path requirement.
2. **G1.** Personally affirm in the human's own words whether the full1334-byte record above reflects their statements. Preserve that existing record untouched; keep the new statement as a separate human-owned record. Historical timing acceptance does not prove the original60-minute window or authorize future work.
3. **Actual AWS CLI binding.** Before any approved production invocation, obtain the resolved installed executable SHA256 and CLI version in a separately authorized local-only preflight; record actual observed output. Neither has been inspected here. The script expects `/opt/homebrew/bin/aws` and compares the resolved executable with the gate hash. Do not invent a hash/version, install/upgrade or add a CLI override. The version is required in the human decision/evidence; the gate JSON accepts the hash but has no version field, so adding a version key there would fail its exact schema. Required skeleton capability is checked offline by the wrapper before the exact-name request.
4. **Dated execution window and actor.** Choose a start/end with UTC offsets and America/Chicago timezone, no more than one hour, covering one fresh MFA role session, human STS, P3, one apply, backup, readbacks and final scan. Do not start a window now or reuse yesterday's login. Apply cap300seconds, graceful-stop60seconds, reap5seconds and local-preservation headroom15seconds require80seconds reserve before launch; reads cap60seconds. Local preservation remains authorized after window expiry; all further live/readback work stops. A later readback after expiry needs a separately reviewed path, not edited timestamps or replay.
5. **Scope and failure policy.** Explicitly approve the exact plan/proposal/five wrapper file hashes, source commit, identity/account/profile/region, offline CLI capability check, P3 exact-name read, one saved-plan apply, unconditional local backup/preservation, narrow readbacks and final privacy scan. Include minimal environment with `AWS_MAX_ATTEMPTS=1`, retention and same-disk limitations, W3 publication procedure and R1 persistent-terminal procedure. No retry/import/destroy/IAM widening/implicit rollback is included. Human confirms ownership reconciliation honestly; unknown remote inventory/adoption remains F4, not a fictitious complete inventory.

The human decision may reference this handoff by its final manifest hash. Any changed script/proposal/plan requires review, never automatic regeneration. Once the exact release and real CLI metadata are available, the coordinator can validate the personal gate schema and hashes without composing or signing the approval itself. No fresh notification email is requested here; the protected input remains untouched.

## Machine gate field guide — no filled gate created

The wrapper requires exactly these top-level fields. This guide describes them; it is not an approval JSON template.

| Fields | Source and validation |
| --- | --- |
| `operation` | Human-selected unique operation identifier;1–64 letters/digits/underscore/hyphen; never reuse an existing attempt |
| `plan_sha256`, `proposal_sha256`, `wrapper_files` | Exact reviewed values above and all five repository-relative files/hashes from reviewed-bindings.json |
| `source_commit` | Human-selected40hex release commit; actual canonical checkout HEAD must match and be clean for all live stages |
| `human_record_sha256`, `g1_affirmation` | Bound record and human's own statement; provenance assessed externally, not inferred from hash or minimum string length |
| `actor_arn`, `account`, `profile`, `region` | Exact reviewed role identity/account/profile/region, no alternative credentials |
| `window_start`, `window_end`, `timezone` | Human-selected offset-aware dated timestamps, <=1hour, `America/Chicago` |
| `login_at`, `human_sts_observed_at`, `human_sts` | Fresh human-recorded observations inside that window, exact Account/Arn projection; unknown times/exits stay unknown and block rather than being invented |
| `permissions` | Exact six action categories defined by script: `p3-check`, `apply`, `backup`, `readback`, `post-freeze-scan`, `preserve-partial`; human decision must explicitly cover their meaning |
| `retention_accepted`, `wrapper_review_approved`, `ownership_reconciled` | Human-owned decisions with external evidence; never agent-prepopulated or assumed |
| `aws_cli_sha256` | Observed resolved executable hash from authorized local preflight; version separately retained in human decision/evidence |
| `public_packet_root` | One unique human-approved new repository-relative packet under `docs/agent-runs/phase-12/evidence/`; all W3 suffix copies must be included |

The future CLI also takes the personal gate path/SHA and operation ID. The gate must live outside the canonical clean execution checkout until live stages finish, avoiding a self-referential commit or dirty source tree. Do not retain fresh login URLs, tokens or email addresses in any public record. This task has not authored a real gate, selected an operation/window or consumed any credential.

## R1 — persistent-terminal operating procedure

Before later authorized execution, the human selects a persistent local Terminal session under their control. Run the wrapper in the foreground and keep that Terminal, the wrapper process and the computer awake and available through apply, termination handling and the completed backup receipt. Do not run the apply as a disposable agent-tool process, background task or session liable to end at a tool timeout; do not close Terminal, force-quit, log out, reboot or kill the wrapper. No terminal multiplexer, supervisor or software installation is added by this handoff.

Terraform children run in their own process group. A wrapper crash/death can bypass graceful interruption and backup while children or remote work continue. Persistent Terminal reduces that risk; it does **not** make the wrapper crash-safe, guarantee state persistence or close R1 by itself. On lost wrapper/terminal, absent completion receipt, forced termination or unknown child status: stop the workflow, preserve existing logs/state, do not launch another wrapper/apply, delete locks, refresh credentials or perform recovery commands. Route incident-responder/human review to establish process and remote-state facts with a new bounded read-only diagnosis work order. No monitor is running and no automatic recovery is authorized. The deploy owner records whether uninterrupted foreground supervision and backup completion were actually observed.

## W3 — final publication coverage without changing the scanner

The wrapper scans one packet; it cannot certify later phase-record appends. The later authorized execution procedure must therefore satisfy this complete sequence:

1. Before live work, record each public destination's existing byte length/SHA. Draft no sensitive content. Use a separate evidence workspace for coordinator assembly; keep the canonical source checkout wholly clean during P3/apply/readback. Approved private raw outputs stay outside Git; public projections are allowlisted.
2. After the live stages and private checks, fully assemble **every proposed public artifact and the exact final appended bytes for all five phase records** in the gate's one new packet. Store suffix copies, a mapping of each destination/base length/base hash/suffix length/suffix hash, and a public publication inventory. Include final report prose, command results, human confirmation categories and any outgoing summary intended for publication; no recipient or raw response. Do not publish/append those suffixes yet. Compare all five suffix copies byte-for-byte with their intended additions and retain only public hash/count/equality results.
3. In the canonical source checkout, only that gate-bound new packet and the explicitly named external freeze manifest may now be dirty. Every script/source/other path remains pinned. The manifest outside the packet lists every existing packet file with path/bytes/SHA, including suffixes, inventory and derived packet manifests. Exact-recipient scan runs in the authorized wrapper after all those bytes are frozen, still within the approved session/window. Do not read the actual recipient manually. Failure/expiry blocks publication and requires separately reviewed scope; no claim a generic scan is equivalent.
4. Keep the scan receipt outside the frozen packet, with its fixed safe schema and external-manifest binding. Its own allowed fields and the external freeze manifest are declared exclusions; no arbitrary prose/private payload is allowed in them. Independently verify packet completeness, unchanged hashes, unchanged destination prefixes and exact suffix-to-publication equality immediately before publication. Append **only those exact scanned suffix bytes**; validate resulting full-file hashes against base+suffix and record observed equality. Any extra word, later append, new artifact or changed outgoing summary requires reassembly/refreeze/rescan before publication. Never append an unscanned narrative receipt afterward.
5. Keep final scan receipt and final publication-comparison result outside the frozen packet with a fixed non-sensitive schema (path identifiers, lengths/hashes, booleans/counts and observation times only), explicitly excluded from recursive scanning. The final reviewer checks the full publication inventory, destination base+suffix equality and exclusions. If existing approved helpers cannot perform the required comparison without new code or the canonical checkout cannot satisfy scope rules, stop for separately scoped infra authorship/review. This document does not write a broader scanner or waive checks.

This preparation packet uses generic reserved-fixture email-pattern checks only. W3 remains open until actual final publication evidence exists. No runtime exact-recipient handling occurred here.

## Later execution sequence and stop boundaries

After independent handoff review and the personal gate, the human provides fresh MFA login and STS inside the selected window. Deploy-engineer validates exact release/CLI/gate bindings and executes only the approved source-controlled wrapper, via the persistent-terminal procedure. Stage order is P3 exact-name absence, one apply and immediate local backup, then narrow readbacks, then W3 final assembly/scan/publication. P3 must be <=120seconds old at apply. Wrong identity, budget exists, denial, capability mismatch, unexpected state, changed hashes, stale receipts or failure stops without retry/widening. No human login or production command is requested now.

An apply success alone is not verified monitoring. The human privately reports only actual subscription/delivery observations; absence of a threshold event is not delivery failure. Configuration verification, delivery status and remaining allowance are reported separately and honestly. No artificial spend is manufactured. State/backups remain through reviewed teardown/reconciliation and human-approved cleanup; superseded temporary plans are not deleted.

G1/G2/F4/P3/B1/B2/B3/R1/N19/N20, W3, live budget acceptance/accounting/delivery and EMR gates remain open. This handoff does not prove EMR feasibility or authorize the proposed USD5 spike. Main171-create environment stays unapplied. Phase12D and Phase12 remain open. Next step is user-launched independent review of this handoff; no live continuation in this task.
