"""scripts/upload-emr-artifacts.sh (Phase 14B/15A), written independently by the test-engineer from the requirement:

  * the pipeline operator uploads the EMR bootstrap, the four job JARs, the four step programs, optional config and 1 to 3 input
    datasets to the ARTIFACTS bucket, under emr/<run-prefix>/{bin,jars,steps,config,input/<label>} and nowhere else;
  * a dry run makes no aws call and writes nothing; it prints the plan hash the human approves;
  * --execute is refused BEFORE any aws call without an existing approval record, and with one whose plan, account or region does not
    match; it needs --profile and --principal-role, and the caller must be exactly the assumed role scholarchain-<env>-<principal-role>;
  * every JAR must equal its entry (size and sha256) in target/emr-artifacts/emr-artifact-manifest.json and every step program the
    Terraform pin infra/terraform/emr-step-programs.json;
  * put-object carries --checksum-algorithm SHA256, the base64 SHA-256 and --if-none-match '*'; every key is verified with head-object;
    the manifest shows the bucket as <acct> and never the raw account ID; a re-run is idempotent.

The cloud is the fake aws of fake_s3.py (directory-backed S3 plus sts). The account ID is synthetic. Expected keys, hashes and the plan
hash are computed here, not read from the script's output.
"""
import hashlib
import json
import os
import re
import stat
import unittest
from pathlib import Path

import sc_support as S
from fake_s3 import FAKE_AWS, b64

ACCOUNT = "111122223333"
OTHER_ACCOUNT = "4444" + "5555" + "6666"
BUCKET = "scholarchain-course-%s-artifacts" % ACCOUNT
RUN = "run-20261115"
REGION = "us-east-2"
ROLE = "operator-pipeline"
PIPELINE_ARN = "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-pipeline/session-one" % ACCOUNT
JARS = {"hadoop-submit-jar": "hadoop-submit.jar", "hadoop-dependency-bundle": "hadoop-bundle.jar",
        "entity-resolution-job-jar": "entity-resolution.jar", "spark-job-jar": "spark-job.jar"}
