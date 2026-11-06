"""Retained smoke-test.sh runs against the local stub server (healthy and failure modes). Not part of the repo."""
import os
import subprocess
import sys

REAL = "/Users/danny/Documents/UIC/CS441/ScholarChain"
sys.path.insert(0, REAL + "/scripts/tests")
import test_smoke  # noqa: E402

OUT = sys.argv[1]
THROWAWAY = test_smoke.KEY


def run(label, **flags):
    stub = test_smoke.Stub(**flags)
    env = {"PATH": "/usr/bin:/bin:/opt/homebrew/bin", "HOME": "/tmp", "LC_ALL": "C", "SCHOLARCHAIN_SMOKE_API_KEY": THROWAWAY, "SCHOLARCHAIN_REPO_ROOT": REAL}
    done = subprocess.run(["bash", REAL + "/scripts/smoke-test.sh", "--url", stub.url, "--request-timeout", "3"], env=env, capture_output=True, text=True)
    stub.stop()
    text = (done.stdout + done.stderr).replace(stub.url, "http://127.0.0.1:<port>")
    assert THROWAWAY not in text, "the throwaway value reached the output"
    header = "$ SCHOLARCHAIN_SMOKE_API_KEY=<throwaway> scripts/smoke-test.sh --url <stub>   stub flags=%s\nexit=%d\n" % (flags, done.returncode)
    open(os.path.join(OUT, label + ".txt"), "w").write(header + text)
    print(label, "exit", done.returncode)


run("smoke-stub-healthy")
run("smoke-stub-async", **{"async": True})
run("smoke-stub-fail-readiness", ready_fail=True)
run("smoke-stub-fail-evidence", evidence_404=True)
run("smoke-stub-fail-idempotency", new_query_each_time=True)
run("smoke-stub-fail-error-path", accept_without_auth=True)
