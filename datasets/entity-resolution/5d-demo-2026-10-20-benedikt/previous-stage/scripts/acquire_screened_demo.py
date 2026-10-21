#!/usr/bin/env python3
"""Separately approved, screened Phase 5D demo search. Never reads labels.

No credentials, scores, provider calls, or acquisition fallbacks. Root runs HTTP.
"""
import argparse
import datetime as dt
import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

VERSION = 'scholarchain.screened-demo-population.v1'
DISCOVERY_ORDER = 'relevance_score:desc'
QUERY_PLAN_VERSION = 'scholarchain.topic-discovery-order.v2'
LEGACY_DISCOVERY_ORDER = 'publication_date:asc'
LEGACY_EXECUTED_SCRIPT_SHA256 = '71bc8f13da743ad129b1a82f7e560d36002e15daa3145033c7bbd9f0046d0d9a'
BOUNDS = {'newDistinctOpenAlexWorksIncludingExcluded': 30, 'httpAttemptsIncludingRetries': 20,
          'responseBytes': 8 * 1024 * 1024, 'perResponseBytes': 2 * 1024 * 1024,
          'wallSeconds': 300, 'timeoutSeconds': 20, 'discoveryQueries': 2, 'authors': 4, 'worksPerAuthor': 5,
          'maxTransientRetries': 1, 'concurrency': 1, 'maxStartsPerSecond': 1,
          'recordBytes': 1024 * 1024}
FIELDS = 'id,doi,title,display_name,publication_year,publication_date,type,ids,authorships,primary_location,biblio,topics'
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


TOPICS = ('state machine replication', 'distributed stream processing')


def validate_plan(plan, screen_bytes):
    if (plan.get('schemaVersion') != 'scholarchain.topic-demo-plan.v1'
            or plan.get('screenReceiptSha256') != sha(screen_bytes)
            or plan.get('queries') != list(TOPICS)):
        raise ValueError('fixed topic plan or preceding screen receipt mismatch')


def choose_authors(discovered):
    import re
    authors, known_orcid = set(), set()
    for work, _ in discovered:
        if not allowed(work):
            continue
        for authorship in work.get('authorships', []):
            author = authorship.get('author') or {}
            aid = author.get('id', '')
            institutions = authorship.get('institutions') or []
            if author.get('orcid'):
                known_orcid.add(aid)
            if (re.fullmatch(r'https://openalex.org/A[1-9][0-9]*', aid)
                    and author.get('orcid') is None
                    and any(isinstance(x, dict) and x.get('id') for x in institutions)):
                authors.add(aid)
    return sorted(authors - known_orcid, key=lambda x: (sha(x.encode()), x))[:BOUNDS['authors']]


def _discovery_url(query, order):
    if query not in TOPICS or order not in (DISCOVERY_ORDER, LEGACY_DISCOVERY_ORDER):
        raise ValueError('only fixed approved-domain topic queries and known ordering allowed')
    return 'https://api.openalex.org/works?' + urllib.parse.urlencode({
        'search': query, 'filter': 'from_publication_date:2018-01-01,to_publication_date:2024-12-31',
        'per-page': 5, 'sort': order, 'select': FIELDS})


def discovery_url(query):
    # Explicit relevance order prevents a publication-date sort from overriding search ranking.
    return _discovery_url(query, DISCOVERY_ORDER)


def retained_discovery_order(manifest, executed_script):
    digest = sha(executed_script)
    if digest != manifest['executedScript']['sha256']:
        raise ValueError('executed script hash differs')
    version, order = manifest.get('queryPlanVersion'), manifest.get('discoveryOrdering')
    if version == QUERY_PLAN_VERSION and order == DISCOVERY_ORDER:
        return order
    if version is None and order is None and digest == LEGACY_EXECUTED_SCRIPT_SHA256:
        # This exact retained script produced the immutable historical date-ordered ledger.
        return LEGACY_DISCOVERY_ORDER
    raise ValueError('unrecognized discovery query version or ordering')


def request_url(author):
    return 'https://api.openalex.org/works?' + urllib.parse.urlencode({
        'filter': f'author.id:{author.rsplit("/", 1)[-1]},from_publication_date:2018-01-01,to_publication_date:2024-12-31',
        'per-page': 5, 'sort': 'publication_date:asc', 'select': FIELDS})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class StopBudget(Exception):
    pass


