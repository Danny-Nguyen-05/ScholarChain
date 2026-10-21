#!/usr/bin/env python3
"""Offline strict CS venue slice of an immutable author-focused acquisition.

No acquisition, models, labels or scoring. Repository labels cannot establish a
CS publication venue. The original acquisition and every observed ID stay intact.
"""
import argparse
import json
from pathlib import Path
import acquire_author_focused_demo as parent

VERSION = 'scholarchain.author-focused-cs-slice.v1'
POLICY = 'scholarchain.cs-publication-venue-kind.v1'
PUBLICATION_TYPES = {'conference', 'journal'}


def exclusion(record):
    source = (record.get('primary_location') or {}).get('source') or {}
    kind = source.get('type')
    if kind == 'repository':
        return 'REPOSITORY_IS_NOT_CS_VENUE: database in a repository label is not CS venue evidence'
    if kind not in PUBLICATION_TYPES:
        return 'UNAVAILABLE_COMPARABLE_PUBLICATION_VENUE_TYPE'
    if not parent.allowed_work(record):
        return 'OUTSIDE_EXISTING_CS_YEAR_VENUE_RECORD_BOUNDS'
    return None


def retained_lines(source):
    return [(line, json.loads(line)) for line in parent.load(source).splitlines(keepends=True)]


def expected(parent_root):
    manifest = json.loads(parent.load(parent_root / 'population-manifest.v1.json'))
    selected, rejected = [], []
    for line, record in retained_lines(parent_root / manifest['sources']['openalex']['path']):
        reason = exclusion(record)
        if reason:
            rejected.append({'nativeId': record['id'], 'reason': reason,
                             'sourceLineSha256': parent.sha(line)})
        else:
            selected.append((line, record))
    return manifest, selected, rejected


def create(parent_root, output):
    parent.validate(parent_root)
    if output.exists() or output.is_symlink():
        raise ValueError('new output required; never overwrite')
    manifest_bytes = parent.load(parent_root / 'population-manifest.v1.json')
    manifest, selected, rejected = expected(parent_root)
    output.mkdir(parents=True, exist_ok=False)
    for sub in ('input', 'proof', 'scripts'): (output / sub).mkdir()
    (output / 'scripts/derive_focused_cs_population.py').write_bytes(Path(__file__).read_bytes())
    (output / 'proof/parent-population-manifest.v1.json').write_bytes(manifest_bytes)
    sources = {}
    for source, original in manifest['sources'].items():
        data = (b''.join(line for line, _ in selected) if source == 'openalex'
                else parent.load(parent_root / original['path']))
        rel = original['path']
        (output / rel).parent.mkdir(parents=True, exist_ok=True)
        (output / rel).write_bytes(data)
        sources[source] = {**original, 'path': rel, 'sha256': parent.sha(data)}
        if source == 'openalex':
            sources[source].update(records=len(selected), snapshotId=f'openalex-{output.name}')
    (output / 'selection-exclusions.json').write_bytes(parent.enc(rejected) + b'\n')
    provenance = [{'nativeId': record['id'], 'origin': 'immutable-parent-acquisition',
                   'parentManifestSha256': parent.sha(manifest_bytes),
                   'exactParentSourceLineSha256': parent.sha(line)} for line, record in selected]
    (output / 'record-provenance.jsonl').write_bytes(b''.join(parent.enc(row) + b'\n' for row in provenance))
    result = {'schemaVersion': VERSION, 'stageId': output.name, 'createdAtUtc': parent.utc(),
              'selectionPolicy': POLICY,
              'parent': {'manifestSha256': parent.sha(manifest_bytes), 'stageId': manifest['stageId']},
              'sources': sources, 'observed': {'parentOpenAlexRecords': len(selected) + len(rejected),
                                              'selectedOpenAlexRecords': len(selected),
                                              'excludedOpenAlexRecords': len(rejected)},
              'acquisition': {'newHttpAttempts': 0, 'newReturnedRecords': 0, 'newResponseBytes': 0,
                              'parentObserved': manifest['observed'], 'cumulative': manifest['cumulative'],
                              'accounting': 'Offline subset only. Parent counters referenced, not a new acquisition or additive stage.'},
              'heldOutAdmissionStatus': 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING',
              'limitations': ['Author lookup metadata is not ingested.',
                             'Repository records are excluded before any ER scoring; original raw acquisition is unchanged.',
                             'Kept records and all identifiers are exact original parent source lines.',
                             'Domain slicing is not identity adjudication or evidence of demo eligibility.']}
    result['files'] = {p.relative_to(output).as_posix(): {'bytes': p.stat().st_size, 'sha256': parent.sha(p.read_bytes())}
                       for p in sorted(output.rglob('*')) if p.is_file()}
    (output / 'population-manifest.v1.json').write_bytes(parent.enc(result) + b'\n')
    return validate(output, parent_root)


