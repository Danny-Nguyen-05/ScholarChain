"""Phase 14C slice upload (scripts/upload-slice.sh), written independently by the test-engineer from the requirement (user's 14C
decision 5: "Upload script: accepted, with checksums recorded", USD 25 replan) and the script's own --help contract, not from the
implementation or from scripts/tests/test_upload_slice.py.

Requirement, restated:
  * a dry run (the default) makes no aws call and writes nothing; it plans one object per uploadable file under <run-prefix>/;
  * refusals (nothing is uploaded): bad run prefix, a non-completed export, a key that would leave the prefix (a symlink, an odd
    character, a stray file), an existing object whose content differs (or that carries no SHA-256), a caller that is not the
    operator-loader role, a bucket that is not this project's curated bucket or belongs to another account, an existing manifest;
  * --execute: put-object with a declared SHA-256 and `--if-none-match '*'` (never overwrite), then head-object of every key (the
    stored size and SHA-256 must equal the local file), then a manifest that shows the account as `<acct>`, never the raw ID;
  * re-running is idempotent: identical objects are UNCHANGED and not re-put.

The cloud is a fake `aws` written here (a directory-backed S3 plus sts); no network, no credentials. The account ID is synthetic.
"""
import base64
import hashlib
import json
import os
import re
import stat
import textwrap
import unittest
from pathlib import Path

import sc_support as S

ACCOUNT = "111122223333"
OTHER_ACCOUNT = "4444" + "5555" + "6666"  # a second, foreign account (split so the repository holds no literal 12-digit run)
BUCKET = "scholarchain-course-%s-curated" % ACCOUNT
PREFIX = "run-20261115"
LOADER_ARN = "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-loader/session-one" % ACCOUNT
RUN_ID = "run:00112233-4455-4677-8899-aabbccddeeff"

from fake_s3 import FAKE_AWS, b64  # noqa: E402




