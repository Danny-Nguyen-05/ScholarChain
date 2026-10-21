#!/usr/bin/env python3
"""One separately approved, fixed Rice-team metadata stage; never scores or calls models.

Only fresh response records are ingested. Existing seed rows are immutable
selection evidence, not newly retrieved observations. Root alone executes create.
"""
import argparse
import datetime as dt
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
import acquire_author_focused_demo as history

VERSION = 'scholarchain.rice-team-demo-population.v1'
PLAN_VERSION = 'scholarchain.rice-team-demo-plan.v1'
AUTHOR_IDS = ['https://openalex.org/A5085731856', 'https://openalex.org/A5109437922']
SEED_IDS = ['https://openalex.org/W2799457717', 'https://openalex.org/W2889897289']
WORK_FIELDS = history.WORK_FIELDS
BOUNDS = {'returnedMetadataRecordsIncludingDuplicatesExcluded': 30, 'httpAttemptsIncludingRetries': 20,
          'totalResponseBytes': 8 * 1024 * 1024, 'perResponseBytes': 2 * 1024 * 1024,
          'wallSeconds': 300, 'timeoutSeconds': 20, 'recordsPerRequest': 15,
          'authorQueries': 2, 'maxTransientRetries': 1, 'concurrency': 1,
          'maxStartsPerSecond': 1, 'recordBytes': 1024 * 1024}
enc, sha, load, utc = history.enc, history.sha, history.load, history.utc


def works_url(author):
    if author not in AUTHOR_IDS:
        raise ValueError('only the two observed approved author IDs may be queried')
    return 'https://api.openalex.org/works?' + urllib.parse.urlencode({
        'filter': f'author.id:{author.rsplit("/", 1)[-1]},from_publication_date:2018-01-01,to_publication_date:2024-12-31',
        'per-page': 15, 'sort': 'cited_by_count:desc', 'select': WORK_FIELDS})


def allowed_work(record):
    source = (record.get('primary_location') or {}).get('source') or {}
    return (source.get('type') in {'conference', 'journal'} and history.allowed_work(record)
            and isinstance(record.get('authorships'), list) and len(record['authorships']) <= 16)


def validate_plan(plan):
    fixed = {'schemaVersion': PLAN_VERSION, 'authorIds': AUTHOR_IDS, 'recordsPerRequest': 15,
             'sort': 'cited_by_count:desc'}
    if any(plan.get(key) != value for key, value in fixed.items()):
        raise ValueError('fixed author/query plan differs')
    if not re.fullmatch(r'[a-z0-9-]{1,100}', plan.get('stageId', '')):
        raise ValueError('safe unique stage ID required')
    hashes = [plan.get(key, '') for key in ('seedPopulationManifestSha256', 'previousStageSha256', 'approvalReceiptSha256')]
    seeds = plan.get('seedLinesSha256', [])
    if len(seeds) != 2 or any(not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value) for value in hashes + seeds):
        raise ValueError('fixed seed/history/approval hashes required')


def validate_approval(plan, approval_bytes):
    if sha(approval_bytes) != plan['approvalReceiptSha256']:
        raise ValueError('approval receipt hash differs')
    approval = json.loads(approval_bytes)
    expected = {'returnedWorkRowsIncludingDuplicatesAndExcluded': 30, 'httpAttemptsIncludingRetries': 20,
                'responseBytes': 8 * 1024 * 1024, 'wallSeconds': 300, 'credentials': False, 'paidData': False}
    if approval.get('limits') != expected or approval.get('originalLiveApprovalUnchanged') is not True:
        raise ValueError('approval does not carry the fixed approved limits')


