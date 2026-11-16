# P35 local elasticity rehearsal, run p35-local-1 (all figures observed; derivations shown)
Source: target/experiment-runs/15b-ecs-scaling-semantic-p35-local-1 (loadgen, commit f801d28, tree dirty), cgroup samples in this directory.
Setup: query-api offline-synthetic in Docker, --cpus 0.25 (cgroup cpu.max 25000 100000), --memory 1g, rate limit 100000/100000, one task, loadgen on the host over loopback.
Outcome: completed, 198,750 requests (150 warm-up + 198,600), 0 errors, 0 x 429.
Target derivation: success rps x 60 per task. level 1 = 88.08 x 60 = 5,285; level 25 = 450.572 x 60 = 27,034; level 50 = 806.235 x 60 = 48,374 (hold-50 1,015.538 x 60 = 60,932).
  T > 5,285 and 2T <= 27,034 -> 5,285 < T <= 13,517. Proposed T = 10,000.
r_S2: peak_success_rps_1s at level 50 = 1,262 (level-50), 1,737 (hold-50); max 1,737; 2 x 1,737 = 3,474 -> r_S2 = 3,500, b_S2 = 7,000.
