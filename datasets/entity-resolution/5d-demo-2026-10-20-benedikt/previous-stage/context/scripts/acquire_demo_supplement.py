#!/usr/bin/env python3
"""Authorized Phase 5D demo evidence only; no labels, scoring or model calls.

Extract existing observations first. --acquire-openalex is a separate opt-in.
Every executed script version is copied verbatim before its first HTTP request.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import shutil
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "scholarchain.demo-supplement.v1"
BOUNDS = {"crossrefSeeds": 14, "newOpenAlexWorksIncludingExcluded": 30,
          "doiSeedMatches": 6, "neighborWorks": 24, "httpAttempts": 20,
          "totalResponseBytes": 16 * 1024 * 1024, "responseBytes": 2 * 1024 * 1024,
          "recordBytes": 1024 * 1024, "wallSeconds": 600, "timeoutSeconds": 20,
          "maxTransientRetries": 1, "concurrency": 1, "maxStartsPerSecond": 1}
SEEDS = (
    "10.1145/3299887.3299892", "10.1145/3277006.3277017", "10.1145/3299887.3299899",
    "10.1145/3277006.3277009", "10.1145/3186549.3186555", "10.1145/3186549.3186557",
    "10.1145/3186549.3186559", "10.1145/3186549.3186562", "10.1145/3277006.3277011",
    "10.1145/3299887.3299891", "10.1145/3277006.3277013", "10.1145/3186549.3186551",
    "10.1145/3299887.3299897", "10.1145/3196959.3196962")
SOURCE_SHA = "73a27212459508e6c41df659c391603682e4a9e0afc0da21f4b5a01701263e4f"
OA_FIELDS = "id,doi,title,display_name,publication_year,publication_date,type,ids,authorships,primary_location,biblio,topics"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def canonical_doi(raw):
    value = (raw or "").lower().strip()
    return value.removeprefix("https://doi.org/").removeprefix("http://doi.org/")


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class StopBudget(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, root, opener=None, clock=time.monotonic, sleep=time.sleep):
        self.root, self.clock, self.sleep = root, clock, sleep
        self.start, self.last = clock(), None
        self.events, self.bytes, self.unique = [], 0, set()
        self.stopped = False
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open

    def get(self, url, category, max_results):
        if self.stopped:
            return []
        if urllib.parse.urlsplit(url).netloc != "api.openalex.org":
            raise ValueError("only anonymous public OpenAlex API permitted")
        for retry in range(2):
            wait = max(0, 1 - (self.clock() - self.last)) if self.last is not None else 0
            if (len(self.events) >= BOUNDS["httpAttempts"] or self.bytes >= BOUNDS["totalResponseBytes"]
                    or self.clock() - self.start + wait >= BOUNDS["wallSeconds"]):
                raise StopBudget("request/byte/wall allowance exhausted")
            if wait:
                self.sleep(wait)
            self.last = self.clock()
            event = {"attempt": len(self.events) + 1, "url": url, "category": category,
                     "retry": retry, "retrievedAtUtc": utc(), "result": "incomplete"}
            self.events.append(event)
            body, response = bytearray(), None
            try:
                response = self.opener(urllib.request.Request(url, headers={
                    "User-Agent": "ScholarChain-Authorized-5D-Demo/1.0", "Accept": "application/json", "Accept-Encoding": "identity"}),
                    timeout=min(20, BOUNDS["wallSeconds"] - (self.clock() - self.start)))
                event["status"] = response.status
                event["headers"] = {k: response.headers[k] for k in ("Content-Type", "Content-Length", "Retry-After", "ETag") if k in response.headers}
                if response.headers.get("Content-Encoding", "identity") not in ("", "identity"):
                    raise ValueError("unexpected content encoding")
                cap = min(BOUNDS["responseBytes"], BOUNDS["totalResponseBytes"] - self.bytes)
                while len(body) < cap:
                    remaining = BOUNDS["wallSeconds"] - (self.clock() - self.start)
                    if remaining <= 0:
                        raise StopBudget("wall allowance exhausted during body")
                    # Bound every socket read by the remaining overall allowance.
                    sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
                    if sock is not None:
                        sock.settimeout(min(20, remaining))
                    piece = response.read(min(65536, cap - len(body)))
                    if not piece:
                        break
                    body.extend(piece)
                    self.bytes += len(piece)
                if len(body) == cap or response.status != 200:
                    raise ValueError("response cap/non-200; no bypass")
                data = json.loads(body)
                results = data.get("results")
                if not isinstance(results, list) or len(results) > max_results:
                    raise ValueError("unexpected response shape or requested record bound exceeded")
                for work in results:
                    if not isinstance(work, dict) or not isinstance(work.get("id"), str):
                        raise ValueError("missing native work identity")
                    self.unique.add(work["id"])
                if len(self.unique) > BOUNDS["newOpenAlexWorksIncludingExcluded"]:
                    raise StopBudget("observed work cap exceeded; discard this response from ingestion")
                event["result"] = "ok"
                return [(work, event["attempt"]) for work in results]
            except urllib.error.HTTPError as exc:
                event["status"], event["result"] = exc.code, "http-error"
                event["headers"] = {k: exc.headers[k] for k in ("Retry-After", "Content-Type") if exc.headers and k in exc.headers}
                exc.close()
                if exc.code in (500, 502, 503, 504) and retry == 0:
                    # Stop rather than retry early when upstream asks for a delay.
                    if event["headers"].get("Retry-After"):
                        self.stopped = True
                        return []
                    self.sleep(1)
                    continue
                self.stopped = True
                return []
            except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
                event["result"], event["error"] = "network-error", str(exc)[:300]
                if retry == 0:
                    self.sleep(1)
                    continue
                self.stopped = True
                return []
            except (ValueError, UnicodeError) as exc:
                event["result"], event["error"] = "schema-or-access-error", str(exc)[:300]
                self.stopped = True
                return []
            finally:
                if response is not None:
                    response.close()
                event["bytesRead"] = len(body)
                if body:
                    path = self.root / "responses" / f"{event['attempt']:03d}-openalex.body"
                    path.write_bytes(body)
                    event.update(responsePath=path.relative_to(self.root).as_posix(), sha256=sha(body))
                with (self.root / "request-ledger.jsonl").open("ab") as log:
                    log.write(encoded(event) + b"\n")


def validate(root):
    m = json.loads((root / "population-manifest.v1.json").read_bytes())
    if m["schemaVersion"] != VERSION or m["bounds"] != BOUNDS:
        raise ValueError("wrong demo schema/bounds")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(m["files"]) | {"population-manifest.v1.json"}:
        raise ValueError("demo inventory differs")
    for rel, fact in m["files"].items():
        p = root / rel
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe demo path")
        body = p.read_bytes()
        if len(body) != fact["bytes"] or sha(body) != fact["sha256"]:
            raise ValueError("demo hash mismatch: " + rel)
    if m["observed"]["httpAttempts"] > 20 or m["observed"]["responseBytes"] > BOUNDS["totalResponseBytes"] or m["observed"]["distinctNewOpenAlexWorksIncludingExcluded"] > 30:
        raise ValueError("demo budget exceeded")
    if m["sources"]["crossref"]["records"] > 14 or m["sources"]["openalex"]["records"] > 30:
        raise ValueError("demo ingestion record cap exceeded")
    if m["humanReviews"] != 0 or m["heldOutAdmissionStatus"] != "PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING":
        raise ValueError("dataset cannot claim human labels or canonical admission")
    if sha((root / m["executedScript"]["path"]).read_bytes()) != m["executedScript"]["sha256"]:
        raise ValueError("executed script provenance differs")
    ledger = [json.loads(line) for line in (root / "request-ledger.jsonl").read_bytes().splitlines()]
    if [row["attempt"] for row in ledger] != list(range(1, len(ledger) + 1)) or len(ledger) != m["observed"]["httpAttempts"] or sum(row["bytesRead"] for row in ledger) != m["observed"]["responseBytes"]:
        raise ValueError("request/byte ledger differs from budget claims")
    original = json.loads((root / "responses/original-crossref-discovery.body").read_bytes())["message"]["items"]
    proof = {(p["source"], p["nativeId"]): p for p in map(json.loads, (root / "record-provenance.jsonl").read_bytes().splitlines())}
    total = 0
    for source in ("crossref", "openalex", "orcid"):
        rows = [json.loads(line) for line in (root / m["sources"][source]["path"]).read_bytes().splitlines()]
        if len(rows) != m["sources"][source]["records"]:
            raise ValueError("actual source record count differs")
        for row in rows:
            native = row["message"]["DOI"].lower() if source == "crossref" else row["id"]
            record_proof = proof[(source, native)]
            if sha(encoded(row)) != record_proof["normalizedRecordSha256"]:
                raise ValueError("record provenance hash differs")
            if source == "crossref":
                if row["message"] not in original:
                    raise ValueError("Crossref record not in original response")
            else:
                event = ledger[record_proof["requestAttempt"] - 1]
                response = json.loads((root / event["responsePath"]).read_bytes())
                if event["result"] != "ok" or row not in response["results"]:
                    raise ValueError("OpenAlex record not in successful response")
        total += len(rows)
    if total != len(proof):
        raise ValueError("extra or duplicate record provenance")
    return {"status": "VALID", "records": {s: x["records"] for s, x in m["sources"].items()}, "files": len(m["files"]), "observed": m["observed"], "admission": m["heldOutAdmissionStatus"]}


def publish(output, raw_source, base=None, acquire=False):
    if output.exists():
        raise ValueError("new demo output required; never overwrite")
    original = raw_source.read_bytes()
    if sha(original) != SOURCE_SHA:
        raise ValueError("original Crossref response checksum differs")
    items = {canonical_doi(x["DOI"]): x for x in json.loads(original)["message"]["items"]}
    records = []
    for doi in sorted(SEEDS):
        item = items[doi]
        if not item.get("author") or not item.get("title"):
            raise ValueError("seed lacks source authors/title")
        records.append({"status": "ok", "message-type": "work", "message-version": "1.0.0", "message": item})
    output.parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=".5d-demo-", dir=output.parent))
    for source in ("dblp", "crossref", "openalex", "orcid", "responses", "scripts"):
        (root / source).mkdir()
    executed_script = Path(__file__).read_bytes()
    (root / "scripts/acquire_demo_supplement.py").write_bytes(executed_script)
    (root / "responses/original-crossref-discovery.body").write_bytes(original)
    (root / "request-ledger.jsonl").write_bytes(b"")
    observed, excluded, proofs = {}, [], []
    status, client = "SEEDS_ONLY", None
    if base is not None:
        validate(base)
    if acquire:
        client = Client(root)
        status = "COMPLETE_WITHIN_BOUNDS"
        seed_dois = sorted(SEEDS, key=lambda d: sha(("5d-demo-v1:" + d).encode()))[:6]
        try:
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": "doi:" + "|".join("https://doi.org/" + d for d in seed_dois), "per-page": 6, "select": OA_FIELDS})
            seed_matches = client.get(url, "doi-seed-match", 6)
            for work, attempt in seed_matches:
                if canonical_doi(work.get("doi")) not in seed_dois:
                    excluded.append({"id": work["id"], "reason": "unexpected-seed-doi"})
                    continue
                observed[work["id"]] = (work, attempt, "doi-seed-match")
            # Fixed hash chooses one actually observed author without ORCID where
            # available. This is an explicit missing-ID evidence stratum, not a score.
            authors = []
            for work, _ in sorted(seed_matches, key=lambda row: row[0]["id"]):
                candidates = [a.get("author", {}) for a in work.get("authorships", []) if a.get("author", {}).get("id")]
                candidates.sort(key=lambda a: (bool(a.get("orcid")), sha(a["id"].encode())))
                if candidates and candidates[0]["id"] not in authors:
                    authors.append(candidates[0]["id"])
            for author in authors[:6]:
                url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": f"author.id:{author.rsplit('/', 1)[-1]},from_publication_date:2018-01-01,to_publication_date:2024-12-31", "per-page": 4, "select": OA_FIELDS})
                for work, attempt in client.get(url, "observed-author-neighbor", 4):
                    observed.setdefault(work["id"], (work, attempt, "observed-author-neighbor"))
        except StopBudget as exc:
            status = "PARTIAL_BUDGET_STOP"
            excluded.append({"reason": str(exc)})
    accepted = []
    cs_venue = ("sigmod", "vldb", "data engineering", "cloud computing", "middleware", "distributed", "operating systems", "database", "management of data", "computing surveys", "parallel", "computer systems")
    for native, (work, attempt, stratum) in sorted(observed.items()):
        venue = (((work.get("primary_location") or {}).get("source") or {}).get("display_name") or "").lower()
        if not 2018 <= (work.get("publication_year") or 0) <= 2024 or (stratum != "doi-seed-match" and not any(v in venue for v in cs_venue)) or len(encoded(work)) > BOUNDS["recordBytes"]:
            excluded.append({"id": native, "reason": "year-domain-or-record-byte-filter", "stratum": stratum})
            continue
        accepted.append(work)
        proofs.append({"source": "openalex", "nativeId": native, "requestAttempt": attempt, "stratum": stratum, "normalizedRecordSha256": sha(encoded(work))})
    for item in records:
        proofs.append({"source": "crossref", "nativeId": item["message"]["DOI"].lower(), "originalResponse": "responses/original-crossref-discovery.body", "originalResponseSha256": SOURCE_SHA, "retrievalDate": "2026-10-16", "normalizedRecordSha256": sha(encoded(item))})
    (root / "dblp/records.xml").write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n</dblp>\n')
    (root / "orcid/records.jsonl").write_bytes(b"")
    (root / "openalex/works.jsonl").write_bytes(b"".join(encoded(x) + b"\n" for x in accepted))
    (root / "crossref/works.jsonl").write_bytes(b"".join(encoded(x) + b"\n" for x in records))
    (root / "record-provenance.jsonl").write_bytes(b"".join(encoded(x) + b"\n" for x in proofs))
    (root / "selection-exclusions.json").write_bytes(encoded(excluded) + b"\n")
    sources = {}
    for source, rel, count in (("dblp", "dblp/records.xml", 0), ("orcid", "orcid/records.jsonl", 0), ("crossref", "crossref/works.jsonl", len(records)), ("openalex", "openalex/works.jsonl", len(accepted))):
        date = "2026-10-16" if source == "crossref" else dt.datetime.now(dt.timezone.utc).date().isoformat()
        sources[source] = {"path": rel, "records": count, "snapshotId": source + "-5d-demo-" + date, "retrievalDate": date, "sha256": sha((root / rel).read_bytes())}
    manifest = {"schemaVersion": VERSION, "status": status, "bounds": BOUNDS, "createdAtUtc": utc(),
                "executedScript": {"path": "scripts/acquire_demo_supplement.py", "sha256": sha(executed_script)}, "sources": sources,
                "selection": "Fourteen fixed unused Crossref observations from original verified 2018 SIGMOD discovery; hash-first six DOI seeds, then one observed missing-ORCID author per seed and first four 2018-2024 neighbors; no labels/predictions/scores.",
                "baseManifestSha256": sha((base / "population-manifest.v1.json").read_bytes()) if base else None,
                "observed": {"httpAttempts": len(client.events) if client else 0, "responseBytes": client.bytes if client else 0, "distinctNewOpenAlexWorksIncludingExcluded": len(client.unique) if client else 0, "seconds": round(client.clock() - client.start, 4) if client else 0},
                "heldOutAdmissionStatus": "PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING", "humanReviews": 0,
                "limitations": ["Provisional seed screening is not canonical held-out clearance.", "No eligible pair is claimed. Entire components overlapping locked held-out anchors must be excluded before scoring.", "Public anonymous metadata only; no abstracts/full text requested, no credentials or paid service."]}
    manifest["files"] = {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(root.rglob("*")) if p.is_file()}
    (root / "population-manifest.v1.json").write_bytes(encoded(manifest) + b"\n")
    validate(root)
    root.rename(output)
    return validate(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--original-crossref-response", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--base", type=Path)
    create.add_argument("--acquire-openalex", action="store_true")
    check = sub.add_parser("validate")
    check.add_argument("--population", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "validate":
        result = validate(args.population.resolve())
    else:
        if args.acquire_openalex and not args.base:
            parser.error("network supplement requires existing seed-only population --base")
        result = publish(args.output.resolve(), args.original_crossref_response.resolve(), args.base.resolve() if args.base else None, args.acquire_openalex)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