def prior_facts(path):
    manifest = json.loads(load(path / 'population-manifest.v1.json'))
    for rel, fact in manifest['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('unsafe historical path')
        body = load(path / rel)
        if sha(body) != fact['sha256'] or len(body) != fact['bytes']:
            raise ValueError('historical bytes differ')
    return history.history_facts(path)


def seed_records(root):
    manifest_bytes = load(root / 'population-manifest.v1.json')
    original = json.loads(manifest_bytes)
    source = original['sources']['openalex']
    body = load(root / source['path'])
    if sha(body) != source['sha256']:
        raise ValueError('original seed source hash differs')
    rows = []
    for native in SEED_IDS:
        found = [(index, line) for index, line in enumerate(body.splitlines(keepends=True), 1) if json.loads(line).get('id') == native]
        if len(found) != 1 or not found[0][1].endswith(b'\n'):
            raise ValueError('exactly one complete original seed line required')
        index, line = found[0]
        authors = {row['author']['id']: row['author'] for row in json.loads(line)['authorships'] if row['author'].get('id')}
        if any(author not in authors or authors[author].get('orcid') is not None for author in AUTHOR_IDS):
            raise ValueError('seed does not carry approved observed IDs without ORCID')
        rows.append((index, line))
    return manifest_bytes, body, source, rows


class Client:
    def __init__(self, root, opener=None, clock=time.monotonic, sleep=time.sleep, start=None):
        self.root, self.clock, self.sleep = root, clock, sleep
        self.start, self.last = clock() if start is None else start, None
        self.events, self.bytes, self.returned_records = [], 0, 0
        self.work_ids, self.stopped = set(), False
        self.opener = opener or urllib.request.build_opener(history.NoRedirect()).open

    def get(self, author):
        url = works_url(author)
        if self.stopped:
            return []
        for retry in range(2):
            wait = max(0, 1 - (self.clock() - self.last)) if self.last is not None else 0
            if (len(self.events) >= BOUNDS['httpAttemptsIncludingRetries'] or self.bytes >= BOUNDS['totalResponseBytes']
                    or self.returned_records + 15 > 30 or self.clock() - self.start + wait >= 300):
                raise history.StopBudget('request/record/byte/wall allowance exhausted')
            if wait: self.sleep(wait)
            self.last = self.clock()
            event = {'attempt': len(self.events) + 1, 'recordKind': 'works', 'authorId': author, 'url': url,
                     'retry': retry, 'retrievedAtUtc': utc(), 'result': 'incomplete', 'returnedRecords': 0}
            self.events.append(event)
            body, response, retry_ok = bytearray(), None, False
            try:
                try:
                    response = self.opener(urllib.request.Request(url, headers={
                        'User-Agent': 'ScholarChain-Authorized-5D-RiceFinal/1.0', 'Accept': 'application/json', 'Accept-Encoding': 'identity'}),
                        timeout=min(20, 300 - (self.clock() - self.start)))
                except urllib.error.HTTPError as error:
                    response = error
                event['status'] = response.status
                event['headers'] = {key: response.headers[key] for key in ('Content-Type', 'Retry-After', 'ETag') if key in response.headers}
                if response.headers.get('Content-Encoding', 'identity') not in ('', 'identity'):
                    raise ValueError('unexpected content encoding')
                cap = min(BOUNDS['perResponseBytes'], BOUNDS['totalResponseBytes'] - self.bytes)
                while len(body) < cap:
                    remaining = 300 - (self.clock() - self.start)
                    if remaining <= 0: raise history.StopBudget('wall allowance exhausted during body')
                    sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
                    if sock is not None: sock.settimeout(min(20, remaining))
                    part = response.read(min(65536, cap - len(body)))
                    if not part: break
                    body.extend(part); self.bytes += len(part)
                if len(body) >= cap: raise history.StopBudget('response byte cap reached')
                if response.status != 200:
                    event['result'] = 'http-error'
                    retry_ok = response.status in (500, 502, 503, 504) and retry == 0 and not event['headers'].get('Retry-After')
                    if not retry_ok: self.stopped = True
                else:
                    rows = json.loads(body).get('results')
                    if not isinstance(rows, list): raise ValueError('expected results array')
                    event['returnedRecords'] = len(rows); self.returned_records += len(rows)
                    if len(rows) > 15 or self.returned_records > 30: raise history.StopBudget('returned row cap exceeded')
                    for row in rows:
                        if not isinstance(row, dict) or not re.fullmatch(r'https://openalex.org/W[1-9][0-9]*', row.get('id', '')):
                            raise ValueError('invalid native work ID')
                        self.work_ids.add(row['id'])
                        if 'abstract_inverted_index' in row or 'fulltext' in row:
                            raise ValueError('unexpected abstract/fulltext field')
                    event['result'] = 'ok'
                    return [(row, event['attempt']) for row in rows]
            except (urllib.error.URLError, socket.timeout, TimeoutError) as error:
                event['result'], event['errorType'] = 'network-error', type(error).__name__
                retry_ok = retry == 0
                if not retry_ok: self.stopped = True
            except (ValueError, UnicodeError) as error:
                event['result'], event['errorType'] = 'schema-or-access-error', type(error).__name__
                self.stopped = True
            finally:
                if response is not None: response.close()
                event['bytesRead'] = len(body)
                if body:
                    rel = f'responses/{event["attempt"]:03d}-works.body'
                    (self.root / rel).write_bytes(body)
                    event.update(responsePath=rel, sha256=sha(body))
                with (self.root / 'request-ledger.jsonl').open('ab') as handle:
                    handle.write(enc(event) + b'\n')
            if retry_ok:
                self.sleep(1); continue
            return []


def cumulative(prior, client, seconds):
    return {'distinctWorkIdsAcrossStages': len(prior['works'] | client.work_ids),
            'distinctAuthorProfileIdsAcrossStages': len(prior['authors']),
            'returnedWorkRecordsAcrossStages': prior['returnedWorks'] + client.returned_records,
            'returnedAuthorProfileRecordsAcrossStages': prior['returnedAuthors'],
            'returnedMetadataRecordsAcrossStages': prior['returnedWorks'] + prior['returnedAuthors'] + client.returned_records,
            'httpAttemptsAcrossStages': prior['attempts'] + len(client.events),
            'responseBytesAcrossStages': prior['bytes'] + client.bytes,
            'secondsAcrossStages': round(prior['seconds'] + seconds, 4)}


def publish(output, plan_path, approval_path, seed_population, previous_stage):
    started = time.monotonic()
    if output.exists() or output.is_symlink(): raise ValueError('new output required; never overwrite')
    plan_bytes, approval_bytes = load(plan_path), load(approval_path)
    plan = json.loads(plan_bytes); validate_plan(plan); validate_approval(plan, approval_bytes)
    seed_manifest, seed_body, seed_source, seeds = seed_records(seed_population)
    previous_manifest = load(previous_stage / 'population-manifest.v1.json')
    if (output.name != plan['stageId'] or sha(seed_manifest) != plan['seedPopulationManifestSha256']
            or sha(previous_manifest) != plan['previousStageSha256']
            or [sha(line) for _, line in seeds] != plan['seedLinesSha256']):
        raise ValueError('planned source/output binding differs')
    prior = prior_facts(previous_stage)
    output.mkdir(parents=True)
    for sub in ('scripts', 'responses', 'input', 'seed', 'proof'): (output / sub).mkdir()
    for script in (Path(__file__), Path(history.__file__)):
        (output / 'scripts' / script.name).write_bytes(script.read_bytes())
    for name, body in [('proof/plan.json', plan_bytes), ('proof/user-approval.json', approval_bytes),
                       ('seed/population-manifest.v1.json', seed_manifest), ('seed/original-openalex.jsonl', seed_body),
                       ('seed/selection-only.jsonl', b''.join(line for _, line in seeds))]:
        (output / name).write_bytes(body)
    (output / 'proof/previous-population-manifest.v1.json').write_bytes(previous_manifest)
    (output / 'request-ledger.jsonl').write_bytes(b'')
    client, returned, status = Client(output, start=started), {}, 'COMPLETE_WITHIN_BOUNDS'
    try:
        for author in AUTHOR_IDS:
            for row, attempt in client.get(author): returned.setdefault(row['id'], (row, attempt, author))
            if client.stopped: break
    except history.StopBudget:
        status = 'PARTIAL_BUDGET_STOP'
    if client.stopped: status = 'STOPPED_ACCESS_OR_SCHEMA'
    selected, proofs, excluded = [], [], []
    for native, (row, attempt, author) in sorted(returned.items()):
        if not allowed_work(row):
            excluded.append({'nativeId': native, 'requestAttempt': attempt, 'reason': 'OUTSIDE_CS_PUBLICATION_VENUE_YEAR_RECORD_OR_TEAM_SIZE_16_BOUNDS'})
            continue
        selected.append(row)
        proofs.append({'nativeId': native, 'requestAttempt': attempt, 'queriedProvisionalAuthorId': author,
                       'recordSha256': sha(enc(row)), 'origin': 'fresh-response'})
    data = {'openalex': b''.join(enc(row) + b'\n' for row in selected), 'crossref': b'', 'orcid': b'',
            'dblp': b'<?xml version="1.0" encoding="UTF-8"?>\n<dblp>\n</dblp>\n'}
    sources = {}
    for source, body in data.items():
        rel = 'input/' + source + ('.xml' if source == 'dblp' else '.jsonl')
        (output / rel).write_bytes(body)
        sources[source] = {'path': rel, 'records': len(selected) if source == 'openalex' else 0, 'sha256': sha(body),
                           'snapshotId': f'{source}-{plan["stageId"]}', 'retrievalDate': dt.datetime.now(dt.timezone.utc).date().isoformat()}
    (output / 'record-provenance.jsonl').write_bytes(b''.join(enc(row) + b'\n' for row in proofs))
    (output / 'selection-exclusions.json').write_bytes(enc(excluded) + b'\n')
    seconds = round(client.clock() - client.start, 4)
    manifest = {'schemaVersion': VERSION, 'stageId': plan['stageId'], 'createdAtUtc': utc(), 'status': status,
                'bounds': BOUNDS, 'sources': sources, 'planSha256': sha(plan_bytes), 'approvalReceiptSha256': sha(approval_bytes),
                'previousStageSha256': sha(previous_manifest), 'previousStageDirectory': previous_stage.name,
                'executedScripts': {p.name: {'path': 'scripts/' + p.name, 'sha256': sha(p.read_bytes())} for p in (Path(__file__), Path(history.__file__))},
                'seed': {'role': 'SELECTION_PROOF_ONLY_NOT_INGESTED', 'originalPopulationManifestSha256': sha(seed_manifest),
                         'originalSource': seed_source, 'records': [{'nativeId': native, 'sourceLineNumber': index, 'sha256': sha(line), 'bytes': len(line)} for native, (index, line) in zip(SEED_IDS, seeds)]},
                'observed': {'httpAttempts': len(client.events), 'responseBytes': client.bytes, 'seconds': seconds,
                             'returnedWorkRecordsIncludingDuplicatesExcluded': client.returned_records,
                             'distinctWorkIdsIncludingExcluded': len(client.work_ids), 'newIngestionWorks': len(selected),
                             'newWorkIdsNotObservedInPriorStages': len(client.work_ids - prior['works'])},
                'cumulative': cumulative(prior, client, seconds),
                'heldOutAdmissionStatus': 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING', 'humanReviews': 0,
                'limitations': ['Only fresh responses are ingested; original seed rows preserve original provenance as selection proof only.',
                                'All returned duplicate/excluded rows consume the cap. No pagination, refill, name masking, policy tuning or label access.',
                                'Canonical held-out component exclusion must precede scoring. No eligible pair or real-provider result is claimed.']}
    manifest['files'] = {p.relative_to(output).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())} for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'population-manifest.v1.json').write_bytes(enc(manifest) + b'\n')
    return validate(output)


