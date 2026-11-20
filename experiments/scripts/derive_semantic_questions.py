#!/usr/bin/env python3
"""Derive the fixed semantic question set for the P42 load (stdlib only; run with python3 -I). No network, no AWS.

Reads ONLY the Phase 6 DBLP slice (dblp-2026-10-03, 10,577 inproceedings; CC0) that datasets/phase6/dblp-slice-manifest.v1.json records, and
writes (refuses to overwrite unless --overwrite; LF-terminated; byte-identical for the same input):
  experiments/inputs/15b/semantic-questions.txt         one topic phrase per line, in rank order (the warm-up sends them in this order)
  experiments/inputs/15b/semantic-questions.provenance.json   source file and sha256, the rule, counts, the document frequency of every phrase
                                                        and the sha256 of the questions file

Rule (no randomness; every tie is broken by the phrase text):
  title tokens  = lowercase words of every <title> (HTML entities decoded, trailing period dropped); a token is letters with inner hyphens only
                  (no digits, no one-letter words); a token that is not a token ends the n-gram window.
  candidates    = every 2-word and 3-word window of consecutive tokens, none of them a stop word or a generic word (STOP, GENERIC below),
                  counted once per title (document frequency).
  eligible      = document frequency at least --min-df (default 5), 8..60 characters.
  fragments     = a 2-word candidate is dropped when a 3-word candidate that contains it has at least FRAGMENT_SHARE (0.6) of its document frequency
                  ("large language" is a fragment of "large language models").
  order         = (-document frequency, -words, phrase); greedy selection of --count (default 150) phrases; a candidate is skipped when it is a
                  word-sequence part of an already selected phrase or contains one, or when it differs from a selected phrase only by plural
                  "s" endings (so the 150 phrases are 150 distinct topics, not one topic at several lengths or number forms).
  The count must be within 100..200 (the plan's fixed set of about 100-200 distinct questions) or the run is refused.

The phrases are topics that occur in real DBLP titles of the slice (distributed systems venues: PODC, DISC, ICDCS, OSDI, SOSP, NSDI, EuroSys,
Middleware). They are sent as the "question" of POST /v1/semantic/retrieve; they hold no personal data and no credential.

Exit codes: 0 ok, 1 refused, 2 usage.
"""
import argparse
import collections
import hashlib
import html
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA = "scholarchain.experiment-inputs-provenance.v1"
DEFAULT_SOURCE = os.path.join("target", "phase6-inputs", "6fg-dblp", "dblp.xml")
SLICE_MANIFEST = os.path.join("datasets", "phase6", "dblp-slice-manifest.v1.json")
OUT_DIR = os.path.join("experiments", "inputs", "15b")
QUESTIONS_NAME = "semantic-questions.txt"
PROVENANCE_NAME = "semantic-questions.provenance.json"
TOKEN = re.compile(r"^[a-z]{2,}(?:-[a-z]{2,})*$")
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
TAG = re.compile(r"<[^>]+>")
STOP = frozenset("""a about above after again against all also am an and any are as at be because been before being below between both but by can could did do does
doing down during each few for from further had has have having he her here hers him his how i if in into is it its itself just me more most my no nor not now of off
on once only or other our out over own same she should so some such than that the their them then there these they this those through to too under until up us very was we
were what when where which while who whom why will with within without would you your""".split())
GENERIC = frozenset("""approach approaches based using use used via new novel towards toward case study studies paper evaluation evaluating analysis towards
efficient effective practical simple better improving improved making make toward revisited lessons experience experiences
brief announcement industry track extended abstract invited talk keynote workshop panel session tutorial introduction preface special issue
proceedings conference international symposium""".split())
DEFAULTS = {"count": 150, "min_df": 5}
FRAGMENT_SHARE = 0.6
COUNT_MIN, COUNT_MAX = 100, 200


class Refused(Exception):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def titles(text):
    return [html.unescape(TAG.sub("", m)).strip() for m in TITLE.findall(text)]


def windows(title):
    """All 2-word and 3-word phrases of consecutive valid tokens (a stop word, a generic word or a non-token breaks the window)."""
    words = re.split(r"[\s:;,.!?()\[\]{}\"'/&+=*]+", title.lower().rstrip("."))
    runs, run = [], []
    for word in words:
        if TOKEN.match(word) and word not in STOP and word not in GENERIC:
            run.append(word)
        else:
            if run:
                runs.append(run)
            run = []
    if run:
        runs.append(run)
    found = set()
    for run in runs:
        for size in (2, 3):
            for start in range(len(run) - size + 1):
                found.add(" ".join(run[start:start + size]))
    return found


def contains(longer, shorter):
    a, b = longer.split(), shorter.split()
    return len(b) <= len(a) and any(a[i:i + len(b)] == b for i in range(len(a) - len(b) + 1))


def singular_key(phrase):
    return " ".join(word[:-1] if word.endswith("s") and not word.endswith("ss") else word for word in phrase.split())