STEPS = ("sc-ceiling-check.py", "sc-class-origin-verify.py", "sc-render-spark-config.py", "sc-step.sh")
SAMPLES = ("dblp/linked-records.xml", "openalex/works.jsonl", "crossref/works.jsonl", "orcid/records.jsonl")


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.fx = S.Fixture(self)
        fx = self.fx
        self.fake_dir = fx.aux / "fakes3"
        (self.fake_dir / "objects").mkdir(parents=True)
        aws = fx.bin / "aws"
        aws.write_text(FAKE_AWS)
        aws.chmod(aws.stat().st_mode | stat.S_IXUSR)
        self.configure()
        self.build_artifacts()
        self.datasets = {"size-25": self.make_dataset("size-25")}

    # ---- fake cloud ----
    def configure(self, **kw):
        cfg = {"account": ACCOUNT, "arn": PIPELINE_ARN}
        cfg.update(kw)
        (self.fake_dir / "config.json").write_text(json.dumps(cfg))

    def stored(self):
        return sorted(p.name.replace("__SLASH__", "/") for p in (self.fake_dir / "objects").iterdir() if not p.name.endswith(".meta"))

    def preload(self, key, body):
        objs = self.fake_dir / "objects"
        name = key.replace("/", "__SLASH__")
        (objs / name).write_bytes(body)
        (objs / (name + ".meta")).write_text(json.dumps({"sha": b64(sha(body)), "version": "v-pre"}))

    # ---- local artifacts ----
    def build_artifacts(self):
        repo = self.fx.repo
        out = repo / "target/emr-artifacts"
        out.mkdir(parents=True)
        entries = []
        for role, name in sorted(JARS.items()):
            data = (b"PK-fake-jar-" + role.encode()) * 20
            (out / name).write_bytes(data)
            entries.append({"role": role, "path": "target/emr-artifacts/" + name, "sha256": sha(data), "bytes": len(data)})
        self.manifest_entries = entries
        self.write_artifact_manifest()

    def write_artifact_manifest(self, entries=None):
        (self.fx.repo / "target/emr-artifacts/emr-artifact-manifest.json").write_text(
            json.dumps({"schema": "scholarchain.emr-artifact-manifest.v1", "artifacts": entries if entries is not None else self.manifest_entries}))

    def make_dataset(self, label, scale=1):
        root = self.fx.aux / ("ds-" + label)
        for rel in SAMPLES:
            path = root / "datasets/samples" / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((label + rel).encode() * (10 * scale))
        return root

    # ---- expectations, computed here ----
    def expected(self, datasets=None, extra=None):
        """{key: (bytes, sha256)} of what must be uploaded, from first principles."""
        repo = self.fx.repo
        prefix = "emr/%s/" % RUN
        out = {}

        def add(key, path):
            data = Path(path).read_bytes()
            out[prefix + key] = (len(data), sha(data))

        add("bin/bootstrap.sh", repo / "scripts/emr/bootstrap.sh")
        for name in JARS.values():
            add("jars/" + name, repo / "target/emr-artifacts" / name)
        for name in STEPS:
            add("steps/" + name, repo / "scripts/emr" / name)
        for label, root in (datasets or self.datasets).items():
            for p in sorted(Path(root).rglob("*")):
                if p.is_file():
                    add("input/%s/%s" % (label, p.relative_to(root).as_posix()), p)
        for key, path in (extra or {}).items():
            add(key, path)
        return out

    @staticmethod
    def plan_sha(expected):
        text = "".join("%s\t%d\t%s\n" % (k, b, h) for k, (b, h) in sorted(expected.items()))
        return sha(text.encode())

    # ---- running ----
    def args(self, execute=False, approval=None, datasets=None, **over):
        a = [("--artifacts-bucket", BUCKET), ("--run-prefix", RUN), ("--region", REGION)]
        for label, root in (datasets or self.datasets).items():
            a.append(("--input-dataset", "%s=%s" % (label, root)))
        a += [(k, v) for k, v in over.items() if v is not None]
        out = []
        for k, v in a:
            out += [k, str(v)]
        if execute:
            out += ["--profile", "scholarchain-pipeline", "--principal-role", ROLE]
            if approval is not None:
                out += ["--approval", str(approval)]
            out += ["--execute"]
        return out

    def run_script(self, args, env=None):
        self.fx.log.write_text("")
        return self.fx.run("upload-emr-artifacts.sh", args, dict({"FAKE_DIR": str(self.fake_dir)}, **(env or {})))

    def approval(self, name="approval.md", plan=None, account=ACCOUNT, region=REGION, drop=(), extra=(), raw=None):
        plan = plan or self.plan_sha(self.expected())
        values = [("APPROVED_ACTION", "upload-emr-artifacts"), ("APPROVED_PLAN_SHA256", plan),
                  ("APPROVED_ACCOUNT_SHA256", sha(account.encode())), ("APPROVED_REGION", region)]
        lines = ["%s=%s" % kv for kv in values if kv[0] not in drop] + list(extra)
        path = self.fx.aux / name
        path.write_text(raw if raw is not None else "Reviewed by the human.\n" + "\n".join(lines) + "\n")
        return path

    def puts(self, run):
        return [c for c in run.tool_calls("aws") if c["argv"][:2] == ["s3api", "put-object"]]

    def s3_calls(self, run):
        return [c for c in run.tool_calls("aws") if c["argv"][0] == "s3api"]

    @property
    def manifest_path(self):
        return self.fx.repo / "target/phase14/evidence/15a/emr-upload-manifest.json"


