#!/usr/bin/env python3
"""Fixed, separately approved author-focused demo acquisition; no labels or models.

Root alone executes create. Every returned metadata row consumes the record cap,
including author profiles, duplicates and excluded works. There is no fallback.
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = 'scholarchain.author-focused-demo-population.v1'
PLAN_VERSION = 'scholarchain.author-focused-demo-plan.v1'
AUTHOR_NAME = 'Michael Benedikt'
SEED_DOI = '10.1145/3299887.3299889'
AUTHOR_FIELDS = 'id,display_name,orcid,affiliations'
WORK_FIELDS = 'id,doi,title,display_name,publication_year,publication_date,type,ids,authorships,primary_location,biblio,topics'
BOUNDS = {'returnedMetadataRecordsIncludingAuthorsDuplicatesExcluded': 30, 'httpAttemptsIncludingRetries': 20,
          'totalResponseBytes': 8 * 1024 * 1024, 'perResponseBytes': 2 * 1024 * 1024,
          'wallSeconds': 300, 'timeoutSeconds': 20, 'authorLookupRequests': 1,
          'authorProfiles': 5, 'authorWorkQueries': 5, 'recordsPerRequest': 5,
          'maxTransientRetries': 1, 'concurrency': 1, 'maxStartsPerSecond': 1,
          'recordBytes': 1024 * 1024}
VENUES = ('sigmod', 'vldb', 'data engineering', 'cloud computing', 'middleware', 'distributed',
          'operating systems', 'database', 'management of data', 'computing surveys', 'parallel', 'computer systems')


def enc(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load(path, cap=20 * 1024 * 1024):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > cap:
        raise ValueError('unsafe or oversized input')
    return path.read_bytes()


def authors_url():
    return 'https://api.openalex.org/authors?' + urllib.parse.urlencode({
        'search': AUTHOR_NAME, 'sort': 'relevance_score:desc', 'per-page': 5, 'select': AUTHOR_FIELDS})


def works_url(author):
    if not re.fullmatch(r'https://openalex.org/A[1-9][0-9]*', author):
        raise ValueError('invalid actually returned author ID')
    return 'https://api.openalex.org/works?' + urllib.parse.urlencode({
        'filter': f'author.id:{author.rsplit("/", 1)[-1]},from_publication_date:2018-01-01,to_publication_date:2024-12-31',
        'per-page': 5, 'sort': 'publication_date:asc', 'select': WORK_FIELDS})


def validate_plan(plan):
    expected = {'schemaVersion': PLAN_VERSION, 'authorSearch': AUTHOR_NAME, 'seedDoi': SEED_DOI,
                'authorSelect': AUTHOR_FIELDS, 'recordsPerRequest': 5,
                'maxReturnedRecordsIncludingAuthorLookups': 30}
    if any(plan.get(key) != value for key, value in expected.items()):
        raise ValueError('plan differs from fixed author/seed/field/record scope')
    stage = plan.get('stageId', '')
    if not re.fullmatch(r'[a-z0-9-]{1,100}', stage):
        raise ValueError('safe unique stage ID required')
    for field in ('seedPopulationManifestSha256', 'previousStageSha256', 'approvalReceiptSha256', 'seedLineSha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', plan.get(field, '')):
            raise ValueError('missing fixed receipt binding: ' + field)


def validate_approval(plan, approval_bytes):
    if sha(approval_bytes) != plan['approvalReceiptSha256']:
        raise ValueError('approval receipt hash differs')
    approval = json.loads(approval_bytes)
    limits = approval.get('limits', {})
    expected = {'returnedMetadataRecordsIncludingProfilesWorksDuplicatesAndExcluded': 30,
                'httpAttemptsIncludingRetries': 20, 'responseBytes': 8 * 1024 * 1024,
                'wallSeconds': 300, 'credentials': False, 'paidData': False}
    if limits != expected or approval.get('originalLiveApprovalUnchanged') is not True:
        raise ValueError('approval does not carry the approved fixed limits')


def selected_authors(profiles):
    ids = [record['id'] for record, _ in profiles]
    if any(not re.fullmatch(r'https://openalex.org/A[1-9][0-9]*', native) for native in ids):
        raise ValueError('invalid returned author ID')
    # Every returned profile is provisional, even an ORCID-bearing one. Never mask it.
    return sorted(set(ids))[:BOUNDS['authorWorkQueries']]


def allowed_work(record):
    year = record.get('publication_year') or 0
    venue = (((record.get('primary_location') or {}).get('source') or {}).get('display_name') or '').lower()
    return isinstance(year, int) and 2018 <= year <= 2024 and any(x in venue for x in VENUES) and len(enc(record)) <= BOUNDS['recordBytes']


class StopBudget(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, root, opener=None, clock=time.monotonic, sleep=time.sleep, start=None):
        self.root, self.clock, self.sleep = root, clock, sleep
        self.start, self.last = clock() if start is None else start, None
        self.events, self.bytes = [], 0
        self.returned_records, self.author_records, self.work_records = 0, 0, 0
        self.author_ids, self.work_ids = set(), set()
        self.stopped = False
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open

    def get(self, kind, author=None):
        if kind not in ('authors', 'works') or (kind == 'authors' and author is not None):
            raise ValueError('only fixed lookup or actual-author works request allowed')
        url = authors_url() if kind == 'authors' else works_url(author)
        if self.stopped:
            return []
        for retry in range(2):
            wait = max(0, 1 - (self.clock() - self.last)) if self.last is not None else 0
            if (len(self.events) >= BOUNDS['httpAttemptsIncludingRetries']
                    or self.bytes >= BOUNDS['totalResponseBytes']
                    or self.returned_records + BOUNDS['recordsPerRequest'] > BOUNDS['returnedMetadataRecordsIncludingAuthorsDuplicatesExcluded']
                    or self.clock() - self.start + wait >= BOUNDS['wallSeconds']):
                raise StopBudget('request/record/byte/wall allowance exhausted')
            if wait:
                self.sleep(wait)
            self.last = self.clock()
            event = {'attempt': len(self.events) + 1, 'recordKind': kind, 'authorId': author, 'url': url,
                     'retry': retry, 'retrievedAtUtc': utc(), 'result': 'incomplete', 'returnedRecords': 0}
            self.events.append(event)
            body, response, retry_ok = bytearray(), None, False
            try:
                try:
                    response = self.opener(urllib.request.Request(url, headers={
                        'User-Agent': 'ScholarChain-Authorized-5D-AuthorDemo/1.0', 'Accept': 'application/json', 'Accept-Encoding': 'identity'}),
                        timeout=min(BOUNDS['timeoutSeconds'], BOUNDS['wallSeconds'] - (self.clock() - self.start)))
                except urllib.error.HTTPError as error:
                    response = error
                event['status'] = response.status
                event['headers'] = {key: response.headers[key] for key in ('Content-Type', 'Retry-After', 'ETag') if key in response.headers}
                if response.headers.get('Content-Encoding', 'identity') not in ('', 'identity'):
                    raise ValueError('unexpected content encoding')
                cap = min(BOUNDS['perResponseBytes'], BOUNDS['totalResponseBytes'] - self.bytes)
                while len(body) < cap:
                    remaining = BOUNDS['wallSeconds'] - (self.clock() - self.start)
                    if remaining <= 0:
                        raise StopBudget('wall allowance exhausted during body')
                    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                    if sock is not None:
                        sock.settimeout(min(BOUNDS['timeoutSeconds'], remaining))
                    part = response.read(min(65536, cap - len(body)))
                    if not part:
                        break
                    body.extend(part)
                    self.bytes += len(part)
                if len(body) >= cap:
                    raise StopBudget('response byte cap reached')
                if response.status != 200:
                    event['result'] = 'http-error'
                    retry_ok = response.status in (500, 502, 503, 504) and retry == 0 and not event['headers'].get('Retry-After')
                    if not retry_ok:
                        self.stopped = True
                else:
                    results = json.loads(body).get('results')
                    if not isinstance(results, list):
                        raise ValueError('expected results array')
                    # Count rows before filtering, deduplication or any identity interpretation.
                    event['returnedRecords'] = len(results)
                    self.returned_records += len(results)
                    if kind == 'authors': self.author_records += len(results)
                    else: self.work_records += len(results)
                    if len(results) > 5 or self.returned_records > 30:
                        raise StopBudget('server exceeded requested metadata-record bound')
                    prefix = 'A' if kind == 'authors' else 'W'
                    for record in results:
                        if not isinstance(record, dict) or not re.fullmatch(r'https://openalex.org/' + prefix + r'[1-9][0-9]*', record.get('id', '')):
                            raise ValueError('invalid native record ID')
                        (self.author_ids if kind == 'authors' else self.work_ids).add(record['id'])
                    if any('abstract_inverted_index' in record or 'fulltext' in record for record in results):
                        raise ValueError('unexpected abstract/fulltext field')
                    event['result'] = 'ok'
                    return [(record, event['attempt']) for record in results]
            except (urllib.error.URLError, socket.timeout, TimeoutError) as error:
                event['result'], event['errorType'] = 'network-error', type(error).__name__
                retry_ok = retry == 0
                if not retry_ok: self.stopped = True
            except (ValueError, UnicodeError) as error:
                event['result'], event['errorType'] = 'schema-or-access-error', type(error).__name__
                self.stopped = True
            finally:
                if response is not None:
                    response.close()
                event['bytesRead'] = len(body)
                if body:
                    rel = f'responses/{event["attempt"]:03d}-{kind}.body'
                    (self.root / rel).write_bytes(body)
                    event.update(responsePath=rel, sha256=sha(body))
                with (self.root / 'request-ledger.jsonl').open('ab') as handle:
                    handle.write(enc(event) + b'\n')
            if retry_ok:
                self.sleep(1)
                continue
            return []


def history_facts(root, seen=None):
    seen = set() if seen is None else seen
    body = load(root / 'population-manifest.v1.json')
    if sha(body) in seen:
        return {'works': set(), 'authors': set(), 'returnedWorks': 0, 'returnedAuthors': 0, 'attempts': 0, 'bytes': 0, 'seconds': 0.0}
    seen.add(sha(body))
    manifest = json.loads(body)
    events = [json.loads(line) for line in load(root / 'request-ledger.jsonl').splitlines()]
    result = {'works': set(), 'authors': set(), 'returnedWorks': 0, 'returnedAuthors': 0,
              'attempts': len(events), 'bytes': sum(event['bytesRead'] for event in events), 'seconds': manifest['observed']['seconds']}
    for event in events:
        if event.get('result') == 'ok' and event.get('responsePath'):
            records = json.loads(load(root / event['responsePath'])).get('results', [])
            kind = 'authors' if event.get('recordKind') == 'authors' else 'works'
            result[kind].update(record['id'] for record in records)
            result['returnedAuthors' if kind == 'authors' else 'returnedWorks'] += len(records)
    for child in ('context', 'previous-stage'):
        if (root / child / 'population-manifest.v1.json').is_file():
            nested = history_facts(root / child, seen)
            result['works'].update(nested['works']); result['authors'].update(nested['authors'])
            for field in ('returnedWorks', 'returnedAuthors', 'attempts', 'bytes', 'seconds'):
                result[field] += nested[field]
    return result


def seed_record(population):
    manifest_bytes = load(population / 'population-manifest.v1.json')
    manifest = json.loads(manifest_bytes)
    source = manifest['sources']['crossref']
    source_bytes = load(population / source['path'])
    if len(source_bytes) != source['bytes'] or sha(source_bytes) != source['sha256']:
        raise ValueError('original Crossref source bytes differ')
    found = [(index, line) for index, line in enumerate(source_bytes.splitlines(keepends=True), 1)
             if json.loads(line).get('message', {}).get('DOI', '').lower() == SEED_DOI]
    if len(found) != 1:
        raise ValueError('exactly one approved seed DOI required')
    index, line = found[0]
    if not line.endswith(b'\n'):
        raise ValueError('source seed line needs original JSONL newline')
    return manifest_bytes, source_bytes, source, index, line


def copy_population(source, destination):
    manifest_bytes = load(source / 'population-manifest.v1.json')
    manifest = json.loads(manifest_bytes)
    for rel, fact in manifest['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('unsafe historical path')
        data = load(source / rel)
        if sha(data) != fact['sha256'] or len(data) != fact['bytes']:
            raise ValueError('historical stage file differs')
    for rel in list(manifest['files']) + ['population-manifest.v1.json']:
        dest = destination / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(load(source / rel))


def publish(output, plan_path, approval_path, seed_population, previous_stage):
    started = time.monotonic()
    if output.exists():
        raise ValueError('new output required; never overwrite')
    plan_bytes, approval_bytes = load(plan_path), load(approval_path)
    plan = json.loads(plan_bytes)
    validate_plan(plan)
    validate_approval(plan, approval_bytes)
    if plan['stageId'] != output.name:
        raise ValueError('output must match unique declared stage ID')
    manifest_bytes, crossref_bytes, seed_source, seed_index, seed_line = seed_record(seed_population)
    if sha(seed_line) != plan['seedLineSha256']:
        raise ValueError('approved seed line binding differs')
    previous_manifest = load(previous_stage / 'population-manifest.v1.json')
    if plan.get('seedPopulationManifestSha256') != sha(manifest_bytes) or plan.get('previousStageSha256') != sha(previous_manifest):
        raise ValueError('seed/previous-stage receipt binding differs')
    prior = history_facts(previous_stage)
    output.mkdir(parents=True, exist_ok=False)
    for name in ('scripts', 'responses', 'input', 'lookup', 'seed', 'proof'):
        (output / name).mkdir()
    script = Path(__file__).read_bytes()
    (output / 'scripts/acquire_author_focused_demo.py').write_bytes(script)
    (output / 'proof/plan.json').write_bytes(plan_bytes)
    (output / 'proof/user-approval.json').write_bytes(approval_bytes)
    (output / 'seed/population-manifest.v1.json').write_bytes(manifest_bytes)
    (output / 'seed/crossref-original-works.jsonl').write_bytes(crossref_bytes)
    (output / 'input/crossref.jsonl').write_bytes(seed_line)
    copy_population(previous_stage, output / 'previous-stage')
    (output / 'request-ledger.jsonl').write_bytes(b'')
    profiles, returned, authors, exclusions = [], {}, [], []
    client, status = Client(output, start=started), 'COMPLETE_WITHIN_BOUNDS'
    try:
        profiles = client.get('authors')
        authors = selected_authors(profiles)
        for author in authors:
            for record, attempt in client.get('works', author):
                returned.setdefault(record['id'], (record, attempt, author))
            if client.stopped: break
    except StopBudget as error:
        status = 'PARTIAL_BUDGET_STOP'
        exclusions.append({'reason': str(error)})
    if client.stopped and status == 'COMPLETE_WITHIN_BOUNDS': status = 'STOPPED_ACCESS_OR_SCHEMA'
    accepted, proofs = [], []
    for native, (record, attempt, author) in sorted(returned.items()):
        if not allowed_work(record):
            exclusions.append({'id': native, 'reason': 'year-CS-venue-or-record-byte-filter', 'requestAttempt': attempt})
            continue
        accepted.append(record)
        proofs.append({'nativeId': native, 'recordSha256': sha(enc(record)), 'requestAttempt': attempt, 'provisionalAuthorId': author})
    (output / 'lookup/authors.jsonl').write_bytes(b''.join(enc(record) + b'\n' for record, _ in profiles))
    (output / 'input/openalex.jsonl').write_bytes(b''.join(enc(record) + b'\n' for record in accepted))
    (output / 'input/orcid.jsonl').write_bytes(b'')
    (output / 'input/dblp.xml').write_bytes(b'<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n</dblp>\n')
    (output / 'record-provenance.jsonl').write_bytes(b''.join(enc(row) + b'\n' for row in proofs))
    (output / 'selection-exclusions.json').write_bytes(enc(exclusions) + b'\n')
    trace = {'lookupName': AUTHOR_NAME, 'returnedProfileIds': [x['id'] for x, _ in profiles],
             'selectedProvisionalAuthorIds': authors, 'profileLookupUsedAsIdentityEvidence': False,
             'rules': 'Sorted actually returned IDs only; all ORCIDs and profile fields retained as observed; no identity assertion, pagination, refill, labels or scoring.'}
    (output / 'selection-trace.json').write_bytes(enc(trace) + b'\n')
    elapsed = round(client.clock() - client.start, 4)
    retrieval_date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    sources = {}
    for source, rel, count in [('openalex', 'input/openalex.jsonl', len(accepted)), ('crossref', 'input/crossref.jsonl', 1), ('orcid', 'input/orcid.jsonl', 0), ('dblp', 'input/dblp.xml', 0)]:
        sources[source] = {'path': rel, 'records': count, 'sha256': sha((output / rel).read_bytes()),
                           'snapshotId': seed_source['snapshotId'] if source == 'crossref' else f'{source}-{plan["stageId"]}',
                           'retrievalDate': seed_source['retrievalDate'] if source == 'crossref' else retrieval_date}
    manifest = {'schemaVersion': VERSION, 'status': status, 'stageId': plan['stageId'], 'bounds': BOUNDS, 'createdAtUtc': utc(),
                'sources': sources, 'executedScript': {'path': 'scripts/acquire_author_focused_demo.py', 'sha256': sha(script)},
                'planSha256': sha(plan_bytes), 'approvalReceiptSha256': sha(approval_bytes), 'previousStageSha256': sha(previous_manifest),
                'seed': {'doi': SEED_DOI, 'originalPopulationManifestSha256': sha(manifest_bytes), 'originalSource': seed_source,
                         'sourceLineNumber': seed_index, 'exactSourceLineSha256': sha(seed_line), 'bytes': len(seed_line)},
                'observed': {'httpAttempts': len(client.events), 'responseBytes': client.bytes, 'seconds': elapsed,
                             'returnedMetadataRecordsIncludingDuplicatesExcluded': client.returned_records,
                             'returnedAuthorProfileRecords': client.author_records, 'returnedWorkRecords': client.work_records,
                             'distinctAuthorProfileIds': len(client.author_ids), 'distinctWorkIdsIncludingExcluded': len(client.work_ids),
                             'newWorkIdsNotObservedInPriorStages': len(client.work_ids - prior['works']), 'newIngestionWorks': len(accepted)},
                'cumulative': {'distinctWorkIdsAcrossStages': len(prior['works'] | client.work_ids),
                               'distinctAuthorProfileIdsAcrossStages': len(prior['authors'] | client.author_ids),
                               'returnedWorkRecordsAcrossStages': prior['returnedWorks'] + client.work_records,
                               'returnedAuthorProfileRecordsAcrossStages': prior['returnedAuthors'] + client.author_records,
                               'returnedMetadataRecordsAcrossStages': prior['returnedWorks'] + prior['returnedAuthors'] + client.returned_records,
                               'httpAttemptsAcrossStages': prior['attempts'] + len(client.events),
                               'responseBytesAcrossStages': prior['bytes'] + client.bytes,
                               'secondsAcrossStages': round(prior['seconds'] + elapsed, 4)},
                'heldOutAdmissionStatus': 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING', 'humanReviews': 0,
                'limitations': ['Author lookup profiles are discovery metadata only, not researcher resolution or ingested author facts.',
                               'All profiles, duplicates and excluded records consume the new-stage 30-record cap.',
                               'Canonical whole-component held-out exclusion must precede scoring; no eligible pair or provider evidence is claimed.',
                               'Only the exact approved existing Crossref publication is reused; original source snapshot and retrieval date are preserved.']}
    manifest['files'] = {p.relative_to(output).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'population-manifest.v1.json').write_bytes(enc(manifest) + b'\n')
    return validate(output)


def validate(root):
    m = json.loads(load(root / 'population-manifest.v1.json'))
    if m['schemaVersion'] != VERSION or m['bounds'] != BOUNDS: raise ValueError('schema/bounds differ')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(m['files']) | {'population-manifest.v1.json'}: raise ValueError('inventory differs')
    for rel, fact in m['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts: raise ValueError('unsafe manifest path')
        body = load(root / rel)
        if sha(body) != fact['sha256'] or len(body) != fact['bytes']: raise ValueError('file hash differs: ' + rel)
    plan = json.loads(load(root / 'proof/plan.json')); validate_plan(plan)
    validate_approval(plan, load(root / 'proof/user-approval.json'))
    if plan['stageId'] != m['stageId']:
        raise ValueError('declared stage differs')
    if sha(load(root / 'proof/plan.json')) != m['planSha256'] or sha(load(root / 'proof/user-approval.json')) != m['approvalReceiptSha256']: raise ValueError('receipt differs')
    if sha(load(root / m['executedScript']['path'])) != m['executedScript']['sha256']: raise ValueError('script differs')
    if sha(load(root / 'previous-stage/population-manifest.v1.json')) != m['previousStageSha256']: raise ValueError('history differs')
    if m['previousStageSha256'] != plan['previousStageSha256']:
        raise ValueError('planned history differs')
    original = json.loads(load(root / 'seed/population-manifest.v1.json'))
    original_source = original['sources']['crossref']
    if sha(load(root / 'seed/population-manifest.v1.json')) != plan['seedPopulationManifestSha256']:
        raise ValueError('planned seed population differs')
    original_bytes = load(root / 'seed/crossref-original-works.jsonl')
    if sha(original_bytes) != original_source['sha256'] or len(original_bytes) != original_source['bytes']: raise ValueError('seed original bytes differ')
    line = original_bytes.splitlines(keepends=True)[m['seed']['sourceLineNumber'] - 1]
    if (line != load(root / 'input/crossref.jsonl') or sha(line) != m['seed']['exactSourceLineSha256']
            or sha(line) != plan['seedLineSha256']
            or json.loads(line)['message']['DOI'].lower() != SEED_DOI): raise ValueError('approved exact seed line differs')
    if (m['sources']['crossref']['snapshotId'], m['sources']['crossref']['retrievalDate']) != (original_source['snapshotId'], original_source['retrievalDate']): raise ValueError('seed source identity rewritten')
    for source, fact in m['sources'].items():
        data = load(root / fact['path'])
        if sha(data) != fact['sha256']:
            raise ValueError('source hash differs')
        if source in ('openalex', 'crossref', 'orcid') and len(data.splitlines()) != fact['records']:
            raise ValueError('source count differs')
        if source != 'crossref' and fact['snapshotId'] != f'{source}-{m["stageId"]}':
            raise ValueError('source snapshot must be stage-unique')
    ledger = [json.loads(line) for line in load(root / 'request-ledger.jsonl').splitlines()]
    if [e['attempt'] for e in ledger] != list(range(1, len(ledger) + 1)): raise ValueError('attempt sequence differs')
    counts = {'authors': 0, 'works': 0}; ids = {'authors': set(), 'works': set()}; profile_rows = []
    responses = {}
    for event in ledger:
        expected = authors_url() if event['recordKind'] == 'authors' else works_url(event['authorId'])
        if event['url'] != expected or event['retry'] not in (0, 1): raise ValueError('escaped fixed request plan')
        if event.get('responsePath'):
            body = load(root / event['responsePath'])
            if len(body) != event['bytesRead'] or sha(body) != event['sha256']: raise ValueError('ledger response differs')
            if event['result'] == 'ok':
                rows = json.loads(body)['results']; responses[event['attempt']] = rows
                if len(rows) > 5 or len(rows) != event['returnedRecords']: raise ValueError('response row bound differs')
                counts[event['recordKind']] += len(rows)
                ids[event['recordKind']].update(row['id'] for row in rows)
                if event['recordKind'] == 'authors': profile_rows.extend((row, event['attempt']) for row in rows)
    total = sum(counts.values())
    if total > 30 or len(ledger) > 20 or sum(e['bytesRead'] for e in ledger) > BOUNDS['totalResponseBytes'] or m['observed']['seconds'] > 300: raise ValueError('approved stage cap exceeded')
    if (counts['authors'], counts['works'], total) != (m['observed']['returnedAuthorProfileRecords'], m['observed']['returnedWorkRecords'], m['observed']['returnedMetadataRecordsIncludingDuplicatesExcluded']): raise ValueError('author/work/total record accounting differs')
    if len(ledger) != m['observed']['httpAttempts'] or sum(e['bytesRead'] for e in ledger) != m['observed']['responseBytes']: raise ValueError('request/byte counters differ')
    selected = selected_authors(profile_rows)
    if any(e['authorId'] not in selected for e in ledger if e['recordKind'] == 'works'): raise ValueError('unobserved author queried')
    initial = [e for e in ledger if e['retry'] == 0]
    if initial and [(e['recordKind'], e['authorId']) for e in initial] != [('authors', None)] + [('works', author) for author in selected[:len(initial) - 1]]:
        raise ValueError('query schedule differs from actual sorted authors')
    for index, event in enumerate(ledger):
        if event['retry'] == 1:
            previous = ledger[index - 1] if index else {}
            if previous.get('retry') != 0 or previous.get('url') != event['url'] or previous.get('result') not in ('network-error', 'http-error'):
                raise ValueError('invalid retry sequence')
    lookup = [json.loads(line) for line in load(root / 'lookup/authors.jsonl').splitlines()]
    if lookup != [row for row, _ in profile_rows]: raise ValueError('lookup profiles changed or masked')
    works = [json.loads(line) for line in load(root / 'input/openalex.jsonl').splitlines()]
    proofs = [json.loads(line) for line in load(root / 'record-provenance.jsonl').splitlines()]
    if len(works) != m['sources']['openalex']['records'] or len(proofs) != len(works) or len({row['id'] for row in works}) != len(works): raise ValueError('ingestion/proof count differs')
    proof = {row['nativeId']: row for row in proofs}
    for row in works:
        fact = proof[row['id']]
        if row not in responses[fact['requestAttempt']] or fact['recordSha256'] != sha(enc(row)) or not allowed_work(row): raise ValueError('ingestion lacks original bounded response')
    observed_works = {}
    for event in ledger:
        if event['recordKind'] == 'works' and event['result'] == 'ok':
            for row in responses[event['attempt']]:
                observed_works.setdefault(row['id'], (row, event['attempt'], event['authorId']))
    expected_works = [row for _, (row, _, _) in sorted(observed_works.items()) if allowed_work(row)]
    if works != expected_works:
        raise ValueError('ingestion selection differs from all original responses')
    if len(ids['authors']) != m['observed']['distinctAuthorProfileIds'] or len(ids['works']) != m['observed']['distinctWorkIdsIncludingExcluded'] or len(works) != m['observed']['newIngestionWorks']:
        raise ValueError('distinct/ingestion counters differ')
    history = history_facts(root)
    expected_history = {'distinctWorkIdsAcrossStages': len(history['works']), 'distinctAuthorProfileIdsAcrossStages': len(history['authors']),
                        'returnedWorkRecordsAcrossStages': history['returnedWorks'], 'returnedAuthorProfileRecordsAcrossStages': history['returnedAuthors'],
                        'returnedMetadataRecordsAcrossStages': history['returnedWorks'] + history['returnedAuthors'], 'httpAttemptsAcrossStages': history['attempts'],
                        'responseBytesAcrossStages': history['bytes'], 'secondsAcrossStages': round(history['seconds'], 4)}
    if expected_history != m['cumulative']: raise ValueError('cumulative retained history counters differ')
    if m['heldOutAdmissionStatus'] != 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING' or m['humanReviews'] != 0: raise ValueError('false admission or review claim')
    return {'status': 'VALID', 'schemaVersion': VERSION, 'sources': {source: fact['records'] for source, fact in m['sources'].items()},
            'observed': m['observed'], 'cumulative': m['cumulative'], 'files': len(m['files']), 'admission': m['heldOutAdmissionStatus']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    create = subs.add_parser('create')
    for flag in ('output', 'plan', 'approval', 'seed-population', 'previous-stage'): create.add_argument('--' + flag, type=Path, required=True)
    check = subs.add_parser('validate'); check.add_argument('--population', type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.population.resolve()) if args.command == 'validate' else publish(args.output.resolve(), args.plan.resolve(), args.approval.resolve(), args.seed_population.resolve(), args.previous_stage.resolve())
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
