#!/usr/bin/env python3
"""Select the Phase 15 P21 DBLP L slice (about 50,000 works) as a strict superset of S.

Offline only: this script never opens a network connection. The pinned
dblp-2026-10-03 archive must already be present (fetched once by the reviewed
bounded downloader datasets/scripts/phase6/acquire_dblp_slice.py) and must match
the pinned size, MD5 and SHA-256 before any record is read.

Rule (deterministic on the pinned archive):
  * Same record type (inproceedings), same years (2005-2026), same per-venue cap
    (2,500 first eligible records in archive source order), same record
    normalization and document framing as the Phase 6 S slice.
  * Venues: the 8 S venues always, then whole candidate venues taken in the fixed
    CANDIDATE_VENUES priority order while the running total stays <= TARGET_MAX.
    The first candidate that would push the total above TARGET_MAX stops the
    list (prefix rule, no skipping). Because each venue adds at most 2,500, the
    result lies in (TARGET_MAX - 2,500, TARGET_MAX] unless candidates run out;
    a total below MINIMUM_TOTAL fails.
Nesting S subset-of L is proved, not assumed: S is rebuilt from L's records under
S's own recorded rule and must reproduce the committed S manifest's output
SHA-256, selected-keys SHA-256, count and per-venue counts; if the S XML is
present its keys must all be in L. Any violation stops before output is written.
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
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / 'phase6'))
sys.path.insert(0, str(HERE.parents[1]))
import acquire_dblp_slice as s6  # noqa: E402  (reuse exact S scanner and normalization)

PINNED_ARCHIVE = {'bytes': s6.EXPECTED_BYTES, 'md5': s6.EXPECTED_MD5,
                  'sha256': '20e45961bec5610dc07b8e932ccd27a2387534cfa12c92a24289fe873aebe969'}
PER_VENUE_CAP = 2500
MIN_YEAR, MAX_YEAR = 2005, 2026
TARGET_MAX = 50000
MINIMUM_TOTAL = 45000
# Priority order: closest to the S community (distributed computing theory,
# OS/storage/cloud systems, dependability, parallel/HPC, networking/measurement,
# then data systems and security) so added coauthors connect to the S core.
CANDIDATE_VENUES = (
    ('usenix', ('usenix',)),        # USENIX ATC
    ('fast', ('fast',)),
    ('socc', ('cloud',)),           # ACM SoCC is DBLP conf/cloud
    ('hotos', ('hotos',)),
    ('asplos', ('asplos',)),
    ('opodis', ('opodis',)),
    ('spaa', ('spaa',)),
    ('sss', ('sss',)),
    ('sirocco', ('sirocco',)),
    ('srds', ('srds',)),
    ('dsn', ('dsn',)),
    ('hpdc', ('hpdc',)),
    ('ppopp', ('ppopp',)),
    ('cluster', ('cluster',)),
    ('ccgrid', ('ccgrid',)),
    ('icpp', ('icpp',)),
    ('europar', ('europar',)),
    ('ipdps', ('ipps',)),           # IPDPS is DBLP conf/ipps
    ('sc', ('sc',)),
    ('sigcomm', ('sigcomm',)),
    ('conext', ('conext',)),
    ('imc', ('imc',)),
    ('sigmetrics', ('sigmetrics',)),
    ('infocom', ('infocom',)),
    ('mobisys', ('mobisys',)),
    ('sigmod', ('sigmod',)),
    ('icde', ('icde',)),
    ('www', ('www',)),
    ('ccs', ('ccs',)),
    ('uss', ('uss',)),
    ('ndss', ('ndss',)),
)
SCHEMA_VERSION = 'scholarchain.dataset.phase15-l-slice.v1'
KEY_RE = re.compile(r'\bkey="conf/([^/]+)/[^"\n]+"')


class NestingError(RuntimeError):
    """S is not a strict subset of L; never write L."""


def verify_pinned_archive(path, expected=PINNED_ARCHIVE):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f'Archive {path} is not present; this script never downloads. '
                                'Fetch it once with the approved bounded downloader first.')
    observed = s6.hashes(path)
    for field in ('bytes', 'md5', 'sha256'):
        if observed[field] != expected[field]:
            raise RuntimeError(f'Pinned archive {field} mismatch ({observed[field]} != {expected[field]}); refusing extraction')
    return observed


def load_s_rule(s_manifest):
    selection = s_manifest['selection']
    rule = {'aliases': dict(selection['venueKeyAliases']), 'cap': int(selection['perVenueMaximumRecords']),
            'minYear': int(selection['minYear']), 'maxYear': int(selection['maxYear'])}
    if selection.get('recordType') != 'inproceedings':
        raise NestingError('S record type is not inproceedings')
    return rule


def l_aliases(s_rule, candidates):
    aliases = dict(s_rule['aliases'])
    for venue, keys in candidates:
        if venue in aliases.values():
            raise ValueError(f'Candidate venue {venue} collides with an S venue')
        for key in keys:
            if key in aliases:
                raise ValueError(f'Candidate key conf/{key}/ already assigned to {aliases[key]}')
            aliases[key] = venue
    return aliases


def check_rule_monotonic(s_rule, cap, min_year, max_year, aliases):
    """Every S record must remain eligible and selected under the L rule."""
    if cap < s_rule['cap']:
        raise NestingError(f'L per-venue cap {cap} is below S cap {s_rule["cap"]}')
    if min_year > s_rule['minYear'] or max_year < s_rule['maxYear']:
        raise NestingError('L year range does not cover the S year range')
    for key, venue in s_rule['aliases'].items():
        if aliases.get(key) != venue:
            raise NestingError(f'S venue key conf/{key}/ is not mapped identically in L')


def scan(archive, aliases, cap, min_year, max_year):
    """One pass: first `cap` eligible records per venue, in archive order."""
    counts, rows, observed = Counter(), [], 0
    with gzip.open(archive, 'rt', encoding='utf-8') as source:
        for seq, text in enumerate(s6.publication_records(source)):
            observed += 1
            match = KEY_RE.search(text)
            if not match or match.group(1) not in aliases:
                continue
            venue = aliases[match.group(1)]
            if counts[venue] >= cap:
                continue
            normalized = s6.xml_entities(text)
            node = ET.fromstring(normalized)
            year = int(node.findtext('year', '-1'))
            if not min_year <= year <= max_year:
                continue
            counts[venue] += 1
            rows.append({'seq': seq, 'venue': venue, 'key': node.attrib['key'], 'year': year,
                         'authors': [''.join(a.itertext()) for a in node.findall('author')],
                         'text': normalized.strip()})
    return rows, observed


def choose_venues(rows, s_venues, candidates, target_max, minimum):
    available = Counter(row['venue'] for row in rows)
    total = sum(available[v] for v in s_venues)
    included, stopped_at = [], None
    for venue, _ in candidates:
        if total + available[venue] > target_max:
            stopped_at = venue
            break
        total += available[venue]
        included.append(venue)
    if total < minimum:
        raise ValueError(f'L total {total} below minimum {minimum}; candidate list exhausted')
    return included, stopped_at, {venue: available[venue] for venue, _ in candidates}


def document(records):
    return '<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n' + '\n'.join(records) + '\n</dblp>\n'


def keys_sha256(keys):
    return hashlib.sha256(('\n'.join(keys) + '\n').encode()).hexdigest()


def summarize(rows):
    teams, people = Counter(len(r['authors']) for r in rows), set()
    for row in rows:
        people.update(row['authors'])
    return {'publicationCount': len(rows), 'distinctExactAuthorStrings': len(people),
            'perVenue': dict(sorted(Counter(r['venue'] for r in rows).items())),
            'perYear': dict(sorted(Counter(str(r['year']) for r in rows).items())),
            'authorCountHistogram': {str(k): v for k, v in sorted(teams.items())},
            'maximumAuthorCount': max(teams, default=0),
            'publicationCountOver16Authors': sum(v for k, v in teams.items() if k > 16),
            'publicationCountOver32Authors': sum(v for k, v in teams.items() if k > 32),
            'selectedKeysSha256': keys_sha256([r['key'] for r in rows])}


def nesting_check(l_rows, s_manifest, s_rule, s_xml=None):
    """Rebuild S from L under S's rule and prove S subset-of L, strictly."""
    counts, s_rows = Counter(), []
    for row in l_rows:
        venue = s_rule['aliases'].get(row['key'].split('/')[1])
        if venue is None or venue != row['venue'] or counts[venue] >= s_rule['cap']:
            continue
        if not s_rule['minYear'] <= row['year'] <= s_rule['maxYear']:
            continue
        counts[venue] += 1
        s_rows.append(row)
    rebuilt = document([r['text'] for r in s_rows]).encode('utf-8')
    rebuilt_sha = hashlib.sha256(rebuilt).hexdigest()
    selection = s_manifest['selection']
    s_keys = [r['key'] for r in s_rows]
    problems = []
    if rebuilt_sha != s_manifest['output']['sha256']:
        problems.append(f'rebuilt S sha256 {rebuilt_sha} != committed {s_manifest["output"]["sha256"]}')
    if keys_sha256(s_keys) != selection['selectedKeysSha256']:
        problems.append('rebuilt S selected-keys sha256 differs from committed S manifest')
    if len(s_rows) != selection['publicationCount']:
        problems.append(f'rebuilt S count {len(s_rows)} != committed {selection["publicationCount"]}')
    if dict(sorted(counts.items())) != dict(sorted(selection['perVenue'].items())):
        problems.append('rebuilt S per-venue counts differ from committed S manifest')
    l_keys = {r['key'] for r in l_rows}
    s_xml_result = {'checked': False}
    if s_xml is not None and Path(s_xml).is_file():
        observed = s6.hashes(s_xml)
        xml_keys = [n.attrib['key'] for n in ET.parse(s_xml).getroot()]
        missing = [k for k in xml_keys if k not in l_keys]
        if observed['sha256'] != s_manifest['output']['sha256']:
            problems.append('S XML file sha256 differs from committed S manifest')
        if missing:
            problems.append(f'{len(missing)} S XML keys missing from L, first {missing[0]}')
        s_xml_result = {'checked': True, 'path': str(s_xml), 'sha256': observed['sha256'],
                        'keys': len(xml_keys), 'keysMissingFromL': len(missing)}
    if not set(s_keys) <= l_keys:
        problems.append('rebuilt S keys are not all in L')
    if len(l_keys) <= len(set(s_keys)):
        problems.append('L is not a strict superset of S')
    if problems:
        raise NestingError('S subset-of L FAILED: ' + '; '.join(problems))
    return {'result': 'PASS', 'sPublicationCount': len(s_rows), 'lPublicationCount': len(l_rows),
            'sRebuiltOutputSha256': rebuilt_sha, 'sSelectedKeysSha256': keys_sha256(s_keys),
            'sKeysSubsetOfL': True, 'strictSuperset': True, 'sXmlFile': s_xml_result}