class DryRun(Base):
    def test_dry_run_makes_no_aws_call_and_writes_nothing(self):
        before = sorted(p.relative_to(self.fx.repo).as_posix() for p in self.fx.repo.rglob("*") if p.is_file() and ".git/" not in p.as_posix() and "__pycache__" not in p.as_posix())
        run = self.run_script(self.args())
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        self.assertEqual(run.calls, [])
        after = sorted(p.relative_to(self.fx.repo).as_posix() for p in self.fx.repo.rglob("*") if p.is_file() and ".git/" not in p.as_posix() and "__pycache__" not in p.as_posix())
        self.assertEqual(before, after, "a dry run writes no file")
        self.assertFalse(self.manifest_path.exists())
        self.assertEqual(self.stored(), [])

    def test_the_planned_keys_are_exactly_the_documented_layout_with_the_right_sizes_and_hashes(self):
        run = self.run_script(self.args())
        planned = {}
        for line in run.lines():
            m = re.match(r"UPLOAD-FILE: \d+ class=\S+ key=(\S+) bytes=(\d+) sha256=([0-9a-f]{64})$", line)
            if m:
                planned[m.group(1)] = (int(m.group(2)), m.group(3))
        self.assertEqual(planned, self.expected())
        for key in planned:
            self.assertRegex(key, r"^emr/%s/(bin|jars|steps|config|input/size-25)/" % RUN)
        self.assertEqual(sorted(k.split("/")[2] for k in planned if k.split("/")[2] in ("bin", "jars", "steps")).count("jars"), 4)

    def test_the_plan_hash_is_the_hash_over_the_sorted_key_size_and_sha256_lines(self):
        run = self.run_script(self.args())
        self.assertEqual(run.grep(r"^PLAN-SHA256: "), ["PLAN-SHA256: " + self.plan_sha(self.expected())])

    def test_the_dry_run_prints_the_four_approval_lines_for_the_human(self):
        run = self.run_script(self.args())
        lines = [l for l in run.lines() if l.startswith("APPROVAL-LINE: ")]
        self.assertEqual(lines, ["APPROVAL-LINE: APPROVED_ACTION=upload-emr-artifacts",
                                 "APPROVAL-LINE: APPROVED_PLAN_SHA256=" + self.plan_sha(self.expected()),
                                 "APPROVAL-LINE: APPROVED_ACCOUNT_SHA256=" + sha(ACCOUNT.encode()),
                                 "APPROVAL-LINE: APPROVED_REGION=" + REGION])

    def test_next_values_name_the_job_jar_uri_and_hash_with_the_account_redacted(self):
        run = self.run_script(self.args())
        spark = next(m for m in self.manifest_entries if m["role"] == "spark-job-jar")
        want = "EMR-CONFIG: job_jar_uri=s3://scholarchain-course-<acct>-artifacts/emr/%s/jars/spark-job.jar job_jar_sha256=%s" % (RUN, spark["sha256"])
        self.assertIn(want, run.lines())
        self.assertNotIn(ACCOUNT, run.out)

    def test_up_to_three_datasets_are_planned_under_their_own_labels(self):
        datasets = {l: self.make_dataset(l, scale=i + 1) for i, l in enumerate(("size-25", "size-50", "size-100"))}
        run = self.run_script(self.args(datasets=datasets))
        self.assertEqual(run.rc, 0, run.describe())
        planned = {m.group(1) for m in (re.match(r"UPLOAD-FILE: \d+ class=\S+ key=(\S+) ", l) for l in run.lines()) if m}
        self.assertEqual(planned, set(self.expected(datasets)))
        four = dict(datasets, **{"size-200": self.make_dataset("size-200")})
        refused = self.run_script(self.args(datasets=four))
        self.assertEqual(refused.rc, 3, refused.describe())

    def test_optional_config_files_land_under_config(self):
        er_policy = self.fx.aux / "er-policy.json"
        er_policy.write_text('{"policy": 1}')
        run = self.run_script(self.args(**{"--er-policy": er_policy}))
        self.assertEqual(run.rc, 0, run.describe())
        self.assertIn("emr/%s/config/er-policy.json" % RUN, run.out)
        expected = self.expected(extra={"config/er-policy.json": er_policy})
        self.assertIn("emr/%s/config/er-policy.json" % RUN, expected)
        self.assertEqual(run.grep(r"^PLAN-SHA256: "), ["PLAN-SHA256: " + self.plan_sha(expected)])

    def test_usage_errors_exit_2_and_touch_nothing(self):
        cases = {
            "no run prefix": [a for a in self.args() if a not in ("--run-prefix", RUN)],
            "bad run prefix": self.args() + ["--run-prefix", "Run-1"],
            "no dataset": ["--artifacts-bucket", BUCKET, "--run-prefix", RUN, "--region", REGION],
            "wrong bucket": [("scholarchain-course-%s-curated" % ACCOUNT) if a == BUCKET else a for a in self.args()],
            "no region": [a for a in self.args() if a not in ("--region", REGION)],
            "unknown option": self.args() + ["--frobnicate"],
        }
        for label, argv in cases.items():
            with self.subTest(case=label):
                run = self.run_script(argv)
                self.assertIn(run.rc, (2, 3), run.describe())
                self.assertEqual(run.calls, [])
                self.assertFalse(self.manifest_path.exists())


