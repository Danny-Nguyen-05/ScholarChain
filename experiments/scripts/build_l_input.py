#!/usr/bin/env python3
"""One command for the size-L input tree of Experiment 15A (P21; stdlib; python3 -I). No network, no AWS.

Size L is LOCAL EVIDENCE ONLY (user, 2026-11-16, P25 rule): it is not run on EMR and has no EMR manifest. The tree feeds local runs
(P6, the identity-bypass Spark run); experiments/inputs/15a/size-l-local-evidence.json records the results.

  python3 -I experiments/scripts/build_l_input.py [--output-root target/experiment-inputs/15a]

Needs the dataset-engineer's L slice (datasets/scripts/phase15/select_dblp_l_slice.py): the manifest
datasets/phase15/dblp-l-slice-manifest.v1.json and the git-ignored XML it names (target/phase15-inputs/dblp-l/dblp.xml).

  1. checks the L slice manifest: nestingCheck.result PASS, and its sManifest.sha256 is the committed S manifest
     (datasets/phase6/dblp-slice-manifest.v1.json);
  2. builds <output-root>/size-l/datasets/samples/{dblp,openalex,crossref,orcid}/... and <output-root>/size-l.subset.json with
     make_dblp_subsets.py (all records: --sizes 100 --tree-label size-l); the source must match the L manifest's sha256 and
     publicationCount, the DBLP file must be byte-identical to the L slice, and the other three sources are the committed samples;
  3. if the S slice XML is present (target/phase6-inputs/6fg-dblp/dblp.xml, sha256 checked against the S manifest), checks again that every
     S key is in the L tree (S subset of L, independently of the dataset-engineer's check);
  4. checks that experiments/inputs/15a/size-l-local-evidence.json states the same publication count and sha256.

Refuses an existing tree. Writes nothing in the repository.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
L_MANIFEST = os.path.join("datasets", "phase15", "dblp-l-slice-manifest.v1.json")
S_MANIFEST = os.path.join("datasets", "phase6", "dblp-slice-manifest.v1.json")
S_XML = os.path.join("target", "phase6-inputs", "6fg-dblp", "dblp.xml")
LABEL = "size-l"


def load(name):
    spec = importlib.util.spec_from_file_location(name + "_for_l", os.path.join(HERE, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


subsets = load("make_dblp_subsets")
EVIDENCE = os.path.join("experiments", "inputs", "15a", "size-l-local-evidence.json")


def resolve(path):
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def sha256_file(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def check_l_manifest(l_manifest, s_manifest):
    with open(l_manifest, encoding="utf-8") as handle:
        document = json.load(handle)
    nesting = document.get("nestingCheck", {})
    if nesting.get("result") != "PASS":
        raise subsets.Refused("the L slice manifest does not record nestingCheck.result PASS")
    if nesting.get("sManifest", {}).get("sha256") != sha256_file(s_manifest):
        raise subsets.Refused("the L slice manifest's nestingCheck.sManifest.sha256 is not the committed S manifest %s" % S_MANIFEST)
    return document


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--l-slice-manifest", default=L_MANIFEST)
    parser.add_argument("--s-slice-manifest", default=S_MANIFEST)
    parser.add_argument("--s-xml", default=S_XML)
    parser.add_argument("--samples-dir", default=subsets.DEFAULT_SAMPLES)
    parser.add_argument("--output-root", default=subsets.DEFAULT_OUTPUT)
    parser.add_argument("--evidence", default=EVIDENCE, help="the L local-evidence record (default %(default)s)")
    args = parser.parse_args(argv)
    try:
        l_manifest = resolve(args.l_slice_manifest)
        if not os.path.isfile(l_manifest):
            raise subsets.Refused("%s does not exist: the dataset-engineer's L slice (P21) is not delivered yet" % args.l_slice_manifest)
        document = check_l_manifest(l_manifest, resolve(args.s_slice_manifest))
        source = document["output"]["path"]
        build_args = argparse.Namespace(source=source, slice_manifest=args.l_slice_manifest, samples_dir=args.samples_dir, output_root=args.output_root,
                                        sizes="100", tree_label=LABEL, skip_source_check=False)
        (info,) = subsets.build(build_args)
        if not info["byte_identical_to_source"]:
            raise subsets.Refused("the size-l DBLP file is not byte-identical to the L slice %s (record framing differs); the tree under %s must not be uploaded" % (source, args.output_root))
        out_root = resolve(args.output_root)
        s_xml = resolve(args.s_xml)
        nested = "not rechecked (S slice XML absent; the L manifest's nestingCheck PASS stands)"
        if os.path.isfile(s_xml):
            with open(resolve(args.s_slice_manifest), encoding="utf-8") as handle:
                s_sha = json.load(handle)["output"]["sha256"]
            if sha256_file(s_xml) != s_sha:
                raise subsets.Refused("%s does not match the S slice manifest sha256" % args.s_xml)
            with open(s_xml, encoding="utf-8") as handle:
                s_keys = {key for key, _ in subsets.parse_records(handle.read())}
            with open(os.path.join(out_root, LABEL, "datasets", "samples", "dblp", "linked-records.xml"), encoding="utf-8") as handle:
                l_keys = {key for key, _ in subsets.parse_records(handle.read())}
            if not s_keys < l_keys:
                raise subsets.Refused("S is not a strict subset of the size-l tree (%d S keys missing)" % len(s_keys - l_keys))
            nested = "PASS (%d S keys, all in the %d size-l keys)" % (len(s_keys), len(l_keys))
        with open(resolve(args.evidence), encoding="utf-8") as handle:
            recorded = json.load(handle)["slice"]
        if (recorded["publicationCount"], recorded["sha256"]) != (document["selection"]["publicationCount"], document["output"]["sha256"]):
            raise subsets.Refused("%s states %s / %s, the L slice manifest %s / %s: update the evidence record" % (
                args.evidence, recorded["publicationCount"], recorded["sha256"], document["selection"]["publicationCount"], document["output"]["sha256"]))
    except (subsets.Refused, OSError, KeyError, ValueError) as error:
        print("L-INPUT-REFUSED: %s" % error)
        return 1
    c = info["counts"]
    print("L-TREE %s publications=%d authorships=%d distinct_author_strings=%d dblp_sha256=%s identical_to_slice=%s"
          % (os.path.join(args.output_root, LABEL), c["publications"], c["authorships"], c["distinct_exact_author_strings"], info["dblp_file_sha256"], info["byte_identical_to_source"]))
    print("L-SUBSET %s" % os.path.join(args.output_root, LABEL + ".subset.json"))
    print("L-NESTING %s" % nested)
    print("L-EVIDENCE %s matches the L slice (local evidence only; L is not an EMR run)" % args.evidence)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