def build(archive, s_manifest_path, s_xml=None, expected=PINNED_ARCHIVE, candidates=CANDIDATE_VENUES,
          cap=PER_VENUE_CAP, min_year=MIN_YEAR, max_year=MAX_YEAR, target_max=TARGET_MAX,
          minimum=MINIMUM_TOTAL):
    """Return (xml_bytes, manifest_body) without writing anything."""
    archive_hash = verify_pinned_archive(archive, expected)
    s_manifest_bytes = Path(s_manifest_path).read_bytes()
    s_manifest = json.loads(s_manifest_bytes)
    s_rule = load_s_rule(s_manifest)
    aliases = l_aliases(s_rule, candidates)
    check_rule_monotonic(s_rule, cap, min_year, max_year, aliases)
    rows, observed = scan(archive, aliases, cap, min_year, max_year)
    s_venues = sorted(set(s_rule['aliases'].values()))
    included, stopped_at, candidate_counts = choose_venues(rows, s_venues, candidates, target_max, minimum)
    keep = set(s_venues) | set(included)
    l_rows = [r for r in rows if r['venue'] in keep]
    nesting = nesting_check(l_rows, s_manifest, s_rule, s_xml)
    nesting['sManifest'] = {'path': str(s_manifest_path), 'sha256': hashlib.sha256(s_manifest_bytes).hexdigest()}
    xml_bytes = document([r['text'] for r in l_rows]).encode('utf-8')
    selection = {'recordType': 'inproceedings', 'minYear': min_year, 'maxYear': max_year,
                 'perVenueMaximumRecords': cap, 'targetMaximumRecords': target_max,
                 'minimumRecords': minimum, 'sVenues': s_venues,
                 'candidateVenuePriority': [v for v, _ in candidates],
                 'candidateEligibleCounts': candidate_counts,
                 'includedCandidateVenues': included, 'stoppedAtCandidate': stopped_at,
                 'venueKeyAliases': {k: v for k, v in sorted(aliases.items()) if v in keep},
                 'order': 'First eligible records in pinned archive source order, independently per venue; output in archive order',
                 'venueRule': 'All S venues, then the longest prefix of candidateVenuePriority whose running total stays <= targetMaximumRecords',
                 'bias': 'Convenience slice; venue choice, per-venue cap and source order are not a random sample',
                 'observedInproceedings': observed, **summarize(l_rows)}
    return xml_bytes, {'schemaVersion': SCHEMA_VERSION,
                       'source': {'release': 'dblp-2026-10-03', 'doi': '10.4230/dblp.xml.2026-10-03',
                                  'url': s6.URL, 'archive': str(archive), **archive_hash},
                       'license': {'name': 'CC0 1.0 Universal (DBLP bibliographic metadata)',
                                   'evidenceUrl': s6.LICENSE_URL, 'evidence': 'datasets/dataset-manifest.yaml'},
                       'selection': selection, 'nestingCheck': nesting,
                       'retrieval': {'mode': 'verified-local-copy', 'bodyBytes': 0}}