class SourceChecks(Base):
    """Local refusals: they hold in a dry run too, so nothing uploadable is ever approved against bad inputs."""

    def refused(self, run):
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.calls, [])

    def test_a_jar_that_differs_from_the_artifact_manifest_in_content_or_size(self):
        jar = self.fx.repo / "target/emr-artifacts/spark-job.jar"
        original = jar.read_bytes()
        jar.write_bytes(original[:-1] + b"X")  # same size, other sha256
        self.refused(self.run_script(self.args()))
        jar.write_bytes(original + b"!")  # other size
        self.refused(self.run_script(self.args()))
        jar.write_bytes(original)
        self.assertEqual(self.run_script(self.args()).rc, 0)

    def test_a_missing_jar_or_a_manifest_with_the_wrong_roles(self):
        (self.fx.repo / "target/emr-artifacts/hadoop-bundle.jar").unlink()
        self.refused(self.run_script(self.args()))
        (self.fx.repo / "target/emr-artifacts/hadoop-bundle.jar").write_bytes(b"x")
        self.write_artifact_manifest(self.manifest_entries[:3])
        self.refused(self.run_script(self.args()))
        self.write_artifact_manifest(self.manifest_entries + [dict(self.manifest_entries[0], role="extra-jar")])
        self.refused(self.run_script(self.args()))

    def test_a_manifest_without_the_schema_or_with_an_unsafe_path_is_refused(self):
        (self.fx.repo / "target/emr-artifacts/emr-artifact-manifest.json").write_text(json.dumps({"artifacts": self.manifest_entries}))
        self.refused(self.run_script(self.args()))
        bad = [dict(e) for e in self.manifest_entries]
        bad[0]["path"] = "../outside.jar"
        self.write_artifact_manifest(bad)
        self.refused(self.run_script(self.args()))

    def test_a_step_program_that_differs_from_the_terraform_pin_is_refused(self):
        step = self.fx.repo / "scripts/emr/sc-step.sh"
        step.write_text(step.read_text() + "\n# drift\n")
        run = self.run_script(self.args())
        self.refused(run)
        self.assertIn("STEP-PROGRAM-DRIFT", run.out)

    def test_every_step_program_matches_the_pin_in_the_repository(self):
        pin = json.loads((S.REPO / "infra/terraform/emr-step-programs.json").read_text())["programs"]
        self.assertEqual(sorted(pin), sorted(STEPS))
        for name, digest in pin.items():
            self.assertEqual(sha((S.REPO / "scripts/emr" / name).read_bytes()), digest, name)

    def test_datasets_must_hold_the_four_sample_files_and_no_links(self):
        root = self.datasets["size-25"]
        (root / "datasets/samples/orcid/records.jsonl").unlink()
        self.refused(self.run_script(self.args()))
        (root / "datasets/samples/orcid/records.jsonl").write_bytes(b"x")
        os.symlink(root / "datasets/samples/dblp/linked-records.xml", root / "datasets/samples/dblp/link.xml")
        self.refused(self.run_script(self.args()))

    def test_a_dataset_label_outside_the_pattern_is_refused(self):
        for label in ("Size-25", "x", "size 25", "a" * 30, "-size"):
            with self.subTest(label=label):
                run = self.run_script(self.args(datasets={label: self.datasets["size-25"]}))
                self.assertIn(run.rc, (2, 3), run.describe())
                self.assertEqual(run.calls, [])

    def test_an_input_dataset_above_the_pipeline_input_ceiling_is_refused(self):
        limit = int(dict(re.findall(r"^(PIPELINE_MAX_INPUT_BYTES)=(\d+)", (S.REPO / "scripts/config/release.conf").read_text(), re.M))["PIPELINE_MAX_INPUT_BYTES"])
        big = self.datasets["size-25"] / "datasets/samples/crossref/works.jsonl"
        with open(big, "wb") as handle:
            handle.truncate(limit + 1)
        self.refused(self.run_script(self.args()))

    def test_an_existing_manifest_out_is_never_overwritten_and_it_must_lie_below_target(self):
        existing = self.fx.repo / "target/precious.json"
        existing.write_text("evidence\n")
        run = self.run_script(self.args(**{"--manifest-out": existing}))
        self.refused(run)
        outside = self.fx.repo / "docs/manifest.json"
        self.refused(self.run_script(self.args(**{"--manifest-out": outside})))
        self.assertEqual(existing.read_text(), "evidence\n")


