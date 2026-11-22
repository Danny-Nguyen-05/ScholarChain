#!/usr/bin/env python3
"""Phase 16, group 3 (retrieval): retrieval-quality metrics where relevance labels exist in raw form, and an explicit GAP where they do not
(stdlib only; python3 -I; offline).

  python3 -I experiments/scripts/eval16_retrieval.py [--out-dir experiments/results/phase16/retrieval]

What exists, and what each source can support:
  1. Q12 graph-mode runs (q12-run-1, q12-run-2; local export, 33 questions, answer key experiments/inputs/q12/answer-key.json). For the 7 ranking questions the key lists the
     corpus-wide top 100 researchers with their metric value, so the retrieved evidence list (explain.body.evidenceIds, in order, mapped to researcher ids through the
     evidence sourceRecordId) can be scored: precision@K, MRR of the key's rank-1 researcher, nDCG@K (graded: gain = the key's metric value). K is the number of
     researcher items the runtime retrieved (3 or 4), not a free parameter.
  2. The Q12 scorer's per-type retrieval pass rate (q12_score.py: every cited evidence id resolves, names the required entities, has the required kind and carries correct
     values) read from target/phase15/q12/scores/*.json, with Wilson 95% intervals. It is a pass/fail check per question, not recall@K.
  3. The S3 Vectors query smoke (docs/agent-runs/phase-15/evidence/session-2/vectors/query-report.json): 5 known-item queries, one per index.
Not available (written as GAPs with the reason, never estimated): vector-only and fused retrieval with relevance labels; recall@K and nDCG for the 150 semantic load questions
(topic phrases without labels; response bodies were not stored); any graded human relevance labels.

Metric definitions (all pure functions, unit-tested): precision@K = hits in the first K / K; recall@K = hits in the first K / number of relevant; reciprocal rank = 1 / rank of the
first relevant item, 0 when none; DCG@K = sum of gain_i / log2(i + 1) for ranks i = 1..K; nDCG@K = DCG of the retrieved list / DCG of the ideal list (the K largest labelled
gains), undefined (null) when the ideal is 0. Proportions carry a Wilson 95% interval. Exit codes: 0 done, 1 refused, 3 inputs unavailable (neither the committed frozen copy nor the git-ignored original of an input exists).
"""
import argparse
import collections
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-retrieval.v1"
Z = 1.959963984540054
KEY = "experiments/inputs/q12/answer-key.json"
QUESTIONS_15B = "experiments/inputs/15b/semantic-questions.txt"
QUESTIONS_15B_PROV = "experiments/inputs/15b/semantic-questions.provenance.json"
QUERY_REPORT = "docs/agent-runs/phase-15/evidence/session-2/vectors/query-report.json"
INGEST_REPORT = "docs/agent-runs/phase-15/evidence/session-2/vectors/ingest-report-2.json"
Q12_RUNS = ("q12-run-1", "q12-run-2")
RUN_DIR = ("experiments/results/phase16/q12-raw/q12-benchmark-%s/answers.jsonl", "target/experiment-runs/q12-benchmark-%s/raw/answers.jsonl")  # frozen copy first
SCORES = ("experiments/results/phase16/answers/%s-scores.json", "target/phase15/q12/scores/%s-scores.json")  # the scorer's output: committed copy first
LOADGEN = "load-tests/loadgen.py"
RANKING_TYPES = ("coauthor_breadth", "max_team_size", "bridge")
RESEARCHER_ID = re.compile(r"researcher:[a-z]+:[0-9a-f]{64}")


class Refused(Exception):
    pass