class Case(unittest.TestCase):
    def setUp(self):
        self.fx = S.Fixture(self)
        fx = self.fx
        self.fake_dir = fx.aux / "fakes3"
        (self.fake_dir / "objects").mkdir(parents=True)
        aws = fx.bin / "aws"
        aws.write_text(FAKE_AWS)
        aws.chmod(aws.stat().st_mode | stat.S_IXUSR)
        self.configure()
        self.export = self.make_export()

    # ---- fake cloud ----
    def configure(self, **kw):
        cfg = {"account": ACCOUNT, "arn": LOADER_ARN}
        cfg.update(kw)
        (self.fake_dir / "config.json").write_text(json.dumps(cfg))

    def stored(self):
        objs = self.fake_dir / "objects"
        return sorted(p.name.replace("__SLASH__", "/") for p in objs.iterdir() if not p.name.endswith(".meta"))

    def preload(self, key, body, with_checksum=True):
        objs = self.fake_dir / "objects"
        name = key.replace("/", "__SLASH__")
        (objs / name).write_bytes(body)
        (objs / (name + ".meta")).write_text(json.dumps({"sha": b64(hashlib.sha256(body).hexdigest()), "version": "v-pre"}))

    # ---- the export ----
    def make_export(self, root=None, run_id=RUN_ID, marker=True, manifests=True):
        root = Path(root or (self.fx.aux / "export"))
        files = {
            "nodes/type=researcher/part-00000.snappy.parquet": b"PAR1-researchers-" + b"r" * 300,
            "nodes/type=work/part-00000.snappy.parquet": b"PAR1-works-" + b"w" * 120,
            "edges/type=coauthored_with/part-00000.snappy.parquet": b"PAR1-edges-" + b"e" * 80,
            "metrics/type=researcher_collaboration/window=all-years/part-00000.snappy.parquet": b"PAR1-metrics-" + b"m" * 40,
            # Spark and Hadoop sidecars and a graph-loader directory: never uploaded
            "nodes/type=researcher/_SUCCESS": b"",
            "nodes/type=researcher/.part-00000.snappy.parquet.crc": b"crc",
            "neptune-opencypher-csv/nodes.csv": b"id\n1\n",
            "counters.json": b'{"rows": 3}\n',
        }
        run_manifest = json.dumps({"runId": run_id, "schema": "synthetic"}).encode()
        run_metadata = json.dumps({"runId": run_id, "note": "synthetic"}).encode()
        files["run-manifest.json"] = run_manifest
        files["run-metadata.json"] = run_metadata
        if marker:
            files["_SCHOLARCHAIN_SPARK_COMPLETE"] = (hashlib.sha256(run_manifest + b"\n" + run_metadata).hexdigest() + "\n").encode()
        if manifests:
            files["load-manifests/s3.json"] = b'{"manifests": []}\n'
        for rel, body in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        return root

    def expected_uploads(self, root=None):
        """{key: (bytes, sha256 hex)} of what the requirement says is uploaded: Parquet part files (not sidecars), the four root
        files and load-manifests/*.json, each under <run-prefix>/. Computed independently here."""
        root = Path(root or self.export)
        out = {}
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            name = p.name
            top = rel.split("/")[0]
            if top in ("nodes", "edges", "metrics", "path-evidence", "semantic-summaries"):
                if name.startswith((".", "_")) or name.endswith(".crc") or not name.endswith(".parquet"):
                    continue
            elif rel not in ("run-manifest.json", "run-metadata.json", "counters.json", "_SCHOLARCHAIN_SPARK_COMPLETE") and not (
                    top == "load-manifests" and name.endswith(".json")):
                continue
            body = p.read_bytes()
            out["%s/%s" % (PREFIX, rel)] = (len(body), hashlib.sha256(body).hexdigest())
        return out

    # ---- running ----
    def args(self, execute=False, **over):
        a = {"--export-dir": str(self.export), "--run-prefix": PREFIX, "--bucket": BUCKET, "--region": "us-east-2",
             "--manifest-out": str(self.fx.repo / "target/phase14/evidence/14c/upload-manifest.json")}
        a.update(over)
        out = []
        for k, v in a.items():
            if v is not None:
                out += [k, str(v)]
        if execute:
            out += ["--profile", "operator-loader-test", "--execute"]
        return out

    def run_upload(self, execute=False, **over):
        self.fx.log.write_text("")
        return self.fx.run("upload-slice.sh", self.args(execute, **over), {"FAKE_DIR": str(self.fake_dir)})

    def puts(self, run):
        return [c for c in run.tool_calls("aws") if c["argv"][:2] == ["s3api", "put-object"]]

    def assert_refused_before_upload(self, run, codes=(3,)):
        self.assertIn(run.rc, codes, run.describe())
        self.assertEqual(self.puts(run), [], "a put-object ran although the run was refused")
        self.assertEqual(self.stored(), [], "the store must stay empty")

    @property
    def manifest_path(self):
        return self.fx.repo / "target/phase14/evidence/14c/upload-manifest.json"


class DryRun(Case):
    def test_dry_run_makes_no_aws_call_and_writes_no_file(self):
        before = sorted(p.relative_to(self.fx.repo).as_posix() for p in self.fx.repo.rglob("*") if ".git/" not in p.as_posix() and p.is_file())
        run = self.run_upload()
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        self.assertEqual(run.calls, [], "the dry run must not call aws")
        self.assertEqual(self.stored(), [])
        self.assertFalse(self.manifest_path.exists())
        self.assertFalse((self.fx.repo / "target").exists(), "nothing may be written below target/ by a dry run")
        after = sorted(p.relative_to(self.fx.repo).as_posix() for p in self.fx.repo.rglob("*") if ".git/" not in p.as_posix() and p.is_file())
        self.assertEqual(before, after)

    def test_dry_run_plans_exactly_the_uploadable_files_with_their_own_sha256(self):
        run = self.run_upload()
        planned = {}
        for line in run.lines():
            m = re.match(r"UPLOAD-FILE: \d+ path=(\S+) key=(\S+) bytes=(\d+) sha256=([0-9a-f]{64})$", line)
            if m:
                planned[m.group(2)] = (int(m.group(3)), m.group(4))
                self.assertEqual(m.group(2), "%s/%s" % (PREFIX, m.group(1)))
        self.assertEqual(planned, self.expected_uploads())
        self.assertTrue(all(k.startswith(PREFIX + "/") for k in planned))
        self.assertFalse([k for k in planned if k.endswith(("_SUCCESS", ".crc", ".csv"))], "sidecars and the CSV directory are not uploaded")
        self.assertTrue(run.grep(r"EXPORT-SKIPPED"), "the skipped sidecars are counted")

    def test_dry_run_prints_the_put_object_command_with_the_required_flags(self):
        run = self.run_upload()
        cmds = run.grep(r"DRY-RUN CMD: .*put-object")
        self.assertEqual(len(cmds), 1, run.describe())
        for flag in ("--checksum-algorithm SHA256", "--checksum-sha256"):
            self.assertIn(flag, cmds[0])
        self.assertRegex(cmds[0], r"--if-none-match (\\\*|'\*'|\"\*\")")
        self.assertNotIn("--acl", run.out)

    def test_dry_run_still_refuses_a_bad_export(self):
        (self.export / "_SCHOLARCHAIN_SPARK_COMPLETE").unlink()
        run = self.run_upload()
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.calls, [])


