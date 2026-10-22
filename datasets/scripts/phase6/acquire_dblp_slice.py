#!/usr/bin/env python3
"""Acquire the approved Phase 6 slice, with one cumulative network budget.

Only the pinned Dagstuhl archive is fetched. No retries or metadata requests.
Raw payloads live in ignored target/. The archive is verified before extraction.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dblp_entities import DBLP_NAMED_ENTITIES, ENTITY_REF_RE, XML_PREDEFINED_ENTITIES

URL = 'https://drops.dagstuhl.de/storage/artifacts/dblp/xml/2026/dblp-2026-10-03.xml.gz'
EXPECTED_BYTES = 1107081001
EXPECTED_MD5 = 'cbd329100ea1bbb2873fa2f6d414ea00'
BYTE_CAP = 1342177280
SECONDS_CAP = 1800
VENUES = ('podc', 'disc', 'icdcs', 'osdi', 'sosp', 'nsdi', 'eurosys', 'middleware')
VENUE_ALIASES = {venue: venue for venue in VENUES} | {'wdag': 'disc'}
PER_VENUE_CAP = 2500
MIN_YEAR, MAX_YEAR = 2005, 2026
LICENSE_URL = 'https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released'


class Budget:
    def __init__(self, byte_cap=BYTE_CAP, seconds_cap=SECONDS_CAP, clock=time.monotonic):
        self.byte_cap = byte_cap
        self.seconds_cap = seconds_cap
        self.clock = clock
        self.started = clock()
        self.received = 0

    def remaining_seconds(self):
        value = self.seconds_cap - (self.clock() - self.started)
        if value <= 0:
            raise RuntimeError('30-minute acquisition deadline reached; stop, no retry')
        return value

    def allowance(self):
        self.remaining_seconds()
        left = self.byte_cap - self.received
        if left <= 0:
            raise RuntimeError('Cumulative network byte cap reached; stop, no retry')
        return min(1024 * 1024, left)


def hashes(path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with Path(path).open('rb') as source:
        while block := source.read(1024 * 1024):
            md5.update(block)
            sha.update(block)
    return {'md5': md5.hexdigest(), 'sha256': sha.hexdigest(), 'bytes': Path(path).stat().st_size}


def verify_archive(path):
    result = hashes(path)
    if result['bytes'] != EXPECTED_BYTES or result['md5'] != EXPECTED_MD5:
        raise RuntimeError('Local pinned archive size/MD5 mismatch; refusing extraction')
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise RuntimeError('Redirect refused before reading its body')


def download(path, budget, opener=None):
    """Every response read is bounded BEFORE reading; redirect/retry disabled."""
    if opener is None:
        opener = urllib.request.build_opener(NoRedirect()).open
    request = urllib.request.Request(URL, headers={'User-Agent': 'ScholarChainPhase6/1.0', 'Accept-Encoding': 'identity'})
    timeout = min(30.0, budget.remaining_seconds())
    with opener(request, timeout=timeout) as response:
        if response.status != 200 or response.geturl() != URL:
            raise RuntimeError('Unexpected HTTP status or redirect; stop')
        length = response.headers.get('Content-Length')
        if length is None or int(length) != EXPECTED_BYTES:
            raise RuntimeError('Pinned archive Content-Length mismatch; refusing body')
        if int(length) > budget.byte_cap - budget.received:
            raise RuntimeError('Content-Length exceeds remaining cumulative byte budget')
        partial = path.with_suffix(path.suffix + '.partial')
        with partial.open('xb') as output:
            remaining = int(length)
            while remaining:
                amount = min(budget.allowance(), remaining)
                # urllib's socket timeout also bounds a blocking final read.
                sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                if sock is not None:
                    sock.settimeout(min(30.0, budget.remaining_seconds()))
                block = response.read(amount)
                budget.received += len(block)
                budget.remaining_seconds()
                if not block:
                    raise RuntimeError('Truncated archive response; stop, no retry')
                output.write(block)
                remaining -= len(block)
        partial.rename(path)
    return {'url': URL, 'status': 200, 'bodyBytes': budget.received, 'redirects': 0, 'retries': 0,
            'elapsedSeconds': round(budget.clock() - budget.started, 3)}


def xml_entities(text):
    def replace(match):
        name = match.group(1)
        if name in XML_PREDEFINED_ENTITIES:
            return match.group(0)
        if name not in DBLP_NAMED_ENTITIES:
            raise ValueError('Unknown DBLP named entity: ' + name)
        return DBLP_NAMED_ENTITIES[name]
    return ENTITY_REF_RE.sub(replace, text)


def publication_records(source, chunk_size=1024 * 1024):
    """Find complete inproceedings across arbitrary line/chunk boundaries.

    DBLP joins closing/opening publication tags on one line. Never assume
    newline-delimited records; retain at most one record plus one chunk.
    """
    buffer = ''
    opening, closing = '<inproceedings', '</inproceedings>'
    while block := source.read(chunk_size):
        buffer += block
        offset = 0
        while True:
            begin = buffer.find(opening, offset)
            if begin < 0:
                buffer = buffer[max(offset, len(buffer) - len(opening)):]
                break
            end = buffer.find(closing, begin)
            if end < 0:
                buffer = buffer[begin:]
                if len(buffer) > 16 * 1024 * 1024:
                    raise ValueError('Publication exceeds 16 MiB bounded scanner limit')
                break
            offset = end + len(closing)
            yield buffer[begin:offset]
    if opening in buffer:
        raise ValueError('Truncated final publication')


def select_slice(archive, output, per_venue_cap=PER_VENUE_CAP):
    counts, years, teams, people = Counter(), Counter(), Counter(), set()
    records, observed = [], 0
    selected_keys = []
    with gzip.open(archive, 'rt', encoding='utf-8') as source:
        for text in publication_records(source):
            observed += 1
            match = re.search(r'\bkey="conf/([^/]+)/[^"\n]+"', text)
            if not match or match.group(1) not in VENUE_ALIASES:
                continue
            venue = VENUE_ALIASES[match.group(1)]
            if counts[venue] >= per_venue_cap:
                continue
            node = ET.fromstring(xml_entities(text))
            year = int(node.findtext('year', '-1'))
            if not MIN_YEAR <= year <= MAX_YEAR:
                continue
            # Numeric entities make self-contained XML without DTD fetching.
            records.append(xml_entities(text).strip())
            counts[venue] += 1
            years[str(year)] += 1
            selected_keys.append(node.attrib['key'])
            authors = [''.join(a.itertext()) for a in node.findall('author')]
            people.update(authors)
            teams[len(authors)] += 1
    if not records:
        raise ValueError('Empty approved slice')
    document = '<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n' + '\n'.join(records) + '\n</dblp>\n'
    with output.open('x', encoding='utf-8', newline='\n') as target:
        target.write(document)
    return {'publicationCount': len(records), 'distinctExactAuthorStrings': len(people),
            'perVenue': dict(sorted(counts.items())), 'perYear': dict(sorted(years.items())),
            'authorCountHistogram': {str(k): v for k, v in sorted(teams.items())},
            'maximumAuthorCount': max(teams, default=0),
            'publicationCountOver16Authors': sum(v for k, v in teams.items() if k > 16),
            'publicationCountOver32Authors': sum(v for k, v in teams.items() if k > 32),
            'observedInproceedings': observed,
            'selectedKeysSha256': hashlib.sha256(('\n'.join(selected_keys) + '\n').encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=Path('target/phase6-inputs/6fg-dblp/dblp-2026-10-03.xml.gz'))
    parser.add_argument('--output', type=Path, default=Path('target/phase6-inputs/6fg-dblp/dblp.xml'))
    parser.add_argument('--acquisition-receipt', type=Path, help='Optional earlier network acquisition receipt to retain alongside local extraction')
    parser.add_argument('--manifest', type=Path, default=Path('datasets/phase6/dblp-slice-manifest.v1.json'))
    args = parser.parse_args()
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    budget = Budget()
    retrieval = {'mode': 'verified-local-copy', 'bodyBytes': 0}
    try:
        if not args.archive.exists():
            retrieval = {'mode': 'pinned-download', **download(args.archive, budget)}
        archive_hash = verify_archive(args.archive)
        print(json.dumps({'archiveVerified': archive_hash, 'retrieval': retrieval}), flush=True)
        selection = select_slice(args.archive, args.output)
        manifest = {'schemaVersion': 'scholarchain.dataset.phase6-slice.v1',
                    'source': {'release': 'dblp-2026-10-03', 'doi': '10.4230/dblp.xml.2026-10-03',
                               'url': URL, 'archive': str(args.archive), **archive_hash},
                    'license': {'name': 'CC0 1.0 Universal (DBLP bibliographic metadata)',
                                'evidenceUrl': LICENSE_URL, 'evidence': 'datasets/dataset-manifest.yaml'},
                    'selection': {'recordType': 'inproceedings', 'venueKeyPrefixes': ['conf/' + v + '/' for v in VENUE_ALIASES],
                                  'venueKeyAliases': VENUE_ALIASES,
                                  'minYear': MIN_YEAR, 'maxYear': MAX_YEAR, 'maximumRecords': 20000,
                                  'perVenueMaximumRecords': PER_VENUE_CAP,
                                  'order': 'First eligible records in pinned archive source order, independently per venue',
                                  'bias': 'Convenience slice; per-venue cap and source order are not a random sample', **selection},
                    'output': {'path': str(args.output), **hashes(args.output)},
                    'retrieval': retrieval, 'approvedNetworkCaps': {'bytes': BYTE_CAP, 'seconds': SECONDS_CAP},
                    'script': {'path': 'datasets/scripts/phase6/acquire_dblp_slice.py', 'sha256': hashes(Path(__file__))['sha256']},
                    'createdAt': datetime.now(timezone.utc).isoformat()}
        if args.acquisition_receipt:
            receipt = json.loads(args.acquisition_receipt.read_text())
            if receipt.get('url') != URL or receipt.get('bodyBytes') != EXPECTED_BYTES:
                raise ValueError('Acquisition receipt is not for the complete pinned archive')
            manifest['archiveAcquisitionReceipt'] = {'path': str(args.acquisition_receipt), **receipt}
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open('x') as target:
            json.dump(manifest, target, indent=2, sort_keys=True)
            target.write('\n')
        print(json.dumps(manifest, sort_keys=True), flush=True)
    except Exception as error:
        print(json.dumps({'status': 'STOPPED', 'error': str(error), 'networkBodyBytes': budget.received,
                          'networkByteCap': BYTE_CAP, 'networkSecondsCap': SECONDS_CAP}), file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
