# ScholarChain Session 2 approval record

```text
ScholarChain Session 2 approval record (Procedure R)

Approver: Danny Nguyen   Date: 2026-11-17   Time (UTC): 17:57Z

I approve Session 2 under plan option (i), as written in
docs/runbooks/session-2-plan.md at commit
aee1c022d2e6df7d76475600ec04ed6e4f83fe21 (aee1c02), with these limits:

1. Budget. Firm limit USD 25.00. Floor 2: the project total
   (C11_TOTAL_USD plus Session 2 spend) must stay at or below USD 23.00.
   Planned project total 19.54; at caps 22.98 (tax-0 column; margin 0.02).

2. Tax: 0 on credit-covered spend (my decision 2026-11-16); valid while
   credits cover the spend.
   AWS credit balance read: USD 184.25 at 17:55Z (UTC) on 2026-11-17
   (Billing, Credits: "Total estimated amount remaining"). It must be at
   least the Session 2 AWS cap of USD 6.73; otherwise this approval is
   void.

3. Stage a, EMR. S = 10,577 works on EMR. L is dropped on EMR (P25
   rule); both EMR runs go to S and its retry. L is reported from local
   evidence only: Hadoop 132 s, 210 works dropped by the team limit,
   maximum team 79, ER out of memory at 22g after 16 min; Spark with ER
   bypassed (identity pass-through, local only, not the EMR path) 1,110 s,
   48,188 works, 76,623 researchers, 320,690 all-years edges.
   Cluster: r5.xlarge primary and m5.xlarge core, 0.555/h; ER heap 12g; S run cap 75 min;
   step timeouts stage-in 225 s, hadoop-prep 900 s, ER 900 s,
   class-origin 225 s, spark 1800 s, copy-out 450 s. EMR cap block
   2 x (75 + 15) min + 20 min cold start = 3.33 h, USD 1.93.
   EMR ledger caps: 4 live runs and USD 3.53 cumulative (was 3.36),
   including Session 1's EMR spend: 3.53 = 1.68 + 3.33 h x 0.555/h = 1.85.
   Worst case before actuals: 1.68 + 0.84 + 0.84 = 3.36 of 3.53. The
   project figures do not change: 19.54 / 22.98, EMR block 3.33 h =
   1.93, and the pre-R-b check stays spend + 3.57 <= 23.00.
   Pricing restated (it sits under emr-pricing.conf's human pricing
   confirmation): r5.xlarge primary EC2 0.252 + EMR 0.063 = 0.315/h;
   m5.xlarge core 0.240/h; cluster total 0.555/h.
   S retry condition: after S's actual is recorded, the retry is admitted
   only if S's measured cost (from cluster creation, boot included) is
   at most 0.87 (3.53 - 1.68 - 0.84 - 0.14 tail), about 94 min at
   0.555/h. Otherwise the retry is refused (fail-closed) and the plan
   goes to the "S fails twice" fallback (P6 local S export).
   Rounding budget (accepted 2026-11-16, "Accept, add steps"; cap stays
   3.53): every ledger term rounds up to the cent. With a full 75-min S,
   the retry is admitted only if the time from cluster creation to S
   submission, plus the wait before --record-actual, is at most about
   19 min (95 min = 0.87875, rounded up to 0.88; 1.68 + 0.88 + 0.14 +
   0.84 = 3.54 > 3.53). Measured cold start is 4-5 min. Operator steps:
   (a) write record 1 and submit S as soon as the cluster ID exists;
   (b) run --record-actual immediately after an S failure, before
   anything else.
   The EMR actual cost is recorded right after each S run
   (run-bounded-pipeline.sh --record-actual), and gate 1 and the
   pre-R-b check use the recorded actuals, not the cap. Run rule: S first; if S
   fails, retry S once, subject to the retry condition above. L is not
   run on EMR.
   If S fails twice, R-b is not dropped: the chunks and vectors come
   from the retained local P6 S export (same Voyage cap), they are
   loaded, and R-b runs if gate 1 and the pre-R-b check pass by about
   12:15 CST. The report states "vectors derived from the local P6 S run".
   Vectors: up to 10,000 real voyage-4-lite vectors, actual count reported.

4. Gate 1 and the pre-R-b check (both must pass before any R-b apply).
   Gate 1: X_a <= 7.17 - E_b - 0.75 = 7.17 - 3.57 - 0.75 = 2.85.
   Pre-R-b check: spend to date (C11_TOTAL_USD as last read, with its read
   time, plus the clock-based estimate since that read) + R-b cap
   (E_b = 3.57) <= 23.00 (floor 2). Above 23.00, R-b is skipped and
   cleanup starts, unless I record a new decision.

5. R-b Neptune. Capacity min 1 / max 2.5 NCU (P34, max 1 NCU, is not
   possible). The Neptune window is a hard stop at 5.8 h:
   - T_N0 = the actual start of the Neptune base-apply, written in the
     session log (planned 10:50 CST / 16:50Z);
   - the R-b load starts immediately after the B6 smoke passes (planned
     12:45 CST / 18:45Z); the failure example comes after the load
     collection;
   - latest full-variant (about 50 min) load start: T_N0 + 3 h 35 min
     (planned 14:25 CST / 20:25Z);
   - latest load start of any kind (37-min short variant): T_N0 + 3 h 48 min
     (planned 14:38 CST / 20:38Z);
   - the pre-destroy steps (B13, C2 cleanup-prepare plan and apply, the
     C3 pass-1 listing; about 50 min) start no later than T_N0 + 4 h 25 min
     (planned 15:15 CST / 21:15Z);
   - target: the Neptune destroy is issued at T_N0 + 5 h 15 min
     (planned 16:05 CST / 22:05Z);
   - absolute hard stop: the Neptune destroy is issued no later than
     T_N0 + 5 h 30 min (planned 16:20 CST / 22:20Z), whether R-b has
     finished or not, so that about 18 min of deletion (an estimate) ends
     by 5.8 h. Whatever elasticity data was captured is kept, and the
     report states what was cut.
   The overall session hard stop stays 19:00 CST (01:00Z next day).

6. R-b load. The level-50 hold stays at 150,000 requests. The per-level
   request limits are 600 / 3,000 / 15,000 / 30,000 / 150,000 (levels 1, 5,
   25, 50 and the hold at 50) and must not be raised.

7. R-c is dropped. No Neptune graph load and no paid answers in Session 2.

8. Provider keys. The Session 2 Voyage key (stage-a ingest and query
   smoke) goes only into Secrets Manager or the environment of the one
   process that needs it, never as a command-line argument; shell tracing
   is off (set +x); it is deleted at cleanup and revoked afterwards, with
   UTC times recorded. The Anthropic secret holds a non-working
   placeholder (8 to 512 printable ASCII characters, no spaces, not a real
   key), entered the same way as a real key (put-secret-value from stdin,
   never in a file or the repo). No real Anthropic key is created for
   Session 2, so no Anthropic spend limit or revocation is needed, and any
   accidental Anthropic call fails instead of spending.

Signed: Danny Nguyen
```
