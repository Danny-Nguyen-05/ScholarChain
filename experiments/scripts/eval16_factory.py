#!/usr/bin/env python3
"""Phase 16, group 6 (agentic factory): count reviewer verdicts, findings, repair rounds, BLOCKED-ON reports, manual interventions and guard blocks from the
phase records (stdlib only; python3 -I; offline).

  python3 -I experiments/scripts/eval16_factory.py [--out-dir experiments/results/phase16/factory]

Sources: docs/agent-runs/phase-01 .. phase-15 {review,repairs,human-gate,owner-report,test-report}.md (committed) and, if present, the coordinator's
git-ignored notes target/phase15/session2/evidence/coordinator-notes.log (written to its own output files; when it is absent the committed-record outputs
are still written and the exit code is 3). Phase 16's own records are written after this evaluation and are deliberately not read.

Method: line-based heuristics with the documented regular expressions below. EVERY counted item is written with its source file and line number
(factory-items.json, factory-notes-items.json) so a reader can audit it; the per-phase table only sums those items. The records were written in different
formats in different phases (free prose, STATUS/VERDICT lines, tables), so the counts are approximations of what was written down, not a census of what
happened. Limitations are listed in the output. Exit codes: 0 done, 1 refused (a committed record is missing), 3 the local notes log is absent.
"""
import argparse
import collections
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMA = "scholarchain.eval16-factory.v1"
PHASES = tuple("%02d" % n for n in range(1, 16))
RECORDS = ("review", "repairs", "human-gate", "owner-report", "test-report")
NOTES = "target/phase15/session2/evidence/coordinator-notes.log"
NOTES_FROZEN_LINES = 199  # the log is append-only; the evaluation reads the first 199 lines (its state when Phase 16 started) so later notes do not change the tables
EXCERPT = 200

# ------------------------------------------------------------------------------------------------------------ documented regexes
VERDICT_TOKEN = re.compile(r"\b(APPROVE|REQUEST[-_ ]CHANGES|CHANGES[-_ ]REQUESTED|CHANGES[-_ ]REQUIRED)\b", re.I)
VERDICT_LABEL = re.compile(r"^[\s>*_#|\-]*\**\s*(?P<label>STATUS|[A-Za-z0-9 ,.]{0,40}verdict\b[^:\n]{0,50})\**\s*[:：]", re.I)
VERDICT_EXCLUDE = re.compile(r"supersede|remains unchanged|no new external verdict|no readiness review verdict|awaiting|pending|no new verdict|preparing", re.I)
FINDING = re.compile(r"^\s*(?:[-*]\s+|\d{1,3}[.)]\s+|#{2,4}\s+|\|\s*)?\**(?P<id>[A-Z]{1,2}\d{1,3}|Finding\s+\d{1,3})?\**[\s·—:–\-.()]*\**"
                     r"(?P<sev>Critical|Blocker|High|Medium-High|Low-Medium|Medium|Low|Info(?:rmational)?|Nit(?:pick)?|Major|Minor|P[0-3])\b")
BLOCKING = re.compile(r"\bblock(?:s|ing)\b", re.I)
NONBLOCKING = re.compile(r"non-?blocking", re.I)
ROLE = re.compile(r"\b([a-z]+(?:-[a-z]+)*-(?:engineer|reviewer|responder|updater))\b")
OWNER_FIELD = re.compile(r"^\**OWNER\**:\s*(.*)$")
STATUS_BLOCKED = re.compile(r"^\**STATUS\**:\s*\**BLOCKED-ON", re.I)
BLOCKED_OWNER = re.compile(r"^\**BLOCKED-ON OWNER\**:\s*(.*)$")
REPAIR_HEADING = re.compile(r"^#{2,4}\s+.*repair\s+round\s*\d*", re.I)
REPAIR_ANY = re.compile(r"^#{2,4}\s+.*repair", re.I)
HUMAN_QUOTE = re.compile(r"^>\s+\S")
HUMAN_DECISION_LINE = re.compile(r"^\**DECISION:|^\*\*DECISION", re.I)
MANUAL = re.compile(r"\bmanual(?:ly)?\s+(?:intervention|repair|fix|edit|override)\b", re.I)
MANUAL_FIELD = re.compile(r"^\**MANUAL ACTION REQUIRED\**:\s*(.*)$")
MANUAL_NONE = re.compile(r"^\W*(?:none|n/a|nothing)\b", re.I)
GUARD_BLOCK = re.compile(r"(?:pretooluse|project\W{0,3}s? guard|guard hook|\bhook\b)[^.\n]{0,100}\b(?:blocked|refused|rejected|denied|flagged)\b"
                         r"|\b(?:blocked|refused|rejected|denied|flagged)\b[^.\n]{0,60}\bby (?:the |a |an |our )?(?:project\W{0,3}s? )?(?:pretooluse|guard|hook)", re.I)
