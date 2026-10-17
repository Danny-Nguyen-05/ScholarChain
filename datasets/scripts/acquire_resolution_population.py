#!/usr/bin/env python3
"""Bounded Phase 5C metadata acquisition. No credentials, labels or predictions.

Only an explicit --acquire starts HTTP. Never replaces an existing population.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import email.utils
import hashlib
import json
import re
import socket
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = "scholarchain.er-acquisition.v1"
BOUNDS = {"records": {"dblp": 600, "openalex": 800, "crossref": 600, "orcid": 60},
          "attempts": {"dblp": 750, "openalex": 850, "crossref": 650, "orcid": 100},
          "totalAttempts": 2400, "totalBytes": 256 * 1024 * 1024,
          "discoveryBytes": 2 * 1024 * 1024, "recordBytes": 1024 * 1024,
          "seconds": 4500, "timeoutSeconds": 20, "retries": 2, "ratePerSecond": 1}
VENUES = {
    "sigmod": ("ACM SIGMOD", r"sigmod|management of data"),
    "vldb": ("VLDB", r"vldb|very large data bases"),
    "icde": ("International Conference on Data Engineering", r"data engineering"),
    "socc": ("ACM Symposium on Cloud Computing", r"cloud computing"),
    "middleware": ("International Middleware Conference", r"middleware"),
    "icdcs": ("International Conference on Distributed Computing Systems", r"distributed computing systems"),
    "osdi": ("Operating Systems Design and Implementation", r"operating systems design and implementation"),
    "sosp": ("Symposium on Operating Systems Principles", r"operating systems principles"),
}
CROSSREF_FIELDS = "DOI,title,author,published,published-print,published-online,issued,type,container-title,ISSN,ISBN,publisher,URL,page"
OA_FIELDS = "id,doi,title,display_name,publication_year,publication_date,type,ids,authorships,primary_location,biblio,topics"
LICENSES = {
    "dblp": "https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released.html",
    "crossref": "https://www.crossref.org/documentation/retrieve-metadata/",
    "openalex": "https://help.openalex.org/how-to-use-the-data/",
    "orcid": "https://info.orcid.org/public-data-file-use-policy/",
}


def digest(body):
    return hashlib.sha256(body).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_doi(value):
    if not isinstance(value, str):
        return None
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(), flags=re.I).lower()
    return value if re.fullmatch(r"10\.\d{4,9}/\S+", value) else None


def date_year(item):
    for key in ("published-print", "published-online", "published", "issued"):
        try:
            return int(item[key]["date-parts"][0][0])
        except (KeyError, TypeError, IndexError, ValueError):
            continue
    return None


def choose_records(items, venue, year, limit=10):
    """Label/prediction-independent hash selection within verified venue/year."""
    unique = {}
    for item in items:
        doi = canonical_doi(item.get("DOI"))
        title = " ".join(item.get("title", []))
        container = " ".join(item.get("container-title", []))
        if (doi and title and item.get("author") and date_year(item) == year
                and re.search(VENUES[venue][1], container, re.I)):
            unique[doi] = item
    return sorted(unique.values(), key=lambda x: digest(("phase5c-v1:" + x["DOI"].lower()).encode()))[:limit]


class BoundReached(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, root, opener=None, clock=time.monotonic, sleeper=time.sleep):
        self.root, self.clock, self.sleeper = root, clock, sleeper
        self.start, self.last = clock(), None
        self.attempts, self.byte_count = collections.Counter(), 0
        self.events, self.disabled = [], set()
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open

    def get(self, source, url, discovery=False):
        if source in self.disabled:
            return None
        for retry in range(BOUNDS["retries"] + 1):
            now = self.clock()
            wait = max(0, 1 - (now - self.last)) if self.last is not None else 0
            if (now - self.start + wait >= BOUNDS["seconds"]
                    or sum(self.attempts.values()) >= BOUNDS["totalAttempts"]
                    or self.attempts[source] >= BOUNDS["attempts"][source]
                    or self.byte_count >= BOUNDS["totalBytes"]):
                raise BoundReached("HTTP request/time/byte allowance exhausted")
            if wait:
                self.sleeper(wait)
            self.last = self.clock()
            self.attempts[source] += 1
            number = sum(self.attempts.values())
            cap = min(BOUNDS["discoveryBytes" if discovery else "recordBytes"],
                      BOUNDS["totalBytes"] - self.byte_count)
            event = {"attempt": number, "source": source, "url": url,
                     "retrievedAt": dt.datetime.now(dt.timezone.utc).isoformat(), "retry": retry}
            response = None
            body = bytearray()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "ScholarChain-Phase5C-BoundedMetadata/1.0",
                                                               "Accept": "application/json" if source != "dblp" else "application/json,application/xml",
                                                               "Accept-Encoding": "identity"})
                remaining = BOUNDS["seconds"] - (self.clock() - self.start)
                response = self.opener(request, timeout=min(BOUNDS["timeoutSeconds"], remaining))
                event["status"] = response.status
                event["headers"] = {k: response.headers[k] for k in ("Content-Type", "Content-Length", "Retry-After", "ETag", "Last-Modified") if k in response.headers}
                if response.headers.get("Content-Encoding", "identity").lower() not in ("identity", ""):
                    raise ValueError("unexpected content encoding; refusing decompression")
                while len(body) < cap:
                    if self.clock() - self.start >= BOUNDS["seconds"]:
                        raise BoundReached("wall clock allowance exhausted while reading")
                    piece = response.read(min(65536, cap - len(body)))
                    if not piece:
                        break
                    body.extend(piece)
                    self.byte_count += len(piece)
                # Fail closed at cap, without reading even one byte past the budget.
                if len(body) == cap:
                    raise ValueError("response reached hard byte cap (possibly truncated)")
                if event["status"] != 200:
                    raise ValueError("non-200 response; no challenge/redirect bypass")
                data = json.loads(bytes(body))
                if not isinstance(data, dict):
                    raise ValueError("expected JSON object")
                event["result"] = "ok"
                return data, number
            except urllib.error.HTTPError as exc:
                event["status"] = exc.code
                event["headers"] = {k: exc.headers[k] for k in ("Content-Type", "Content-Length", "Retry-After") if k in exc.headers}
                event["result"] = "http-error"
                exc.close()
                # No response body read: bytes=0 is explicit, errors are not ingestion.
                if exc.code in (401, 403, 429):
                    self.disabled.add(source)
                if exc.code in (500, 502, 503, 504) and retry < BOUNDS["retries"]:
                    retry_after = event["headers"].get("Retry-After", "0")
                    try:
                        requested_pause = max(0, int(retry_after))
                    except ValueError:
                        try:
                            requested_pause = max(0, (email.utils.parsedate_to_datetime(retry_after) - dt.datetime.now(dt.timezone.utc)).total_seconds())
                        except (TypeError, ValueError, OverflowError):
                            requested_pause = 0
                    pause = max(2 ** retry, requested_pause)
                    if self.clock() - self.start + pause >= BOUNDS["seconds"]:
                        raise BoundReached("Retry-After exceeds remaining wall clock allowance")
                    self.sleeper(pause)
                    continue
                return None
            except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
                event["result"] = "network-error"
                event["error"] = str(exc)[:300]
                if retry < BOUNDS["retries"]:
                    self.sleeper(min(2 ** retry, max(0, BOUNDS["seconds"] - (self.clock() - self.start))))
                    continue
                self.disabled.add(source)
                return None
            except (ValueError, UnicodeError) as exc:
                event["result"] = "schema-or-access-error"
                event["error"] = str(exc)[:300]
                self.disabled.add(source)
                return None
            finally:
                if response is not None:
                    response.close()
                event["bytesRead"] = len(body)
                if body:
                    raw = self.root / "responses" / f"{number:04d}-{source}.body"
                    raw.write_bytes(bytes(body))
                    event.update(responsePath=raw.relative_to(self.root).as_posix(), sha256=digest(body))
                self.events.append(event)
                with (self.root / "request-ledger.jsonl").open("a", encoding="utf-8") as log:
                    log.write(encoded(event).decode() + "\n")


def acquire(root, base=None):
    if root.exists():
        raise ValueError("output already exists; acquisition never overwrites or resumes silently")
    root.mkdir(parents=True)
    (root / "responses").mkdir()
    for source in BOUNDS["records"]:
        (root / source).mkdir()
    client = Client(root)
    records = {source: {} for source in BOUNDS["records"]}
    provenance, diagnostics = [], []
    status = "COMPLETE_WITH_SOURCE_LIMITATIONS"
    base_manifest_hash = None
    if base is not None:
        prior = json.loads((base / "population-manifest.v1.json").read_bytes())
        base_manifest_hash = digest((base / "population-manifest.v1.json").read_bytes())
        for rel, fact in prior["files"].items():
            if digest((base / rel).read_bytes()) != fact["sha256"]:
                raise ValueError("base population hash mismatch: " + rel)
        for source in records:
            if source != "dblp":
                for line in (base / prior["sources"][source]["path"]).read_bytes().splitlines():
                    item = json.loads(line)
                    native = canonical_doi(item["message"]["DOI"]) if source == "crossref" else item["id"] if source == "openalex" else item["orcid-identifier"]["path"]
                    records[source][native] = item
        provenance = [json.loads(line) for line in (base / "record-provenance.jsonl").read_bytes().splitlines()]
        diagnostics = json.loads((base / "diagnostics.json").read_bytes())
        for file in (base / "responses").iterdir():
            shutil.copyfile(file, root / "responses" / file.name)
        shutil.copyfile(base / "request-ledger.jsonl", root / "request-ledger.jsonl")
        client.events = [json.loads(line) for line in (base / "request-ledger.jsonl").read_bytes().splitlines()]
        client.attempts.update(prior["observed"]["attempts"])
        client.byte_count = prior["observed"]["responseBytes"]
        client.disabled.update(prior["observed"]["disabledSources"])
        first_request = dt.datetime.fromisoformat(client.events[0]["retrievedAt"])
        client.start -= max(prior["observed"]["seconds"], (dt.datetime.now(dt.timezone.utc) - first_request).total_seconds())

    def add(source, native, item, attempt, stratum):
        if native in records[source] or len(records[source]) >= BOUNDS["records"][source]:
            return
        body = encoded(item)
        if len(body) >= BOUNDS["recordBytes"]:
            diagnostics.append({"source": source, "nativeId": native, "reason": "oversize-normalized-record"})
            return
        records[source][native] = item
        provenance.append({"source": source, "nativeId": native, "requestAttempt": attempt,
                           "stratum": stratum, "normalizedRecordSha256": digest(body)})

    try:
        # An official endpoint probe is retained. A challenge disables this source;
        # no alternate host, cookie, token, browser, challenge solving or bulk fallback.
        if base is None:
            client.get("dblp", "https://dblp.org/search/publ/api?" + urllib.parse.urlencode({"q": "stream:streams/conf/sigmod: year:2020:", "h": 2, "format": "json"}), True)
        diagnostics.append({"source": "dblp", "reason": "record-acquisition-unavailable: use-public-crossref-discovery; no challenge bypass"})
        for venue, (query, _) in (VENUES.items() if base is None else []):
            for year in range(2018, 2025):
                url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
                    "query.container-title": query, "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
                    "rows": 30, "select": CROSSREF_FIELDS})
                result = client.get("crossref", url, True)
                if result:
                    data, attempt = result
                    items = data.get("message", {}).get("items", [])
                    if not isinstance(items, list):
                        raise ValueError("Crossref discovery message.items missing")
                    chosen = choose_records(items, venue, year)
                    for item in chosen:
                        add("crossref", canonical_doi(item["DOI"]), {"status": "ok", "message-type": "work", "message-version": "1.0.0", "message": item}, attempt, f"{venue}/{year}")
                    diagnostics.append({"source": "crossref", "stratum": f"{venue}/{year}", "returned": len(items), "selected": len(chosen)})
                print(f"crossref {venue}/{year}: {len(records['crossref'])} total records; {sum(client.attempts.values())} HTTP attempts", flush=True)
        # Public OpenAlex first-page venue/year discovery is also usable when
        # another source is inaccessible. Verify the returned source name first.
        for venue, (query, pattern) in VENUES.items():
            result = client.get("openalex", "https://api.openalex.org/sources?" + urllib.parse.urlencode({"search": query, "per-page": 5, "select": "id,display_name,issn"}), True)
            if not result:
                continue
            data, _ = result
            matches = [row for row in data.get("results", []) if re.search(pattern, row.get("display_name", ""), re.I)]
            if not matches:
                diagnostics.append({"source": "openalex", "stratum": venue, "reason": "no-verified-venue-source"})
                continue
            selected_source = sorted(matches, key=lambda row: row["id"])[0]
            for year in range(2018, 2025):
                if len(records["openalex"]) >= BOUNDS["records"]["openalex"]:
                    break
                url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": f"primary_location.source.id:{selected_source['id'].rsplit('/', 1)[-1]},publication_year:{year}", "per-page": 12, "select": OA_FIELDS})
                result = client.get("openalex", url, True)
                if result:
                    data, attempt = result
                    for item in data.get("results", []):
                        source = (item.get("primary_location") or {}).get("source") or {}
                        if item.get("publication_year") == year and source.get("id") == selected_source["id"] and re.search(pattern, source.get("display_name", ""), re.I):
                            add("openalex", item["id"], item, attempt, f"{venue}/{year}")
                print(f"openalex {venue}/{year}: {len(records['openalex'])} records; {sum(client.attempts.values())} aggregate attempts", flush=True)
        dois = sorted(records["crossref"])
        for offset in range(0, len(dois), 20):
            batch = dois[offset:offset + 20]
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": "doi:" + "|".join("https://doi.org/" + doi for doi in batch), "per-page": 100, "select": OA_FIELDS})
            result = client.get("openalex", url, True)
            if result:
                data, attempt = result
                for item in data.get("results", []):
                    doi = canonical_doi(item.get("doi"))
                    if doi in batch and isinstance(item.get("id"), str):
                        add("openalex", item["id"], item, attempt, "crossref-doi-match")
        # Bounded neighboring works supply repeated-author and confusing-name contexts.
        authors = collections.Counter(a.get("author", {}).get("id") for item in records["openalex"].values() for a in item.get("authorships", []) if a.get("author", {}).get("id"))
        for author, _ in sorted(authors.items(), key=lambda x: (-x[1], digest(x[0].encode())))[:20]:
            if len(records["openalex"]) >= BOUNDS["records"]["openalex"]:
                break
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": f"author.id:{author.rsplit('/', 1)[-1]},from_publication_date:2018-01-01,to_publication_date:2024-12-31", "per-page": 10, "select": OA_FIELDS})
            result = client.get("openalex", url, True)
            if result:
                data, attempt = result
                for item in data.get("results", []):
                    if isinstance(item.get("id"), str) and 2018 <= item.get("publication_year", 0) <= 2024:
                        add("openalex", item["id"], item, attempt, "repeated-author-neighbor:" + author)
        orcids = set()
        for item in records["crossref"].values():
            orcids.update(a.get("ORCID", "").rsplit("/", 1)[-1] for a in item["message"].get("author", []) if a.get("ORCID"))
        for item in records["openalex"].values():
            orcids.update(a.get("author", {}).get("orcid", "").rsplit("/", 1)[-1] for a in item.get("authorships", []) if a.get("author", {}).get("orcid"))
        for orcid in sorted(orcids, key=lambda x: digest(x.encode()))[:60]:
            if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid):
                continue
            result = client.get("orcid", f"https://pub.orcid.org/v3.0/{orcid}/record")
            if result:
                data, attempt = result
                if data.get("orcid-identifier", {}).get("path") == orcid:
                    add("orcid", orcid, data, attempt, "observed-author-orcid")
    except (BoundReached, ValueError) as exc:
        status = "PARTIAL"
        diagnostics.append({"reason": str(exc)})
    sources = {}
    for source in records:
        path = root / source / ("records.xml" if source == "dblp" else "records.jsonl" if source == "orcid" else "works.jsonl")
        if source == "dblp":
            path.write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n</dblp>\n')
        else:
            path.write_bytes(b"".join(encoded(records[source][key]) + b"\n" for key in sorted(records[source])))
        sources[source] = {"path": path.relative_to(root).as_posix(), "records": len(records[source]), "sha256": digest(path.read_bytes()), "bytes": path.stat().st_size,
                           "snapshotId": f"{source}-er5c-live-api-" + dt.datetime.now(dt.timezone.utc).date().isoformat(),
                           "retrievalDate": dt.datetime.now(dt.timezone.utc).date().isoformat(), "licenseEvidenceUri": LICENSES[source]}
    (root / "record-provenance.jsonl").write_bytes(b"".join(encoded(x) + b"\n" for x in provenance))
    (root / "diagnostics.json").write_bytes(encoded(diagnostics) + b"\n")
    names = collections.Counter()
    for row in records["crossref"].values():
        names.update(set(" ".join((a.get("given", ""), a.get("family", ""))).strip().casefold() for a in row["message"].get("author", [])))
    manifest = {"version": VERSION, "status": status, "selectionVersion": "venue-year-hash-v1/repeated-author-neighbors-v1",
                "selectionSeed": "phase5c-v1", "years": [2018, 2024], "venueFamilies": list(VENUES), "bounds": BOUNDS,
                "observed": {"attempts": dict(client.attempts), "totalAttempts": sum(client.attempts.values()), "responseBytes": client.byte_count,
                             "seconds": round(client.clock() - client.start, 3), "disabledSources": sorted(client.disabled), "repeatedCrossrefAuthorNames": sum(n > 1 for n in names.values())},
                "sources": sources, "humanReviews": 0, "readiness": "PAIR_AND_DISJOINT_GROUP_COUNTS_REQUIRE_COMPLETED_HADOOP_AND_ER_QUEUE",
                "limitations": ["DBLP endpoint challenge is not bypassed; empty XML is explicit, not acquired DBLP data.", "Source metadata and names are not human identity labels.", "Crossref discovery top-30 and OpenAlex first-page neighbors form a convenience population, not unbiased global sampling.", "ORCID public API policy applies; no credential, authenticated or private API access.", "Response bodies are retained; Crossref select excludes abstracts/references, OpenAlex select excludes abstracts."]}
    manifest["basePopulationManifestSha256"] = base_manifest_hash
    manifest["acquisitionScriptSha256"] = digest(Path(__file__).read_bytes())
    manifest["files"] = {p.relative_to(root).as_posix(): {"sha256": digest(p.read_bytes()), "bytes": p.stat().st_size} for p in sorted(root.rglob("*")) if p.is_file()}
    tmp = root / "population-manifest.v1.json.tmp"
    tmp.write_bytes(encoded(manifest) + b"\n")
    tmp.rename(root / "population-manifest.v1.json")
    print(json.dumps({"status": status, "records": {s: v["records"] for s, v in sources.items()}, "observed": manifest["observed"]}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquire", action="store_true", help="explicit opt-in to bounded public HTTP")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=Path, help="immutable completed population to extend within its original aggregate bounds")
    args = parser.parse_args()
    if not args.acquire:
        parser.error("network disabled; pass --acquire explicitly")
    acquire(args.output.resolve(), args.base.resolve() if args.base else None)


if __name__ == "__main__":
    main()