def load_receipt(path, expected=PINNED_ARCHIVE):
    """Reject a receipt that is not for one complete download of the pinned archive."""
    receipt = json.loads(Path(path).read_text())
    if receipt.get('url') != s6.URL or receipt.get('bodyBytes') != expected['bytes']:
        raise ValueError('Acquisition receipt is not for the complete pinned archive')
    if receipt.get('sha256', expected['sha256']) != expected['sha256']:
        raise ValueError('Acquisition receipt sha256 differs from the pinned archive sha256')
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--archive', type=Path, default=Path('target/phase6-inputs/6fg-dblp/dblp-2026-10-03.xml.gz'))
    parser.add_argument('--s-manifest', type=Path, default=Path('datasets/phase6/dblp-slice-manifest.v1.json'))
    parser.add_argument('--s-xml', type=Path, default=Path('target/phase6-inputs/6fg-dblp/dblp.xml'),
                        help='S slice XML; its keys are checked against L when the file exists')
    parser.add_argument('--output', type=Path, default=Path('target/phase15-inputs/dblp-l/dblp.xml'))
    parser.add_argument('--manifest', type=Path, default=Path('datasets/phase15/dblp-l-slice-manifest.v1.json'))
    parser.add_argument('--acquisition-receipt', type=Path,
                        help='JSON receipt of the one approved archive download (url, bodyBytes, sha256); '
                             'validated against the pin before the archive is scanned')
    args = parser.parse_args(argv)
    for path in (args.output, args.manifest):
        if path.exists():
            raise FileExistsError(f'{path} exists; refusing to overwrite')
    try:
        receipt = load_receipt(args.acquisition_receipt) if args.acquisition_receipt else None
        xml_bytes, manifest = build(args.archive, args.s_manifest, args.s_xml)
        if receipt is not None:
            manifest['archiveAcquisitionReceipt'] = {'path': str(args.acquisition_receipt), **receipt}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('xb') as target:
            target.write(xml_bytes)
        manifest['output'] = {'path': str(args.output), **s6.hashes(args.output)}
        manifest['script'] = {'path': 'datasets/scripts/phase15/select_dblp_l_slice.py', 'sha256': s6.hashes(HERE)['sha256'],
                              'reusedModule': {'path': 'datasets/scripts/phase6/acquire_dblp_slice.py',
                                               'sha256': s6.hashes(Path(s6.__file__))['sha256']}}
        manifest['createdAt'] = datetime.now(timezone.utc).isoformat()
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        with args.manifest.open('x') as target:
            json.dump(manifest, target, indent=2, sort_keys=True)
            target.write('\n')
        print(json.dumps({'status': 'OK', 'publicationCount': manifest['selection']['publicationCount'],
                          'distinctExactAuthorStrings': manifest['selection']['distinctExactAuthorStrings'],
                          'perVenue': manifest['selection']['perVenue'], 'output': manifest['output'],
                          'nestingCheck': manifest['nestingCheck']['result']}, sort_keys=True), flush=True)
    except Exception as error:
        print(json.dumps({'status': 'STOPPED', 'error': str(error), 'networkBodyBytes': 0}), file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
