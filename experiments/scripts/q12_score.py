#!/usr/bin/env python3
"""Score the raw Q12 run (load-tests/evalq12.py) against the computed answer key (stdlib only; python3 -I; offline, no network).

  python3 -I experiments/scripts/q12_score.py --key experiments/inputs/q12/answer-key.json --raw target/experiment-runs/q12-benchmark-<run-id>/raw \\
      [--export-dir <spark export dir>] --out-json <scores.json> --out-md <scores.md>

Three scores per question, each pass/fail with the reasons recorded (nothing is guessed; a missing fetch is a failure, not a pass):
  (i)   retrieval   every evidence id cited by the answer's claims or by /v1/explain resolves through /v1/evidence/{id}; the evidence names the
                    entities the key requires and has the evidence kind the key requires; every cited value that the key (always) or the export
                    (with --export-dir: distinct coauthors, weighted degree, component and community ids, bridge measures, team sizes,
                    coauthor lists, path edges, community members, temporal deltas) can check is correct.
  (ii)  claims      counts attempted / verified / rejected from /v1/explain; passes when at least one claim was attempted, none was rejected, all
                    attempted claims verified, and every verified claim's values match the key or the export.
  (iii) text        the answer prose (summary and uncertainty) contains the key facts: numbers, names and, for paths, the hop count and the
                    interior names of a shortest path; for ranking questions the name and value of the rank-1 cited researcher.
Abstention is correct ONLY where the key says abstain (topic and institution questions on this thin-data export): then retrieval is not
applicable, the claims score requires that no ranking claim was verified, and the text score requires an abstention (an ABSTAINED outcome,
an insufficient-evidence summary or an HTTP 4xx refusal). Where the key says answer, an abstention fails all three scores.
Ranking questions: the runtime ranks only the researchers inside its bounded artifact, so agreement with the corpus-wide top is reported as
information (corpus_top1_agrees) and never decides pass or fail; every cited value and the descending order are checked.
Exit codes: 0 scored (the exit code does not depend on the scores), 1 refused (unreadable input), 2 usage.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = "scholarchain.q12-scores.v1"
WORDS = {1: ("one", "direct", "directly", "single"), 2: ("two",), 3: ("three",), 4: ("four",), 5: ("five",), 6: ("six",)}
ABSTAIN_TEXT = re.compile(r"insufficient|cannot be answered|can(?:no|')t answer|unable to|not enough|no verified|not (?:available|supported|stored)|abstain|unsupported", re.I)
NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")
HOMONYM = re.compile(r"\s+\d{4}$")


def load_graph():
    spec = importlib.util.spec_from_file_location("q12_graph_for_score", os.path.join(HERE, "q12_graph.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_rows(raw_dir):
    path = os.path.join(raw_dir, "answers.jsonl")
    rows = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                rows[row.get("qid")] = row
    return rows


# evidence normalisation ------------------------------------------------------------------------------------------------------------
def to_number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def flatten(item):
    """(kind, subjects, windows, {field: value}) of an /v1/evidence/{id} body (or a pseudo-item built from a claim)."""
    content = item.get("supportingContent") or {}
    fields = {}
    for value in content.get("values") or []:
        name = value.get("field")
        if value.get("number") is not None:
            fields[name] = to_number(value["number"])
        elif value.get("text") is not None:
            fields[name] = value["text"]
        elif value.get("ids") is not None:
            fields[name] = list(value["ids"])
        elif value.get("flag") is not None:
            fields[name] = bool(value["flag"])
    kind = fields.get("kind", "")
    return kind, list(content.get("subjectIds") or []), list(content.get("windowIds") or []), fields


def same(a, b, tol=1e-9):
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(float(a) - float(b)) <= tol
    return a == b


class Deep:
    """Checks cited values against the export (optional)."""

    def __init__(self, g, export):
        self.g, self.ex = g, export
        self.sizes = g.team_sizes(export)
        self.max_all = max(self.sizes.values()) - 1

    def check(self, kind, subjects, windows, f):
        """Returns a list of mismatch strings for the fields this kind can verify."""
        g, ex = self.g, self.ex
        out = []
        window = windows[0] if windows else "all-years"
        if window not in g.WINDOWS:
            return ["unknown window %s" % window]
        wg = ex.window(window)
        subject = subjects[0] if subjects else None
        if kind in ("ranking", "metrics", "bridge") and subject:
            if subject not in wg.adj:
                return ["%s has no edge in %s" % (subject, window)]
            if "distinctCoauthorCount" in f and not same(f["distinctCoauthorCount"], wg.degree(subject)):
                out.append("distinctCoauthorCount %s != %s" % (f["distinctCoauthorCount"], wg.degree(subject)))
            if "weightedDegree" in f and not same(f["weightedDegree"], sum(wg.adj[subject].values())):
                out.append("weightedDegree %s != %s" % (f["weightedDegree"], sum(wg.adj[subject].values())))
            if "componentId" in f and f["componentId"] != g.analytics_id("component", window, wg.components()[0][subject]):
                out.append("componentId differs from the export component of %s in %s" % (subject, window))
            if "communityId" in f and f["communityId"] != g.analytics_id("community", window, wg.communities()[0][subject]):
                out.append("communityId differs from the ported community of %s in %s" % (subject, window))
            if "maximumCoauthorsOnOnePaper" in f:
                best, _ = g.max_team(ex, subject, self.sizes)
                value = f["maximumCoauthorsOnOnePaper"]
                if window == "all-years" and not same(value, best):
                    out.append("maximumCoauthorsOnOnePaper %s != %s" % (value, best))
                if window != "all-years" and value > best:
                    out.append("windowed maximumCoauthorsOnOnePaper %s exceeds the all-years maximum %s" % (value, best))
                for work in f.get("maxTeamWorkIds") or []:
                    if subject not in ex.authored.get(work, ()) or self.sizes.get(work, 0) - 1 != value:
                        out.append("max-team work %s is not a %s-coauthor work of the researcher" % (work, int(value)))
            if "publicationCount" in f and window == "all-years" and not same(f["publicationCount"], len(ex.authored_by.get(subject, ()))):
                out.append("publicationCount %s != %s" % (f["publicationCount"], len(ex.authored_by.get(subject, ()))))
            if kind == "bridge":
                bridge = wg.bridges()[subject]
                for name in ("crossCommunityDegree", "crossCommunityWeight", "communitiesConnected", "participationCoefficient"):
                    if name in f and not same(f[name], bridge[name], 1e-6):
                        out.append("%s %s != %s" % (name, f[name], bridge[name]))
        elif kind == "direct-coauthors" and subject:
            adj = wg.adj.get(subject, {})
            ids = f.get("coauthorIds") or []
            extra = [x for x in ids if x not in adj]
            if extra:
                out.append("%d cited coauthors are not coauthors of the researcher in %s" % (len(extra), window))
            if "returnedCount" in f and not same(f["returnedCount"], len(ids)):
                out.append("returnedCount %s != number of coauthorIds %d" % (f["returnedCount"], len(ids)))
            if len(ids) < min(len(adj), 25):
                out.append("page holds %d coauthors, expected %d" % (len(ids), min(len(adj), 25)))
        elif kind == "edge":
            a, b = f.get("researcherA"), f.get("researcherB")
            if wg.joint(a, b) == 0:
                out.append("no coauthor edge between the cited researchers in %s" % window)
            else:
                if "jointPublicationCount" in f and not same(f["jointPublicationCount"], wg.joint(a, b)):
                    out.append("jointPublicationCount %s != %s" % (f["jointPublicationCount"], wg.joint(a, b)))
                if len(f.get("workIds") or []) != wg.joint(a, b):
                    out.append("workIds count %d != joint publications %d" % (len(f.get("workIds") or []), wg.joint(a, b)))
        elif kind == "path":
            status = f.get("pathStatus")
            if status == "Found":
                path = f.get("orderedResearcherIds") or []
                bad = [(x, y) for x, y in zip(path, path[1:]) if wg.joint(x, y) == 0]
                if bad:
                    out.append("path has %d hops that are not coauthor edges in %s" % (len(bad), window))
                if "hopCount" in f and not same(f["hopCount"], len(path) - 1):
                    out.append("hopCount %s != %d" % (f["hopCount"], len(path) - 1))
                if path and wg.bfs(path[0], len(path) - 1)[0].get(path[-1]) != len(path) - 1:
                    out.append("cited path of %d hops is not a shortest path" % (len(path) - 1))
            elif status == "Disconnected" and len(subjects) == 2:
                label_of = wg.components()[0]
                if label_of.get(subjects[0]) == label_of.get(subjects[1]) and subjects[0] in label_of:
                    out.append("Disconnected, but both researchers share a component in %s" % window)
        elif kind == "community" and subject:
            label = wg.communities()[0].get(subject)
            if label is None:
                return ["%s has no community in %s" % (subject, window)]
            members = wg.community_members()[label]
            if "communityId" in f and f["communityId"] != g.analytics_id("community", window, label):
                out.append("communityId differs from the ported community")
            if "size" in f and not same(f["size"], len(members)):
                out.append("community size %s != %d" % (f["size"], len(members)))
            if set(f.get("selectedMemberIds") or []) - set(members):
                out.append("selectedMemberIds are not all members of the community")
        return out


# per-type key checks (always available) --------------------------------------------------------------------------------------------
def key_check(q, items):
    """Mismatches between cited evidence and the values recorded in the key for this question."""
    exp, kind, out = q["expected"], q["type"], []
    seen = [flatten(i) for i in items if i]
    if kind == "component":
        r = exp["researcher"]["id"]
        found = [f for k, s, w, f in seen if k == "metrics" and r in s and w[:1] == [exp["window"]] and "componentId" in f]
        if not found:
            out.append("no metrics evidence with a componentId for the researcher in %s" % exp["window"])
        elif any(f["componentId"] != exp["component_id"] for f in found):
            out.append("componentId differs from the key component %s" % exp["component_id"][:20])
    elif kind == "community":
        r = exp["researcher"]["id"]
        found = [f for k, s, w, f in seen if k == "community" and r in s]
        if not found:
            out.append("no community evidence for the researcher")
        for f in found:
            if f.get("communityId") != exp["community_id"]:
                out.append("communityId differs from the key community")
            if not same(f.get("size"), exp["size"]):
                out.append("community size %s != key %d" % (f.get("size"), exp["size"]))
            if set(f.get("selectedMemberIds") or []) - set(exp["members"]):
                out.append("selectedMemberIds are not all key members")
            if set(f.get("neighborCommunityIds") or []) - set(exp["neighbor_community_ids"]):
                out.append("neighborCommunityIds are not all key neighbour communities")
    elif kind == "temporal":
        r = exp["researcher"]["id"]
        found = [f for k, s, w, f in seen if k == "temporal" and r in s]
        if not found:
            out.append("no temporal evidence for the researcher")
        for f in found:
            for name in ("deltaDistinctCoauthors", "deltaComponentSize", "deltaCrossCommunityDegree", "deltaCrossCommunityWeight",
                         "deltaCommunitiesConnected", "communityJaccardOverlap", "deltaParticipationCoefficient"):
                if name in f and not same(f[name], exp[name], 1e-6):
                    out.append("%s %s != key %s" % (name, f[name], exp[name]))
            for name in ("previousCommunityId", "currentCommunityId", "enteredLargestComponent", "leftLargestComponent", "fromPresent", "toPresent"):
                if name in f and f[name] != exp[name]:
                    out.append("%s %s != key %s" % (name, f[name], exp[name]))
    elif kind == "direct_collab":
        r = exp["researcher"]["id"]
        ids = {c["id"] for c in exp["coauthors"]}
        found = [f for k, s, w, f in seen if k == "direct-coauthors" and r in s]
        if not found:
            out.append("no direct-coauthors evidence for the researcher")
        for f in found:
            if set(f.get("coauthorIds") or []) - ids:
                out.append("cited coauthors outside the key coauthor list")
            if len(f.get("coauthorIds") or []) < min(exp["total"], exp["page_limit"]):
                out.append("only %d of the %d expected page entries" % (len(f.get("coauthorIds") or []), min(exp["total"], exp["page_limit"])))
    elif kind == "shortest_path":
        a, b = exp["a"]["id"], exp["b"]["id"]
        found = [f for k, s, w, f in seen if k == "path" and a in s and b in s]
        good = [f for f in found if f.get("pathStatus") == "Found"]
        if not good:
            out.append("no Found path evidence between the two researchers")
        for f in good:
            path = f.get("orderedResearcherIds") or []
            if len(path) - 1 != exp["hops"] or path[0] != a or path[-1] != b:
                out.append("path %d hops from %s to %s, key says %d hops" % (len(path) - 1, path[:1], path[-1:], exp["hops"]))
    elif kind in ("coauthor_breadth", "bridge", "max_team_size") and "top" in exp:
        table = {e["id"]: e["value"] for e in exp["top"]}
        field = {"coauthor_breadth": "distinctCoauthorCount", "bridge": "crossCommunityDegree", "max_team_size": "maximumCoauthorsOnOnePaper"}[kind]
        ranked = []
        for k, s, w, f in seen:
            if k in ("ranking", "bridge") and s:
                if s[0] in table and field in f and not same(f[field], table[s[0]]):
                    out.append("%s of %s is %s, key says %s" % (field, s[0][-8:], f[field], table[s[0]]))
                if "rank" in f and "rankingValue" in f:
                    ranked.append((f["rank"], f["rankingValue"], s[0]))
        ranked.sort()
        for (r1, v1, i1), (r2, v2, i2) in zip(ranked, ranked[1:]):
            if v2 > v1 or (v2 == v1 and i2 < i1):
                out.append("ranking order broken between rank %d and %d" % (r1, r2))
                break
        if not ranked:
            out.append("no ranking evidence with rank and rankingValue")
    elif kind == "max_team_size":
        for k, s, w, f in seen:
            if k == "ranking" and "maximumCoauthorsOnOnePaper" in f and f["maximumCoauthorsOnOnePaper"] > exp["global_maximum_all_years"]:
                out.append("a windowed team size exceeds the all-years maximum")
    elif kind == "evidence":
        r = exp["researcher"]["id"]
        if not any(r in s for k, s, w, f in seen):
            out.append("no evidence item names the researcher")
        for k, s, w, f in seen:
            if r in s and "distinctCoauthorCount" in f and not same(f["distinctCoauthorCount"], exp["distinctCoauthorCount"]):
                out.append("distinctCoauthorCount %s != key %s" % (f["distinctCoauthorCount"], exp["distinctCoauthorCount"]))
            if r in s and "publicationCount" in f and not same(f["publicationCount"], exp["publicationCount"]):
                out.append("publicationCount %s != key %s" % (f["publicationCount"], exp["publicationCount"]))
    return out


# text checks -----------------------------------------------------------------------------------------------------------------------
def answer_text(body):
    answer = (body or {}).get("answer") if isinstance(body, dict) else None
    if not isinstance(answer, dict):
        return ""
    parts = [answer.get("summary"), answer.get("uncertainty")]
    return " ".join(p if isinstance(p, str) else json.dumps(p, sort_keys=True) for p in parts if p)


def numbers_in(text):
    found = set()
    for raw in NUMBER.findall(text):
        value = to_number(raw.replace(",", ""))
        if value is not None:
            found.add(value)
    return found


def has_name(text, name):
    low = text.casefold()
    return name.casefold() in low or HOMONYM.sub("", name).casefold() in low


def text_check(q, body, ranking_first):
    req, text = q.get("required_text") or {}, answer_text(body)
    out = []
    if not text:
        return ["the answer has no summary text"]
    nums = numbers_in(text)
    for group in ([] if q["type"] == "shortest_path" else req.get("numbers") or []):   # a path's hop count is checked below, digits or words
        if not any(all(float(n) in nums for n in alt) for alt in group):
            out.append("none of the number alternatives %s appears" % json.dumps(group))
    for name in req.get("names") or []:
        if not has_name(text, name):
            out.append("the name %r does not appear" % name)
    if q["type"] == "shortest_path":
        hops = q["expected"]["hops"]
        low = text.casefold()
        if not any(re.search(r"\b%s\b" % re.escape(w), low) for w in WORDS.get(hops, ())) and float(hops) not in nums:
            out.append("the hop count %d is not stated" % hops)
        if hops >= 2 and not any(all(has_name(text, n) for n in names) for names in req.get("path_names_any_of") or []):
            out.append("no shortest path's interior names all appear")
    if q["type"] == "direct_collab":
        shown = req.get("coauthor_names_expected", 0)
        exp = q["expected"]
        names = [c["name"] for c in exp["coauthors"]][:max(shown, 0)]
        if shown and not exp["truncated"]:
            hit = sum(1 for n in names if has_name(text, n))
            if hit < req.get("coauthor_name_recall_min", 0.6) * shown:
                out.append("only %d of %d coauthor names appear" % (hit, shown))
    if req.get("mode") == "ranking":
        if not ranking_first:
            out.append("no rank-1 cited researcher to compare the text with")
        else:
            name, value = ranking_first
            if name and not has_name(text, name):
                out.append("the rank-1 cited researcher %r does not appear" % name)
            if value is not None and float(value) not in nums:
                out.append("the rank-1 value %s does not appear" % value)
    return out


# one question ---------------------------------------------------------------------------------------------------------------------
def classify(row):
    if row is None:
        return "missing"
    status = row.get("status")
    body = row.get("answer")
    explain = (row.get("explain") or {}).get("body") or {}
    if not isinstance(status, int) or status >= 500 or status == 0:
        return "error"
    if 400 <= status < 500:
        return "refused"
    outcome = str(explain.get("outcome", "")).upper()
    verification = str(explain.get("verificationStatus", "")).upper()
    summary = ((body or {}).get("answer") or {}).get("summary", "") if isinstance(body, dict) else ""
    if outcome == "ABSTAINED" or verification == "ABSTAINED" or (isinstance(summary, str) and re.search(r"insufficient verified evidence", summary, re.I)):
        return "abstained"
    if row.get("job_state") not in (None, "SUCCEEDED", "SUCCESS", "COMPLETED", "DONE"):
        return "error"
    return "answered"


def verified_ids(explain):
    out = set()
    for c in explain.get("verification") or []:
        if str(c.get("verdict", "")).upper() == "VERIFIED":
            out.add(c.get("claimId"))
    return out


def score_question(q, row, deep):
    kind = classify(row)
    result = {"id": q["id"], "type": q["type"], "question": q["question"], "check_level": q["check_level"], "expected_outcome": q["expected_outcome"],
              "outcome_kind": kind, "http_status": (row or {}).get("status"), "retrieval": {}, "claims": {}, "text": {}}
    if row is None:
        for part in ("retrieval", "claims", "text"):
            result[part] = {"pass": False, "reasons": ["the question was not asked"]}
        result["pass"] = False
        return result
    if row.get("question") != q["question"]:
        for part in ("retrieval", "claims", "text"):
            result[part] = {"pass": False, "reasons": ["the asked question text differs from the key question"]}
        result["pass"] = False
        return result
    body = row.get("answer")
    explain = (row.get("explain") or {}).get("body") or {}
    counters = explain.get("counters") or {}
    attempted, verified, rejected = counters.get("attemptedClaims"), counters.get("verifiedClaims"), counters.get("rejectedClaims")
    claims = (body or {}).get("claims") if isinstance(body, dict) else []
    claims = claims if isinstance(claims, list) else []
    evidence = row.get("evidence") or {}
    cited = sorted({e for c in claims for e in c.get("evidenceIds") or []} | set(explain.get("evidenceIds") or []))
    resolved = {}
    for eid in cited:
        entry = evidence.get(eid) or {}
        item = entry.get("item")
        if entry.get("status") == 200 and isinstance(item, dict) and item.get("evidenceId") == eid:
            resolved[eid] = item
    result["claims"] = {"attempted": attempted, "verified": verified, "rejected": rejected, "answer_claims": len(claims),
                        "verification_status": explain.get("verificationStatus"), "outcome": explain.get("outcome")}
    if q["expected_outcome"] == "abstain":
        ranking_verified = [c for c in claims if (c.get("runtime") or {}).get("claimType") in ("RANKING", "BRIDGE") and c.get("claimId") in verified_ids(explain)]
        result["retrieval"] = {"pass": True, "applicable": False, "reasons": ["not applicable: the key expects an abstention"]}
        ok_claims = kind in ("abstained", "refused") and not ranking_verified
        result["claims"]["pass"] = ok_claims
        result["claims"]["reasons"] = [] if ok_claims else ["a ranking claim was verified or the system answered where the key expects an abstention"]
        text = answer_text(body)
        is_abstention = kind in ("abstained", "refused") and (kind == "refused" or kind == "abstained" or bool(ABSTAIN_TEXT.search(text)))
        result["text"] = {"pass": is_abstention, "reasons": [] if is_abstention else ["not an abstention (outcome kind %s)" % kind],
                          "abstention_kind": "refused-4xx" if kind == "refused" else ("verified-abstention" if kind == "abstained" else None)}
        result["pass"] = result["claims"]["pass"] and result["text"]["pass"]
        return result
    # expected answer ---------------------------------------------------------------------------------------------------------------
    reasons = []
    if kind != "answered":
        reasons.append("the system did not answer (outcome kind %s)" % kind)
    unresolved = [e for e in cited if e not in resolved]
    if not cited:
        reasons.append("no evidence cited")
    if unresolved:
        reasons.append("%d of %d cited evidence ids do not resolve" % (len(unresolved), len(cited)))
    items = list(resolved.values())
    req = q.get("required_evidence") or {}
    flat = [flatten(i) for i in items]
    subjects = {s for k, ss, w, f in flat for s in ss}
    for s in req.get("subjects") or []:
        if s not in subjects:
            reasons.append("required entity %s is not named by any cited evidence" % s[-12:])
    kinds = {k for k, ss, w, f in flat}
    needed = req.get("kinds") or []
    if needed and not (kinds & set(needed)):
        reasons.append("no cited evidence of kind %s (found %s)" % (needed, sorted(kinds)))
    reasons += key_check(q, items)
    deep_mismatch, deep_checked = [], 0
    if deep:
        for k, ss, w, f in flat:
            if k:
                deep_checked += 1
                deep_mismatch += deep.check(k, ss, w, f)
    reasons += deep_mismatch
    result["retrieval"] = {"pass": not reasons, "cited": len(cited), "resolved": len(resolved), "kinds": sorted(kinds), "deep_checked_items": deep_checked if deep else None,
                           "deep": "export" if deep else "skipped (no --export-dir)", "reasons": reasons[:12], "reason_count": len(reasons)}
    # claims
    creasons = []
    if attempted is None:
        creasons.append("/v1/explain gave no claim counters")
    else:
        if attempted < 1:
            creasons.append("no claim attempted")
        if rejected:
            creasons.append("%d claims rejected" % rejected)
        if verified != attempted:
            creasons.append("verified %s of %s attempted" % (verified, attempted))
    vids = verified_ids(explain)
    mismatches = 0
    by_id = {c.get("claimId"): c for c in claims}
    for cid in vids:
        claim = by_id.get(cid)
        if not claim:
            continue
        rt = claim.get("runtime") or {}
        eids = claim.get("evidenceIds") or []
        base = next((resolved[e] for e in eids if e in resolved), None)
        if base is None:
            creasons.append("verified claim %s cites no resolvable evidence" % cid)
            mismatches += 1
            continue
        k0, s0, w0, f0 = flatten(base)
        values = {}
        for v in rt.get("values") or []:
            val = to_number(v["number"]) if v.get("number") is not None else v.get("text", v.get("ids", v.get("flag")))
            values[v["field"]] = val
        subj = rt.get("subjectIds") or s0
        pseudo = {"supportingContent": {"subjectIds": subj, "windowIds": w0, "values": rt.get("values") or []}}
        pseudo["supportingContent"]["values"] = [{"field": "kind", "text": k0}] + [v for v in rt.get("values") or [] if v.get("field") != "kind"]
        bad = [m for m in key_check(q, [pseudo]) if not m.startswith("no ")] if q["type"] != "evidence" else []
        if deep and k0:
            pk, ps, pw, pf = flatten(pseudo)
            bad += deep.check(pk, ps, pw, pf)
        # a claim only restates values of its evidence: every claim value must equal the evidence value
        for name, val in values.items():
            if name in f0 and not same(val, f0[name], 1e-9) and not isinstance(val, (list, bool)) and val != f0[name]:
                bad.append("claim %s value %s differs from its evidence %s" % (name, val, f0[name]))
        if bad:
            mismatches += 1
            creasons.append("verified claim %s: %s" % (cid, "; ".join(bad[:2])))
    result["claims"].update({"pass": not creasons, "verified_claims_checked": len(vids), "verified_claims_mismatching": mismatches, "reasons": creasons[:12]})
    # text
    first = None
    if q["type"] in ("coauthor_breadth", "max_team_size", "bridge"):
        best = None
        for k, ss, w, f in flat:
            if k in ("ranking", "bridge") and f.get("rank") is not None and ss and (best is None or f["rank"] < best[0]):
                best = (f["rank"], ss[0], f.get("rankingValue"))
        if best:
            name = None
            claim_names = {}
            for researcher in ((body or {}).get("answer") or {}).get("researchers") or []:
                claim_names[researcher.get("researcherId")] = researcher.get("displayName")
            if deep:
                name = deep.ex.researchers.get(best[1], "").strip() or None
            name = name or claim_names.get(best[1])
            if not name:
                name = {e["id"]: e["name"] for e in (q["expected"].get("top") or [])}.get(best[1])
            first = (name, best[2])
        if first:
            ranking_info = {"rank1_id": best[1], "rank1_value": best[2]}
            top = (q["expected"].get("top") or [])
            if top:
                ranking_info["corpus_top1_agrees"] = top[0]["id"] == best[1]
            result["ranking"] = ranking_info
    treasons = [] if kind == "answered" else ["the system did not answer (outcome kind %s)" % kind]
    treasons += text_check(q, body, first)
    result["text"] = {"pass": not treasons, "reasons": treasons[:12], "chars": len(answer_text(body))}
    result["pass"] = result["retrieval"]["pass"] and result["claims"]["pass"] and result["text"]["pass"]
    return result


def summarize(results):
    types = {}
    for r in results:
        t = types.setdefault(r["type"], {"questions": 0, "retrieval_pass": 0, "claims_pass": 0, "text_pass": 0, "all_pass": 0, "abstained_or_refused": 0})
        t["questions"] += 1
        t["retrieval_pass"] += bool(r["retrieval"].get("pass"))
        t["claims_pass"] += bool(r["claims"].get("pass"))
        t["text_pass"] += bool(r["text"].get("pass"))
        t["all_pass"] += bool(r["pass"])
        t["abstained_or_refused"] += r["outcome_kind"] in ("abstained", "refused")
    total = {k: sum(t[k] for t in types.values()) for k in ("questions", "retrieval_pass", "claims_pass", "text_pass", "all_pass", "abstained_or_refused")}
    return dict(sorted(types.items())), total


def markdown(doc):
    lines = ["# Q12 benchmark scores", "", "Run `%s`, key `%s` (export run `%s`), deep checks: %s." % (doc["run_id"], doc["key_sha256"][:16], doc["export_run_id"], doc["deep_checks"]), "",
             "| id | type | level | outcome | retrieval | claims (a/v/r) | text | all | first failure |", "|---|---|---|---|---|---|---|---|---|"]
    for r in doc["questions"]:
        c = r["claims"]
        first = (r["retrieval"].get("reasons") or r["claims"].get("reasons") or r["text"].get("reasons") or [""])[0]
        lines.append("| %s | %s | %s | %s | %s | %s/%s/%s %s | %s | %s | %s |" % (
            r["id"], r["type"], r["check_level"], r["outcome_kind"], "pass" if r["retrieval"].get("pass") else "FAIL",
            c.get("attempted"), c.get("verified"), c.get("rejected"), "pass" if c.get("pass") else "FAIL",
            "pass" if r["text"].get("pass") else "FAIL", "pass" if r["pass"] else "FAIL", first.replace("|", "/")[:110]))
    lines += ["", "## Per type", "", "| type | questions | retrieval | claims | text | all pass | abstained/refused |", "|---|---|---|---|---|---|---|"]
    for name, t in doc["per_type"].items():
        lines.append("| %s | %d | %d | %d | %d | %d | %d |" % (name, t["questions"], t["retrieval_pass"], t["claims_pass"], t["text_pass"], t["all_pass"], t["abstained_or_refused"]))
    t = doc["totals"]
    lines += ["| **total** | %d | %d | %d | %d | %d | %d |" % (t["questions"], t["retrieval_pass"], t["claims_pass"], t["text_pass"], t["all_pass"], t["abstained_or_refused"]), ""]
    return "\n".join(lines) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--key", required=True)
    parser.add_argument("--raw", required=True, help="directory holding answers.jsonl (and run-record.json) of a load-tests/evalq12.py run")
    parser.add_argument("--export-dir", help="completed Phase 6 Spark export (read only): enables the deep value checks")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)
    g = load_graph()
    try:
        with open(args.key, encoding="utf-8") as handle:
            key = json.load(handle)
        rows = read_rows(args.raw)
        deep, export_run = None, key["source"]["run_id"]
        if args.export_dir:
            export = g.Export(args.export_dir)
            if export.run_id != key["source"]["run_id"]:
                print("SCORE-REFUSED: the export %s is not the run the key was computed from (%s)" % (export.run_id, key["source"]["run_id"]))
                return 1
            deep = Deep(g, export)
        record_path = os.path.join(args.raw, "run-record.json")
        run_id = json.load(open(record_path, encoding="utf-8")).get("run_id", "unknown") if os.path.isfile(record_path) else "unknown"
        results = [score_question(q, rows.get(q["id"]), deep) for q in key["questions"]]
    except (OSError, ValueError, KeyError, g.Refused) as error:
        print("SCORE-REFUSED: %s: %s" % (type(error).__name__, error))
        return 1
    per_type, totals = summarize(results)
    doc = {"schema": SCHEMA, "run_id": run_id, "key_sha256": g.sha256_file(args.key), "export_run_id": export_run,
           "deep_checks": "export" if deep else "skipped (no --export-dir)", "per_type": per_type, "totals": totals, "questions": results}
    with open(args.out_json, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    with open(args.out_md, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown(doc))
    print("SCORED questions=%d retrieval=%d claims=%d text=%d all=%d abstained_or_refused=%d deep_checks=%s" % (
        totals["questions"], totals["retrieval_pass"], totals["claims_pass"], totals["text_pass"], totals["all_pass"], totals["abstained_or_refused"], doc["deep_checks"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
