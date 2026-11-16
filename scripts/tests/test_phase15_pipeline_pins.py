"""Phase 15 pipeline pins (lane A): P22 Hadoop record ceiling, P23 copy-out ceiling, P25 EMR ledger caps, P5 cleanup teardown rules.

Every expectation is hand-derived in this file from the decision it encodes; the pinned values are read from scripts/config/release.conf
and fed to the real programs (scripts/emr/sc-ceiling-check.py, scripts/lib/budget.py, scripts/lib/verify.py) in temp directories.
No network, no AWS call, no credentials.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

from helpers import REAL_REPO, SCRIPTS_DIR

CONF_PATH = os.path.join(SCRIPTS_DIR, "config", "release.conf")
CEILING_PY = os.path.join(SCRIPTS_DIR, "emr", "sc-ceiling-check.py")
FIELDS = ("maxLocalSampleRecords", "reducerCount", "maxCandidateBlockSize", "maxCandidatePairsPerBlock", "maxAuthorTeamSize", "maxRecordBytes",
          "maxXmlEntityExpansion")
CEILING_KEYS = ("MAX_LOCAL_SAMPLE_RECORDS", "REDUCER_COUNT", "MAX_CANDIDATE_BLOCK_SIZE", "MAX_CANDIDATE_PAIRS_PER_BLOCK", "MAX_AUTHOR_TEAM_SIZE",
                "MAX_RECORD_BYTES", "MAX_XML_ENTITY_EXPANSION")


def conf():
    values = {}
    with open(CONF_PATH, encoding="utf-8") as handle:
        for line in handle:
            if "=" in line and not line.startswith("#"):
                key, _, value = line.rstrip("\n").partition("=")
                values[key] = value
    return values


def ceilings():
    values = conf()
    return [values["PIPELINE_CEILING_" + k] for k in CEILING_KEYS]


# ---- P22: Hadoop record ceiling ------------------------------------------------------------------------------------------------
# L holds at most 50000 DBLP works (datasets/scripts/phase15/select_dblp_l_slice.py TARGET_MAX); the other three sources are the
# committed one-line samples, so the one SampleBound budget must admit 50000 + 3 = 50003 records.
L_MAX_DBLP_WORKS = 50000
OTHER_SOURCE_SAMPLES = ("datasets/samples/openalex/works.jsonl", "datasets/samples/crossref/works.jsonl", "datasets/samples/orcid/records.jsonl")
P22_PIN = 60000


class HadoopRecordCeilingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-p22-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)

    def check(self, **changes):
        document = {"maxLocalSampleRecords": 100, "reducerCount": 8, "maxCandidateBlockSize": 256, "maxCandidatePairsPerBlock": 4096,
                    "maxAuthorTeamSize": 64, "maxRecordBytes": 8388608, "maxXmlEntityExpansion": 8388608}
        document.update(changes)
        path = os.path.join(self.tmp, "prep-config.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        return subprocess.run([sys.executable, "-I", CEILING_PY, path] + ceilings(), capture_output=True, text=True)

    def test_the_pin_is_60000(self):
        self.assertEqual(conf()["PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS"], str(P22_PIN))

    def test_the_committed_other_source_samples_hold_three_records_so_l_needs_50003(self):
        # SampleBound counts non-empty JSONL lines (HadoopIO.scala scanLines); each committed sample holds one.
        count = 0
        for rel in OTHER_SOURCE_SAMPLES:
            with open(os.path.join(REAL_REPO, rel), "rb") as handle:
                count += sum(1 for line in handle.read().split(b"\n") if line.strip(b"\r").strip())
        self.assertEqual(count, 3)
        self.assertGreaterEqual(P22_PIN, L_MAX_DBLP_WORKS + count)
        self.assertLessEqual(P22_PIN, int((L_MAX_DBLP_WORKS + count) * 1.25), "headroom is bounded (about 20 percent), not unbounded")

    def test_the_installed_ceiling_program_accepts_l_and_the_inclusive_pin_and_refuses_one_above(self):
        self.assertEqual(self.check(maxLocalSampleRecords=50003).returncode, 0)
        self.assertEqual(self.check(maxLocalSampleRecords=60000).returncode, 0)
        above = self.check(maxLocalSampleRecords=60001)
        self.assertEqual(above.returncode, 1)
        self.assertIn("maxLocalSampleRecords 60001 exceeds ceiling 60000", above.stderr)

    def test_the_other_six_ceilings_are_unchanged(self):
        self.assertEqual(ceilings()[1:], ["8", "256", "4096", "64", "8388608", "8388608"])
        self.assertNotEqual(self.check(reducerCount=9).returncode, 0)



# ---- P23: copy-out selection and ceiling -----------------------------------------------------------------------------------------
STEP_SH = os.path.join(SCRIPTS_DIR, "emr", "sc-step.sh")
P23_PIN = 8 * 1024 ** 3
# A fake `aws` that applies the AWS CLI filter rules exactly as awscli/customizations/s3/filters.py does for a local source: each
# pattern is joined to the source directory and matched with fnmatch against the full file path; everything is included by default and
# the LAST matching filter wins. `--no-follow-symlinks` skips links. Copies land in FAKE_S3_ROOT/<dest without s3://>. Every argv is logged.
FAKE_AWS = r"""#!/usr/bin/env python3
import fnmatch, json, os, shutil, sys
args = sys.argv[1:]
with open(os.environ["FAKE_AWS_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(args) + "\n")
if args[:2] != ["s3", "cp"]:
    sys.exit(0)
src, dest = args[2], args[3]
target = os.path.join(os.environ["FAKE_S3_ROOT"], dest[len("s3://"):])
filters, follow, i = [], True, 4
while i < len(args):
    if args[i] in ("--exclude", "--include"):
        filters.append((args[i][2:], args[i + 1])); i += 2; continue
    if args[i] == "--no-follow-symlinks":
        follow = False
    i += 1
if "--recursive" not in args:
    os.makedirs(os.path.dirname(target), exist_ok=True); shutil.copyfile(src, target); sys.exit(0)
root = src.rstrip("/")
for current, dirs, files in os.walk(root, followlinks=follow):
    for name in files:
        full = os.path.join(current, name)
        if os.path.islink(full) and not follow:
            continue
        keep = True
        for action, pattern in filters:
            if fnmatch.fnmatch(full, os.path.join(root, pattern)):
                keep = action == "include"
        if keep:
            out = os.path.join(target, os.path.relpath(full, root))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copyfile(full, out)
"""

# The local Phase 6 layout at 10,577 works (target/phase6-runs, observed 2026-11-16), reduced to one small file per kind.
LAYOUT = {
    "hadoop/r1/_SCHOLARCHAIN_COMPLETE": True, "hadoop/r1/counter-summary.json": True, "hadoop/r1/run-manifest.json": True,
    "hadoop/r1/.counter-summary.json.crc": True, "hadoop/r1/stats/j05-attempt.txt": True,
    "hadoop/r1/export/snapshot=dblp-2026-10-03/run=r1/reject/part-r-00000": True,
    "hadoop/r1/export/snapshot=hadoop-prep/run=r1/reject/part-r-00000": True,
    "hadoop/r1/export/snapshot=dblp-2026-10-03/run=r1/work/part-r-00000": False,
    "hadoop/r1/export/snapshot=hadoop-prep/run=r1/match-candidate/part-r-00000": False,
    "hadoop/r1/intermediate/j06/part-r-00000": False, "hadoop/r1/intermediate/j01/reject/part": False,
    "er/run/_SCHOLARCHAIN_RESOLUTION_COMPLETE": True, "er/run/resolution-manifest.json": True, "er/run/diagnostics.jsonl": True,
    "er/run/effective-config.json": True, "er/run/effective-policy.json": True,
    "er/run/evidence.jsonl": False, "er/run/audit-details.jsonl": False, "er/run/work/part-0": False, "er/run/researcher/part-0": False,
    "spark/run:abc/load-manifests/nodes.json": True, "spark/run:abc/neptune-opencypher-csv/data/edges-0.csv": True,
    "spark/run:abc/nodes/type=work/part-0.parquet": True, "spark/.event-logs/app-1/local-1": True,
    "results/class-origin.json": True, "config/spark-config.json": True,
}


class CopyOutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sc-p23-"))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.mnt = os.path.join(self.tmp, "mnt")
        self.run_root = os.path.join(self.mnt, "runs", "bp-0001")
        self.s3 = os.path.join(self.tmp, "s3")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        with open(os.path.join(self.bin, "aws"), "w", encoding="utf-8") as handle:
            handle.write(FAKE_AWS.replace("#!/usr/bin/env python3", "#!" + sys.executable + " -I", 1))
        os.chmod(os.path.join(self.bin, "aws"), 0o755)
        self.mounts = os.path.join(self.tmp, "mounts")
        with open(self.mounts, "w", encoding="utf-8") as handle:
            handle.write("fs-fake:/ %s efs rw 0 0\n" % self.mnt)
        self.log = os.path.join(self.tmp, "aws.log")

    def make(self, layout=LAYOUT, size=None):
        for rel in layout:
            path = os.path.join(self.run_root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write((rel + "\n").encode() if size is None else b"x" * size)

    def body(self, max_bytes=P23_PIN):
        env = {"PATH": self.bin + ":/usr/bin:/bin:/usr/sbin:/sbin", "SC_PROC_MOUNTS": self.mounts, "TMPDIR": self.tmp, "LC_ALL": "C",
               "FAKE_AWS_LOG": self.log, "FAKE_S3_ROOT": self.s3, "HOME": self.tmp}
        argv = ["bash", STEP_SH, "__body", "copy-out", "STEP_SECONDS=60", "KILL_AFTER=5", "RUN_ID=bp-0001", "TAG=bp-0001", "MNT=" + self.mnt,
                "OUTPUT_PREFIX=s3://out-bucket/pipeline/run-x/bp-0001", "REGION=us-east-2", "MAX_COPYOUT_BYTES=%d" % max_bytes]
        return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)

    def manifest_paths(self):
        with open(os.path.join(self.run_root, "copyout-manifest.sha256"), encoding="utf-8") as handle:
            return sorted(line.split("  ", 1)[1] for line in handle.read().splitlines())

    def copied(self):
        base = os.path.join(self.s3, "out-bucket", "pipeline", "run-x", "bp-0001")
        found = []
        for current, _dirs, files in os.walk(base):
            for name in files:
                found.append(os.path.relpath(os.path.join(current, name), base))
        return sorted(f for f in found if f != "copyout-manifest.sha256")

    def aws_calls(self):
        with open(self.log, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def test_the_pin_is_8_gib(self):
        # Local sizes at 10,577 works (target/phase6-runs): Spark export run dir 592 MB + event logs 462 MB + the kept Hadoop and ER files
        # (stats 56 KB, rejects 436 KB, ER top-level files < 10 KB) = about 1.06 GB at S; x 50000 / 10577 = about 5.0 GB at L; 8 GiB ~ 1.7x L.
        self.assertEqual(conf()["PIPELINE_MAX_COPYOUT_BYTES"], str(P23_PIN))
        self.assertEqual(conf()["PIPELINE_MAX_INPUT_BYTES"], "268435456", "the stage-in ceiling is unchanged (L input is about 28 MB)")

    def test_only_the_report_and_loader_files_are_selected_hashed_and_copied(self):
        self.make()
        done = self.body()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        wanted = sorted(rel for rel, keep in LAYOUT.items() if keep)
        self.assertEqual(self.manifest_paths(), wanted)
        self.assertEqual(self.copied(), wanted, "the aws filters select exactly the manifest set")
        total = sum(len((rel + "\n").encode()) for rel in wanted)
        self.assertIn("STEP-LOG copy-out: copied %d bytes" % total, done.stdout)

    def test_the_upload_carries_the_filters_in_order_and_never_follows_links(self):
        self.make()
        self.assertEqual(self.body().returncode, 0)
        calls = {c[3].rsplit("/", 2)[-2]: c for c in self.aws_calls() if c[:2] == ["s3", "cp"] and "--recursive" in c}
        self.assertEqual(sorted(calls), ["config", "er", "hadoop", "results", "spark"])
        self.assertEqual(calls["hadoop"][4:], ["--recursive", "--exclude", "intermediate/*", "--exclude", "*/intermediate/*", "--exclude", "export/*",
                                               "--exclude", "*/export/*", "--include", "export/*/reject/*", "--include", "*/export/*/reject/*",
                                               "--no-follow-symlinks", "--region", "us-east-2", "--only-show-errors"])
        self.assertEqual(calls["er"][4:], ["--recursive", "--exclude", "*/*/*", "--exclude", "evidence.jsonl", "--exclude", "*/evidence.jsonl",
                                           "--exclude", "audit-details.jsonl", "--exclude", "*/audit-details.jsonl", "--no-follow-symlinks",
                                           "--region", "us-east-2", "--only-show-errors"])
        for part in ("spark", "results", "config"):
            self.assertEqual(calls[part][4:], ["--recursive", "--no-follow-symlinks", "--region", "us-east-2", "--only-show-errors"])

    def test_the_ceiling_counts_only_the_selected_bytes(self):
        # 10 kept files x 100 bytes would be 1000 bytes; the excluded big files do not count.
        layout = {"hadoop/r1/counter-summary.json": True, "hadoop/r1/intermediate/j01/big": False, "er/run/evidence.jsonl": False,
                  "spark/run:abc/part-0": True}
        self.make(layout, size=100)
        with open(os.path.join(self.run_root, "er/run/evidence.jsonl"), "wb") as handle:
            handle.write(b"e" * 100000)
        self.assertEqual(self.body(max_bytes=200).returncode, 0, "200 selected bytes fit an inclusive 200 byte ceiling")
        os.remove(os.path.join(self.run_root, "copyout-manifest.sha256"))
        before = len(self.aws_calls())
        over = self.body(max_bytes=199)
        self.assertEqual(over.returncode, 1)
        self.assertIn("copy-out 200 bytes exceeds the 199 byte ceiling", over.stderr)
        self.assertEqual(len(self.aws_calls()), before, "the refused run makes no aws call")

    def test_a_refused_copy_out_uploads_nothing(self):
        self.make({"spark/run:abc/part-0": True}, size=100)
        done = self.body(max_bytes=99)
        self.assertEqual(done.returncode, 1)
        self.assertFalse(os.path.exists(self.log), "no aws call at all")
        self.assertFalse(os.path.exists(os.path.join(self.run_root, "copyout-manifest.sha256")))

    def test_a_symbolic_link_is_neither_counted_nor_copied(self):
        self.make({"spark/run:abc/part-0": True}, size=10)
        outside = os.path.join(self.tmp, "outside.bin")
        with open(outside, "wb") as handle:
            handle.write(b"o" * 5000)
        os.symlink(outside, os.path.join(self.run_root, "spark", "run:abc", "link.bin"))
        done = self.body(max_bytes=10)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.manifest_paths(), ["spark/run:abc/part-0"])
        self.assertEqual(self.copied(), ["spark/run:abc/part-0"])

    def test_a_hadoop_layout_without_a_run_directory_is_filtered_the_same_way(self):
        layout = {"hadoop/counter-summary.json": True, "hadoop/intermediate/j01/p": False, "hadoop/export/snapshot=x/run=y/reject/p": True,
                  "hadoop/export/snapshot=x/run=y/work/p": False, "er/diagnostics.jsonl": True, "er/evidence.jsonl": False, "er/run/work/p": False}
        self.make(layout)
        self.assertEqual(self.body().returncode, 0)
        wanted = sorted(rel for rel, keep in layout.items() if keep)
        self.assertEqual(self.manifest_paths(), wanted)
        self.assertEqual(self.copied(), wanted)



# ---- P25: EMR ledger caps -------------------------------------------------------------------------------------------------------
# User decision 2026-11-16 (docs/agent-runs/phase-15/prompt.md line 131): "Cap 4 runs and USD 3.36 cumulative, including Session 1's
# EMR spend". Session 1 left 2 reservations of 0.84 (1.68) in the ledger; each 90-minute run of primary + one core m5.xlarge estimates
# 2 x (0.192 + 0.048) x (90 min + 900 s = 1.75 h) = 0.84, so runs 3 and 4 fit exactly (3.36) and run 5 is refused.
BUDGET = os.path.join(SCRIPTS_DIR, "lib", "budget.py")


def budget(*args):
    done = subprocess.run([sys.executable, "-I", BUDGET] + [str(a) for a in args], capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


class LedgerCapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sc-p25-"))
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.home)
        os.makedirs(self.repo)
        self.ledger = os.path.join(self.home, ".scholarchain", "emr-ledger", "runs.jsonl")
        values = conf()
        self.max_runs, self.cap = values["EMR_MAX_LIVE_RUNS"], values["EMR_CUMULATIVE_CAP_USD"]
        rc, out, err = budget("ledger-init", "--root", self.home, "--within-name", ".scholarchain under HOME", "--within",
                              os.path.join(self.home, ".scholarchain"), "--ledger", self.ledger, "--repo-root", self.repo,
                              "--initialized-by", "fixture", "--initialized-utc", "2026-11-06T09:00:00Z")
        self.assertEqual(rc, 0, out + err)
        for index in (1, 2):  # the two Session 1 runs
            self.assertEqual(self.reserve("s1-run-%d" % index)[0], 0)

    def reserve(self, run_id, estimate="0.84"):
        return budget("ledger-reserve", "--root", self.home, "--ledger", self.ledger, "--repo-root", self.repo, "--run-id", run_id,
                      "--estimate", estimate, "--max-runs", self.max_runs, "--cumulative-cap", self.cap, "--action", "run-bounded-pipeline",
                      "--run-config-sha256", "a" * 64, "--approval-sha256", __import__("hashlib").sha256(run_id.encode()).hexdigest(),
                      "--reserved-utc", "2026-11-18T10:00:00Z")

    def check(self, estimate="0.84"):
        return budget("ledger-check", "--ledger", self.ledger, "--repo-root", self.repo, "--estimate", estimate, "--max-runs", self.max_runs,
                      "--cumulative-cap", self.cap)

    def lines(self):
        with open(self.ledger, encoding="utf-8") as handle:
            return len(handle.readlines())

    def test_the_pins_are_the_approved_values(self):
        self.assertEqual((self.max_runs, self.cap, conf()["EMR_MAX_RUN_USD"]), ("4", "3.36", "3"))

    def test_the_cap_is_four_times_the_scripts_own_90_minute_estimate(self):
        rc, out, _ = budget("estimate", "--instance-type", "m5.xlarge", "--primary-count", 1, "--core-count", 1, "--task-count", 0, "--minutes", 90,
                            "--idle-seconds", 900, "--ec2-rate", "0.192", "--emr-rate", "0.048", "--max-run-usd", conf()["EMR_MAX_RUN_USD"],
                            "--budget-usd", "0.84")
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads(out)["estimate_usd"], "0.84")
        self.assertEqual(4 * 84, int(self.cap.replace(".", "")))

    def test_runs_3_and_4_are_reserved_and_run_5_is_refused(self):
        rc, out, _ = self.reserve("s2-run-3")
        self.assertEqual(rc, 0, out)
        rc, out, _ = self.reserve("s2-run-4")
        self.assertEqual(rc, 0, out)
        self.assertIn("cumulative_usd=3.36", out)
        rc, out, _ = self.check("0.01")
        self.assertEqual(rc, 1)
        self.assertIn("4 live EMR runs are already recorded in the ledger (limit 4)", out)
        rc, out, _ = self.reserve("s2-run-5", "0.01")
        self.assertEqual(rc, 1)
        self.assertIn("live EMR runs", out)
        self.assertEqual(self.lines(), 5, "the init record and four reservations only")

    def test_the_cumulative_cap_refuses_above_3_36_and_admits_exactly_3_36(self):
        self.assertEqual(self.reserve("s2-run-3")[0], 0)  # 2.52 recorded
        rc, out, _ = self.check("0.85")
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 3.37 USD (recorded 2.52 + this run 0.85) would exceed the cap 3.36 USD", out)
        rc, out, _ = self.reserve("s2-run-4-big", "0.85")
        self.assertEqual(rc, 1)
        self.assertIn("would exceed the cap 3.36 USD", out)
        self.assertEqual(self.lines(), 4, "a refused reservation writes nothing")
        rc, out, _ = self.check("0.84")
        self.assertEqual(rc, 0, out)

    def test_a_longer_l_run_does_not_fit_after_s(self):
        # An L manifest at 120 minutes estimates 2 x 0.24 x (2 h + 0.25 h) = 1.08; 2.52 + 1.08 = 3.60 > 3.36: refused (recompute the cap first).
        self.assertEqual(self.reserve("s2-run-3")[0], 0)
        rc, out, _ = self.check("1.08")
        self.assertEqual(rc, 1)
        self.assertIn("cumulative estimate 3.60 USD (recorded 2.52 + this run 1.08) would exceed the cap 3.36 USD", out)



# ---- P6 defects D1 and D2 in the hadoop-prep step --------------------------------------------------------------------------------
RUN_ID_V4 = re.compile(r"^run:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")  # StableIds.runPattern


def expected_hadoop_run_id(run_id):
    h = __import__("hashlib").sha256(run_id.encode()).hexdigest()[:32]
    u = h[:12] + "4" + h[13:16] + "89ab"[int(h[16], 16) & 3] + h[17:32]
    return "run:%s-%s-%s-%s-%s" % (u[:8], u[8:12], u[12:16], u[16:20], u[20:32])


class HadoopPrepArgumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="sc-p6d-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        with open(STEP_SH, encoding="utf-8") as handle:
            self.text = handle.read()
        function = re.search(r"^hadoop_run_id\(\) \{.*?^\}$", self.text, re.M | re.S).group(0)
        self.lib = os.path.join(self.tmp, "fn.sh")
        with open(self.lib, "w", encoding="utf-8") as handle:
            handle.write('die() { echo "die: $*" >&2; exit 1; }\n' + function + "\n")

    def derive(self, run_id):
        done = subprocess.run(["bash", "-c", '. "$1"; hadoop_run_id "$2"', "x", self.lib, run_id], capture_output=True, text=True,
                              env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LC_ALL": "C"})
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def test_d1_the_hadoop_run_id_is_a_deterministic_v4_run_id_derived_from_the_pipeline_run_id(self):
        for run_id in ("bp-0001", "20261118-s-001", "p6-S-20261116T155022Z", "x"):
            with self.subTest(run_id):
                derived = self.derive(run_id)
                self.assertRegex(derived, RUN_ID_V4)
                self.assertEqual(derived, expected_hadoop_run_id(run_id))
                self.assertEqual(self.derive(run_id), derived, "deterministic")
        self.assertNotEqual(self.derive("bp-0001"), self.derive("bp-0002"))

    def test_d1_the_step_passes_the_derived_id_and_logs_the_mapping(self):
        self.assertIn('--run-id "${hadoop_id}"', self.text)
        self.assertNotIn('--run-id "${RUN_ID}"', self.text)
        self.assertIn('log "Hadoop run id ${hadoop_id} (derived from pipeline run id ${RUN_ID})"', self.text)

    def test_d2_the_output_root_is_a_plain_absolute_path(self):
        self.assertIn('--output-root "${out_dir}"', self.text)
        self.assertNotIn('--output-root "file://', self.text)
        self.assertIn('out_dir="${RUN_ROOT}/hadoop"', self.text)
        self.assertIn('RUN_ROOT="${MNT}/runs/${RUN_ID}"', self.text, "MNT is absolute, so the output root is absolute")


if __name__ == "__main__":
    unittest.main()
