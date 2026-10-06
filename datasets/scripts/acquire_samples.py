#!/usr/bin/env python3
"""Bounded, idempotent sample acquisition for ScholarChain datasets.

Default mode (--mode regenerate) does not download from the network. It verifies
committed samples against datasets/samples/SHA256SUMS.

Refresh mode fetches only bounded byte ranges or single API records documented
in datasets/dataset-manifest.yaml. It never downloads a full DBLP, OpenAlex,
ORCID, or Crossref corpus snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sys
import urllib.error
import urllib.request
import zlib
from pathlib import Path

from dblp_entities import dblp_sample_prolog

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
SHA256SUMS = SAMPLES / "SHA256SUMS"

USER_AGENT = "ScholarChainPhase3/1.0 (mailto:student@uic.edu)"

# Hard caps enforced by validate_datasets.py (must stay in sync).
DBLP_MAX_COMPRESSED_BYTES = 8 * 1024 * 1024  # 8 MiB of monthly snapshot .xml.gz
OPENALEX_MAX_WORKS = 1
ORCID_MAX_RECORDS = 1
CROSSREF_MAX_WORKS = 1
API_MAX_RESPONSE_BYTES = 512 * 1024  # 512 KiB per enrichment API response body

# Pinned upstream gzip for bounded refresh (DOI 10.4230/dblp.xml.2026-10-03).
# Observed HTTP metadata and MD5: datasets/provenance/dblp-snapshot-2026-10-03-dagstuhl.txt
DBLP_SNAPSHOT_GZIP_URL = (
    "https://drops.dagstuhl.de/storage/artifacts/dblp/xml/2026/dblp-2026-10-03.xml.gz"
)
LINKED_DOI = "10.1007/978-3-642-31674-6_1"
LINKED_ORCID = "0000-0002-4414-6920"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sha256sums() -> dict[str, str]:
    expected: dict[str, str] = {}
    for line in SHA256SUMS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        expected[rel.strip()] = digest.lower()
    return expected


def verify_committed_samples() -> None:
    expected = load_sha256sums()
    for rel, digest in expected.items():
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"missing committed sample: {rel}")
        actual = sha256_file(path)
        if actual != digest:
            raise SystemExit(
                f"checksum mismatch for {rel}: expected {digest}, got {actual}"
            )
    print(f"verified {len(expected)} committed sample(s) against SHA256SUMS")


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    max_bytes: int = API_MAX_RESPONSE_BYTES,
) -> bytes:
    if max_bytes <= 0 or max_bytes > API_MAX_RESPONSE_BYTES:
        raise ValueError(f"refusing out-of-bounds API response cap: {max_bytes}")
    req = urllib.request.Request(url, headers=headers or {"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        content_length = resp.headers.get("Content-Length")
        if content_length is not None:
            declared = int(content_length)
            if declared > max_bytes:
                raise RuntimeError(
                    f"Content-Length {declared} exceeds cap {max_bytes}"
                )
        body = read_body_with_hard_cap(resp, max_bytes)
        if resp.read(1):
            raise RuntimeError(f"response body exceeds hard cap {max_bytes}")
        return body


def read_body_with_hard_cap(resp: http.client.HTTPResponse, max_bytes: int) -> bytes:
    """Read at most max_bytes from resp regardless of Content-Length."""
    chunks: list[bytes] = []
    remaining = max_bytes
    while remaining > 0:
        piece = resp.read(min(65536, remaining))
        if not piece:
            break
        chunks.append(piece)
        remaining -= len(piece)
    body = b"".join(chunks)
    if len(body) > max_bytes:
        raise RuntimeError(f"read exceeded hard cap: {len(body)} > {max_bytes}")
    return body


def parse_content_range_total(value: str | None) -> int | None:
    if not value:
        return None
    # bytes 0-65535/1107081001
    match = re.match(r"bytes\s+\d+-\d+/(\d+|\*)", value.strip(), re.IGNORECASE)
    if not match:
        return None
    total = match.group(1)
    if total == "*":
        return None
    return int(total)


def http_get_range(url: str, max_bytes: int) -> bytes:
    if max_bytes <= 0 or max_bytes > DBLP_MAX_COMPRESSED_BYTES:
        raise ValueError(f"refusing out-of-bounds DBLP range request: {max_bytes}")
    headers = {
        "User-Agent": USER_AGENT,
        "Range": f"bytes=0-{max_bytes - 1}",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=180) as resp:
        status = resp.status
        if status == 200:
            raise RuntimeError(
                "server ignored Range request (HTTP 200); refusing unbounded DBLP download"
            )
        if status != 206:
            raise RuntimeError(f"unexpected HTTP status for DBLP range GET: {status}")

        content_range = resp.headers.get("Content-Range")
        if not content_range:
            raise RuntimeError("missing Content-Range on partial DBLP response")

        span_match = re.match(
            r"bytes\s+(\d+)-(\d+)/", content_range.strip(), re.IGNORECASE
        )
        if not span_match:
            raise RuntimeError(f"malformed Content-Range: {content_range!r}")
        start, end = int(span_match.group(1)), int(span_match.group(2))
        span_len = end - start + 1
        if span_len > max_bytes:
            raise RuntimeError(
                f"Content-Range span {span_len} bytes exceeds cap {max_bytes}"
            )

        content_length = resp.headers.get("Content-Length")
        if content_length is not None:
            declared = int(content_length)
            if declared > max_bytes:
                raise RuntimeError(
                    f"Content-Length {declared} exceeds cap {max_bytes}"
                )

        return read_body_with_hard_cap(resp, max_bytes)


def extract_dblp_records(compressed: bytes, limit: int = 3) -> str:
    text = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(compressed).decode(
        "utf-8", errors="replace"
    )
    pattern = re.compile(r"<(inproceedings|article)[^>]*>.*?</\1>", re.DOTALL)
    blocks: list[str] = []
    for match in pattern.finditer(text):
        block = match.group(0)
        if block.count("<author") >= 2:
            blocks.append(block)
        if len(blocks) >= limit:
            break
    if len(blocks) < limit:
        raise RuntimeError(
            f"only extracted {len(blocks)} multi-author records; increase byte cap"
        )
    body = "\n".join(blocks) + "\n"
    header = dblp_sample_prolog(body) + "<dblp>\n"
    footer = "</dblp>\n"
    return header + body + footer


def refresh_dblp(max_bytes: int) -> None:
    compressed = http_get_range(DBLP_SNAPSHOT_GZIP_URL, max_bytes)
    xml = extract_dblp_records(compressed)
    out = SAMPLES / "dblp" / "linked-records.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes) from {len(compressed)} compressed bytes")


def refresh_openalex() -> None:
    url = f"https://api.openalex.org/works/https://doi.org/{LINKED_DOI}"
    payload = json.loads(http_get(url))
    out = SAMPLES / "openalex" / "works.jsonl"
    out.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def refresh_crossref() -> None:
    url = f"https://api.crossref.org/works/{LINKED_DOI}"
    payload = json.loads(http_get(url))
    out = SAMPLES / "crossref" / "works.jsonl"
    out.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def refresh_orcid() -> None:
    url = f"https://pub.orcid.org/v3.0/{LINKED_ORCID}/record"
    payload = json.loads(
        http_get(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    )
    out = SAMPLES / "orcid" / "records.jsonl"
    out.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def rewrite_sha256sums() -> None:
    rel_paths = sorted(
        p.relative_to(ROOT).as_posix()
        for p in SAMPLES.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS"
    )
    lines = [f"{sha256_file(ROOT / rel)}  {rel}" for rel in rel_paths]
    SHA256SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"updated {SHA256SUMS}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("regenerate", "refresh"),
        default="regenerate",
        help="regenerate verifies committed bytes; refresh performs bounded network fetch",
    )
    parser.add_argument(
        "--target",
        choices=("all", "dblp", "openalex", "orcid", "crossref"),
        default="all",
        help="dataset to refresh (refresh mode only)",
    )
    parser.add_argument(
        "--dblp-max-bytes",
        type=int,
        default=DBLP_MAX_COMPRESSED_BYTES,
        help=f"compressed byte cap for DBLP delta range GET (max {DBLP_MAX_COMPRESSED_BYTES})",
    )
    parser.add_argument(
        "--rewrite-checksums",
        action="store_true",
        help="after refresh, recompute datasets/samples/SHA256SUMS (manual manifest update required)",
    )
    args = parser.parse_args()

    if args.mode == "regenerate":
        verify_committed_samples()
        return

    if args.dblp_max_bytes > DBLP_MAX_COMPRESSED_BYTES:
        raise SystemExit(
            f"--dblp-max-bytes {args.dblp_max_bytes} exceeds cap {DBLP_MAX_COMPRESSED_BYTES}"
        )

    targets = (
        ["dblp", "openalex", "orcid", "crossref"]
        if args.target == "all"
        else [args.target]
    )
    for name in targets:
        if name == "dblp":
            refresh_dblp(args.dblp_max_bytes)
        elif name == "openalex":
            if OPENALEX_MAX_WORKS != 1:
                raise SystemExit("openalex refresh exceeds bounded work count")
            refresh_openalex()
        elif name == "crossref":
            if CROSSREF_MAX_WORKS != 1:
                raise SystemExit("crossref refresh exceeds bounded work count")
            refresh_crossref()
        elif name == "orcid":
            if ORCID_MAX_RECORDS != 1:
                raise SystemExit("orcid refresh exceeds bounded record count")
            refresh_orcid()

    if args.rewrite_checksums:
        rewrite_sha256sums()
    else:
        print(
            "refresh complete; run with --rewrite-checksums and update dataset-manifest.yaml checksums"
        )


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"network error: {exc}") from exc
