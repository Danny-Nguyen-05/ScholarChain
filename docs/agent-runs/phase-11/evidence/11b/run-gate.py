"""Run a coordinator gate after the specialist's writing barrier; retain lean evidence."""

from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
gate, *arguments = sys.argv[1:]
assert gate and arguments
barrier = json.loads((OUT / "writing-barrier.json").read_text())
assert barrier["stopped_writing"] is True
env = os.environ.copy()
env["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
env["PATH"] = env["JAVA_HOME"] + "/bin:" + env["PATH"]
env["SBT_OPTS"] = "-Dlogback.configurationFile=" + str(
    ROOT / "docs/agent-runs/phase-04/xml-repair-logback.xml"
)
if not (OUT / "java-version.txt").exists():
    version = subprocess.run(["java", "-version"], env=env, capture_output=True, text=True)
    assert version.returncode == 0
    (OUT / "java-version.txt").write_text(version.stdout + version.stderr)
sources = {
    str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted((ROOT / "tests/src/test/scala").rglob("AdversarialRuntime*.scala"))
}
raw_log = Path("/tmp") / ("phase11b-" + gate + ".log")
assert not raw_log.exists(), "Never overwrite prior raw gate logs"
command = ["/usr/bin/time", "-p", "sbt", "-batch", *arguments]
with raw_log.open("xb") as log:
    started = time.time()
    record = dict(
        start_epoch=started,
        start_utc=datetime.datetime.fromtimestamp(started, datetime.timezone.utc).isoformat(),
        command=command,
        cwd=str(ROOT),
        environment={k: env[k] for k in ["JAVA_HOME", "SBT_OPTS"]},
        path_prefix=env["JAVA_HOME"] + "/bin",
        raw_log=str(raw_log),
        source_files=sources,
        writing_barrier=barrier,
    )
    with (OUT / (gate + "-start.json")).open("x") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    print(json.dumps(dict(gate=gate, pid=process.pid, start_epoch=started)), flush=True)
    exit_code = process.wait()
raw = raw_log.read_bytes()
after = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
result = dict(
    exit_code=exit_code,
    end_epoch=time.time(),
    elapsed_seconds=time.time() - started,
    raw_log=str(raw_log),
    raw_bytes=len(raw),
    raw_sha256=hashlib.sha256(raw).hexdigest(),
    source_files_after=after,
    rewritten_sources=[p for p in sources if sources[p] != after[p]],
)
with (OUT / (gate + "-result.json")).open("x") as f:
    json.dump(result, f, indent=2)
    f.write("\n")
lines = raw.decode(errors="replace").splitlines()
tokens = ["welcome to sbt", "compiling ", "Reformatted", "[error]", "FAILED", "Total number",
          "Suites:", "Tests:", "All tests passed", "[success]", "injected format-stage failure",
          "TestRunMarker", "scalafmt", "real ", "user ", "sys "]
excerpt = [f"{n}: {line}" for n, line in enumerate(lines, 1) if any(t in line for t in tokens)]
(OUT / (gate + "-excerpt.txt")).write_text("\n".join(excerpt) + "\n")
print(json.dumps(result), flush=True)
sys.exit(exit_code)