def validate(root):
    m = json.loads(load(root / 'population-manifest.v1.json'))
    if m['schemaVersion'] != VERSION or m['bounds'] != BOUNDS: raise ValueError('schema/bounds differ')
    if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} != set(m['files']) | {'population-manifest.v1.json'}: raise ValueError('inventory differs')
    for rel, fact in m['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts: raise ValueError('unsafe retained path')
        body = load(root / rel)
        if sha(body) != fact['sha256'] or len(body) != fact['bytes']: raise ValueError('retained bytes differ: ' + rel)
    plan_bytes, approval_bytes = load(root / 'proof/plan.json'), load(root / 'proof/user-approval.json')
    plan = json.loads(plan_bytes); validate_plan(plan); validate_approval(plan, approval_bytes)
    if sha(plan_bytes) != m['planSha256'] or sha(approval_bytes) != m['approvalReceiptSha256'] or plan['stageId'] != m['stageId']: raise ValueError('receipt differs')
    if m['previousStageDirectory'] != '5d-demo-2026-10-20-benedikt': raise ValueError('unexpected historical stage')
    previous_stage = root.parent / m['previousStageDirectory']
    if (load(root / 'proof/previous-population-manifest.v1.json') != load(previous_stage / 'population-manifest.v1.json')
            or sha(load(previous_stage / 'population-manifest.v1.json')) != m['previousStageSha256']
            or m['previousStageSha256'] != plan['previousStageSha256']): raise ValueError('history differs')
    seed_manifest, seed_body, seed_source, seeds = seed_records_from_copy(root)
    if sha(seed_manifest) != plan['seedPopulationManifestSha256'] or [sha(line) for _, line in seeds] != plan['seedLinesSha256']: raise ValueError('seed receipt differs')
    expected_seed = {'role': 'SELECTION_PROOF_ONLY_NOT_INGESTED', 'originalPopulationManifestSha256': sha(seed_manifest), 'originalSource': seed_source,
                     'records': [{'nativeId': native, 'sourceLineNumber': index, 'sha256': sha(line), 'bytes': len(line)} for native, (index, line) in zip(SEED_IDS, seeds)]}
    if m['seed'] != expected_seed or load(root / 'seed/selection-only.jsonl') != b''.join(line for _, line in seeds): raise ValueError('original seed provenance differs')
    for fact in m['executedScripts'].values():
        if sha(load(root / fact['path'])) != fact['sha256']: raise ValueError('executed script differs')
    ledger = [json.loads(line) for line in load(root / 'request-ledger.jsonl').splitlines()]
    if [event['attempt'] for event in ledger] != list(range(1, len(ledger) + 1)): raise ValueError('attempt sequence differs')
    initial = [e for e in ledger if e['retry'] == 0]
    if [e['authorId'] for e in initial] != AUTHOR_IDS[:len(initial)] or len(initial) > 2: raise ValueError('fixed request sequence differs')
    rows, ids, total = {}, set(), 0
    for index, event in enumerate(ledger):
        if event['recordKind'] != 'works' or event['url'] != works_url(event['authorId']) or event['retry'] not in (0, 1): raise ValueError('request escaped fixed plan')
        if event['retry'] == 1:
            prev = ledger[index - 1] if index else {}
            if prev.get('retry') != 0 or prev.get('url') != event['url'] or prev.get('result') not in ('network-error', 'http-error'): raise ValueError('retry sequence differs')
        if event.get('responsePath'):
            body = load(root / event['responsePath'])
            if sha(body) != event['sha256'] or len(body) != event['bytesRead']: raise ValueError('response bytes differ')
            if event['result'] == 'ok':
                results = json.loads(body)['results']
                if len(results) > 15 or len(results) != event['returnedRecords']: raise ValueError('response row count differs')
                total += len(results)
                for row in results:
                    ids.add(row['id']); rows.setdefault(row['id'], (row, event['attempt'], event['authorId']))
            elif event['returnedRecords']:
                raise ValueError('partial invalid-response row count requires manual integrity review')
    if total > 30 or len(ledger) > 20 or sum(e['bytesRead'] for e in ledger) > BOUNDS['totalResponseBytes'] or m['observed']['seconds'] > 300: raise ValueError('approved cap exceeded')
    expected_rows, expected_proofs, expected_excluded = [], [], []
    for native, (row, attempt, author) in sorted(rows.items()):
        if allowed_work(row):
            expected_rows.append(row); expected_proofs.append({'nativeId': native, 'requestAttempt': attempt, 'queriedProvisionalAuthorId': author, 'recordSha256': sha(enc(row)), 'origin': 'fresh-response'})
        else: expected_excluded.append({'nativeId': native, 'requestAttempt': attempt, 'reason': 'OUTSIDE_CS_PUBLICATION_VENUE_YEAR_RECORD_OR_TEAM_SIZE_16_BOUNDS'})
    if load(root / 'input/openalex.jsonl') != b''.join(enc(row) + b'\n' for row in expected_rows): raise ValueError('ingestion is not all selected fresh response records')
    if load(root / 'record-provenance.jsonl') != b''.join(enc(row) + b'\n' for row in expected_proofs) or json.loads(load(root / 'selection-exclusions.json')) != expected_excluded: raise ValueError('selection/provenance differs')
    for source, fact in m['sources'].items():
        data = load(root / fact['path'])
        if sha(data) != fact['sha256'] or fact['snapshotId'] != f'{source}-{m["stageId"]}': raise ValueError('fresh source identity differs')
        if source != 'dblp' and len(data.splitlines()) != fact['records']: raise ValueError('source count differs')
        if source in ('crossref', 'orcid') and data: raise ValueError('only fresh OpenAlex observations may be ingested')
    prior = prior_facts(previous_stage)
    observed = {'httpAttempts': len(ledger), 'responseBytes': sum(e['bytesRead'] for e in ledger), 'seconds': m['observed']['seconds'],
                'returnedWorkRecordsIncludingDuplicatesExcluded': total, 'distinctWorkIdsIncludingExcluded': len(ids),
                'newIngestionWorks': len(expected_rows), 'newWorkIdsNotObservedInPriorStages': len(ids - prior['works'])}
    if m['observed'] != observed: raise ValueError('observed accounting differs')
    client = type('Observed', (), {'work_ids': ids, 'returned_records': total, 'events': ledger, 'bytes': observed['responseBytes']})()
    if m['cumulative'] != cumulative(prior, client, observed['seconds']): raise ValueError('cumulative history differs')
    if m['heldOutAdmissionStatus'] != 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING' or m['humanReviews'] != 0: raise ValueError('false admission/label claim')
    return {'status': 'VALID', 'schemaVersion': VERSION, 'sources': {k: v['records'] for k, v in m['sources'].items()}, 'observed': observed, 'cumulative': m['cumulative'], 'files': len(m['files'])}


def seed_records_from_copy(root):
    manifest_bytes = load(root / 'seed/population-manifest.v1.json')
    source = json.loads(manifest_bytes)['sources']['openalex']
    body = load(root / 'seed/original-openalex.jsonl')
    if sha(body) != source['sha256']: raise ValueError('original source bytes differ')
    seeds = []
    for native in SEED_IDS:
        found = [(index, line) for index, line in enumerate(body.splitlines(keepends=True), 1) if json.loads(line).get('id') == native]
        if len(found) != 1: raise ValueError('original seed row differs')
        seeds.append(found[0])
    return manifest_bytes, body, source, seeds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('create')
    for flag in ('output', 'plan', 'approval', 'seed-population', 'previous-stage'): create.add_argument('--' + flag, type=Path, required=True)
    check = sub.add_parser('validate'); check.add_argument('--population', type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.population.resolve()) if args.command == 'validate' else publish(args.output.resolve(), args.plan.resolve(), args.approval.resolve(), args.seed_population.resolve(), args.previous_stage.resolve())
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
