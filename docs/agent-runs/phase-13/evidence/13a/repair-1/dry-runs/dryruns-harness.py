"""Dry runs of plan.sh, deploy.sh (each stage), rollback.sh and cleanup.sh against a synthetic clean temp repository.

Synthetic values only; fake aws/terraform/docker/sbt on PATH; no network, no cloud. Writes one file per run into
the output directory given as argv[1]. Run with: python3 dryruns.py OUTDIR
"""
import os
import sys
import unittest

sys.path.insert(0, "/Users/danny/Documents/UIC/CS441/ScholarChain/scripts/tests")
from helpers import REGION, SERVICES, Fixture, registry_digest, sha256_bytes  # noqa: E402

OUT = sys.argv[1]
PRIOR = "c" * 40
ARCHIVE = b"tiny-runtime-archive"


class Harness(Fixture):
    def runTest(self):  # pragma: no cover - harness entry point
        pass

    def save(self, name, result):
        with open(os.path.join(OUT, name), "w") as handle:
            handle.write("# exit code: %d\n" % result.rc)
            handle.write(result.stdout)
            if result.stderr:
                handle.write("\n# --- stderr ---\n" + result.stderr)
        print("%-34s exit=%d  %s" % (name, result.rc, result.result_line()[:100]))

    def go(self):
        prev_commit = self.head()
        self.write("note.txt", "a second commit so a previous commit exists\n")
        self.commit("second")
        archive = os.path.join(self.tmp, "runtime.tgz")
        with open(archive, "wb") as handle:
            handle.write(ARCHIVE)
        self.use_config(RUNTIME_ARCHIVE_EXPECTED_SIZE=str(len(ARCHIVE)), RUNTIME_ARCHIVE_EXPECTED_SHA256=sha256_bytes(ARCHIVE))
        private = os.path.join(self.tmp, "synthetic-private.local.tfvars")
        with open(private, "w") as handle:
            handle.write('owner_note = "SYNTHETIC-PRIVATE-VALUE-000111"\n')
        base_env = {
            "SCHOLARCHAIN_TF_PRIVATE_VARS": private,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE": archive,
            "SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI": "s3://bucket-test/key/runtime.tgz",
        }
        # plan.sh dry run
        self.save("plan-dry-run.txt", self.run_script("plan.sh", "--env", "course", "--region", REGION, **base_env))
        self.save("plan-dry-run-source-commit.txt", self.run_script("plan.sh", "--env", "course", "--region", REGION, "--source-commit", prev_commit, **base_env))
        # deploy.sh dry runs, one per stage
        for stage in ("base-apply", "push", "runtime-apply"):
            revision = None if stage == "base-apply" else self.head()
            plan, sha = self.make_plan(name="%s.tfplan" % stage)
            self.write_plan_receipt(plan, sha, image_revision=revision)
            show = self.write_show_json([("aws_s3_bucket.a", "aws_s3_bucket", ["create"])], image_revision=revision, name="%s-show.json" % stage)
            prespend, prespend_sha = self.write_prespend(name="%s-prespend.json" % stage)
            approval = self.write_approval(self.approval_text(sha, prespend_sha=prespend_sha, stage=stage), name="%s-gate.md" % stage)
            if stage != "base-apply":
                self.write_release_manifest()
            env = dict(base_env, FAKE_SHOW_JSON=show)
            self.save(
                "deploy-dry-run-%s.txt" % stage,
                self.run_script("deploy.sh", "--stage", stage, "--plan", plan, "--region", REGION, "--approval", approval, "--prespend", prespend, **env),
            )
        # rollback.sh dry runs (app and infra)
        previous = self.write_deploy_manifest(revision=PRIOR, digests={s: registry_digest(s, PRIOR) for s in SERVICES})
        self.save(
            "rollback-dry-run-app.txt",
            self.run_script("rollback.sh", "--env", "course", "--region", REGION, "--previous-manifest", previous, "--profile", "scholarchain-deployer-tf", **base_env),
        )
        self.save(
            "rollback-dry-run-infra.txt",
            self.run_script("rollback.sh", "--env", "course", "--region", REGION, "--mode", "infra", "--previous-commit", prev_commit, **base_env),
        )
        # cleanup.sh dry run
        self.save("cleanup-dry-run.txt", self.run_script("cleanup.sh", "--env", "course", "--region", REGION, **base_env))
        # refusals worth keeping: stale pre-spend receipt and a dirty tree
        prespend, prespend_sha = self.write_prespend(name="stale.json", cost_snapshot_utc="2020-01-01T00:00:00Z")
        plan, sha = self.make_plan(name="refuse.tfplan")
        self.write_plan_receipt(plan, sha, image_revision=self.head())
        approval = self.write_approval(self.approval_text(sha, prespend_sha=prespend_sha, stage="runtime-apply"), name="refuse-gate.md")
        self.save(
            "deploy-refused-stale-prespend.txt",
            self.run_script("deploy.sh", "--stage", "runtime-apply", "--plan", plan, "--region", REGION, "--approval", approval, "--prespend", prespend, "--execute", "--profile", "p", **base_env),
        )
        self.write("stray-untracked-file.txt", "dirty\n")
        self.save(
            "deploy-refused-dirty-tree.txt",
            self.run_script("deploy.sh", "--stage", "runtime-apply", "--plan", plan, "--region", REGION, "--approval", approval, "--prespend", prespend, "--execute", "--profile", "p", **base_env),
        )


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    case = Harness()
    case.setUp()
    try:
        case.go()
    finally:
        case._remove_tmp()