class ExecuteGate(Base):
    """--execute is refused before any aws call unless the human's approval record exists and matches the plan."""

    def test_execute_without_an_approval_option_is_a_usage_error(self):
        run = self.run_script(self.args(execute=True))
        self.assertEqual(run.rc, 2, run.describe())
        self.assertEqual(run.calls, [])

    def test_execute_without_profile_or_principal_role_is_a_usage_error(self):
        approval = self.approval()
        base = self.args(execute=False) + ["--approval", str(approval), "--execute"]
        run = self.run_script(base + ["--principal-role", ROLE])
        self.assertEqual(run.rc, 2, run.describe())
        run = self.run_script(base + ["--profile", "scholarchain-pipeline"])
        self.assertEqual(run.rc, 2, run.describe())
        self.assertEqual(run.calls, [])

    def test_a_missing_approval_file_refuses_before_any_aws_call_and_before_the_scan(self):
        run = self.run_script(self.args(execute=True, approval=self.fx.aux / "absent.md"))
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.calls, [])
        self.assertNotIn("UPLOAD-FILE", run.out, "not even a local scan runs before the record exists")

    def test_an_approval_that_is_a_symbolic_link_is_refused(self):
        real = self.approval("real.md")
        link = self.fx.aux / "link.md"
        os.symlink(real, link)
        run = self.run_script(self.args(execute=True, approval=link))
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.calls, [])

    def test_a_mismatching_record_refuses_with_no_aws_call(self):
        good_plan = self.plan_sha(self.expected())
        cases = {
            "plan hash of another plan": dict(plan="0" * 64),
            "plan hash one digit off": dict(plan=good_plan[:-1] + ("0" if good_plan[-1] != "0" else "1")),
            "another account": dict(account=OTHER_ACCOUNT),
            "another region": dict(region="us-west-2"),
            "missing plan line": dict(drop=("APPROVED_PLAN_SHA256",)),
            "missing account line": dict(drop=("APPROVED_ACCOUNT_SHA256",)),
            "missing action line": dict(drop=("APPROVED_ACTION",)),
            "unknown APPROVED key": dict(extra=("APPROVED_EXTRA=1",)),
            "duplicate region": dict(extra=("APPROVED_REGION=" + REGION,)),
            "quoted value": dict(raw='APPROVED_ACTION="upload-emr-artifacts"\nAPPROVED_PLAN_SHA256=%s\nAPPROVED_ACCOUNT_SHA256=%s\nAPPROVED_REGION=%s\n'
                                     % (good_plan, sha(ACCOUNT.encode()), REGION)),
            "empty record": dict(raw=""),
        }
        for label, kw in cases.items():
            with self.subTest(case=label):
                run = self.run_script(self.args(execute=True, approval=self.approval(**kw)))
                self.assertEqual(run.rc, 3, run.describe())
                self.assertEqual(run.calls, [], "no aws call may precede a refused approval")
                self.assertEqual(self.stored(), [])

    def test_an_approval_for_changed_files_is_stale(self):
        approval = self.approval()
        jar_path = self.fx.repo / "target/emr-artifacts/spark-job.jar"
        new = jar_path.read_bytes() + b"more"
        jar_path.write_bytes(new)
        for e in self.manifest_entries:
            if e["role"] == "spark-job-jar":
                e["sha256"], e["bytes"] = sha(new), len(new)
        self.write_artifact_manifest()
        run = self.run_script(self.args(execute=True, approval=approval))
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(run.calls, [])