class Refusals(Case):
    def test_bad_run_prefixes_are_rejected_before_any_call(self):
        for bad in ("run-", "Run-20261115", "run-UPPER", "prefix-1", "run-20261115/x", "run-" + "a" * 40, "run--x", ".."):
            with self.subTest(prefix=bad):
                run = self.run_upload(**{"--run-prefix": bad})
                self.assertIn(run.rc, (2, 3), run.describe())
                self.assertEqual(run.calls, [])

    def test_a_missing_run_prefix_is_rejected(self):
        run = self.run_upload(**{"--run-prefix": None})
        self.assertIn(run.rc, (2, 3), run.describe())
        self.assertEqual(run.calls, [])

    def test_a_non_completed_export_is_refused_in_every_way(self):
        def drop(rel):
            return lambda root: (root / rel).unlink()

        def tamper_marker(root):
            (root / "_SCHOLARCHAIN_SPARK_COMPLETE").write_text("0" * 64 + "\n")

        def other_run(root):
            (root / "run-metadata.json").write_text(json.dumps({"runId": "run:other"}))

        def no_parquet(root):
            for p in list(root.rglob("*.parquet")):
                p.unlink()

        def no_manifests(root):
            (root / "load-manifests/s3.json").unlink()

        cases = {
            "no marker": drop("_SCHOLARCHAIN_SPARK_COMPLETE"), "no run manifest": drop("run-manifest.json"),
            "no run metadata": drop("run-metadata.json"), "no counters": drop("counters.json"), "wrong marker": tamper_marker,
            "manifests name different runs": other_run, "no parquet": no_parquet, "no load manifest": no_manifests,
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                export = self.make_export(self.fx.aux / ("export-" + name.replace(" ", "-")))
                mutate(export)
                run = self.run_upload(execute=True, **{"--export-dir": export})
                self.assert_refused_before_upload(run)
                self.assertEqual(run.calls, [], "the export is checked before the first aws call")
                self.assertFalse(self.manifest_path.exists())

    def test_a_symbolic_link_anywhere_in_the_export_is_refused(self):
        os.symlink(self.export / "counters.json", self.export / "nodes/type=work/linked.snappy.parquet")
        run = self.run_upload()
        self.assertEqual(run.rc, 3, run.describe())
        os.unlink(self.export / "nodes/type=work/linked.snappy.parquet")
        os.symlink(self.export / "nodes", self.export / "edges/type=coauthored_with/dirlink")
        run = self.run_upload()
        self.assertEqual(run.rc, 3, run.describe())

    def test_keys_that_would_leave_the_prefix_or_use_odd_characters_are_refused(self):
        for rel in ("nodes/type=work/has space.snappy.parquet", "nodes/type=work/percent%20.snappy.parquet",
                    "nodes/type=work/dollar$.snappy.parquet", "nodes/type=work/semi;colon.snappy.parquet",
                    "nodes/type=work/stray.txt", "edges/type=coauthored_with/data.csv"):
            with self.subTest(rel=rel):
                export = self.make_export(self.fx.aux / "odd")
                (export / rel).write_bytes(b"x")
                run = self.run_upload(**{"--export-dir": export})
                self.assertEqual(run.rc, 3, run.describe())
                self.assertEqual(run.calls, [])
                import shutil
                shutil.rmtree(export)

    def test_an_existing_object_with_different_content_refuses_before_the_first_put(self):
        planned = self.expected_uploads()
        victim = sorted(planned)[0]
        self.preload(victim, b"somebody else's bytes")
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.puts(run), [])
        self.assertEqual(self.stored(), [victim])
        self.assertEqual((self.fake_dir / "objects" / victim.replace("/", "__SLASH__")).read_bytes(), b"somebody else's bytes", "nothing is overwritten")
        self.assertFalse(self.manifest_path.exists())

    def test_an_existing_object_without_a_sha256_checksum_is_refused(self):
        planned = self.expected_uploads()
        victim = sorted(planned)[1]
        body = (self.export / victim[len(PREFIX) + 1:]).read_bytes()
        self.preload(victim, body)  # identical bytes, but S3 holds no SHA-256 for it
        self.configure(no_checksum_keys=[victim])
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.puts(run), [])

    def test_an_existing_object_of_the_same_key_but_another_size_is_refused(self):
        victim = sorted(self.expected_uploads())[0]
        body = (self.export / victim[len(PREFIX) + 1:]).read_bytes()
        self.preload(victim, body + b"!")
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.puts(run), [])

    def test_a_caller_that_is_not_the_operator_loader_is_refused_before_listing_or_putting(self):
        for arn in ("arn:aws:sts::%s:assumed-role/scholarchain-deployer/s" % ACCOUNT,
                    "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-reader/s" % ACCOUNT,
                    "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-cleanup/s" % ACCOUNT,
                    "arn:aws:iam::%s:user/example-operator" % ACCOUNT,
                    "arn:aws:iam::%s:root" % ACCOUNT):
            with self.subTest(arn=arn.split(":")[-1]):
                self.configure(arn=arn)
                run = self.run_upload(execute=True)
                self.assertEqual(run.rc, 3, run.describe())
                self.assertEqual([c["argv"][:2] for c in run.tool_calls("aws") if c["argv"][0] == "s3api"], [])

    def test_a_bucket_of_another_account_is_refused_before_listing(self):
        self.configure(account=OTHER_ACCOUNT, arn="arn:aws:sts::%s:assumed-role/scholarchain-course-operator-loader/s" % OTHER_ACCOUNT)
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual([c for c in run.tool_calls("aws") if c["argv"][0] == "s3api"], [])
        self.assertNotIn(OTHER_ACCOUNT, run.out, "an account ID the run learned must be redacted from the output")

    def test_buckets_that_are_not_the_projects_curated_bucket_are_refused(self):
        for bucket in ("some-other-bucket", "scholarchain-course-%s-graph" % ACCOUNT, "scholarchain-course-%s-raw" % ACCOUNT,
                       "scholarchain-course-curated", "scholarchain-course-%s-curated-extra" % ACCOUNT, "scholarchain-course-12345-curated"):
            with self.subTest(bucket=bucket):
                run = self.run_upload(execute=True, **{"--bucket": bucket})
                self.assertIn(run.rc, (2, 3), run.describe())
                self.assertEqual([c for c in run.tool_calls("aws") if c["argv"][0] == "s3api"], [])

    def test_an_existing_manifest_is_never_overwritten(self):
        self.manifest_path.parent.mkdir(parents=True)
        self.manifest_path.write_text("precious evidence\n")
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.puts(run), [])
        self.assertEqual(self.manifest_path.read_text(), "precious evidence\n")

    def test_a_manifest_outside_target_is_refused(self):
        run = self.run_upload(execute=True, **{"--manifest-out": self.fx.repo / "docs/upload-manifest.json"})
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.puts(run), [])

    def test_execute_needs_a_profile_name(self):
        self.fx.log.write_text("")
        run = self.fx.run("upload-slice.sh", self.args(False) + ["--execute"], {"FAKE_DIR": str(self.fake_dir)})
        self.assertEqual(run.rc, 2, run.describe())
        self.assertEqual(run.calls, [])


