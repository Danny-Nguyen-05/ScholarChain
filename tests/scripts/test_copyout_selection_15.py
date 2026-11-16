"""Phase 15 P23: the selective copy-out keeps the Hadoop reject files and drops the Hadoop intermediate data (test-engineer, independent).

Requirement (Session 2 plan F17 / P23 as pinned in scripts/config/release.conf): copy-out selects only what the report and the loaders
need. For the Hadoop part that means: counters, run manifest, completion marker and stats are kept; `intermediate/` and the record
export are NOT copied; the reject files under `export/*/reject/` ARE copied, because the P6 reject-file check (zero rejects with reason
"maxLocalSampleRecords") reads them from the copied output. The byte ceiling counts the selected bytes only, and the ceiling pin is
8 GiB (was 256 MiB).

Black box: the copy-out body is taken verbatim from a dry run of the real scripts/run-bounded-pipeline.sh (a scratch copy) and run
with bash, as command-runner.jar would, against the sc_support fakes. Two observable outputs are judged:
  * the sha256 manifest the body writes next to the run (which files are selected and hashed), and
  * the `aws s3 cp` argv it issues, evaluated here with the documented AWS CLI filter semantics (every file is included unless a
    filter matches; filters apply in order and the last match wins; patterns are matched against the path relative to the source
    directory and `*` also matches `/`). This models the external AWS CLI, not the script.
The fixture tree mirrors a real local Hadoop run (target/phase5c-prep-runs/..., read 2026-11-16): <run>/export/snapshot=<s>/run=<id>/
<kind>/part-r-00000 with .crc side files, <run>/export/part-r-00000 and _SUCCESS, <run>/intermediate/jNN/, <run>/stats/.
"""
import fnmatch
import hashlib
import re
import unittest

import sc_support as S
from test_pipeline_bodies import TAG, Harness, argv_of

RUN = "hadoop-run-1"
REJECT_ROW = b'{"reasonCode":"maxLocalSampleRecords","source":"dblp"}\n'
HADOOP_KEEP = {
    RUN + "/_SCHOLARCHAIN_COMPLETE": b"",
    RUN + "/counter-summary.json": b'{"counters":{}}\n',
    RUN + "/run-manifest.json": b'{"run":"hadoop-run-1"}\n',
    RUN + "/stats/j05-attempt_local_0005_r_000000_0.txt": b"stats\n",
    RUN + "/export/snapshot=hadoop-prep/run=r1/reject/part-r-00000": REJECT_ROW,
    RUN + "/export/snapshot=hadoop-prep/run=r1/reject/.part-r-00000.crc": b"crc",
    RUN + "/export/snapshot=openalex-2026/run=r1/reject/part-r-00000": b'{"reasonCode":"malformedRecord"}\n',
}
HADOOP_DROP = {
    RUN + "/intermediate/j01/part-r-00000": b"intermediate j01 " * 64,
    RUN + "/intermediate/j08/_SUCCESS": b"",
    RUN + "/intermediate/j08/.part-r-00000.crc": b"crc",
    RUN + "/export/part-r-00000": b"export records " * 64,
    RUN + "/export/_SUCCESS": b"",
    RUN + "/export/snapshot=hadoop-prep/run=r1/match-candidate/part-r-00000": b"candidates " * 64,
    RUN + "/export/snapshot=hadoop-prep/run=r1/work/part-r-00000": b"works " * 64,
}
OTHER_KEEP = {"spark/export/graph.json": b"{}\n", "results/class-origin.json": b"{}\n"}


def aws_cli_selects(relative, argv):
    """AWS CLI `s3 cp --recursive` filter semantics, applied to one path relative to the source directory."""
    keep = True
    for i, word in enumerate(argv):
        if word in ("--exclude", "--include") and i + 1 < len(argv) and fnmatch.fnmatchcase(relative, argv[i + 1]):
            keep = word == "--include"
    return keep