class ExecuteIdentity(Base):
    def test_only_the_exact_pipeline_role_may_upload(self):
        approval = self.approval()
        for arn in ("arn:aws:sts::%s:assumed-role/scholarchain-course-operator-loader/s" % ACCOUNT,
                    "arn:aws:sts::%s:assumed-role/scholarchain-deployer/s" % ACCOUNT,
                    "arn:aws:sts::%s:assumed-role/scholarchain-course-operator-pipeline-extra/s" % ACCOUNT,
                    "arn:aws:sts::%s:assumed-role/xscholarchain-course-operator-pipeline/s" % ACCOUNT,
                    "arn:aws:iam::%s:user/example-operator" % ACCOUNT,
                    "arn:aws:sts::%s:federated-user/x" % ACCOUNT):
            with self.subTest(arn=arn.split(":", 5)[5]):
                self.configure(arn=arn)
                run = self.run_script(self.args(execute=True, approval=approval))
                self.assertEqual(run.rc, 3, run.describe())
                self.assertEqual(self.s3_calls(run), [], "no list, put or head before the identity is accepted")

    def test_the_principal_role_is_an_argument_the_caller_must_match_exactly(self):
        approval = self.approval()
        self.configure(arn="arn:aws:sts::%s:assumed-role/scholarchain-course-operator-reader/s" % ACCOUNT)
        argv = self.args(execute=True, approval=approval)
        argv[argv.index("--principal-role") + 1] = "operator-reader"
        run = self.run_script(argv)
        self.assertEqual(run.rc, 0, run.describe())  # the same script serves any principal the deployer grants

    def test_a_bucket_of_another_account_is_refused_before_listing(self):
        self.configure(account=OTHER_ACCOUNT, arn="arn:aws:sts::%s:assumed-role/scholarchain-course-operator-pipeline/s" % OTHER_ACCOUNT)
        run = self.run_script(self.args(execute=True, approval=self.approval()))
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.s3_calls(run), [])
        self.assertNotIn(OTHER_ACCOUNT, run.out)