class Execute(Case):
    def upload_ok(self, **over):
        run = self.run_upload(execute=True, **over)
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        return run

    def test_each_new_file_is_put_with_a_declared_sha256_and_if_none_match(self):
        run = self.upload_ok()
        expected = self.expected_uploads()
        puts = self.puts(run)
        self.assertEqual(len(puts), len(expected))
        seen = {}
        for c in puts:
            argv = c["argv"]
            key = argv[argv.index("--key") + 1]
            seen[key] = argv
            self.assertEqual(argv[argv.index("--bucket") + 1], BUCKET)
            self.assertTrue(key.startswith(PREFIX + "/"))
            self.assertEqual(argv[argv.index("--checksum-algorithm") + 1], "SHA256")
            self.assertEqual(argv[argv.index("--checksum-sha256") + 1], b64(expected[key][1]), "base64 of the LOCAL file's sha256")
            self.assertEqual(argv[argv.index("--if-none-match") + 1], "*")
            self.assertEqual(c["profile"], "operator-loader-test")
        self.assertEqual(sorted(seen), sorted(expected))
        self.assertEqual(self.stored(), sorted(expected))

    def test_the_recorded_put_object_argv_carries_the_never_overwrite_and_checksum_flags(self):
        """Direct assertions on what was SENT (the fake does not refuse a missing flag on its own)."""
        run = self.upload_ok()
        puts = self.puts(run)
        self.assertTrue(puts)
        for c in puts:
            argv = c["argv"]
            self.assertIn("--if-none-match", argv, "put-object must say --if-none-match")
            self.assertEqual(argv[argv.index("--if-none-match") + 1], "*")
            self.assertIn("--checksum-algorithm", argv)
            self.assertIn("--checksum-sha256", argv)

    def test_a_key_that_appears_just_before_the_put_is_never_overwritten(self):
        victim = sorted(self.expected_uploads())[3]
        self.configure(race_key=victim)
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 5, run.describe())
        self.assertEqual((self.fake_dir / "objects" / victim.replace("/", "__SLASH__")).read_bytes(), b"concurrent writer")
        self.assertFalse(self.manifest_path.exists())

    def test_every_key_is_verified_with_head_object_after_the_uploads(self):
        run = self.upload_ok()
        calls = [c["argv"] for c in run.tool_calls("aws")]
        ops = [a[1] for a in calls if a[0] == "s3api"]
        first_head = ops.index("head-object")
        self.assertNotIn("put-object", ops[first_head:], "all uploads happen before the verification pass")
        heads = [a for a in calls if a[:2] == ["s3api", "head-object"]]
        self.assertEqual(sorted(a[a.index("--key") + 1] for a in heads), sorted(self.expected_uploads()))
        for a in heads:
            self.assertIn("ENABLED", a)  # --checksum-mode ENABLED
        # the identity checks come first, the bucket listing before the first put
        self.assertEqual(calls[0][:2], ["sts", "get-caller-identity"])
        self.assertLess(ops.index("list-objects-v2"), ops.index("put-object"))

    def test_the_manifest_records_every_file_and_hides_the_account(self):
        run = self.upload_ok()
        text = self.manifest_path.read_text()
        manifest = json.loads(text)
        self.assertEqual(manifest["schema"], "scholarchain.upload-manifest.v1")
        self.assertIn("<acct>", manifest["bucket"])
        self.assertNotIn(ACCOUNT, text, "the manifest must show <acct>, never the raw account ID")
        self.assertNotIn(ACCOUNT, run.out, "stdout is redacted as well")
        self.assertEqual(manifest["run_prefix"], PREFIX)
        expected = self.expected_uploads()
        self.assertEqual({f["key"]: (f["bytes"], f["sha256"]) for f in manifest["files"]}, expected)
        self.assertEqual({f["status"] for f in manifest["files"]}, {"uploaded"})
        for f in manifest["files"]:
            self.assertEqual(f["checksum_sha256_b64"], b64(f["sha256"]))
            self.assertTrue(f["version_id"])
        self.assertEqual(manifest["totals"], {"files": len(expected), "bytes": sum(b for b, _ in expected.values()),
                                              "uploaded": len(expected), "unchanged": 0})
        self.assertTrue(run.grep(r"^UPLOAD-MANIFEST-SHA256: [0-9a-f]{64}$"))
        self.assertEqual(S.sha256_file(self.manifest_path), re.search(r"UPLOAD-MANIFEST-SHA256: ([0-9a-f]{64})", run.out).group(1))

    def test_rerun_is_idempotent_unchanged_and_makes_no_put(self):
        self.upload_ok()
        before = {k: (self.fake_dir / "objects" / k.replace("/", "__SLASH__")).read_bytes() for k in self.stored()}
        second = self.upload_ok(**{"--manifest-out": self.fx.repo / "target/second-manifest.json"})
        self.assertEqual(self.puts(second), [])
        self.assertEqual(len(second.grep(r"^UNCHANGED: ")), len(self.expected_uploads()))
        self.assertEqual({k: (self.fake_dir / "objects" / k.replace("/", "__SLASH__")).read_bytes() for k in self.stored()}, before)
        manifest = json.loads((self.fx.repo / "target/second-manifest.json").read_text())
        self.assertEqual({f["status"] for f in manifest["files"]}, {"unchanged"})
        self.assertEqual(manifest["totals"]["uploaded"], 0)
        self.assertEqual(manifest["totals"]["unchanged"], len(self.expected_uploads()))
        # the unchanged objects are still verified with head-object
        self.assertEqual(len([c for c in second.tool_calls("aws") if c["argv"][:2] == ["s3api", "head-object"]]), len(self.expected_uploads()))

    def test_a_partial_earlier_upload_is_completed_without_touching_what_exists(self):
        expected = self.expected_uploads()
        keys = sorted(expected)
        already = keys[:2]
        for key in already:
            self.preload(key, (self.export / key[len(PREFIX) + 1:]).read_bytes())
        run = self.upload_ok()
        self.assertEqual(sorted(c["argv"][c["argv"].index("--key") + 1] for c in self.puts(run)), keys[2:])
        manifest = json.loads(self.manifest_path.read_text())
        by_key = {f["key"]: f["status"] for f in manifest["files"]}
        self.assertEqual({k for k, s in by_key.items() if s == "unchanged"}, set(already))
        self.assertEqual({k for k, s in by_key.items() if s == "uploaded"}, set(keys[2:]))

    def test_a_put_failure_is_exit_5_and_writes_no_manifest_and_a_rerun_finishes(self):
        keys = sorted(self.expected_uploads())
        victim = keys[2]
        self.configure(put_fail_key=victim)
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 5, run.describe())
        self.assertFalse(self.manifest_path.exists())
        stored = self.stored()
        self.assertNotIn(victim, stored)
        self.assertLess(len(stored), len(keys), "the run stops at the first failed put")
        self.configure()
        again = self.upload_ok()
        self.assertEqual(sorted(c["argv"][c["argv"].index("--key") + 1] for c in self.puts(again)), sorted(set(keys) - set(stored)),
                         "only the missing files are put")
        self.assertTrue(self.manifest_path.exists())

    def test_a_stored_object_that_differs_fails_verification_exit_4_without_a_manifest(self):
        keys = sorted(self.expected_uploads())
        self.configure(corrupt_keys=[keys[0]])
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 4, run.describe())
        self.assertFalse(self.manifest_path.exists())

    def test_a_stored_checksum_that_differs_with_the_same_size_fails_verification(self):
        """Same bytes and size, but S3 reports another SHA-256 for the key: only the checksum comparison can notice."""
        keys = sorted(self.expected_uploads())
        self.configure(badsum_keys=[keys[1]])
        run = self.run_upload(execute=True)
        self.assertEqual(run.rc, 4, run.describe())
        self.assertFalse(self.manifest_path.exists())
        self.assertFalse(run.grep(r"^UPLOAD-MANIFEST: "))

    def test_no_credential_or_profile_secret_reaches_the_output(self):
        run = self.upload_ok()
        for canary in S.CANARIES:
            self.assertNotIn(canary, run.text)


if __name__ == "__main__":
    unittest.main()