class SelectiveCopyOut(unittest.TestCase):
    def build(self, **cfg):
        h = Harness(self, **cfg)
        tree = {}
        for rel, data in list(HADOOP_KEEP.items()) + list(HADOOP_DROP.items()):
            tree["hadoop/" + rel] = data
        tree.update(OTHER_KEEP)
        for rel, data in tree.items():
            path = h.run_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return h

    def test_the_copy_out_byte_ceiling_pin_is_eight_gib_and_the_input_ceiling_is_unchanged(self):
        conf = dict(re.findall(r"^([A-Z][A-Z0-9_]*)=(\S+)\s*$", (S.REPO / "scripts/config/release.conf").read_text(), re.M))
        self.assertEqual(int(conf["PIPELINE_MAX_COPYOUT_BYTES"]), 8 * 1024 ** 3)
        self.assertEqual(int(conf["PIPELINE_MAX_INPUT_BYTES"]), 256 * 1024 ** 2)

    def test_hadoop_rejects_are_copied_and_intermediate_and_record_export_are_not(self):
        h = self.build()
        done, calls = h.run_body("copy-out")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("STEP-FAIL", done.stderr)

        # 1. the manifest: exactly the kept files, each with its sha256
        manifest = (h.run_root / "copyout-manifest.sha256").read_text().splitlines()
        listed = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in manifest}
        expected = dict({"hadoop/" + r: d for r, d in HADOOP_KEEP.items()}, **OTHER_KEEP)
        self.assertEqual(sorted(listed), sorted(expected))
        for rel, data in expected.items():
            self.assertEqual(listed[rel], hashlib.sha256(data).hexdigest(), rel)
        reject = "hadoop/%s/export/snapshot=hadoop-prep/run=r1/reject/part-r-00000" % RUN
        self.assertIn(reject, listed, "the P6 maxLocalSampleRecords reject file must be copied out")
        self.assertFalse([r for r in listed if "/intermediate/" in r], "hadoop intermediate data must not be copied out")

        # 2. the upload: the hadoop cp, judged with the AWS CLI's own filter semantics, selects the same set
        cps = [a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]]
        hadoop_cp = [a for a in cps if a[3] == "s3://outbucket/data/out/%s/hadoop/" % TAG]
        self.assertEqual(len(hadoop_cp), 1, cps)
        argv = hadoop_cp[0]
        self.assertEqual(argv[2], str(h.run_root / "hadoop") + "/")
        self.assertIn("--recursive", argv)
        self.assertIn("--no-follow-symlinks", argv)
        for rel in HADOOP_KEEP:
            self.assertTrue(aws_cli_selects(rel, argv), "aws s3 cp would skip %s: %s" % (rel, argv))
        for rel in HADOOP_DROP:
            self.assertFalse(aws_cli_selects(rel, argv), "aws s3 cp would copy %s: %s" % (rel, argv))

        # 3. the logged byte count is the selected bytes only (the dropped intermediate and export bytes are not counted)
        selected = sum(len(d) for d in expected.values())
        self.assertIn("copied %d bytes" % selected, done.stdout + done.stderr)

    def test_the_ceiling_counts_selected_bytes_only_and_rejects_count(self):
        dropped = sum(len(d) for d in HADOOP_DROP.values())
        kept = sum(len(d) for d in HADOOP_KEEP.values()) + sum(len(d) for d in OTHER_KEEP.values())
        self.assertGreater(dropped, kept)
        # a ceiling between the selected bytes and the whole tree: accepted, because the intermediate and export bytes are not copied
        h = self.build(PIPELINE_MAX_COPYOUT_BYTES=str(kept))
        done, calls = h.run_body("copy-out")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        # one byte below the selected bytes: refused before any upload (the reject files are part of the selection)
        h = self.build(PIPELINE_MAX_COPYOUT_BYTES=str(kept - 1))
        done, calls = h.run_body("copy-out")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("exceeds", done.stderr)
        self.assertEqual([a for a in argv_of(calls, "aws") if a[:2] == ["s3", "cp"]], [])


if __name__ == "__main__":
    unittest.main()