class Client:
    def __init__(self, root, opener=None, clock=time.monotonic, sleep=time.sleep, start=None):
        self.root, self.clock, self.sleep = root, clock, sleep
        self.start, self.last = clock() if start is None else start, None
        self.events, self.bytes, self.unique = [], 0, set()
        self.stopped = False
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open

    def get(self, author=None, query=None):
        if self.stopped:
            return []
        if (author is None) == (query is None):
            raise ValueError('exactly one fixed discovery query or observed author required')
        if author is not None:
            import re
            if not re.fullmatch(r'https://openalex.org/A[1-9][0-9]*', author):
                raise ValueError('invalid observed author ID')
        url = discovery_url(query) if query is not None else request_url(author)
        for retry in range(BOUNDS['maxTransientRetries'] + 1):
            wait = max(0, 1 - (self.clock() - self.last)) if self.last is not None else 0
            if len(self.events) >= BOUNDS['httpAttemptsIncludingRetries'] or self.bytes >= BOUNDS['responseBytes'] or self.clock() - self.start + wait >= BOUNDS['wallSeconds']:
                raise StopBudget('request/byte/wall allowance exhausted')
            if wait:
                self.sleep(wait)
            self.last = self.clock()
            event = {'attempt': len(self.events) + 1, 'authorId': author, 'query': query, 'category': 'topic-discovery' if query else 'observed-author-neighbor', 'url': url,
                     'retry': retry, 'retrievedAtUtc': utc(), 'result': 'incomplete'}
            self.events.append(event)
            body, response = bytearray(), None
            retry_ok = False
            try:
                try:
                    response = self.opener(urllib.request.Request(url, headers={
                        'User-Agent': 'ScholarChain-Authorized-5D-ScreenedDemo/1.0', 'Accept': 'application/json', 'Accept-Encoding': 'identity'}),
                        timeout=min(BOUNDS['timeoutSeconds'], BOUNDS['wallSeconds'] - (self.clock() - self.start)))
                except urllib.error.HTTPError as error:
                    response = error  # Error bodies consume the same byte and wall allowances.
                event['status'] = response.status
                event['headers'] = {k: response.headers[k] for k in ('Content-Type', 'Retry-After', 'ETag') if k in response.headers}
                if response.headers.get('Content-Encoding', 'identity') not in ('', 'identity'):
                    raise ValueError('unexpected content encoding')
                cap = min(BOUNDS['perResponseBytes'], BOUNDS['responseBytes'] - self.bytes)
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
                    raise StopBudget('response byte cap reached; stop without further requests')
                if response.status != 200:
                    event['result'] = 'http-error'
                    retry_ok = response.status in (500, 502, 503, 504) and retry == 0 and not event['headers'].get('Retry-After')
                    if not retry_ok:
                        self.stopped = True
                else:
                    value = json.loads(body)
                    results = value.get('results')
                    if not isinstance(results, list):
                        raise ValueError('expected results array')
                    # Count every distinct returned native ID, including excluded records.
                    for record in results:
                        if not isinstance(record, dict) or not isinstance(record.get('id'), str):
                            raise ValueError('missing native work ID')
                        self.unique.add(record['id'])
                    if len(results) > BOUNDS['worksPerAuthor'] or len(self.unique) > BOUNDS['newDistinctOpenAlexWorksIncludingExcluded']:
                        raise StopBudget('server exceeded requested observation cap')
                    if any('abstract_inverted_index' in x or 'fulltext' in x for x in results):
                        raise ValueError('unexpected abstract/fulltext field; no ingestion')
                    event['result'] = 'ok'
                    return [(record, event['attempt']) for record in results]
            except (urllib.error.URLError, socket.timeout, TimeoutError) as error:
                event['result'], event['errorType'] = 'network-error', type(error).__name__
                retry_ok = retry == 0
                if not retry_ok:
                    self.stopped = True
            except (ValueError, UnicodeError) as error:
                event['result'], event['errorType'] = 'schema-or-access-error', type(error).__name__
                self.stopped = True
            finally:
                if response is not None:
                    response.close()
                event['bytesRead'] = len(body)
                if body:
                    rel = f'responses/{event["attempt"]:03}-openalex.body'
                    (self.root / rel).write_bytes(body)
                    event.update(responsePath=rel, sha256=sha(body))
                with (self.root / 'request-ledger.jsonl').open('ab') as out:
                    out.write(enc(event) + b'\n')
            if retry_ok:
                self.sleep(1)
                continue
            return []