GUARD_FIXTURE = re.compile(r"\b(?:probe|fixture|test|self-test|synthetic)\b", re.I)
OWNERSHIP = re.compile(r"ownership (?:violation|collision)|outside (?:the |its |their |my )?(?:owner|territory|ownership|fence)|wrong owner", re.I)
NOTES_HUMAN = re.compile(r"HUMAN DECISION|USER \(verbatim\)|HUMAN \(chat\)|\bHUMAN:|USER:|Human decision", re.I)
NOTES_NEGATE = re.compile(r"\bafter (?:the )?reviewer\b", re.I)
NOTES_VERDICT = re.compile(r"\b(APPROVE|REQUEST-CHANGES|CHANGES-REQUIRED)\b")
SEVERITY_NORMAL = {"critical": "high", "blocker": "high", "high": "high", "p0": "high", "p1": "high", "major": "medium", "medium-high": "medium", "medium": "medium", "p2": "medium",
                   "low-medium": "low", "low": "low", "minor": "low", "p3": "low", "info": "info", "informational": "info", "nit": "info", "nitpick": "info"}
REDACT = [(re.compile(r"\b\d{12}\b"), "<12-digit>"), (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>")]


# Hand audit of one phase (written by the experiment-engineer by reading docs/agent-runs/phase-03/review.md; the parser's counted lines are checked against it in the tests).
HAND_AUDIT_PHASE_03 = {
    "phase": "03", "file": "docs/agent-runs/phase-03/review.md", "method": "read the whole file and listed every review event by hand",
    "hand_review_events": 14, "hand_request_changes_outcomes": 10, "hand_approve_outcomes": 4,
    "hand_listing": "numbered reviews 1-6 REQUEST_CHANGES (lines 3, 29, 47, 62, 79, 97); review 7 APPROVE (125); WorkRecord binding reviews: first REQUEST_CHANGES and second APPROVE, both in prose "
                    "without a STATUS line (139, 143); review 8 REQUEST_CHANGES (149); review 9 REQUEST_CHANGES (174); review 10 APPROVE (189); review 11 'STATUS: COMPLETE' whose body routes a fix "
                    "to dataset-engineer, i.e. changes required without a verdict token (201, 231); review 12 APPROVE (235)",
    "parser_counted": {"APPROVE": 3, "REQUEST-CHANGES": 8, "lines": [3, 29, 47, 62, 79, 97, 125, 149, 174, 189, 235]},
    "parser_missed": "3 of 14 events (lines 139, 143 and 201): the parser undercounts verdicts written in prose or under 'STATUS: COMPLETE'",
    "review_units_by_hand": 1, "review_units_by_parser": 1,
    "first_pass_by_hand": "not approved first time (review 1 REQUEST_CHANGES)", "first_pass_by_parser": "not approved first time (0 of 1)",
    "reading": "The first-pass result for phase 03 agrees; the verdict COUNT is 11 against 14 by hand",
    "also_checked_first_verdicts_of_phases": {"01": "CHANGES REQUESTED (line 3)", "02": "REQUEST-CHANGES (line 5)", "04": "REQUEST-CHANGES (line 3)"}}
FIRST_PASS_CAVEAT = ("Phases 01-04 have no subphases, so each is scored as ONE phase-wide unit (first verdict of the whole phase) while phases 05-15 are scored per subphase or work order; the 8 of 38 "
                     "first-pass rate therefore mixes two granularities (4 of the 38 units are whole phases, all of which were not approved first time; checked by hand for the first verdicts of "
                     "phases 01, 02, 03 and 04). The hand audit of phase 03 (hand_audit_phase_03) found the parser undercounts verdict events there (11 counted against 14 by hand) because some "
                     "verdicts are in prose or under 'STATUS: COMPLETE'; the first-pass result of that phase is the same either way. The rate is a heuristic over records, not a count of agent "
                     "attempts, and no per-agent rate can be derived (see gaps).")


class Refused(Exception):
    pass


def redact(text):
    for pattern, repl in REDACT:
        text = pattern.sub(repl, text)
    return text


def excerpt(text):
    return redact(re.sub(r"\s+", " ", text.strip())[:EXCERPT])


def around(pattern, line):
    """An excerpt centred on the first match of pattern (for long lines where the match is far from the start)."""
    m = pattern.search(line)
    if not m:
        return excerpt(line)
    return excerpt(line[max(0, m.start() - 90):m.end() + 90])


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify_verdict(token):
    t = re.sub(r"[_ ]", "-", token.upper())
    return t


def unit_from_text(text):
    m = re.search(r"\b(\d{1,2}[A-G])\b", text)
    if m:
        return m.group(1)
    m = re.search(r"Work order (\d+)", text, re.I)
    return "WO" + m.group(1) if m else None


# ----------------------------------------------------------------------------------------------------------------- line parsers
def parse_review(lines, phase, rel):
    """Verdict declarations, deduplicated footer restatements, and finding lines of one review.md."""
    verdicts, findings = [], []
    heading_unit = None
    last_kept = None
    for number, line in enumerate(lines, 1):
        if re.match(r"^#{1,4}\s", line):
            heading_unit = unit_from_text(line) or heading_unit
        label = VERDICT_LABEL.match(line)
        if label:
            rest = line[label.end():label.end() + 220]
            token = VERDICT_TOKEN.search(rest)
            if token:
                is_status = label.group("label").strip().upper() == "STATUS"
                cls = classify_verdict(token.group(1))
                entry = {"phase": phase, "file": rel, "line": number, "class": cls, "form": "STATUS" if is_status else "VERDICT", "unit": unit_from_text(line[:label.end() + 120]) or heading_unit or "-",
                         "text": excerpt(line), "counted": True, "reason": None, "paired": False}
                if VERDICT_EXCLUDE.search(line[:label.end() + token.end()]):
                    entry.update({"counted": False, "reason": "restates or defers a verdict (matched the exclusion pattern)"})
                elif (is_status and last_kept and last_kept["form"] == "VERDICT" and last_kept["class"] == cls and number - last_kept["line"] <= 150
                      and not last_kept.get("paired")):
                    last_kept["paired"] = True
                    entry.update({"counted": False, "reason": "footer restatement of the verdict on line %d" % last_kept["line"]})
                verdicts.append(entry)
                if entry["counted"]:
                    last_kept = entry
                continue
        f = FINDING.match(line)
        if f and (f.group("id") or re.match(r"^\s*(?:[-*]\s+|\d{1,3}[.)]\s+|#{2,4}\s+|\|\s*)", line)):
            sev = f.group("sev")
            owners = sorted(set(ROLE.findall(line)))
            blocking = bool(BLOCKING.search(line[:300])) and not NONBLOCKING.search(line[:300])
            findings.append({"phase": phase, "file": rel, "line": number, "id": f.group("id"), "unit": unit_from_text(line[:80]) or heading_unit or "-", "severity_as_written": sev,
                             "severity_normalized": SEVERITY_NORMAL[sev.lower()], "blocking_flag_in_line": blocking, "owners_named": owners, "text": excerpt(line)})
    return verdicts, findings


def parse_simple(lines, phase, rel, record):
    items = []
    for number, line in enumerate(lines, 1):
        m = OWNER_FIELD.match(line)
        if m and record in ("owner-report", "test-report"):
            roles = ROLE.findall(m.group(1))
            role = roles[0] if roles else ("coordinator" if re.match(r"\s*\(?coordinator", m.group(1), re.I) else "unnamed")
            items.append({"kind": "report", "role": role, "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        if STATUS_BLOCKED.match(line):
            items.append({"kind": "status_blocked_on", "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        m = BLOCKED_OWNER.match(line)
        if m:
            roles = ROLE.findall(m.group(1)) + (["coordinator"] if re.match(r"\s*(?:the )?coordinator\b", m.group(1), re.I) else [])
            if roles:
                items.append({"kind": "blocked_on_owner_named", "role": roles[0], "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        if record == "repairs" and REPAIR_HEADING.match(line):
            items.append({"kind": "repair_round_heading", "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        if record == "repairs" and REPAIR_ANY.match(line):
            items.append({"kind": "repair_heading_any", "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        if record == "human-gate" and (HUMAN_QUOTE.match(line) or HUMAN_DECISION_LINE.match(line)):
            items.append({"kind": "human_gate_quote_or_decision", "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        m = MANUAL_FIELD.match(line)
        if m:
            kind = "manual_action_field_none" if (not m.group(1).strip() or MANUAL_NONE.match(m.group(1))) else "manual_action_required"
            items.append({"kind": kind, "phase": phase, "file": rel, "line": number, "text": excerpt(line)})
        elif MANUAL.search(line):
            items.append({"kind": "manual_intervention_phrase", "phase": phase, "file": rel, "line": number, "text": around(MANUAL, line)})
        if GUARD_BLOCK.search(line):
            items.append({"kind": "guard_block", "fixture_or_test": bool(GUARD_FIXTURE.search(line)), "phase": phase, "file": rel, "line": number, "text": around(GUARD_BLOCK, line)})
        if OWNERSHIP.search(line):
            items.append({"kind": "ownership_phrase", "phase": phase, "file": rel, "line": number, "text": around(OWNERSHIP, line)})
    return items


def read_record(phase, record):
    rel = "docs/agent-runs/phase-%s/%s.md" % (phase, record)
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return rel, None
    with open(path, encoding="utf-8", errors="replace") as handle:
        return rel, handle.read().split("\n")


def first_pass(verdicts):
    """Per (phase, unit): the first counted verdict decides first-pass acceptance."""
    units = collections.OrderedDict()
    for v in verdicts:
        if not v["counted"]:
            continue
        units.setdefault((v["phase"], v["unit"]), v)
    return units


def build_committed():
    verdicts, findings, other, inputs, missing = [], [], [], {}, []
    for phase in PHASES:
        for record in RECORDS:
            rel, lines = read_record(phase, record)
            if lines is None:
                missing.append(rel)
                continue
            inputs[rel] = sha256_file(os.path.join(ROOT, rel))
            if record == "review":
                v, f = parse_review(lines, phase, rel)
                verdicts += v
                findings += f
            other += parse_simple(lines, phase, rel, record)
    units = first_pass(verdicts)
    per_phase = collections.OrderedDict()
    for phase in PHASES:
        pv = [v for v in verdicts if v["phase"] == phase and v["counted"]]
        pf = [f for f in findings if f["phase"] == phase]
        distinct = {}
        for f in pf:
            distinct.setdefault((f["unit"], f["id"] or "line%d" % f["line"]), f)
        po = [o for o in other if o["phase"] == phase]
        kinds = collections.Counter(o["kind"] for o in po)
        pu = [(k, v) for k, v in units.items() if k[0] == phase]
        per_phase[phase] = {
            "verdicts": dict(sorted(collections.Counter(v["class"] for v in pv).items())), "verdict_lines_counted": len(pv),
            "verdict_lines_excluded_as_restatements": sum(1 for v in verdicts if v["phase"] == phase and not v["counted"]),
            "review_units": len(pu), "first_pass_approved_units": sum(1 for _, v in pu if v["class"] == "APPROVE"),
            "first_pass_rate": round(sum(1 for _, v in pu if v["class"] == "APPROVE") / len(pu), 3) if pu else None,
            "finding_lines": len(pf), "findings_distinct_by_unit_and_id": len(distinct),
            "findings_by_severity_as_written": dict(sorted(collections.Counter(f["severity_as_written"] for f in pf).items())),
            "findings_by_severity_normalized": dict(sorted(collections.Counter(f["severity_normalized"] for f in pf).items())),
            "findings_with_blocking_flag": sum(1 for f in pf if f["blocking_flag_in_line"]),
            "repair_round_headings": kinds.get("repair_round_heading", 0), "repair_headings_any": kinds.get("repair_heading_any", 0),
            "reports_filed": kinds.get("report", 0), "status_blocked_on_reports": kinds.get("status_blocked_on", 0),
            "blocked_on_owner_fields_naming_a_role": kinds.get("blocked_on_owner_named", 0),
            "human_gate_quote_or_decision_lines": kinds.get("human_gate_quote_or_decision", 0), "manual_action_required_fields_not_none": kinds.get("manual_action_required", 0), "manual_action_fields_none": kinds.get("manual_action_field_none", 0),
            "manual_intervention_phrases": kinds.get("manual_intervention_phrase", 0),
            "guard_block_mentions": kinds.get("guard_block", 0), "guard_block_mentions_not_fixture_or_test": sum(1 for o in po if o["kind"] == "guard_block" and not o["fixture_or_test"]),
            "ownership_phrases": kinds.get("ownership_phrase", 0)}
    totals = collections.Counter()
    for row in per_phase.values():
        for key, value in row.items():
            if isinstance(value, int):
                totals[key] += value
    verdict_totals = collections.Counter()
    for row in per_phase.values():
        verdict_totals.update(row["verdicts"])
    sev_as = collections.Counter()
    sev_norm = collections.Counter()
    for row in per_phase.values():
        sev_as.update(row["findings_by_severity_as_written"])
        sev_norm.update(row["findings_by_severity_normalized"])
    by_owner = collections.OrderedDict()
    roles = sorted(set(o["role"] for o in other if o["kind"] == "report") | set(r for f in findings for r in f["owners_named"]) | set(o["role"] for o in other if o["kind"] == "blocked_on_owner_named"))
    first_round_rejected = collections.defaultdict(set)
    for (phase, unit), v in units.items():
        if v["class"] != "APPROVE":
            for f in findings:
                if f["phase"] == phase and f["unit"] == unit:
                    for r in f["owners_named"]:
                        first_round_rejected[r].add((phase, unit))
    for role in roles:
        by_owner[role] = {"reports_filed": sum(1 for o in other if o["kind"] == "report" and o["role"] == role),
                          "finding_lines_naming_owner": sum(1 for f in findings if role in f["owners_named"]),
                          "units_whose_first_review_requested_changes_and_named_owner": len(first_round_rejected.get(role, ())),
                          "status_blocked_on_reports_filed": sum(1 for o in other if o["kind"] == "status_blocked_on" and re.search(re.escape(role), o["text"])),
                          "named_as_blocked_on_owner": sum(1 for o in other if o["kind"] == "blocked_on_owner_named" and o["role"] == role)}
    result = {"schema": SCHEMA, "scope": "committed phase records docs/agent-runs/phase-01..15 (heuristic line parsing; every item has file and line in factory-items.json)",
              "inputs_sha256": dict(sorted(inputs.items())), "missing_records": missing,
              "regexes": {"verdict_label": VERDICT_LABEL.pattern, "verdict_token": VERDICT_TOKEN.pattern, "verdict_exclude": VERDICT_EXCLUDE.pattern, "finding_line": FINDING.pattern,
                          "blocking_flag": BLOCKING.pattern, "blocking_negation": NONBLOCKING.pattern, "role_token": ROLE.pattern, "owner_field": OWNER_FIELD.pattern,
                          "status_blocked_on": STATUS_BLOCKED.pattern, "blocked_on_owner_field": BLOCKED_OWNER.pattern, "repair_round_heading": REPAIR_HEADING.pattern,
                          "human_gate_quote": HUMAN_QUOTE.pattern, "manual_phrase": MANUAL.pattern, "manual_action_field": MANUAL_FIELD.pattern, "manual_action_none": MANUAL_NONE.pattern, "guard_block": GUARD_BLOCK.pattern, "ownership_phrase": OWNERSHIP.pattern},
              "rules": ["Verdict lines: a line starting with STATUS or '...verdict' and a colon whose next 220 characters contain a verdict token. A STATUS line that repeats the class of the "
                        "closest preceding VERDICT-labelled line within 150 lines is a footer restatement and is not counted (listed with reason).",
                        "Review unit: the unit id (nnX) in the verdict line, else in the nearest preceding heading, else '-' (the whole phase). First-pass acceptance = the first counted "
                        "verdict of the unit is APPROVE.",
                        "Finding lines: a numbered/bulleted/heading/table line or an id (B1, N2, F3) followed by a severity word as written. A finding restated in a recheck is counted again as "
                        "a line; 'distinct' keeps one per (unit, id).",
                        "Severity normalisation (a documented mapping, not a record): critical/blocker/high/P0/P1 -> high; major/medium-high/medium/P2 -> medium; low-medium/low/minor/P3 -> low; "
                        "info/nit -> info. The 'blocking flag' is the word block/blocks/blocking (not non-blocking) in the first 300 characters of the line.",
                        "BLOCKED-ON: lines 'STATUS: BLOCKED-ON' count as BLOCKED-ON reports; 'BLOCKED-ON OWNER:' fields that name an engineer role or the coordinator count as routed dependencies.",
                        "Manual interventions: (a) the report-contract line 'MANUAL ACTION REQUIRED:' whose value is not none/n-a (a step an agent said only the human could take; nearly all name the human review or commit gate, so this is a gate count, not a count of unplanned interventions), counted apart from the 'none' lines; "
                        "(b) the human's own quoted words or DECISION lines in human-gate.md; (c) the phrase 'manual(ly) intervention/repair/fix/edit/override' in running text.",
                        "Guard blocks (unsafe actions prevented): a line pairing PreToolUse/guard hook/hook with blocked/refused/rejected/denied; 'fixture_or_test' marks lines that describe a probe "
                        "or fixture rather than a real blocked action."],
              "first_pass_caveat": FIRST_PASS_CAVEAT, "hand_audit_phase_03": HAND_AUDIT_PHASE_03, "per_phase": per_phase, "totals": dict(sorted(totals.items())), "verdict_totals": dict(sorted(verdict_totals.items())),
              "severity_totals_as_written": dict(sorted(sev_as.items())), "severity_totals_normalized": dict(sorted(sev_norm.items())), "by_owner_role": by_owner,
              "first_pass_units": [{"phase": p, "unit": u, "first_verdict": v["class"], "file": v["file"], "line": v["line"]} for (p, u), v in units.items()],
              "gaps": ["First-pass acceptance by owning agent: the review records name the reviewed unit and sometimes the owner of a finding, but a first-pass APPROVE names no owner, "
                       "so only per-unit acceptance and owner-attributed findings are reported; a per-agent acceptance rate cannot be computed from the records.",
                       "Ownership violations caught by the hook/guard as a count: the records mention hook blocks in prose only; the lines found are listed under guard_block_mentions, "
                       "not a log-derived total (the hook writes no persistent log in the repository)."],
              "limitations": ["Heuristic parsing: formats differ by phase (STATUS lines, VERDICT lines, tables, verbatim external reviews); a verdict or finding written in a shape the "
                              "regexes do not match is not counted, and prose that matches is counted. The audit list is the remedy: every counted item has a line number.",
                              "Events that were not written down are not counted (for example hook blocks nobody described, repairs done inside a round without a heading).",
                              "Phases 1-5 used external (human-supplied) reviewers and different file layouts from Phases 12-15 (code-reviewer subagent); rates are not comparable across eras.",
                              "Severity words follow each reviewer's own scale (P1/P2, High/Medium/Low, blocker/nonblocking); the normalised table is a documented mapping.",
                              "Repair rounds are counted from headings in repairs.md; a phase whose repairs.md has no 'repair round' heading shows 0 even if repairs happened.",
                              "No independent ground truth for the counts exists: they were not cross-checked against a second parser."]}
    items = {"schema": SCHEMA, "verdicts": verdicts, "findings": findings, "other_items": other}
    return result, items


def parse_notes_lines(lines):
    items = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        for m in NOTES_VERDICT.finditer(line):
            if NOTES_NEGATE.search(line[max(0, m.start() - 40):m.end()]):
                continue
            items.append({"kind": "verdict", "class": m.group(1), "line": number, "text": excerpt(line[max(0, m.start() - 100):m.end() + 60])})
        if NOTES_HUMAN.search(line):
            items.append({"kind": "human_decision_line", "line": number, "text": excerpt(line)})
        if GUARD_BLOCK.search(line):
            items.append({"kind": "guard_block", "fixture_or_test": bool(GUARD_FIXTURE.search(line)), "line": number, "text": around(GUARD_BLOCK, line)})
        if re.search(r"report (?:was )?not delivered|harness refused", line, re.I):
            items.append({"kind": "agent_report_not_delivered", "line": number, "text": excerpt(line)})
        if re.search(r"\bstopped at user request|interrupt", line, re.I):
            items.append({"kind": "run_interrupted_by_human", "line": number, "text": excerpt(line)})
    return items


def build_notes():
    path = os.path.join(ROOT, NOTES)
    with open(path, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().split("\n")[:NOTES_FROZEN_LINES]
    if len(lines) < NOTES_FROZEN_LINES:
        raise OSError("the notes log has fewer than %d lines" % NOTES_FROZEN_LINES)
    sha = hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8", errors="replace")).hexdigest()
    items = parse_notes_lines(lines)
    verdict_counts = collections.Counter(i["class"] for i in items if i["kind"] == "verdict")
    summary = {"schema": SCHEMA, "source": NOTES, "source_sha256": sha, "source_lines": len(lines), "scope": "coordinator notes, Phase 15 Session 2 closeout and the Q12 / option-A work (2026-11-18 to 2026-11-21)",
               "verdicts_by_class": dict(sorted(verdict_counts.items())), "counts_by_kind": dict(sorted(collections.Counter(i["kind"] for i in items).items())),
               "rules": ["Verdicts: the upper-case tokens APPROVE, REQUEST-CHANGES, CHANGES-REQUIRED (so 'APPROVED_PLAN_SHA256' and lower-case 'approve' do not match); a token preceded within "
                         "40 characters by 'after reviewer' is a consent condition, not a verdict, and is skipped. Several verdicts on one line are each counted (r1, r2, r3).",
                         "Human decisions: lines containing HUMAN DECISION, USER (verbatim), HUMAN (chat), HUMAN:, USER: or 'Human decision'.",
                         "Guard blocks: the same pattern as the committed-record parser."],
               "limitations": ["The notes are a coordinator's running log, not an event log: a verdict, block or intervention that was not noted is not counted.",
                               "The log is append-only and git-ignored: only its first %d lines are read (its state when Phase 16 started; the sha256 is over those lines), later notes are not part of "
                               "this evaluation; the output cannot be regenerated from a fresh clone." % NOTES_FROZEN_LINES],
               "items": items}
    return summary


# ----------------------------------------------------------------------------------------------------------------------- markdown
def md_table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]


def render_md(r):
    L = ["# Phase 16 group 6: agentic factory", "",
         "Generated by `experiments/scripts/eval16_factory.py`. The tables sum line-level items parsed from the phase records; each item (file, line, excerpt) is in `factory-items.json`. "
         "Counts are approximations of what was written down (see Limitations).", "", "## 1. Per-phase table", ""]
    rows = []
    for phase, p in r["per_phase"].items():
        v = p["verdicts"]
        rows.append([phase, v.get("APPROVE", 0), v.get("REQUEST-CHANGES", 0), v.get("CHANGES-REQUESTED", 0) + v.get("CHANGES-REQUIRED", 0), p["review_units"],
                     "%d (%s)" % (p["first_pass_approved_units"], p["first_pass_rate"]), p["finding_lines"], p["findings_distinct_by_unit_and_id"],
                     p["findings_by_severity_normalized"], p["findings_with_blocking_flag"], p["repair_round_headings"], p["status_blocked_on_reports"],
                     p["blocked_on_owner_fields_naming_a_role"], p["manual_action_required_fields_not_none"], p["human_gate_quote_or_decision_lines"], p["guard_block_mentions"]])
    t = r["totals"]
    v = r["verdict_totals"]
    rows.append(["**total**", v.get("APPROVE", 0), v.get("REQUEST-CHANGES", 0), v.get("CHANGES-REQUESTED", 0) + v.get("CHANGES-REQUIRED", 0), t["review_units"],
                 "%d" % t["first_pass_approved_units"], t["finding_lines"], t["findings_distinct_by_unit_and_id"], r["severity_totals_normalized"], t["findings_with_blocking_flag"],
                 t["repair_round_headings"], t["status_blocked_on_reports"], t["blocked_on_owner_fields_naming_a_role"], t["manual_action_required_fields_not_none"],
                 t["human_gate_quote_or_decision_lines"], t["guard_block_mentions"]])
    L += md_table(["phase", "APPROVE", "REQUEST-CHANGES", "CHANGES-REQUESTED/REQUIRED", "review units", "first-pass approved (rate)", "finding lines", "distinct", "by severity (normalised)",
                   "with blocking flag", "repair-round headings", "STATUS BLOCKED-ON", "BLOCKED-ON OWNER names a role", "MANUAL ACTION REQUIRED field not none (mostly review/commit gates)", "human quote/decision lines", "guard-block mentions"], rows)
    L += ["", "**First-pass caveat.** " + r["first_pass_caveat"], "", "**Hand audit (phase 03).** " + r["hand_audit_phase_03"]["hand_listing"] + ". Hand: %d review events (%d changes required, %d approvals); parser: %d counted (%d REQUEST-CHANGES, %d APPROVE; lines %s). %s." % (
        r["hand_audit_phase_03"]["hand_review_events"], r["hand_audit_phase_03"]["hand_request_changes_outcomes"], r["hand_audit_phase_03"]["hand_approve_outcomes"], 11, 8, 3,
        r["hand_audit_phase_03"]["parser_counted"]["lines"], r["hand_audit_phase_03"]["reading"]),
          "", "Severity as written, all phases: %s." % r["severity_totals_as_written"], "",
          "Verdict lines excluded as footer restatements or deferrals: %d (listed with reasons in `factory-items.json`)." % t["verdict_lines_excluded_as_restatements"], "",
          "## 2. By owner role (where the records name one)", ""]
    L += md_table(["role", "reports filed", "finding lines naming it", "units first-reviewed REQUEST-CHANGES and naming it", "STATUS BLOCKED-ON reports naming it", "named as BLOCKED-ON OWNER"],
                  [[k, o["reports_filed"], o["finding_lines_naming_owner"], o["units_whose_first_review_requested_changes_and_named_owner"], o["status_blocked_on_reports_filed"], o["named_as_blocked_on_owner"]]
                   for k, o in r["by_owner_role"].items()])
    L += ["", "## 3. First-pass acceptance per review unit", "", "A unit is the subphase/work-order id found in the verdict line or its heading; the first counted verdict decides.", ""]
    L += md_table(["phase", "unit", "first verdict", "source"], [[u["phase"], u["unit"], u["first_verdict"], "%s:%d" % (u["file"], u["line"])] for u in r["first_pass_units"]])
    L += ["", "## 4. Rules (documented regexes are in `factory-metrics.json`)", ""] + ["- " + x for x in r["rules"]]
    L += ["", "## 5. GAPs", ""] + ["- " + x for x in r["gaps"]]
    L += ["", "## 6. Limitations and threats to validity", ""] + ["- " + x for x in r["limitations"]]
    L += ["", "The coordinator notes (git-ignored, local) are summarised apart in `factory-notes.md`.", "", "## 7. Inputs (sha256)", ""] + ["- `%s` %s" % (k, h) for k, h in r["inputs_sha256"].items()]
    return "\n".join(L) + "\n"


def render_notes_md(n):
    L = ["# Phase 16 group 6: coordinator notes (local log)", "", "Generated by `experiments/scripts/eval16_factory.py` from `%s` (first %d lines, sha256 %s); the log is git-ignored, so this file is "
         "regenerable only on the machine that holds it. Every item with its line number is in `factory-notes-items.json`." % (n["source"], n["source_lines"], n["source_sha256"]), "",
         "Scope: %s." % n["scope"], "", "Verdicts by class: %s." % n["verdicts_by_class"], "", "Counts by kind: %s." % n["counts_by_kind"], "", "## Verdict lines", ""]
    L += md_table(["line", "class", "excerpt"], [[i["line"], i["class"], i["text"].replace("|", "/")] for i in n["items"] if i["kind"] == "verdict"])
    for kind, title in (("guard_block", "Guard blocks"), ("human_decision_line", "Human decision lines"), ("agent_report_not_delivered", "Agent reports not delivered"), ("run_interrupted_by_human", "Runs interrupted by the human")):
        L += ["", "## " + title, ""] + md_table(["line", "excerpt"], [[i["line"], i["text"].replace("|", "/")] for i in n["items"] if i["kind"] == kind])
    L += ["", "## Rules", ""] + ["- " + x for x in n["rules"]] + ["", "## Limitations", ""] + ["- " + x for x in n["limitations"]]
    return "\n".join(L) + "\n"


def write(out_dir, name, text):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def dump(obj):
    return json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", default=os.path.join(ROOT, "experiments", "results", "phase16", "factory"))
    args = parser.parse_args(argv)
    try:
        result, items = build_committed()
    except OSError as error:
        print("REFUSED: %s" % error)
        return 1
    if result["missing_records"] and len(result["missing_records"]) > 12:
        print("REFUSED: too many committed records are missing: %s" % result["missing_records"][:5])
        return 1
    notes = None
    code = 0
    if os.path.isfile(os.path.join(ROOT, NOTES)):
        try:
            notes = build_notes()
        except OSError as error:
            print("INPUTS-UNAVAILABLE: %s (%s)" % (NOTES, error))
            notes = None
            code = 3
        if notes:
            write(args.out_dir, "factory-notes-items.json", dump(notes))
            write(args.out_dir, "factory-notes.md", render_notes_md(notes))
    else:
        print("INPUTS-UNAVAILABLE: %s (git-ignored local log; the committed-record outputs are still written; the notes outputs are not)" % NOTES)
        code = 3
    write(args.out_dir, "factory-metrics.json", dump(result))
    write(args.out_dir, "factory-items.json", dump(items))
    write(args.out_dir, "factory-metrics.md", render_md(result))
    print("WROTE %s (factory-metrics.json, factory-items.json, factory-metrics.md%s)" % (args.out_dir, ", factory-notes-items.json, factory-notes.md" if notes else ""))
    return code


if __name__ == "__main__":
    sys.exit(main())
