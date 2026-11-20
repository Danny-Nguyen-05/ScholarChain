# P35 analysis: reads only the run's derived/summary.json, raw/events.jsonl and the cgroup samples. Prints figures; invents nothing.
import json, datetime, sys, bisect
RUN = "target/experiment-runs/15b-ecs-scaling-semantic-p35-local-1"
EV = "target/p35-rehearsal/run-1"
s = json.load(open(f"{RUN}/derived/summary.json"))
def ep(t): return datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc).timestamp()
samples = []
for line in open(f"{EV}/cgroup-cpu-samples.txt"):
    p = line.split()
    if len(p) < 9: continue
    d = dict(zip(p[1::2], p[2::2])); 
    samples.append((float(p[0]), int(d["usage_usec"]), int(d["nr_periods"]), int(d["nr_throttled"])))
ts = [x[0] for x in samples]
def at(t, k):
    i = bisect.bisect_left(ts, t)
    if i == 0: return samples[0][k]
    if i >= len(ts): return samples[-1][k]
    (t0, t1) = ts[i-1], ts[i]
    f = (t - t0) / (t1 - t0)
    return samples[i-1][k] + f * (samples[i][k] - samples[i-1][k])
rows = []
for ph in s["phases"]:
    a, b = ep(ph["started_utc"]), ep(ph["ended_utc"])
    cpu = (at(b,1) - at(a,1)) / 1e6
    per = at(b,2) - at(a,2); thr = at(b,3) - at(a,3)
    sem = ph["routes"].get("semantic", {})
    rows.append(dict(phase=ph["phase"], level=ph["level"], seconds=ph["seconds"], requests=ph["requests"], rate_limited_429=ph["rate_limited_429"],
        successful=ph["successful_requests"], success_rps=ph["success_rps"], success_rps_active=ph["success_rps_active"], peak_success_rps_1s=ph["peak_success_rps_1s"],
        semantic_success_rps=sem.get("success_rps"), semantic_peak_1s=sem.get("peak_success_rps_1s"),
        success_per_min=round(ph["success_rps"]*60), cpu_seconds=round(cpu,2), cpu_pct_of_0_25_vcpu=round(100*cpu/(ph["seconds"]*0.25),1),
        cpu_pct_of_1_vcpu=round(100*cpu/ph["seconds"],1), throttled_period_share=round(thr/per,3) if per else None,
        p50=ph["latency_ms_2xx"]["p50"], p95=ph["latency_ms_2xx"]["p95"], p99=ph["latency_ms_2xx"]["p99"]))
json.dump(rows, open(f"{EV}/per-level-results.json", "w"), indent=1)
for r in rows: print(json.dumps(r))
print("samples", len(samples), "first", samples[0][0], "last", samples[-1][0])