def allowed(record):
    year = record.get('publication_year') or 0
    venue = (((record.get('primary_location') or {}).get('source') or {}).get('display_name') or '').lower()
    return isinstance(year, int) and 2018 <= year <= 2024 and any(token in venue for token in VENUES) and len(enc(record)) <= BOUNDS['recordBytes']


def history_facts(root, seen=None):
    """Count manifest-distinct acquisition stages, including excluded observations."""
    seen = set() if seen is None else seen
    body = load(root / 'population-manifest.v1.json')
    identity = sha(body)
    if identity in seen:
        return {'ids': set(), 'attempts': 0, 'bytes': 0, 'seconds': 0.0}
    seen.add(identity)
    manifest = json.loads(body)
    events = [json.loads(line) for line in load(root / 'request-ledger.jsonl').splitlines()]
    result = {'ids': set(), 'attempts': len(events), 'bytes': sum(e['bytesRead'] for e in events),
              'seconds': manifest['observed']['seconds']}
    for event in events:
        if event.get('result') == 'ok' and event.get('responsePath'):
            result['ids'].update(x['id'] for x in json.loads(load(root / event['responsePath'])).get('results', []))
    for child in ('context', 'previous-stage'):
        if (root / child / 'population-manifest.v1.json').is_file():
            nested = history_facts(root / child, seen)
            result['ids'].update(nested['ids'])
            for field in ('attempts', 'bytes', 'seconds'):
                result[field] += nested[field]
    return result


