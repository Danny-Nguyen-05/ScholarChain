#!/usr/bin/env python3
"""Phase 16, group 1 (entity resolution): recompute the Phase 5E held-out metrics from the labels and the predictions (stdlib only; python3 -I; offline).

  python3 -I experiments/scripts/eval16_identity.py [--out-dir experiments/results/phase16/identity]

Inputs (all read-only, every sha256 is written to the output):
  docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json   the 300 queued pairs: partition, role (initial or reserve), stratum, entity type
  datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/validated-labels.json   one label per pair: same, different, uncertain or missing
  docs/agent-runs/phase-05/evidence/5e/disabled-a-predictions.json          one prediction per pair: outcome and matching path (the fake and disabled
                                                                            runs have byte-identical predictions, see the manifest)
  docs/agent-runs/phase-05/evidence/5e/exclude-assisted-pairs.json          the 22 self-attested externally assisted pairs (the "without assisted" slice)
  docs/agent-runs/phase-05/evidence/5e/*/evaluation.json                    the 5E evaluator's own output: a cross-check only, never a source of a number
Definitions (the same as the 5E evaluator): a positive prediction is ACCEPTED; every other outcome is non-acceptance. Only labels same and different are
binary gold; uncertain and missing are excluded and reported apart. precision = TP/(TP+FP), recall = TP/(TP+FN), accuracy = (TP+TN)/binary,
decisive coverage = pairs predicted ACCEPTED or REJECTED / binary, unresolved rate = UNRESOLVED / binary, conflict rate = CONFLICT / binary. Proportions
carry a Wilson 95% interval; F1 carries a seeded percentile bootstrap interval (it is not a proportion). Undefined ratios are null, never zero.
Exit codes: 0 done, 1 refused (an input is missing or unreadable).
"""
import argparse
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-identity.v1"
Z = 1.959963984540054
BOOTSTRAP_SEED = "eval16-identity-v1"
BOOTSTRAP_RESAMPLES = 2000
OUTCOMES = ("ACCEPTED", "REJECTED", "UNRESOLVED", "CONFLICT", "INVALID", "MISSING")

