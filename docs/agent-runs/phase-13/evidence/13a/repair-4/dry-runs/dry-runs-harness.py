"""Dry runs of rollback.sh --mode infra on fixture states (fake aws/terraform/docker on PATH; temp git repo; no cloud).

Usage: python3 -I dry_runs.py <scripts/tests dir> <output dir>
"""
import os
import sys

TESTS = sys.argv[1]
OUT = sys.argv[2]
sys.path.insert(0, TESTS)

import helpers  # noqa: E402
from test_runtime_rollback import REV  # noqa: E402


class Driver(helpers.Fixture):
    def runTest(self):  # unittest needs a method name; never run as a test
        pass


def main():
    d = Driver()
    d.setUp()
    try:
        archive = os.path.join(d.tmp, "runtime.tgz")
        with open(archive, "wb") as handle:
            handle.write(b"tiny-runtime-archive")
        d.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE="20", RUNTIME_ARCHIVE_EXPECTED_SHA256=helpers.sha256_bytes(b"tiny-runtime-archive"))
        prev = d.head()
        d.write("infra/terraform/modules/runtime/newer.tf", "# newer\n")
        d.commit("newer tree")
        manifest = os.path.join(d.tmp, "deployed-manifest.json")
        import json

        with open(manifest, "w") as handle:
            json.dump({
                "schema": "scholarchain.deploy-manifest.v1", "stage": "runtime-apply", "commit": REV, "image_revision": REV,
                "region": helpers.REGION, "account_sha256": helpers.account_hash(), "plan_sha256": "a" * 64, "run_id": "earlier",
                "images": [{"service": s, "repository": "scholarchain-course/%s" % s, "tag": REV, "registry_digest": helpers.registry_digest(s, REV)} for s in helpers.SERVICES],
                "ecs_services": [{"service": s, "task_definition": "arn:aws:ecs:%s:<acct>:task-definition/scholarchain-course-%s:7" % (helpers.REGION, s)} for s in helpers.SERVICES],
            }, handle)
        push = d.write_push_record(commit=REV)
        base = ["--env", "course", "--region", helpers.REGION, "--mode", "infra", "--previous-commit", prev]
        cases = [
            ("1-post-base-apply-no-binding", helpers.post_base_apply_resources(), []),
            ("2-post-base-apply-deployed-manifest", helpers.post_base_apply_resources(), ["--deployed-manifest", manifest]),
            ("3-post-base-apply-deployed-push-record", helpers.post_base_apply_resources(), ["--deployed-push-record", push]),
            ("4-partial-lb-without-services-no-binding", helpers.post_base_apply_resources() + helpers.deployed_runtime_resources(services=()), []),
            ("5-live-after-runtime-apply-deployed-manifest", helpers.live_after_runtime_apply_resources(), ["--deployed-manifest", manifest]),
            ("6-live-after-runtime-apply-no-binding", helpers.live_after_runtime_apply_resources(), []),
        ]
        summary = []
        for name, resources, extra in cases:
            open(d.log, "w").close()
            d.write_state(extra={"resources": resources})
            result = d.run_script("rollback.sh", *(base + extra))
            calls = [c for c in d.calls() if not c[1].startswith("version")]
            text = "# rollback.sh %s (dry run; fixture state: %s)\n" % (" ".join(["--env course --region", helpers.REGION, "--mode infra --previous-commit <prev>"] + [a if not a.startswith("/") else "<" + os.path.basename(a) + ">" for a in extra]), name)
            text += "# exit=%d last_step=%s non-version tool calls=%d\n" % (result.rc, (result.steps() or ["-"])[-1], len(calls))
            text += result.stdout + ("\n# stderr\n" + result.stderr if result.stderr else "")
            with open(os.path.join(OUT, "dry-run-%s.txt" % name), "w") as handle:
                handle.write(text.replace(d.tmp, "<fixture-tmp>"))
            summary.append("%s: exit=%d last_step=%s non_version_calls=%d %s" % (name, result.rc, (result.steps() or ["-"])[-1], len(calls), result.result_line()[:160]))
        with open(os.path.join(OUT, "dry-runs-summary.txt"), "w") as handle:
            handle.write("\n".join(summary).replace(d.tmp, "<fixture-tmp>") + "\n")
        print("\n".join(summary).replace(d.tmp, "<fixture-tmp>"))
    finally:
        d.doCleanups()


main()