def publish(output, plan_path, screen_path, approval_path, context, previous_stage=None):
    started = time.monotonic()
    if output.exists():
        raise ValueError('new output required; never overwrite')
    plan_bytes, screen_bytes, approval_bytes = load(plan_path), load(screen_path), load(approval_path)
    plan = json.loads(plan_bytes)
    validate_plan(plan, screen_bytes)
    context_manifest_bytes = load(context / 'population-manifest.v1.json')
    context_manifest = json.loads(context_manifest_bytes)
    if plan.get('contextPopulationSha256') != sha(context_manifest_bytes):
        raise ValueError('seed context population differs')
    for rel, fact in context_manifest['files'].items():
        if '..' in Path(rel).parts or Path(rel).is_absolute():
            raise ValueError('unsafe context path')
        data = load(context / rel)
        if sha(data) != fact['sha256'] or len(data) != fact['bytes']:
            raise ValueError('context manifest hash differs')
    history_seen = set()
    prior = history_facts(context, history_seen)
    previous_manifest_sha = None
    if previous_stage is not None:
        validate(previous_stage)
        previous_manifest_sha = sha(load(previous_stage / 'population-manifest.v1.json'))
        if plan.get('previousStageSha256') != previous_manifest_sha:
            raise ValueError('previous-stage plan binding differs')
        previous = history_facts(previous_stage, history_seen)
        prior['ids'].update(previous['ids'])
        for field in ('attempts', 'bytes', 'seconds'):
            prior[field] += previous[field]
    elif plan.get('previousStageSha256') is not None:
        raise ValueError('planned previous stage must be supplied')
    # No HTTP is possible before all receipts, fixed plans and script bytes are retained.
    output.mkdir(parents=True, exist_ok=False)
    for name in ('responses', 'scripts', 'input', 'context', 'proof'):
        (output / name).mkdir()
    script = Path(__file__).read_bytes()
    (output / 'scripts/acquire_screened_demo.py').write_bytes(script)
    (output / 'proof/acquisition-plan.json').write_bytes(plan_bytes)
    (output / 'proof/seed-screen.json').write_bytes(screen_bytes)
    (output / 'proof/user-approval.json').write_bytes(approval_bytes)
    for rel in list(context_manifest['files']) + ['population-manifest.v1.json']:
        dest = output / 'context' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(load(context / rel))
    if previous_stage is not None:
        previous_manifest = json.loads(load(previous_stage / 'population-manifest.v1.json'))
        for rel in list(previous_manifest['files']) + ['population-manifest.v1.json']:
            dest = output / 'previous-stage' / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(load(previous_stage / rel))
    (output / 'request-ledger.jsonl').write_bytes(b'')
    previous_observed = prior['ids']
    observed, exclusions = {}, []
    client, status = Client(output, start=started), 'COMPLETE_WITHIN_BOUNDS'
    discovered, authors = [], []
    try:
        for query in TOPICS:
            for record, attempt in client.get(query=query):
                observed.setdefault(record['id'], (record, attempt, 'topic:' + query))
                discovered.append((record, attempt))
            if client.stopped:
                break
        authors = choose_authors(discovered)
        for author in authors:
            for record, attempt in client.get(author):
                observed.setdefault(record['id'], (record, attempt, author))
            if client.stopped:
                status = 'STOPPED_ACCESS_OR_SCHEMA'
                break
    except StopBudget as error:
        status = 'PARTIAL_BUDGET_STOP'
        exclusions.append({'reason': str(error)})
    if client.stopped and status == 'COMPLETE_WITHIN_BOUNDS':
        status = 'STOPPED_ACCESS_OR_SCHEMA'
    selection_trace = {'queries': list(TOPICS), 'discoveredWorkIds': sorted({x['id'] for x, _ in discovered}),
                       'selectedAuthors': [{'authorId': author, 'sourceWorkIds': sorted({work['id'] for work, _ in discovered if any((a.get('author') or {}).get('id') == author for a in work.get('authorships', []))})} for author in authors],
                       'semantics': 'Provisional observed-metadata selection only; not canonical held-out clearance. No fallback, pagination, refill, labels or scores.'}
    (output / 'selection-trace.json').write_bytes(enc(selection_trace) + b'\n')
    old_records = [json.loads(line) for line in load(context / 'openalex/works.jsonl').splitlines()]
    combined = {x['id']: x for x in old_records}
    record_proofs = [{'nativeId': x['id'], 'origin': 'existing-context', 'sourcePath': 'context/openalex/works.jsonl', 'recordSha256': sha(enc(x))} for x in old_records]
    accepted = 0
    for native, (record, attempt, author) in sorted(observed.items()):
        if not allowed(record):
            exclusions.append({'id': native, 'reason': 'year-domain-or-record-byte-filter', 'requestAttempt': attempt})
        elif native in combined:
            exclusions.append({'id': native, 'reason': 'existing-context-native-ID-preserved', 'requestAttempt': attempt})
        else:
            combined[native] = record
            accepted += 1
            record_proofs.append({'nativeId': native, 'origin': 'new-response', 'requestAttempt': attempt,
                                  'authorId': author, 'recordSha256': sha(enc(record))})
    (output / 'input/openalex.jsonl').write_bytes(b''.join(enc(x) + b'\n' for _, x in sorted(combined.items())))
    (output / 'input/crossref.jsonl').write_bytes(load(context / 'crossref/works.jsonl'))
    (output / 'input/orcid.jsonl').write_bytes(load(context / 'orcid/records.jsonl'))
    (output / 'input/dblp.xml').write_bytes(load(context / 'dblp/records.xml'))
    (output / 'record-provenance.jsonl').write_bytes(b''.join(enc(x) + b'\n' for x in record_proofs))
    (output / 'selection-exclusions.json').write_bytes(enc(exclusions) + b'\n')
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    sources = {}
    for source, rel, count in [('openalex', 'input/openalex.jsonl', len(combined)), ('crossref', 'input/crossref.jsonl', 14), ('orcid', 'input/orcid.jsonl', 0), ('dblp', 'input/dblp.xml', 0)]:
        sources[source] = {'path': rel, 'records': count, 'snapshotId': f'{source}-5d-screened-demo-{date}', 'retrievalDate': date,
                           'sha256': sha((output / rel).read_bytes())}
    observed_seconds = round(client.clock() - client.start, 4)
    manifest = {'schemaVersion': VERSION, 'status': status, 'bounds': BOUNDS, 'createdAtUtc': utc(),
                'sources': sources, 'queryPlanVersion': QUERY_PLAN_VERSION, 'discoveryOrdering': DISCOVERY_ORDER,
                'approvalReceiptSha256': sha(approval_bytes), 'screenReceiptSha256': sha(screen_bytes),
                'executedScript': {'path': 'scripts/acquire_screened_demo.py', 'sha256': sha(script)},
                'contextPopulationSha256': sha(context_manifest_bytes), 'previousStageSha256': previous_manifest_sha, 'authorsRequested': authors,
                'selection': 'Explicit strategy fallback after zero safe existing author seeds: two fixed public topic queries ordered by relevance descending, five works each; hash-first up to four actually observed missing-ORCID affiliated authors, five neighbors each; 2018–2024 and local CS venue filter; no labels, policy scores or predictions.',
                'observed': {'httpAttempts': len(client.events), 'responseBytes': client.bytes, 'seconds': observed_seconds,
                             'distinctReturnedWorksIncludingExcluded': len(client.unique),
                             'newDistinctWorksNotObservedInPreviousStage': len(client.unique - previous_observed),
                             'newIngestionRecords': accepted},
                'cumulative': {'previousStageDistinctReturnedWorks': len(previous_observed),
                               'distinctReturnedWorksAcrossStages': len(previous_observed | client.unique),
                               'httpAttemptsAcrossStages': prior['attempts'] + len(client.events),
                               'responseBytesAcrossStages': prior['bytes'] + client.bytes,
                               'secondsAcrossStages': round(prior['seconds'] + observed_seconds, 4)},
                'heldOutAdmissionStatus': 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING', 'humanReviews': 0,
                'limitations': ['Existing-author prefetch screens found zero safe seeds. New public topic discovery is not held-out clearance; root must apply canonical whole-component held-out exclusion before any scoring.',
                               'No eligible pair, live-provider response, human label, calibration or evaluation is claimed.',
                               'Existing context observations retain their original exact records and provenance; cumulative counters are distinct from the new stage approval.']}
    manifest['files'] = {p.relative_to(output).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'population-manifest.v1.json').write_bytes(enc(manifest) + b'\n')
    return validate(output)


