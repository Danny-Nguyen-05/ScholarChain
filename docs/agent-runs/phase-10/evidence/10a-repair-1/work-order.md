# Subphase10A repair round1

User supplied REQUEST-CHANGES and directed: "Fix up the blocking bugs for me."
Only F1 is blocking and authorized. Exact review retained in external-review.txt.

Route F1 only to service-engineer; territory modules/services/**. Retried(_,Written(s)) must run the same creator path as Written(s), including bind/schedule; other Retried outcomes reconcile without execution. Add module regression tests exactly per F1. README only for changed idempotency description. No F2–F5 changes, no10B, no reviewer.

Gates (JDK17 exact plan environment): java -version; sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'services / test'; sbt -batch 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A*'; sbt -batch check; git diff --check. Retain commands,exits,counts,elapsed,hashes/failures. Docker not rebuilt unless packaging changed; explicitly report stale images. No human-gate edits,cloud/provider/push/commit. Return complete recheck prompt and stop.