E5 = "docs/agent-runs/phase-05/evidence/5e"
INPUTS = {
    "queue": "docs/agent-runs/phase-05/evidence/5c-repair/review-artifacts/queue.json",
    "labels": "datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/validated-labels.json",
    "predictions": E5 + "/disabled-a-predictions.json",
    "exclusions": E5 + "/exclude-assisted-pairs.json",
}
EVALUATOR_OUTPUTS = {
    ("held-out", False): E5 + "/disabled-a-held-out/evaluation.json",
    ("held-out", True): E5 + "/disabled-a-held-out-without-assisted/evaluation.json",
    ("development", False): E5 + "/disabled-a-development/evaluation.json",
    ("development", True): E5 + "/disabled-a-development-without-assisted/evaluation.json",
}
# Cross-check constants: the numbers the 5E report text states (docs/agent-runs/phase-05/evidence/5e/evaluation-report.md). They are never used as results.
REPORT_STATED = {
    ("held-out", False): {"binary": 194, "tp": 57, "fp": 0, "fn": 15, "tn": 122, "uncertain": 6},
    ("held-out", True): {"binary": 181, "tp": 51, "fp": 0, "fn": 8, "tn": 122, "uncertain": 1},
    ("development", False): {"binary": 38, "tp": 7, "fp": 0, "fn": 4, "tn": 27, "uncertain": 2},
    ("development", True): {"binary": 34, "uncertain": 2},
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(k, n, z=Z):
    """Wilson score interval of k successes in n trials as (low, high); None when n is 0."""
    if n <= 0:
        return None
    p = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / denominator
    # exact at the boundaries: the lower limit is 0 when k = 0 and the upper limit is 1 when k = n (avoids a 1e-16 rounding artefact)
    return (0.0 if k == 0 else max(0.0, centre - half), 1.0 if k == n else min(1.0, centre + half))


def proportion(k, n):
    """A proportion with its Wilson interval; value and interval are None when the denominator is 0."""
    interval = wilson(k, n)
    return {"k": k, "n": n, "value": (k / n) if n else None,
            "wilson95": [round(interval[0], 6), round(interval[1], 6)] if interval else None}


def f1_of(tp, fp, fn):
    denominator = 2 * tp + fp + fn
    return (2 * tp / denominator) if denominator else None


def classify_pair(gold, outcome):
    """('tp'|'fp'|'fn'|'tn'|None): None for uncertain, missing or unlabeled gold."""
    if gold not in ("same", "different"):
        return None
    predicted = outcome == "ACCEPTED"
    if gold == "same":
        return "tp" if predicted else "fn"
    return "fp" if predicted else "tn"


def confusion(items):
    """Metrics of a list of {gold, outcome, ...} items (see the definitions in the module docstring)."""
    cell = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    table = {"same": dict.fromkeys(OUTCOMES, 0), "different": dict.fromkeys(OUTCOMES, 0), "uncertain": dict.fromkeys(OUTCOMES, 0)}
    uncertain = 0
    for item in items:
        gold, outcome = item["gold"], item["outcome"]
        if gold in table:
            table[gold][outcome if outcome in OUTCOMES else "INVALID"] += 1
        if gold == "uncertain":
            uncertain += 1
        c = classify_pair(gold, outcome)
        if c:
            cell[c] += 1
    binary = sum(cell.values())
    decisive_correct = cell["tp"] + table["different"]["REJECTED"]
    decisive = table["same"]["ACCEPTED"] + table["same"]["REJECTED"] + table["different"]["ACCEPTED"] + table["different"]["REJECTED"]
    unresolved = table["same"]["UNRESOLVED"] + table["different"]["UNRESOLVED"]
    conflict = table["same"]["CONFLICT"] + table["different"]["CONFLICT"]
    f1 = f1_of(cell["tp"], cell["fp"], cell["fn"])
    return {
        "tasks": len(items), "binary": binary, "uncertain": uncertain, "tp": cell["tp"], "fp": cell["fp"], "fn": cell["fn"], "tn": cell["tn"],
        "precision": proportion(cell["tp"], cell["tp"] + cell["fp"]),
        "recall": proportion(cell["tp"], cell["tp"] + cell["fn"]),
        "false_merge_rate": proportion(cell["fp"], cell["fp"] + cell["tn"]),
        "accuracy": proportion(cell["tp"] + cell["tn"], binary),
        "f1": {"value": f1, "note": "2TP/(2TP+FP+FN); interval: see bootstrap in the overall block" if f1 is not None else "undefined (no positive gold and no accepted pair)"},
        "decisive_coverage": proportion(decisive, binary),
        "decisive_accuracy": proportion(decisive_correct, decisive),
        "unresolved_rate": proportion(unresolved, binary),
        "conflict_rate": proportion(conflict, binary),
        "outcome_by_gold": table,
    }


def percentile_index(n, q):
    """Index of the q-quantile in a sorted list of n values, rounded the same way for both tails (so the two limits are symmetric: index(q) + index(1 - q) = n - 1)."""
    return int(round(q * (n - 1)))


def bootstrap_f1(items, seed=BOOTSTRAP_SEED, resamples=BOOTSTRAP_RESAMPLES):
    """Seeded percentile bootstrap 95% interval of F1 over the binary items (pairs are resampled with replacement)."""
    cells = [classify_pair(i["gold"], i["outcome"]) for i in items]
    cells = [c for c in cells if c]
    if not cells:
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
        for _ in range(len(cells)):
            counts[cells[rng.randrange(len(cells))]] += 1
        f1 = f1_of(counts["tp"], counts["fp"], counts["fn"])
        if f1 is not None:
            values.append(f1)
    if not values:
        return None
    values.sort()
    return {"method": "percentile bootstrap", "resamples": resamples, "seed": seed, "usable_resamples": len(values),
            "low": round(values[percentile_index(len(values), 0.025)], 6), "high": round(values[percentile_index(len(values), 0.975)], 6)}


def group_by(items, key):
    groups = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return {name: confusion(groups[name]) for name in sorted(groups)}


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def build_items(queue, labels, predictions):
    """One item per queued pair: {pair, partition, role, stratum, entity, gold, outcome, path}."""
    label_of = {c["pairId"]: c["label"] for c in labels["current"]}
    prediction_of = {r["pairId"]: r for r in predictions["rows"]}
    items = []
    for task in queue["tasks"]:
        pair_id = task["pair"]["pairId"]
        prediction = prediction_of.get(pair_id)
        items.append({"pair": pair_id, "partition": task["partition"], "role": task["role"], "stratum": task["stratum"],
                      "entity": task["pair"]["entityType"], "gold": label_of.get(pair_id, "missing"),
                      "outcome": prediction["outcome"] if prediction else "MISSING", "path": prediction["path"] if prediction else "MISSING"})
    return items


def slice_items(items, partition, excluded=frozenset()):
    return [i for i in items if i["partition"] == partition and i["role"] == "initial" and i["pair"] not in excluded]


def block(items):
    """The full metric block of one slice: overall, per entity, per path, per entity and path, per stratum."""
    out = {"overall": confusion(items), "by_entity": group_by(items, lambda i: i["entity"]), "by_path": group_by(items, lambda i: i["path"]),
           "by_entity_and_path": group_by(items, lambda i: i["entity"] + " / " + i["path"]), "by_sampling_stratum": group_by(items, lambda i: i["stratum"])}
    out["overall"]["f1_bootstrap95"] = bootstrap_f1(items)
    return out


def cross_check(computed, evaluator, stated):
    """Compare the recomputed counts with the 5E evaluator output and with the 5E report text (field by field)."""
    rows = []
    overall = (evaluator or {}).get("overall") or {}
    for name, ours in (("tp", computed["tp"]), ("fp", computed["fp"]), ("fn", computed["fn"]), ("tn", computed["tn"]), ("binary", computed["binary"]),
                       ("uncertain", computed["uncertain"])):
        theirs = {"binary": overall.get("binaryGold")}.get(name, overall.get(name))
        rows.append({"field": name, "recomputed": ours, "evaluator_json": theirs, "evaluator_agrees": theirs == ours,
                     "report_text": stated.get(name), "report_agrees": (stated.get(name) == ours) if name in stated else None})
    return rows


def evaluator_path_check(computed_by_path, evaluator):
    """The evaluator's byPath tp/fp/fn/tn per path against the recomputed ones."""
    rows = []
    for path, theirs in sorted(((evaluator or {}).get("byPath") or {}).items()):
        ours = computed_by_path.get(path)
        ours_cells = [ours[c] if ours else 0 for c in ("tp", "fp", "fn", "tn")]
        theirs_cells = [theirs.get(c) for c in ("tp", "fp", "fn", "tn")]
        rows.append({"path": path, "recomputed": ours_cells, "evaluator_json": theirs_cells, "agrees": ours_cells == theirs_cells})
    return rows


def fmt(p):
    if p["value"] is None:
        return "undefined (n=%d)" % p["n"]
    low, high = p["wilson95"]
    return "%.1f%% (%d/%d; Wilson 95%% %.1f-%.1f%%)" % (100 * p["value"], p["k"], p["n"], 100 * low, 100 * high)


def metric_table(title, groups):
    lines = ["#### " + title, "", "| group | pairs | binary | TP | FP | FN | TN | precision | recall | decisive coverage | unresolved |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, g in groups.items():
        lines.append("| %s | %d | %d | %d | %d | %d | %d | %s | %s | %s | %s |" % (
            name, g["tasks"], g["binary"], g["tp"], g["fp"], g["fn"], g["tn"], fmt(g["precision"]), fmt(g["recall"]), fmt(g["decisive_coverage"]), fmt(g["unresolved_rate"])))
    return lines + [""]


def markdown(doc):
    lines = ["# Phase 16 group 1: entity resolution (recomputed from the Phase 5E labels and predictions)", "",
             "Generated by `experiments/scripts/eval16_identity.py`; do not edit by hand. Every number below is recomputed from the label and prediction files listed in the",
             "input table; the 5E evaluator outputs and the 5E report text are used only as a cross-check. Measured facts come first, then the cross-check, then the limits;",
             "the interpretation is the last section.", "", "## Inputs", "", "| input | path | sha256 |", "|---|---|---|"]
    for name, info in sorted(doc["inputs"].items()):
        lines.append("| %s | `%s` | `%s` |" % (name, info["path"], info["sha256"]))
    lines += ["", "Configuration under test: the deterministic offline policy `er-offline-uncalibrated-v2` (the LLM adjudicator was disabled: zero real-provider calls). "
              "No LLM-adjudicated pair exists in this evaluation, so no LLM-path accuracy is measured.", ""]
    for key in ("held-out", "development"):
        for assisted in (False, True):
            name = "%s%s" % (key, " without the 22 AI-assisted pairs" if assisted else "")
            b = doc["slices"][name]
            o = b["overall"]
            lines += ["## Measured: %s" % name, "", "%d queued pairs in the slice: %d binary gold (same or different), %d uncertain (not scored)." % (o["tasks"], o["binary"], o["uncertain"]), "",
                      "Confusion matrix (positive prediction = ACCEPTED):", "", "| | predicted ACCEPTED | predicted not accepted |", "|---|---|---|",
                      "| gold same | TP %d | FN %d |" % (o["tp"], o["fn"]), "| gold different | FP %d | TN %d |" % (o["fp"], o["tn"]), "",
                      "TN %d is every gold-different pair that was not accepted: %d REJECTED + %d UNRESOLVED + %d CONFLICT. Only the REJECTED ones are an explicit rejection; accuracy below counts all %d as correct, so read it together with decisive coverage and decisive accuracy." % (
                          o["tn"], o["outcome_by_gold"]["different"]["REJECTED"], o["outcome_by_gold"]["different"]["UNRESOLVED"], o["outcome_by_gold"]["different"]["CONFLICT"], o["tn"]), "",
                      "- precision: %s" % fmt(o["precision"]), "- recall: %s" % fmt(o["recall"]),
                      "- F1: %s%s" % ("undefined" if o["f1"]["value"] is None else "%.4f" % o["f1"]["value"],
                                      "" if not o.get("f1_bootstrap95") else " (bootstrap 95%% %.4f-%.4f, %d resamples, seed `%s`)" % (
                                          o["f1_bootstrap95"]["low"], o["f1_bootstrap95"]["high"], o["f1_bootstrap95"]["resamples"], o["f1_bootstrap95"]["seed"])),
                      "- false merge rate (FP/(FP+TN)): %s" % fmt(o["false_merge_rate"]), "- accuracy: %s" % fmt(o["accuracy"]),
                      "- decisive coverage (pairs predicted ACCEPTED or REJECTED / binary): %s" % fmt(o["decisive_coverage"]),
                      "- accuracy among decisive pairs: %s" % fmt(o["decisive_accuracy"]),
                      "- unresolved rate (UNRESOLVED / binary): %s" % fmt(o["unresolved_rate"]),
                      "- conflict rate (CONFLICT / binary): %s" % fmt(o["conflict_rate"]), "",
                      "Outcome by gold label (rows gold, columns system outcome):", "", "| gold | " + " | ".join(OUTCOMES) + " |", "|---|" + "---|" * len(OUTCOMES)]
            for gold in ("same", "different", "uncertain"):
                lines.append("| %s | %s |" % (gold, " | ".join(str(o["outcome_by_gold"][gold][c]) for c in OUTCOMES)))
            lines.append("")
            lines += metric_table("By entity type", b["by_entity"])
            lines += metric_table("By matching path (the path recorded on the prediction)", b["by_path"])
            lines += metric_table("By entity type and path", b["by_entity_and_path"])
            lines += metric_table("By sampling stratum", b["by_sampling_stratum"])
    lines += ["## Cross-check against the 5E evaluator output and the 5E report text", "",
              "`evaluator` is the 5E Scala evaluator's `evaluation.json`; `report` is the number the 5E report text states. A mismatch would be a finding; the last column says whether every compared value agrees.", "",
              "| slice | field | recomputed | evaluator json | report text | agrees |", "|---|---|---|---|---|---|"]
    for name, rows in doc["cross_check"]["overall"].items():
        for r in rows:
            agree = r["evaluator_agrees"] and (r["report_agrees"] in (True, None))
            lines.append("| %s | %s | %s | %s | %s | %s |" % (name, r["field"], r["recomputed"], r["evaluator_json"], "n/a" if r["report_text"] is None else r["report_text"], "yes" if agree else "NO"))
    lines += ["", "Per-path counts (tp, fp, fn, tn) against the evaluator's `byPath`:", "", "| slice | path | recomputed | evaluator json | agrees |", "|---|---|---|---|---|"]
    for name, rows in doc["cross_check"]["by_path"].items():
        for r in rows:
            lines.append("| %s | %s | %s | %s | %s |" % (name, r["path"], r["recomputed"], r["evaluator_json"], "yes" if r["agrees"] else "NO"))
    lines += ["", "All compared values agree: **%s**." % ("yes" if doc["cross_check"]["all_agree"] else "NO, see the rows marked NO"), "",
              "## Sample limits, threats to validity and missing data", ""]
    lines += ["- %s" % t for t in doc["threats_to_validity"]]
    lines += ["", "## Gaps (not measured, with the reason)", ""]
    lines += ["- **%s**: %s" % (g["metric"], g["reason"]) for g in doc["gaps"]]
    lines += ["", "## Interpretation (separate from the measured facts above)", ""]
    lines += ["- %s" % t for t in doc["interpretation"]]
    return "\n".join(lines) + "\n"


THREATS = [
    "Convenience sample: the 300 queued pairs (200 held-out and 40 development initial reviews, 60 reserves never reviewed) were drawn from candidate pairs by oversampled evidence strata (shared observed id, observed id disagreement, missing authoritative id) with no population weights. The rates are rates in this sample, not rates in the full candidate population (the 5E report states 11,412 decisions) or the corpus.",
    "The sampling strata are defined by the evidence the matcher itself uses (a shared observed identifier selects the ExactIdentifier path), so per-path precision and recall are partly determined by how the stratum was built.",
    "Labels are AI-assisted: a language model drafted the labels and one human reviewer ticked checkboxes; 22 Researcher labels (the exclusion file; per the 5E report 18 held-out and 4 development) used external source checks whose evidence was not retained (self-attested). The 'without 22 assisted' slice removes those 22, but the other labels remain AI-drafted, so neither slice is independent blind gold, and there is a single reviewer, so inter-annotator agreement is unmeasured.",
    "No calibration or threshold tuning was done; the policy is er-offline-uncalibrated-v2 and was not changed for this evaluation. Development sensitivity analysis (eight hypothetical cutoffs) is outside this package and is not calibration.",
    "Blocking recall (whether true matches ever reach the candidate pair list) and global identity recall are unmeasured, so a pair the blocker never proposed is invisible here. Recall here is recall among the proposed, sampled pairs.",
    "{COURSE}",
    "Zero observed false positives (precision 100%) is a statement about this sample: the Wilson upper bound of the false merge rate is reported above and is not zero.",
    "Common-name and unobserved cross-partition leakage risks remain (the split groups known source, identifier and title anchors only).",
    "The LLM-adjudicated path has no observations (disabled by configuration), and no real provider was called; nothing here speaks to LLM-assisted identity decisions.",
]
GAPS = [
    {"metric": "blocking recall and global identity recall", "reason": "the candidate list is the only population labelled; there is no gold set of true matches independent of the blocker"},
    {"metric": "per-path metrics for DeterministicBibliographic and LlmAdjudicated", "reason": "no pair took those paths in the sample (zero observations)"},
    {"metric": "calibration (score reliability) and threshold sweep on held-out data", "reason": "not done by design: no held-out tuning, and the uncalibrated policy emits no probability"},
    {"metric": "inter-annotator agreement", "reason": "a single reviewer; no second independent label set exists"},
    {"metric": "real-provider LLM adjudication accuracy", "reason": "no real-provider call was made in Phase 5E"},
]
def course_sentence(slices):
    h, d = slices["held-out"]["overall"], slices["development"]["overall"]
    return ("The course asks for 200 manually reviewed examples. This sample has %d held-out plus %d development reviewed pairs; %d held-out and %d development pairs are uncertain and not scored, "
            "which leaves %d held-out binary labels. The labels are human-reviewed but AI-drafted (see above)." % (h["tasks"], d["tasks"], h["uncertain"], d["uncertain"], h["binary"]))


def interpretation(slices):
    """Interpretation sentences built from the computed held-out numbers; every qualitative phrase is chosen by a test on those numbers."""
    h = slices["held-out"]
    o = h["overall"]
    table = o["outcome_by_gold"]
    undecided = {k: table["same"][k] + table["different"][k] for k in ("UNRESOLVED", "CONFLICT")}
    lines = ["On the held-out sample the matcher accepted %d pair(s) that the reviewer labelled different and withheld %d of %d true matches. Precision is %s; recall is %s." % (
        o["fp"], o["fn"], o["tp"] + o["fn"], fmt(o["precision"]), fmt(o["recall"]))]
    if o["fp"] == 0 and o["fn"] > 0:
        lines.append("No accepted pair was wrong in this sample while some true matches were not accepted, so the policy favours precision over recall on this sample.")
    lines.append("Decisive coverage is %s: %d of %d binary pairs ended as UNRESOLVED and %d as CONFLICT (not decided), and decisive accuracy (accuracy among the decided pairs) is %s." % (
        fmt(o["decisive_coverage"]), undecided["UNRESOLVED"], o["binary"], undecided["CONFLICT"], fmt(o["decisive_accuracy"])))
    exact, scored = h["by_path"].get("ExactIdentifier"), h["by_path"].get("Scored")
    if exact:
        lines.append("ExactIdentifier path: TP %d, FP %d, FN %d of %d binary pairs. Those pairs were sampled because they share an observed identifier, so this is not a test of identifier-free matching." % (
            exact["tp"], exact["fp"], exact["fn"], exact["binary"]))
    fn_by_path = {name: g["fn"] for name, g in h["by_path"].items() if g["fn"]}
    if fn_by_path:
        lines.append("False negatives by matching path: %s%s." % (", ".join("%s %d" % kv for kv in sorted(fn_by_path.items())),
                                                                   "" if not scored else "; Scored-path recall is %s" % fmt(scored["recall"])))
    lines.append("Read these figures with the intervals above and the sample limits; no claim about the whole corpus follows from this evaluation.")
    return lines


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "experiments", "results", "phase16", "identity"))
    args = parser.parse_args(argv)
    try:
        paths = {name: os.path.join(ROOT, rel) for name, rel in INPUTS.items()}
        for key, rel in EVALUATOR_OUTPUTS.items():
            paths["evaluator-%s%s" % (key[0], "-without-assisted" if key[1] else "")] = os.path.join(ROOT, rel)
        rels = dict(INPUTS)
        for key, rel in EVALUATOR_OUTPUTS.items():
            rels["evaluator-%s%s" % (key[0], "-without-assisted" if key[1] else "")] = rel
        data = {name: load_json(path) for name, path in paths.items()}
        hashes = {name: {"path": rels[name], "sha256": sha256_file(paths[name])} for name in paths}
    except (OSError, ValueError) as error:
        print("EVAL16-IDENTITY-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    items = build_items(data["queue"], data["labels"], data["predictions"])
    excluded = frozenset(data["exclusions"]["pairIds"])
    slices, cross_overall, cross_path = {}, {}, {}
    for partition in ("held-out", "development"):
        for assisted in (False, True):
            name = "%s%s" % (partition, " without the 22 AI-assisted pairs" if assisted else "")
            selected = slice_items(items, partition, excluded if assisted else frozenset())
            slices[name] = block(selected)
            evaluator = data["evaluator-%s%s" % (partition, "-without-assisted" if assisted else "")]
            cross_overall[name] = cross_check(slices[name]["overall"], evaluator, REPORT_STATED.get((partition, assisted), {}))
            cross_path[name] = evaluator_path_check(slices[name]["by_path"], evaluator)
    all_agree = all(r["evaluator_agrees"] and r["report_agrees"] in (True, None) for rows in cross_overall.values() for r in rows) and \
        all(r["agrees"] for rows in cross_path.values() for r in rows)
    doc = {"schema": SCHEMA, "inputs": hashes, "population": {"queued_pairs": len(items), "excluded_assisted_pairs": len(excluded),
                                                               "pairs_without_prediction": sum(1 for i in items if i["outcome"] == "MISSING"),
                                                               "pairs_without_label": sum(1 for i in items if i["gold"] == "missing" and i["role"] == "initial")},
           "slices": slices, "cross_check": {"overall": cross_overall, "by_path": cross_path, "all_agree": all_agree},
           "threats_to_validity": [t.replace("{COURSE}", course_sentence(slices)) for t in THREATS], "gaps": GAPS, "interpretation": interpretation(slices)}
    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "identity-metrics.json"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    with open(os.path.join(args.out_dir, "identity-metrics.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(doc))
    o = slices["held-out"]["overall"]
    print("EVAL16-IDENTITY held-out binary=%d tp=%d fp=%d fn=%d tn=%d precision=%s recall=%s | without-assisted tp=%d fp=%d fn=%d tn=%d | cross_check_all_agree=%s" % (
        o["binary"], o["tp"], o["fp"], o["fn"], o["tn"], fmt(o["precision"]), fmt(o["recall"]),
        slices["held-out without the 22 AI-assisted pairs"]["overall"]["tp"], slices["held-out without the 22 AI-assisted pairs"]["overall"]["fp"],
        slices["held-out without the 22 AI-assisted pairs"]["overall"]["fn"], slices["held-out without the 22 AI-assisted pairs"]["overall"]["tn"], all_agree))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