def validate(root):
    m = json.loads(load(root / 'population-manifest.v1.json'))
    if m['schemaVersion'] != VERSION or m['bounds'] != BOUNDS:
        raise ValueError('schema or bounds differ')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(m['files']) | {'population-manifest.v1.json'}:
        raise ValueError('inventory differs')
    for rel, fact in m['files'].items():
        if '..' in Path(rel).parts or Path(rel).is_absolute():
            raise ValueError('unsafe manifest path')
        data = load(root / rel)
        if sha(data) != fact['sha256'] or len(data) != fact['bytes']:
            raise ValueError('file hash differs: ' + rel)
    discovery_order = retained_discovery_order(m, load(root / m['executedScript']['path']))
    ledger = [json.loads(line) for line in load(root / 'request-ledger.jsonl').splitlines()]
    if [x['attempt'] for x in ledger] != list(range(1, len(ledger) + 1)) or len(ledger) != m['observed']['httpAttempts'] or sum(x['bytesRead'] for x in ledger) != m['observed']['responseBytes']:
        raise ValueError('ledger totals differ')
    if len(ledger) > 20 or m['observed']['responseBytes'] > BOUNDS['responseBytes'] or m['observed']['seconds'] > 300 or m['observed']['distinctReturnedWorksIncludingExcluded'] > 30:
        raise ValueError('approved stage cap exceeded')
    validate_plan(json.loads(load(root / 'proof/acquisition-plan.json')), load(root / 'proof/seed-screen.json'))
    observed = set()
    discoveries = []
    for event in ledger:
        expected = _discovery_url(event['query'], discovery_order) if event['category'] == 'topic-discovery' else request_url(event['authorId'])
        if event['url'] != expected or event['retry'] not in (0, 1):
            raise ValueError('ledger escaped fixed request plan')
        if event.get('responsePath'):
            body = load(root / event['responsePath'])
            if len(body) != event['bytesRead'] or sha(body) != event['sha256']:
                raise ValueError('response ledger hash differs')
            if event['result'] == 'ok':
                result = json.loads(body)['results']
                if len(result) > 5:
                    raise ValueError('response exceeded requested result count')
                observed.update(x['id'] for x in result)
                if event['category'] == 'topic-discovery':
                    discoveries.extend((x, event['attempt']) for x in result)
    if len(observed) != m['observed']['distinctReturnedWorksIncludingExcluded']:
        raise ValueError('observed work counter differs')
    selected = choose_authors(discoveries)
    if m['authorsRequested'] != selected or any(e['authorId'] not in selected for e in ledger if e['category'] == 'observed-author-neighbor'):
        raise ValueError('author selection differs from actual discovered evidence')
    for source in ('crossref', 'orcid', 'dblp'):
        old_rel = {'crossref': 'crossref/works.jsonl', 'orcid': 'orcid/records.jsonl', 'dblp': 'dblp/records.xml'}[source]
        if load(root / m['sources'][source]['path']) != load(root / 'context' / old_rel):
            raise ValueError('existing non-OpenAlex context bytes changed')
    previous_path = root / 'previous-stage/population-manifest.v1.json'
    if m.get('previousStageSha256') is not None:
        if not previous_path.is_file() or sha(load(previous_path)) != m['previousStageSha256']:
            raise ValueError('retained previous stage binding differs')
    elif previous_path.exists():
        raise ValueError('unbound previous acquisition stage')
    history = history_facts(root)
    if (history['attempts'] != m['cumulative']['httpAttemptsAcrossStages']
            or history['bytes'] != m['cumulative']['responseBytesAcrossStages']
            or len(history['ids']) != m['cumulative']['distinctReturnedWorksAcrossStages']
            or round(history['seconds'], 4) != round(m['cumulative']['secondsAcrossStages'], 4)):
        raise ValueError('cumulative acquisition counters differ from distinct retained stages')
    rows = [json.loads(line) for line in load(root / 'input/openalex.jsonl').splitlines()]
    proofs = [json.loads(line) for line in load(root / 'record-provenance.jsonl').splitlines()]
    if len(rows) != m['sources']['openalex']['records'] or len({x['id'] for x in rows}) != len(rows) or len(proofs) != len(rows):
        raise ValueError('ingestion count/identity differs')
    proof_map = {x['nativeId']: x for x in proofs}
    old = {x['id']: x for x in map(json.loads, load(root / 'context/openalex/works.jsonl').splitlines())}
    for row in rows:
        proof = proof_map[row['id']]
        if proof['recordSha256'] != sha(enc(row)):
            raise ValueError('record hash differs')
        if proof['origin'] == 'existing-context':
            if old[row['id']] != row:
                raise ValueError('context observation changed')
        else:
            event = ledger[proof['requestAttempt'] - 1]
            response = json.loads(load(root / event['responsePath']))
            if event['result'] != 'ok' or row not in response['results'] or not allowed(row):
                raise ValueError('new record lacks bounded successful-response provenance')
    if sha(load(root / m['executedScript']['path'])) != m['executedScript']['sha256'] or m['heldOutAdmissionStatus'] != 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING' or m['humanReviews'] != 0:
        raise ValueError('script or admission claim differs')
    return {'status': 'VALID', 'schemaVersion': VERSION, 'queryPlanVersion': m.get('queryPlanVersion', 'legacy-exact-executed-script'),
            'discoveryOrdering': discovery_order, 'sources': {s: x['records'] for s, x in m['sources'].items()},
            'observed': m['observed'], 'cumulative': m['cumulative'], 'files': len(m['files']), 'admission': m['heldOutAdmissionStatus']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    create = subs.add_parser('create')
    for flag in ('output', 'plan', 'screen', 'approval', 'context'):
        create.add_argument('--' + flag, type=Path, required=True)
    create.add_argument('--previous-stage', type=Path)
    check = subs.add_parser('validate')
    check.add_argument('--population', type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.population.resolve()) if args.command == 'validate' else publish(args.output.resolve(), args.plan.resolve(), args.screen.resolve(), args.approval.resolve(), args.context.resolve(), args.previous_stage.resolve() if args.previous_stage else None)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