class ExecuteUpload(Base):
    def upload(self, **kw):
        run = self.run_script(self.args(execute=True, approval=kw.pop("approval", None) or self.approval(), **kw))
        return run

    def ok(self, **kw):
        run = self.upload(**kw)
        self.assertEqual((run.rc, run.status), (0, "PASS"), run.describe())
        return run

    def test_every_put_carries_the_checksum_and_never_overwrite_flags_and_stays_below_the_prefix(self):
        run = self.ok()
        expected = self.expected()
        puts = self.puts(run)
        self.assertEqual(len(puts), len(expected))
        seen = set()
        for c in puts:
            argv = c["argv"]
            key = argv[argv.index("--key") + 1]
            seen.add(key)
            self.assertTrue(key.startswith("emr/%s/" % RUN), key)
            self.assertEqual(argv[argv.index("--bucket") + 1], BUCKET)
            self.assertIn("--if-none-match", argv)
            self.assertEqual(argv[argv.index("--if-none-match") + 1], "*")
            self.assertEqual(argv[argv.index("--checksum-algorithm") + 1], "SHA256")
            self.assertEqual(argv[argv.index("--checksum-sha256") + 1], b64(expected[key][1]))
            self.assertEqual(c["profile"], "scholarchain-pipeline")
        self.assertEqual(seen, set(expected))
        self.assertEqual(self.stored(), sorted(expected))

    def test_every_key_is_verified_with_head_object_after_the_uploads(self):
        run = self.ok()
        ops = [c["argv"][1] for c in self.s3_calls(run)]
        self.assertNotIn("put-object", ops[ops.index("head-object"):])
        heads = [c["argv"] for c in run.tool_calls("aws") if c["argv"][:2] == ["s3api", "head-object"]]
        self.assertEqual(sorted(a[a.index("--key") + 1] for a in heads), sorted(self.expected()))
        self.assertTrue(all("ENABLED" in a for a in heads))

    def test_the_manifest_has_the_acct_placeholder_and_never_the_raw_account(self):
        run = self.ok()
        text = self.manifest_path.read_text()
        manifest = json.loads(text)
        self.assertEqual(manifest["schema"], "scholarchain.emr-upload-manifest.v1")
        self.assertIn("<acct>", manifest["bucket"])
        self.assertNotIn(ACCOUNT, text)
        self.assertNotIn(ACCOUNT, run.out)
        self.assertEqual({f["key"]: (f["bytes"], f["sha256"]) for f in manifest["files"]}, self.expected())
        self.assertEqual({f["status"] for f in manifest["files"]}, {"uploaded"})
        self.assertEqual(manifest["run_prefix"], RUN)

    def test_the_jar_entries_in_the_manifest_equal_the_artifact_manifest(self):
        self.ok()
        manifest = {f["key"]: f for f in json.loads(self.manifest_path.read_text())["files"]}
        for entry in self.manifest_entries:
            record = manifest["emr/%s/jars/%s" % (RUN, JARS[entry["role"]])]
            self.assertEqual((record["bytes"], record["sha256"]), (entry["bytes"], entry["sha256"]))

    def test_rerun_is_idempotent(self):
        self.ok()
        second = self.ok(**{"--manifest-out": self.fx.repo / "target/second.json"})
        self.assertEqual(self.puts(second), [])
        self.assertEqual(len(second.grep(r"^UNCHANGED: ")), len(self.expected()))
        statuses = {f["status"] for f in json.loads((self.fx.repo / "target/second.json").read_text())["files"]}
        self.assertEqual(statuses, {"unchanged"})

    def test_an_existing_object_with_other_content_refuses_before_any_put(self):
        victim = sorted(self.expected())[2]
        self.preload(victim, b"somebody else")
        run = self.upload()
        self.assertEqual(run.rc, 3, run.describe())
        self.assertEqual(self.puts(run), [])
        self.assertEqual(self.stored(), [victim])
        self.assertFalse(self.manifest_path.exists())

    def test_a_key_that_appears_just_before_its_put_is_never_overwritten(self):
        victim = sorted(self.expected())[4]
        self.configure(race_key=victim)
        run = self.upload()
        self.assertEqual(run.rc, 5, run.describe())
        self.assertEqual((self.fake_dir / "objects" / victim.replace("/", "__SLASH__")).read_bytes(), b"concurrent writer")

    def test_a_stored_checksum_that_differs_fails_verification(self):
        self.configure(badsum_keys=[sorted(self.expected())[0]])
        run = self.upload()
        self.assertEqual(run.rc, 4, run.describe())
        self.assertFalse(self.manifest_path.exists())

    def test_nothing_secret_reaches_the_output(self):
        run = self.ok()
        for canary in S.CANARIES:
            self.assertNotIn(canary, run.text)


if __name__ == "__main__":
    unittest.main()