def validate(root, parent_root):
    parent.validate(parent_root)
    result = json.loads(parent.load(root / 'population-manifest.v1.json'))
    if result['schemaVersion'] != VERSION or result['selectionPolicy'] != POLICY:
        raise ValueError('derived schema/policy differs')
    if {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} != set(result['files']) | {'population-manifest.v1.json'}:
        raise ValueError('derived inventory differs')
    for rel, fact in result['files'].items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('unsafe derived path')
        data = parent.load(root / rel)
        if len(data) != fact['bytes'] or parent.sha(data) != fact['sha256']:
            raise ValueError('derived file differs')
    original_bytes = parent.load(parent_root / 'population-manifest.v1.json')
    original, selected, rejected = expected(parent_root)
    if (parent.load(root / 'proof/parent-population-manifest.v1.json') != original_bytes
            or result['parent'] != {'manifestSha256': parent.sha(original_bytes), 'stageId': original['stageId']}):
        raise ValueError('parent binding differs')
    for source, fact in result['sources'].items():
        expected_bytes = (b''.join(line for line, _ in selected) if source == 'openalex'
                          else parent.load(parent_root / original['sources'][source]['path']))
        if parent.load(root / fact['path']) != expected_bytes or parent.sha(expected_bytes) != fact['sha256']:
            raise ValueError('source is not exact selected parent bytes')
        expected_fact = dict(original['sources'][source])
        if source == 'openalex':
            expected_fact.update(records=len(selected), snapshotId=f'openalex-{result["stageId"]}', sha256=parent.sha(expected_bytes))
        if fact != expected_fact:
            raise ValueError('source provenance differs')
    if json.loads(parent.load(root / 'selection-exclusions.json')) != rejected:
        raise ValueError('domain exclusions differ')
    if result['observed'] != {'parentOpenAlexRecords': len(selected) + len(rejected), 'selectedOpenAlexRecords': len(selected), 'excludedOpenAlexRecords': len(rejected)}:
        raise ValueError('selection counters differ')
    acquisition = result['acquisition']
    if (acquisition['newHttpAttempts'], acquisition['newReturnedRecords'], acquisition['newResponseBytes']) != (0, 0, 0) or acquisition['parentObserved'] != original['observed'] or acquisition['cumulative'] != original['cumulative']:
        raise ValueError('offline slice cannot acquire records or reset counters')
    expected_proofs = [{'nativeId': record['id'], 'origin': 'immutable-parent-acquisition',
                        'parentManifestSha256': parent.sha(original_bytes), 'exactParentSourceLineSha256': parent.sha(line)} for line, record in selected]
    if [json.loads(line) for line in parent.load(root / 'record-provenance.jsonl').splitlines()] != expected_proofs:
        raise ValueError('source provenance proofs differ')
    if result['heldOutAdmissionStatus'] != 'PENDING_CANONICAL_ER_COMPONENT_CHECK_BEFORE_SCORING':
        raise ValueError('false admission claim')
    return {'status': 'VALID', 'schemaVersion': VERSION, 'observed': result['observed'],
            'sources': {source: fact['records'] for source, fact in result['sources'].items()},
            'newHttpAttempts': 0, 'cumulative': acquisition['cumulative'], 'files': len(result['files'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['create', 'validate'])
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--population', type=Path, required=True)
    args = parser.parse_args()
    function = create if args.command == 'create' else lambda original, output: validate(output, original)
    print(json.dumps(function(args.parent.resolve(), args.population.resolve()), indent=2))


if __name__ == '__main__': main()