class Unavailable(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------------- metric functions
def precision_at_k(retrieved, relevant, k):
    """Hits among the first k retrieved items divided by k (k is fixed, so a short list is penalised)."""
    if k <= 0:
        return None
    return len(set(retrieved[:k]) & set(relevant)) / float(k)


def recall_at_k(retrieved, relevant, k):
    relevant = set(relevant)
    if not relevant:
        return None
    return len(set(retrieved[:k]) & relevant) / float(len(relevant))


def reciprocal_rank(retrieved, relevant):
    relevant = set(relevant)
    for rank, item in enumerate(retrieved, 1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def dcg_at_k(gains, k):
    return sum(g / math.log(i + 1, 2) for i, g in enumerate(gains[:k], 1))


def ndcg_at_k(retrieved, gain_map, k):
    """nDCG@k with graded gains: gain_map maps item -> gain (an item absent from it has gain 0). The ideal list is the k largest gains in gain_map."""
    ideal = dcg_at_k(sorted(gain_map.values(), reverse=True), k)
    if ideal <= 0:
        return None
    return dcg_at_k([gain_map.get(item, 0.0) for item in retrieved], k) / ideal


def wilson(successes, n):
    if n == 0:
        return None
    p = successes / float(n)
    denominator = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / denominator
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / denominator
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def mean(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 4) if values else None


def retrieved_researchers(row):
    """The ordered researcher ids behind explain.body.evidenceIds. An evidence item that carries no researcher id in its sourceRecordId is counted as unmapped."""
    explain = row.get("explain")
    body = explain.get("body") if isinstance(explain, dict) else None
    if not isinstance(body, dict):
        return None
    ids, unmapped = [], 0
    for evidence_id in body.get("evidenceIds") or []:
        item = ((row.get("evidence") or {}).get(evidence_id) or {}).get("item") or {}
        source = (item.get("provenance") or {}).get("sourceRecordId") or item.get("sourceRecordId") or ""
        m = RESEARCHER_ID.search(source)
        if m:
            if m.group(0) not in ids:
                ids.append(m.group(0))
        else:
            unmapped += 1
    return ids, unmapped


def score_ranking_question(retrieved, key_top):
    """Metrics of one retrieved researcher list against the key's ranked list [{id, rank, value}]."""
    k = len(retrieved)
    key_ids = [t["id"] for t in key_top]
    gains = dict((t["id"], float(t["value"])) for t in key_top)
    top_k = key_ids[:k]
    return {"k": k, "precision_at_k_vs_key_top100": precision_at_k(retrieved, key_ids, k), "precision_at_k_vs_key_topk": precision_at_k(retrieved, top_k, k),
            "reciprocal_rank_of_key_rank1": reciprocal_rank(retrieved, key_ids[:1]), "ndcg_at_k_graded_by_key_value": ndcg_at_k(retrieved, gains, k),
            "ndcg_at_k_binary_vs_key_top100": ndcg_at_k(retrieved, dict((i, 1.0) for i in key_ids), k),
            "retrieved_in_key_top100": sum(1 for r in retrieved if r in gains), "exact_order_match_with_key_topk": retrieved == top_k,
            "key_saturated_by_ties": len(set(gains.values())) == 1}


# ------------------------------------------------------------------------------------------------------------------------------ io
def path_of(rel):
    return os.path.join(ROOT, rel)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(rel):
    try:
        with open(path_of(rel), encoding="utf-8") as handle:
            return json.load(handle)
    except OSError as error:
        raise Unavailable("%s: %s" % (rel, error.strerror))
    except ValueError as error:
        raise Refused("%s is not valid JSON: %s" % (rel, error))


def read_lines(rel):
    try:
        with open(path_of(rel), encoding="utf-8") as handle:
            return handle.read().split("\n")
    except OSError as error:
        raise Unavailable("%s: %s" % (rel, error.strerror))


# --------------------------------------------------------------------------------------------------------------------------- build
def pick(candidates, run):
    """The first existing candidate path (a committed frozen copy before the git-ignored original; the two are byte-identical, and the output names neither)."""
    for template in candidates:
        rel = template % run
        if os.path.isfile(path_of(rel)):
            return rel
    raise Unavailable("%s: no frozen copy and no git-ignored original found" % (candidates[0] % run))


TIE_FIELDS = {"MAXIMUM_COAUTHORS_ON_ONE_PAPER": "maximumCoauthorsOnOnePaper", "DISTINCT_COAUTHOR_COUNT": "distinctCoauthorCount"}


def tie_check(row, retrieved, key_top, metric):
    """For a key whose entries all tie: the metric value the ANSWER states for each retrieved researcher that is outside the key's list. The answer's values were checked against the
    export by the Q12 scorer (q12_score.py, 'every cited value ... is correct'), so this tests the tie premise from raw evidence without reading the export here."""
    field = TIE_FIELDS.get(metric)
    key_value = float(key_top[0]["value"])
    in_key = set(t["id"] for t in key_top)
    stated = dict((r.get("researcherId"), r.get(field)) for r in ((row.get("answer") or {}).get("answer") or {}).get("researchers") or [])
    outside = [{"suffix": r[-8:], "value_stated_in_answer": stated.get(r)} for r in retrieved if r not in in_key]
    equal = [o for o in outside if o["value_stated_in_answer"] is not None and float(o["value_stated_in_answer"]) == key_value]
    return {"key_value_of_all_entries": key_value, "key_entries": len(key_top), "metric_field": field, "retrieved_outside_key": outside,
            "outside_with_value_equal_to_key_value": len(equal), "all_outside_tie_at_key_value": bool(outside) and len(equal) == len(outside), "outside_with_no_value_stated": sum(1 for o in outside if o["value_stated_in_answer"] is None),
            "source": "values stated in the answer (scorer-checked against the export); not read from the export by this script"}


def q12_ranking(inputs):
    key = dict((q["id"], q) for q in read_json(KEY)["questions"])
    inputs[KEY] = sha256_file(path_of(KEY))
    per_run, per_question = {}, []
    for run in Q12_RUNS:
        rel = pick(RUN_DIR, run)
        inputs["q12 answers %s (raw/answers.jsonl)" % run] = sha256_file(path_of(rel))
        rows = [json.loads(l) for l in read_lines(rel) if l.strip()]
        scored = []
        for row in rows:
            q = key.get(row["qid"])
            if not q or q["type"] not in RANKING_TYPES or "top" not in q["expected"] or q["expected_outcome"] != "answer":
                continue
            got = retrieved_researchers(row)
            entry = {"run": run, "qid": row["qid"], "type": q["type"], "outcome": row["outcome"]}
            key_values = [float(t["value"]) for t in q["expected"]["top"]]
            if got is None or not got[0]:
                # nothing was retrieved (error, refusal or abstention): every metric is 0 and the question stays in the aggregates
                entry.update({"retrieved_researcher_suffixes": [], "unmapped_evidence_items": 0, "k": 0, "retrieved_in_key_top100": 0, "exact_order_match_with_key_topk": False,
                              "precision_at_k_vs_key_top100": 0.0, "precision_at_k_vs_key_topk": 0.0, "reciprocal_rank_of_key_rank1": 0.0, "ndcg_at_k_graded_by_key_value": 0.0,
                              "ndcg_at_k_binary_vs_key_top100": 0.0, "key_saturated_by_ties": len(set(key_values)) == 1,
                              "note": "no explain body or no researcher evidence retrieved (outcome %s): all metrics are 0 for this question and it is counted in the aggregates" % row["outcome"]})
            else:
                retrieved, unmapped = got
                entry.update({"retrieved_researcher_suffixes": [r[-8:] for r in retrieved], "unmapped_evidence_items": unmapped,
                              "key_top3_suffixes": [t["id"][-8:] for t in q["expected"]["top"][:3]], "key_metric": q["expected"].get("metric") or q["expected"].get("measure")})
                entry.update(score_ranking_question(retrieved, q["expected"]["top"]))
                if entry["key_saturated_by_ties"]:
                    entry["tie_check"] = tie_check(row, retrieved, q["expected"]["top"], entry["key_metric"])
            scored.append(entry)
            per_question.append(entry)
        per_run[run] = scored
    summary = {}
    for run, scored in per_run.items():
        by_type = collections.defaultdict(list)
        for e in scored:
            by_type[e["type"]].append(e)
        rows = {}
        for t, group in sorted(by_type.items()):
            with_k = [e for e in group if not e["key_saturated_by_ties"]]
            rows[t] = {"questions": len(group), "scorable_questions": len(with_k), "scorable_with_nothing_retrieved": sum(1 for e in with_k if not e["k"]),
                       "mean_precision_at_k_vs_key_top100": mean([e["precision_at_k_vs_key_top100"] for e in with_k]),
                       "mean_precision_at_k_vs_key_topk": mean([e["precision_at_k_vs_key_topk"] for e in with_k]),
                       "mrr_of_key_rank1": mean([e["reciprocal_rank_of_key_rank1"] for e in with_k]),
                       "mean_ndcg_at_k_graded": mean([e["ndcg_at_k_graded_by_key_value"] for e in with_k]),
                       "mean_ndcg_at_k_binary": mean([e["ndcg_at_k_binary_vs_key_top100"] for e in with_k]),
                       "exact_order_matches": sum(1 for e in with_k if e["exact_order_match_with_key_topk"])}
        with_k_all = [e for e in scored if not e["key_saturated_by_ties"]]
        every = list(scored)
        summary[run] = {"by_type": rows, "all_ranking_questions": {
            "questions": len(scored), "scorable_questions": len(with_k_all), "mean_precision_at_k_vs_key_top100": mean([e["precision_at_k_vs_key_top100"] for e in with_k_all]),
            "mean_precision_at_k_vs_key_topk": mean([e["precision_at_k_vs_key_topk"] for e in with_k_all]), "mrr_of_key_rank1": mean([e["reciprocal_rank_of_key_rank1"] for e in with_k_all]),
            "mean_ndcg_at_k_graded": mean([e["ndcg_at_k_graded_by_key_value"] for e in with_k_all]), "mean_ndcg_at_k_binary": mean([e["ndcg_at_k_binary_vs_key_top100"] for e in with_k_all])},
            "all_ranking_questions_including_tie_saturated_as_measured": {
                "questions": len(every), "mean_precision_at_k_vs_key_top100": mean([e["precision_at_k_vs_key_top100"] for e in every]),
                "mean_precision_at_k_vs_key_topk": mean([e["precision_at_k_vs_key_topk"] for e in every]), "mrr_of_key_rank1": mean([e["reciprocal_rank_of_key_rank1"] for e in every]),
                "mean_ndcg_at_k_graded": mean([e["ndcg_at_k_graded_by_key_value"] for e in every]), "mean_ndcg_at_k_binary": mean([e["ndcg_at_k_binary_vs_key_top100"] for e in every]),
                "note": "q03 counted at its measured 0: a lower bound, because part of that 0 is a tie-truncation artifact (see tie_check)"}}
    return {"environment": "LOCAL-LOOPBACK graph mode (local S export run:ba7402d1-959a-4277-8c6e-e92878a38afa; no vectors in this stack)", "per_run_summary": summary, "per_question": per_question,
            "interpretation_limit": "7 ranking questions (3 coauthor_breadth, 1 max_team_size with a ranked key, 3 bridge) x 2 runs, of which 6 are scorable. For q03 (max_team_size) all 100 key entries "
                                    "tie at the same value (15) and the key keeps the first 100 by id order, so a tied researcher outside those 100 scores 0 although it ties. q03 is listed per "
                                    "question and excluded from the main aggregates; a second aggregate counts it at its measured 0 (a lower bound). The tie premise is tested in tie_check from "
                                    "the values the answer states for the three retrieved researchers outside the key (those values were checked against the export by the Q12 scorer; this script "
                                    "does not read the export): one states 15 (a tie cut off by the key's 100-entry limit), one states 14 (below the key's value, so genuinely not a top-ranked "
                                    "researcher for this measure), and for one no value is stated (the answer lists 2 of the 3 retrieved). So the 0 is only partly an artifact of the tie truncation. "
                                    "The same truncation can affect a few tied items at the foot of the other keys. The two runs retrieved identical lists (observed), so they are not independent samples and no confidence interval is given (n = 7 questions would make one meaningless). The key's top-100 "
                                    "is the corpus-wide ranking while the runtime ranks inside its bounded artifact, so P@K against the key's top-100 is a looser test than against its top-K. "
                                    "Graded gain = the key's metric value, a derived grade, not a human relevance judgement. K is the runtime's own context cut (3 or 4 researcher items), so "
                                    "recall@K against the 100-item key is not reported (it would be at most K/100 by construction)."}


def q12_scorer(inputs):
    out = {}
    for run in Q12_RUNS:
        rel = pick(SCORES, run)
        inputs["q12 scorer output %s" % run] = sha256_file(path_of(rel))
        d = read_json(rel)
        types = collections.OrderedDict()
        failing = []
        cited = resolved = 0
        for q in d["questions"]:
            expected_answer = q["expected_outcome"] == "answer"
            t = types.setdefault(q["type"], {"questions_answer_expected": 0, "retrieval_pass": 0})
            if expected_answer:
                t["questions_answer_expected"] += 1
                t["retrieval_pass"] += 1 if q["retrieval"].get("pass") else 0
                cited += q["retrieval"].get("cited") or 0
                resolved += q["retrieval"].get("resolved") or 0
                if not q["retrieval"].get("pass"):
                    failing.append({"qid": q["id"], "type": q["type"], "outcome_kind": q["outcome_kind"], "http_status": q["http_status"],
                                    "first_retrieval_reason": (q["retrieval"].get("reasons") or [None])[0]})
        rows = []
        for t, v in sorted(types.items()):
            if v["questions_answer_expected"]:
                rows.append({"type": t, "answer_expected": v["questions_answer_expected"], "retrieval_pass": v["retrieval_pass"],
                             "rate": round(v["retrieval_pass"] / v["questions_answer_expected"], 4), "wilson_95": wilson(v["retrieval_pass"], v["questions_answer_expected"])})
        total_n = sum(r["answer_expected"] for r in rows)
        total_k = sum(r["retrieval_pass"] for r in rows)
        out[run] = {"scorer_key_sha256": d["key_sha256"], "export_run_id": d["export_run_id"], "deep_checks": d["deep_checks"], "per_type": rows,
                    "answer_expected_total": {"n": total_n, "retrieval_pass": total_k, "rate": round(total_k / total_n, 4), "wilson_95": wilson(total_k, total_n)},
                    "citation_resolution": {"cited_evidence_items": cited, "resolved": resolved, "rate": round(resolved / cited, 4) if cited else None},
                    "failing_answer_expected_questions": failing}
    return {"definition": "experiments/scripts/q12_score.py, check (i): every cited evidence id that was fetched resolves, names the required entities, has the required kind and carries "
                          "correct values. A per-question pass/fail, not recall@K. Abstain-expected questions are excluded (retrieval is not applicable to them).",
            "environment": "LOCAL-LOOPBACK graph mode", "runs": out,
            "interpretation_limit": "3 questions per type: a Wilson interval on n = 3 spans most of [0, 1]; per-type rates are descriptive. The two runs differ in commit (ec675d5, then 827fcd5 "
                                    "after the Q12 service and planner fixes), so the change between them is a before/after of code, not run-to-run noise."}


def vector_smoke(inputs):
    qr = read_json(QUERY_REPORT)
    ing = read_json(INGEST_REPORT)
    inputs[QUERY_REPORT] = sha256_file(path_of(QUERY_REPORT))
    inputs[INGEST_REPORT] = sha256_file(path_of(INGEST_REPORT))
    matched = sum(1 for s in qr["samples"] if s["neighborMatched"])
    return {"environment": "AWS-S3VECTORS+VOYAGE (live, 2026-11-18; the stack and the index were destroyed afterwards)", "index_sizes_vectors": dict(sorted(ing["perIndex"].items())),
            "vectors_written": ing["written"], "embedding_model": qr["model"],
            "known_item_queries": len(qr["samples"]), "expected_neighbor_found": matched, "hit_rate": round(matched / len(qr["samples"]), 4), "wilson_95": wilson(matched, len(qr["samples"])),
            "pointers_verified": qr["verifiedPointers"], "all_samples_present": qr["allSamplesPresent"],
            "queries": [{"index": s["indexName"], "neighbor_matched": s["neighborMatched"], "verified_pointers": s["verifiedPointers"]} for s in qr["samples"]],
            "interpretation_limit": "Each query is the text of a vector that was stored, and 'neighborMatched' means the stored vector's key was among the top-K hits (K is not in the committed "
                                    "report). It shows that ingest, embedding and query agree end to end (known-item round trip). It is NOT recall on novel questions and gives no precision, "
                                    "MRR or nDCG: n = 5, one query per index."}


def loadgen_record_fields():
    """The keys of the per-request record literal in load-tests/loadgen.py (read from the committed source, not from the git-ignored raw)."""
    text = "\n".join(read_lines(LOADGEN))
    block = re.search(r"record = \{(.*?)\n        \}", text, re.S)
    if not block:
        raise Refused("the request record literal was not found in " + LOADGEN)
    return sorted(set(re.findall(r'"(\w+)":', block.group(1))))


def semantic_questions(inputs):
    lines = [l for l in read_lines(QUESTIONS_15B) if l.strip()]
    inputs[QUESTIONS_15B] = sha256_file(path_of(QUESTIONS_15B))
    prov = read_json(QUESTIONS_15B_PROV)
    inputs[QUESTIONS_15B_PROV] = sha256_file(path_of(QUESTIONS_15B_PROV))
    out = {"questions": len(lines), "provenance_sha256_of_questions": prov.get("questions_sha256") or (prov.get("outputs") or {}).get("semantic-questions.txt", {}).get("sha256"),
           "relevance_labels": "none: the file is one topic phrase per line, derived from DBLP title n-gram document frequency; no phrase is paired with a relevant document",
           "ranked_results_recorded_in_load_raw": None}
    fields = loadgen_record_fields()
    inputs[LOADGEN] = sha256_file(path_of(LOADGEN))
    out.update({"load_run": "15b-ecs-scaling-semantic-rb-20261118 (AWS ECS, 2026-11-18), written by load-tests/loadgen.py", "fields_recorded_per_request_by_loadgen": fields,
                "ranked_results_recorded_in_load_raw": any(k in fields for k in ("hits", "body", "results", "neighbors")),
                "source_of_field_list": LOADGEN + " (the request record literal, plus route-specific extras such as question_index added by record.update(fields); no response body, hit list or score is among them)"})
    return out


def build():
    inputs = {}
    ranking = q12_ranking(inputs)
    scorer = q12_scorer(inputs)
    vectors = vector_smoke(inputs)
    semantic = semantic_questions(inputs)
    return {
        "schema": SCHEMA, "scope": "offline recomputation from raw evidence; no network, AWS, model call or spend", "inputs_sha256": dict(sorted(inputs.items())),
        "metric_definitions": {"precision_at_k": "hits in the first K / K", "recall_at_k": "hits in the first K / relevant", "reciprocal_rank": "1 / rank of the first relevant item, 0 if none",
                               "ndcg_at_k": "DCG(retrieved)/DCG(ideal), DCG = sum gain_i / log2(i + 1), ideal = the K largest labelled gains; null when the ideal is 0"},
        "graph_mode_ranking_retrieval": ranking, "q12_scorer_retrieval_pass_rates": scorer, "s3_vectors_known_item_smoke": vectors, "semantic_load_questions": semantic,
        "mode_comparison": {"graph_only": "measured on the Q12 ranking questions above (7 questions, labelled by the answer key)",
                            "vector_only": "GAP", "fused": "GAP",
                            "reason": "No labelled vector-only or fused retrieval run exists. The Q12 benchmark ran the local graph stack only (the answer-key rule: the local stack has no vectors). The "
                                      "15B load asked 150 unlabelled topic phrases of /v1/semantic/retrieve and stored only status, size and latency (no ranked results). The 16B evaluation "
                                      "(run 16b-1, 40 questions) stored 40 ungraded answers and its manifest lists the retrieval modes to compare as an open item. The AWS stack that held the "
                                      "vector index was destroyed on 2026-11-18, so a labelled vector run cannot be added offline."},
        "gaps": [{"metric": "vector-only recall@K, precision@K, MRR, nDCG", "reason": "no relevance labels for any vector query and no stored ranked results; the index no longer exists"},
                 {"metric": "fused (graph + vector) retrieval metrics and the graph-only vs vector-only vs fused comparison", "reason": "no fused run was recorded; the stack was destroyed"},
                 {"metric": "graded nDCG from human relevance judgements", "reason": "no human graded labels exist; the graded nDCG above uses the answer key's metric value as the gain and is labelled as such"},
                 {"metric": "recall@K for direct-collaborator, community and path questions", "reason": "the answer's researcher list is cut by the context window (e.g. 1 of 25 coauthors listed) and the edge evidence carries no plain coauthor id field, "
                                                                                                          "so the retrieved set cannot be reconstructed from the stored raw; the scorer's pass/fail is the only measure"},
                 {"metric": "retrieval latency by stage", "reason": "only end-to-end latency and the S3 Vectors SDK call time (n = 5) were recorded; see the performance group"}],
        "threats_to_validity": ["The answer key is derived by the same repository (an independent Python port of the Spark metrics); it was reviewed, but it is not an external gold standard.",
                                "7 ranking questions and 33 questions in total: no per-type inference is possible, only descriptive rates.",
                                "The retrieval list order is taken to be the order of explain.body.evidenceIds (the runtime's own ranking); the order was not independently logged.",
                                "The Q12 questions were authored with the system's capabilities in mind (3 per type, thin-data topics deliberately included as abstention tests), so the pass rates measure "
                                "coverage of designed query types, not open-domain retrieval.",
                                "The vector smoke is a known-item test on the stored text itself and overstates retrieval quality for novel queries."]}


def md_table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]


def render_md(r):
    L = ["# Phase 16 group 3: retrieval", "",
         "Generated by `experiments/scripts/eval16_retrieval.py` from raw evidence (inputs and sha256 in `retrieval-metrics.json`). Measured facts in the tables; interpretation limits are "
         "stated under each table.", "", "## 1. Graph-mode ranking retrieval against the answer key (Q12, local)", "", r["graph_mode_ranking_retrieval"]["environment"], ""]
    rows = []
    for run, s in r["graph_mode_ranking_retrieval"]["per_run_summary"].items():
        for t, v in s["by_type"].items():
            rows.append([run, t, "%d (%d scorable)" % (v["questions"], v["scorable_questions"]), v["mean_precision_at_k_vs_key_top100"], v["mean_precision_at_k_vs_key_topk"], v["mrr_of_key_rank1"], v["mean_ndcg_at_k_graded"], v["mean_ndcg_at_k_binary"],
                         v["exact_order_matches"]])
        a2 = s["all_ranking_questions_including_tie_saturated_as_measured"]
        rows.append([run, "**all 7 incl. q03 at measured 0 (lower bound)**", a2["questions"], a2["mean_precision_at_k_vs_key_top100"], a2["mean_precision_at_k_vs_key_topk"], a2["mrr_of_key_rank1"], a2["mean_ndcg_at_k_graded"], a2["mean_ndcg_at_k_binary"], ""])
        a = s["all_ranking_questions"]
        rows.append([run, "**all scorable**", "%d (%d scorable)" % (a["questions"], a["scorable_questions"]), a["mean_precision_at_k_vs_key_top100"], a["mean_precision_at_k_vs_key_topk"], a["mrr_of_key_rank1"], a["mean_ndcg_at_k_graded"], a["mean_ndcg_at_k_binary"], ""])
    L += md_table(["run", "type", "questions", "P@K vs key top-100", "P@K vs key top-K", "MRR (key rank-1)", "nDCG@K graded", "nDCG@K binary", "exact order matches"], rows)
    L += ["", "Per question:", ""]
    L += md_table(["run", "qid", "type", "K", "retrieved (id suffix)", "key top-3 (id suffix)", "P@K top-100", "P@K top-K", "RR rank-1", "nDCG graded"],
                  [[e["run"], e["qid"], e["type"], e["k"], e.get("retrieved_researcher_suffixes"), e.get("key_top3_suffixes"), e.get("precision_at_k_vs_key_top100"), e.get("precision_at_k_vs_key_topk"),
                    e.get("reciprocal_rank_of_key_rank1"), "%s%s" % (e.get("ndcg_at_k_graded_by_key_value"), " (key saturated by ties: excluded from aggregates)" if e.get("key_saturated_by_ties") else "")] for e in r["graph_mode_ranking_retrieval"]["per_question"]])
    L += ["", "Interpretation limit: " + r["graph_mode_ranking_retrieval"]["interpretation_limit"], "", "## 2. Q12 scorer: retrieval pass rate per question type (answer-expected questions)", "",
          r["q12_scorer_retrieval_pass_rates"]["definition"], ""]
    rows = []
    for run, v in r["q12_scorer_retrieval_pass_rates"]["runs"].items():
        for t in v["per_type"]:
            rows.append([run, t["type"], "%d / %d" % (t["retrieval_pass"], t["answer_expected"]), t["rate"], t["wilson_95"]])
        a = v["answer_expected_total"]
        rows.append([run, "**all answer-expected**", "%d / %d" % (a["retrieval_pass"], a["n"]), a["rate"], a["wilson_95"]])
    L += md_table(["run", "type", "retrieval pass", "rate", "Wilson 95%"], rows)
    for run, v in r["q12_scorer_retrieval_pass_rates"]["runs"].items():
        c = v["citation_resolution"]
        L += ["", "%s: cited evidence items %d, resolved %d (rate %s). Failing answer-expected questions: %s" % (run, c["cited_evidence_items"], c["resolved"], c["rate"],
                                                                                                               "; ".join("%s %s (%s %s): %s" % (f["qid"], f["type"], f["outcome_kind"], f["http_status"], (f["first_retrieval_reason"] or "")[:90]) for f in v["failing_answer_expected_questions"]))]
    L += ["", "Interpretation limit: " + r["q12_scorer_retrieval_pass_rates"]["interpretation_limit"], "", "## 3. S3 Vectors known-item smoke", "", r["s3_vectors_known_item_smoke"]["environment"], ""]
    v = r["s3_vectors_known_item_smoke"]
    L += ["Index sizes (vectors): %s; model %s. Known-item queries %d, expected neighbour found %d (hit rate %s, Wilson 95%% %s); pointers verified %d." % (
        v["index_sizes_vectors"], v["embedding_model"], v["known_item_queries"], v["expected_neighbor_found"], v["hit_rate"], v["wilson_95"], v["pointers_verified"]), "",
          "Interpretation limit: " + v["interpretation_limit"], "", "## 4. Semantic load questions", ""]
    s = r["semantic_load_questions"]
    L += ["%d topic phrases (`%s`). Relevance labels: %s. Ranked results recorded in the load raw: %s (fields recorded per request: %s)." % (
        s["questions"], QUESTIONS_15B, s["relevance_labels"], s["ranked_results_recorded_in_load_raw"], s.get("fields_recorded_per_request_by_loadgen")), "", "## 5. Graph-only vs vector-only vs fused", ""]
    m = r["mode_comparison"]
    L += ["- graph-only: %s" % m["graph_only"], "- vector-only: **%s**" % m["vector_only"], "- fused: **%s**" % m["fused"], "", "Reason: " + m["reason"], "", "## 6. GAPs", ""]
    L += ["- **%s**: %s" % (g["metric"], g["reason"]) for g in r["gaps"]] + ["", "## 7. Threats to validity", ""] + ["- " + t for t in r["threats_to_validity"]]
    L += ["", "## 8. Metric definitions", ""] + ["- %s: %s" % (k, v2) for k, v2 in r["metric_definitions"].items()]
    L += ["", "## 9. Inputs (sha256)", ""] + ["- `%s` %s" % (k, h) for k, h in r["inputs_sha256"].items()]
    return "\n".join(L) + "\n"


def write(out_dir, name, text):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "experiments", "results", "phase16", "retrieval"))
    args = parser.parse_args(argv)
    try:
        result = build()
    except Unavailable as error:
        print("INPUTS-UNAVAILABLE: %s (git-ignored raw evidence or a committed record is missing; nothing written)" % error)
        return 3
    except Refused as error:
        print("REFUSED: %s" % error)
        return 1
    write(args.out_dir, "retrieval-metrics.json", json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    write(args.out_dir, "retrieval-metrics.md", render_md(result))
    print("WROTE %s (retrieval-metrics.json, retrieval-metrics.md)" % args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