def select(all_titles, count, min_df):
    df = collections.Counter()
    for title in all_titles:
        df.update(windows(title))
    eligible = [(phrase, n) for phrase, n in df.items() if n >= min_df and 8 <= len(phrase) <= 60]
    trigrams = [(phrase, n) for phrase, n in eligible if len(phrase.split()) == 3]
    eligible = [(phrase, n) for phrase, n in eligible
                if len(phrase.split()) == 3 or not any(contains(t, phrase) and tn >= FRAGMENT_SHARE * n for t, tn in trigrams)]
    eligible.sort(key=lambda item: (-item[1], -len(item[0].split()), item[0]))
    chosen = []
    keys = set()
    for phrase, n in eligible:
        if singular_key(phrase) in keys or any(contains(phrase, other) or contains(other, phrase) for other, _ in chosen):
            continue
        keys.add(singular_key(phrase))
        chosen.append((phrase, n))
        if len(chosen) == count:
            break
    return chosen, len(eligible), len(df)


def verify_source(root, source):
    with open(os.path.join(root, SLICE_MANIFEST), encoding="utf-8") as handle:
        manifest = json.load(handle)
    expected = manifest["output"]["sha256"]
    actual = sha256_file(source)
    if actual != expected:
        raise Refused("%s has sha256 %s but %s records %s for the Phase 6 slice" % (source, actual, SLICE_MANIFEST, expected))
    return manifest


def build(root, source, count, min_df):
    if not COUNT_MIN <= count <= COUNT_MAX:
        raise Refused("--count must be within %d..%d" % (COUNT_MIN, COUNT_MAX))
    manifest = verify_source(root, source)
    with open(source, encoding="utf-8") as handle:
        all_titles = titles(handle.read())
    chosen, eligible, distinct = select(all_titles, count, min_df)
    if len(chosen) != count:
        raise Refused("only %d phrases satisfy the rule (document frequency at least %d); %d are needed" % (len(chosen), min_df, count))
    text = "".join(phrase + "\n" for phrase, _ in chosen)
    provenance = {
        "schema": SCHEMA,
        "note": "DBLP title phrases only; DBLP bibliographic metadata is public (CC0). No credential, account, host or personal value. Used as the fixed question set of the P42 semantic load (warm-up pass sends each once; the ramp draws from the same set).",
        "source": {
            "dataset": "dblp-2026-10-03 (DOI 10.4230/dblp.xml.2026-10-03), Phase 6 slice",
            "file": DEFAULT_SOURCE.replace(os.sep, "/"), "sha256": sha256_file(source), "recorded_in": SLICE_MANIFEST.replace(os.sep, "/"),
            "license": manifest["license"]["name"], "titles_read": len(all_titles),
        },
        "rule": {
            "tokens": "lowercase letter words with inner hyphens, 2+ letters; stop words and generic words break a window",
            "candidates": "2-word and 3-word windows, document frequency counted once per title",
            "eligible": "document frequency >= %d, 8..60 characters" % min_df,
            "order": "(-document frequency, -words, phrase); greedy; a phrase that contains, or is part of, a selected phrase is skipped",
            "count": count,
        },
        "counts": {"questions": count, "distinct_candidates": distinct, "eligible_candidates": eligible, "min_df": min_df},
        "outputs": {QUESTIONS_NAME: {"lines": count, "sha256": sha256_text(text)}},
        "phrases": [{"phrase": phrase, "titles": n} for phrase, n in chosen],
        "script": "experiments/scripts/derive_semantic_questions.py",
    }
    return text, provenance


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=REPO, help="repository root (tests use a fixture copy)")
    parser.add_argument("--source", help="the Phase 6 DBLP slice (default: %s under --root)" % DEFAULT_SOURCE)
    parser.add_argument("--out-dir", help="default: %s under --root" % OUT_DIR)
    parser.add_argument("--count", type=int, default=DEFAULTS["count"])
    parser.add_argument("--min-df", type=int, default=DEFAULTS["min_df"])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    source = os.path.abspath(args.source or os.path.join(root, DEFAULT_SOURCE))
    out_dir = os.path.abspath(args.out_dir or os.path.join(root, OUT_DIR))
    try:
        text, provenance = build(root, source, args.count, args.min_df)
        targets = {QUESTIONS_NAME: text, PROVENANCE_NAME: json.dumps(provenance, indent=2, sort_keys=True) + "\n"}
        if not args.overwrite:
            for name in targets:
                if os.path.lexists(os.path.join(out_dir, name)):
                    raise Refused("%s exists (use --overwrite)" % os.path.join(out_dir, name))
        os.makedirs(out_dir, exist_ok=True)
        for name, content in targets.items():
            with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            print("WROTE %s" % os.path.join(out_dir, name))
    except (Refused, OSError, ValueError, KeyError) as error:
        print("DERIVE-REFUSED: %s" % error)
        return 1
    print("questions sha256 %s (%d phrases)" % (provenance["outputs"][QUESTIONS_NAME]["sha256"], provenance["counts"]["questions"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
