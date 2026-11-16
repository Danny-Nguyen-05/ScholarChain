#!/usr/bin/env python3
"""Tests for experiments/scripts/er_identity_bypass.py (offline, stdlib).

Run from the repository root:   python3 -I -m unittest discover -s experiments/tests -v

The contract checks below are written from the Spark reader, not from the script: Phase6CReaders.verifyEr (manifest schema, complete,
marker = sha256(manifest text) + newline, inventory equality with the '.'/'_' skip rule, per-file bytes and sha256, exactly two
constraints), requireErPrepBinding (prepCompletionHash = sha256(hadoop marker text + newline + hadoop manifest text)), load (the eight
named files, line JSON with schemaVersion scholarchain.resolution.v1 and non-null required fields) and StableIds.sparkAnalyticsRunId
(run:<uuid v4>, policy version pattern, 64-hex policy hash).
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
spec = importlib.util.spec_from_file_location("er_identity_bypass", os.path.join(REPO, "experiments", "scripts", "er_identity_bypass.py"))
bypass = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bypass)

RUN_V4 = re.compile(r"^run:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
POLICY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_ER_FILES = [
    "%s/%s" % (folder, name)
    for folder in ("researcher", "work")
    for name in ("accepted-links.jsonl", "grouping-constraints.json", "unresolved.jsonl", "conflict.jsonl")
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def make_hadoop(root, run_id="run:08bf0555-048b-4594-be41-e4e1bdd9d0d8"):
    """A minimal completed Hadoop prep run (marker, manifest, export/_SUCCESS, two export parts)."""
    parts = {
        "snapshot=dblp-2026-10-03/run=x/work/part-r-00000": b'{"schemaVersion":"scholarchain.domain.v1","workId":"w1"}\n',
        "snapshot=dblp-2026-10-03/run=x/author-mention/part-r-00000": b'{"schemaVersion":"scholarchain.domain.v1","mentionId":"m1"}\n',
    }
    for name, data in parts.items():
        write(os.path.join(root, "export", name), data)
    write(os.path.join(root, "export", "_SUCCESS"), b"")
    manifest = {"runId": run_id, "schemaVersion": "scholarchain.domain.v1", "pipelineName": "hadoop-prep",
                "datasetSnapshots": [{"source": "DBLP", "snapshot": "dblp-2026-10-03", "retrievalDate": "2026-10-22"}],
                "configSchemaVersion": "scholarchain.hadoop-prep.v1", "configFingerprint": "f" * 64}
    marker = {"complete": True, "runId": run_id, "configFingerprint": "f" * 64, "schemaVersion": "scholarchain.domain.v1",
              "hadoopPrepSchema": "scholarchain.hadoop-prep.v1",
              "exportParts": [{"path": n, "bytes": len(d), "sha256": sha(d)} for n, d in sorted(parts.items())]}
    write(os.path.join(root, "run-manifest.json"), json.dumps(manifest, indent=2).encode("utf-8"))
    write(os.path.join(root, "_SCHOLARCHAIN_COMPLETE"), json.dumps(marker).encode("utf-8"))
    return root


def tree(root):
    out = {}
    for current, _dirs, files in os.walk(root):
        for name in files:
            full = os.path.join(current, name)
            with open(full, "rb") as handle:
                out[os.path.relpath(full, root)] = handle.read()
    return out


def run_quiet(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bypass.main(argv)
    return code, out.getvalue(), err.getvalue()


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hadoop = make_hadoop(os.path.join(self.tmp.name, "hadoop", "08bf0555"))
        self.er = os.path.join(self.tmp.name, "er", "run")

    def tearDown(self):
        self.tmp.cleanup()

    def test_output_satisfies_spark_er_contract(self):
        code, out, _ = run_quiet(["--hadoop-root", self.hadoop, "--out", self.er, "--verify-hashes"])
        self.assertEqual(code, 0)
        files = tree(self.er)
        manifest_text = files["resolution-manifest.json"].decode("utf-8")
        # verifyEr: marker binds the exact manifest text
        self.assertEqual(files["_SCHOLARCHAIN_RESOLUTION_COMPLETE"].decode("utf-8"), sha(manifest_text.encode("utf-8")) + "\n")
        manifest = json.loads(manifest_text)
        self.assertIs(manifest["complete"], True)
        self.assertEqual(manifest["schemaVersion"], "scholarchain.resolution-export.v1")
        names = [f["path"] for f in manifest["files"]]
        self.assertEqual(len(names), len(set(names)))
        visible = {p for p in files if not os.path.basename(p).startswith((".", "_"))} - {"resolution-manifest.json"}
        self.assertEqual(set(names), visible)
        for f in manifest["files"]:
            self.assertEqual(len(files[f["path"]]), f["bytes"])
            self.assertEqual(sha(files[f["path"]]), f["sha256"])
        self.assertEqual(len(manifest["constraints"]), 2)
        # requireErPrepBinding: computed from the fixture bytes here, not by the script
        with open(os.path.join(self.hadoop, "_SCHOLARCHAIN_COMPLETE"), "rb") as m, open(os.path.join(self.hadoop, "run-manifest.json"), "rb") as r:
            expected = sha(m.read() + b"\n" + r.read())
        self.assertEqual(manifest["prepCompletionHash"], expected)
        # sparkAnalyticsRunId / SparkLineage validation
        self.assertRegex(manifest["runId"], RUN_V4)
        self.assertRegex(manifest["policyVersion"], POLICY)
        self.assertRegex(manifest["policyHash"], HEX64)
        # load(): the eight named files exist; decision files empty (identity: no links, no decisions)
        for name in REQUIRED_ER_FILES:
            self.assertIn(name, files)
        for folder in ("researcher", "work"):
            for name in ("accepted-links.jsonl", "unresolved.jsonl", "conflict.jsonl"):
                self.assertEqual(files["%s/%s" % (folder, name)], b"")
        for folder, entity in (("researcher", "Researcher"), ("work", "Work")):
            lines = files["%s/grouping-constraints.json" % folder].decode("utf-8").splitlines()
            self.assertEqual(len(lines), 1)  # line-delimited JSON: one record
            doc = json.loads(lines[0])
            self.assertEqual(doc["schemaVersion"], "scholarchain.resolution.v1")
            self.assertEqual(doc["entityType"], entity)
            for key in ("coveredEndpoints", "cannotLinks", "authoritativeIdentifiers"):
                self.assertEqual(doc[key], [])  # non-null (required) and empty
            self.assertEqual(doc["policyHash"], manifest["policyHash"])
        self.assertEqual({c["entityType"] for c in manifest["constraints"]}, {"Work", "Researcher"})
        self.assertEqual(json.loads(out)["erRunId"], manifest["runId"])

    def test_disclosure_is_recorded(self):
        run_quiet(["--hadoop-root", self.hadoop, "--out", self.er])
        files = tree(self.er)
        text = "ER bypassed: identity pass-through (no cross-source resolution), local only, not the EMR path"
        manifest = json.loads(files["resolution-manifest.json"])
        self.assertEqual(manifest["disclosure"], text)
        self.assertIs(manifest["erBypassed"], True)
        self.assertEqual(manifest["policyVersion"], "er-identity-bypass-v1")
        self.assertEqual(json.loads(files["bypass-policy.json"])["disclosure"], text)
        self.assertEqual(sha(files["bypass-policy.json"]), manifest["policyHash"])
        self.assertTrue(all(v == 0 for v in manifest["outcomeCounts"].values()))

    def test_deterministic(self):
        other = os.path.join(self.tmp.name, "er2", "run")
        self.assertEqual(run_quiet(["--hadoop-root", self.hadoop, "--out", self.er])[0], 0)
        self.assertEqual(run_quiet(["--hadoop-root", self.hadoop, "--out", other])[0], 0)
        self.assertEqual(tree(self.er), tree(other))

    def test_different_hadoop_run_gives_different_er_run(self):
        second = make_hadoop(os.path.join(self.tmp.name, "hadoop2", "x"), run_id="run:11111111-1111-4111-8111-111111111111")
        other = os.path.join(self.tmp.name, "er2", "run")
        run_quiet(["--hadoop-root", self.hadoop, "--out", self.er])
        run_quiet(["--hadoop-root", second, "--out", other])
        a = json.loads(tree(self.er)["resolution-manifest.json"])
        b = json.loads(tree(other)["resolution-manifest.json"])
        self.assertNotEqual(a["runId"], b["runId"])
        self.assertNotEqual(a["prepCompletionHash"], b["prepCompletionHash"])


class RefusalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hadoop = make_hadoop(os.path.join(self.tmp.name, "hadoop", "r"))
        self.er = os.path.join(self.tmp.name, "er", "run")

    def tearDown(self):
        self.tmp.cleanup()

    def assertRefused(self, root, needle):
        code, out, err = run_quiet(["--hadoop-root", root, "--out", self.er, "--verify-hashes"])
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)
        self.assertIn(needle, err)
        self.assertEqual(out, "")
        self.assertFalse(os.path.exists(self.er))

    def edit_marker(self, change):
        path = os.path.join(self.hadoop, "_SCHOLARCHAIN_COMPLETE")
        with open(path, encoding="utf-8") as handle:
            doc = json.load(handle)
        change(doc)
        write(path, json.dumps(doc).encode("utf-8"))

    def test_refuses_plain_directory(self):
        plain = os.path.join(self.tmp.name, "plain")
        write(os.path.join(plain, "data.jsonl"), b"{}\n")
        self.assertRefused(plain, "_SCHOLARCHAIN_COMPLETE")

    def test_refuses_missing_directory(self):
        self.assertRefused(os.path.join(self.tmp.name, "absent"), "not a directory")

    def test_refuses_er_run_root_as_input(self):
        first = os.path.join(self.tmp.name, "first")
        self.assertEqual(run_quiet(["--hadoop-root", self.hadoop, "--out", first])[0], 0)
        self.assertRefused(first, "entity-resolution run root")

    def test_refuses_incomplete_marker(self):
        self.edit_marker(lambda d: d.update(complete=False))
        self.assertRefused(self.hadoop, "completion/manifest mismatch")

    def test_refuses_wrong_schema(self):
        self.edit_marker(lambda d: d.update(hadoopPrepSchema="scholarchain.hadoop-prep.v0"))
        self.assertRefused(self.hadoop, "unsupported Hadoop completion schema")

    def test_refuses_missing_success(self):
        os.remove(os.path.join(self.hadoop, "export", "_SUCCESS"))
        self.assertRefused(self.hadoop, "export/_SUCCESS")

    def test_refuses_extra_export_file(self):
        write(os.path.join(self.hadoop, "export", "snapshot=dblp-2026-10-03", "stray.json"), b"{}\n")
        self.assertRefused(self.hadoop, "inventory mismatch")

    def test_refuses_tampered_part(self):
        self.edit_marker(lambda d: d["exportParts"][0].update(sha256="0" * 64))
        self.assertRefused(self.hadoop, "byte/hash mismatch")

    def test_refuses_existing_output(self):
        os.makedirs(self.er)
        code, _, err = run_quiet(["--hadoop-root", self.hadoop, "--out", self.er])
        self.assertEqual(code, 2)
        self.assertIn("already exists", err)
        self.assertEqual(os.listdir(self.er), [])


if __name__ == "__main__":
    unittest.main()
