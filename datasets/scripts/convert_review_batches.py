#!/usr/bin/env python3
"""Offline conversion of explicitly human-confirmed Markdown checkboxes.

This does not assign labels, authenticate a reviewer, establish blind review,
import labels, or evaluate predictions. Original source bytes are retained.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

MAX_SOURCE_BYTES = 2_000_000
MAX_QUEUE_BYTES = 20_000_000
NOTE_PREFIX = ('Human checkbox decision converted from an AI-assisted Markdown review; '
               'timestamp is conversion time, not original annotation time.')
LIMITATIONS = [
    'User confirmed completion of all batches in chat; reviewer ID is self-entered provenance, not authentication.',
    'Human reviewer saw AI suggestions and explanations before selecting labels; this is AI-assisted review, not independent blind gold.',
    'Some source Comments explicitly attribute external source checks to Claude. These cases exceeded the original frozen-source-only draft boundary. They are preserved as attributed AI assistance, not independently verified evidence, frozen-queue evidence, or human-authored reasoning.',
    'Original annotation times are unavailable. annotatedAtUtc and exportedAtUtc are conversion time, not inferred review-click time.',
    'Uncertain labels remain uncertain and are excluded from binary gold; no prediction, accuracy, calibration or evaluation is produced.'
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(path, limit=MAX_SOURCE_BYTES):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'not a regular non-symlink input: {path.name}')
    if path.stat().st_size > limit:
        raise ValueError(f'input byte bound exceeded: {path.name}')
    data = path.read_bytes()
    if len(data) > limit:
        raise ValueError('input grew beyond byte bound')
    return data


def parse_batch(text):
    matches = list(re.finditer(r'^## Task (\d+) — (Work|Researcher)\s*$', text, re.M))
    if not matches:
        raise ValueError('no task sections')
    rows = []
    for index, match in enumerate(matches):
        body = text[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        def exactly(pattern, message):
            found = re.findall(pattern, body, re.M)
            if len(found) != 1:
                raise ValueError(message)
            return found[0]
        pair = exactly(r'^- \*\*pairId:\*\* `(resolution-pair:[0-9a-f]{64})`\s*$', 'invalid or repeated pair ID')
        evidence = exactly(r'^- \*\*evidenceHash:\*\* `([0-9a-f]{64})`\s*$', 'invalid or repeated evidence hash')
        decision = exactly(r"^\*\*Danny's decision:\*\* ([^\n]*)$", 'missing or repeated decision line').strip()
        boxes = re.fullmatch(r'([☐☑]) same ([☐☑]) different ([☐☑]) uncertain', decision)
        if not boxes or boxes.groups().count('☑') != 1:
            raise ValueError('exactly one checkbox must be selected')
        label = ('same', 'different', 'uncertain')[boxes.groups().index('☑')]
        comment_raw = exactly(r'^\*\*Comments:\*\*\s*\n([\s\S]*?)\Z', 'missing or repeated Comments section')
        # Only the section separator is formatting, never arbitrary comment text.
        comment_raw = re.sub(r'\n---\s*\Z', '', comment_raw)
        comment = '\n'.join(re.sub(r'^> ?', '', line).rstrip() for line in comment_raw.splitlines()).strip()
        note = NOTE_PREFIX + (('\nSource Comments (verbatim; attribution as written):\n' + comment) if comment else '')
        if len(note) > 2000:
            raise ValueError('note exceeds 2000 characters; no truncation allowed')
        rows.append({'taskNumber': int(match.group(1)), 'pairId': pair, 'entityType': match.group(2),
                     'evidenceHash': evidence, 'label': label, 'sourceComment': comment, 'note': note,
                     'commentAttribution': 'AI_SOURCE_CHECK_AS_EXPLICITLY_WRITTEN' if comment.startswith('Source check by Claude') else ('UNVERIFIED_SOURCE_COMMENT_AUTHORSHIP' if comment else 'NONE')})
    return rows


def build_checkpoint(queue, draft, rows, reviewer, converted_at, source_set_hash):
    instant = datetime.fromisoformat(converted_at.replace('Z', '+00:00'))
    if not converted_at.endswith('Z') or instant.utcoffset().total_seconds() != 0:
        raise ValueError('conversion timestamp must be UTC ending Z')
    if not reviewer or reviewer.strip() != reviewer or len(reviewer) > 128 or any(ord(c) < 32 or ord(c) == 127 for c in reviewer):
        raise ValueError('invalid reviewer ID')
    if draft.get('queueId') != queue['queueId'] or draft.get('queueHash') != queue['queueHash']:
        raise ValueError('draft queue binding mismatch')
    initial = [t for t in queue['tasks'] if t['role'] == 'initial']
    if len(queue['tasks']) != 300 or sum(t['role'] == 'reserve' for t in queue['tasks']) != 60:
        raise ValueError('expected 300 tasks including exactly 60 untouched reserves')
    if len(initial) != 240 or Counter(t['pair']['entityType'] for t in initial) != {'Work': 120, 'Researcher': 120}:
        raise ValueError('expected exactly 240 initial tasks, 120 per entity')
    if len(rows) != 240 or [r['taskNumber'] for r in rows] != list(range(1, 241)):
        raise ValueError('missing, repeated or out-of-order task number')
    if len({r['pairId'] for r in rows}) != 240:
        raise ValueError('duplicate pair ID')
    draft_rows = draft['tasks']
    if len(draft_rows) != 240 or len({r['pairId'] for r in draft_rows}) != 240:
        raise ValueError('draft task count or uniqueness mismatch')
    drafts = {r['pairId']: r for r in draft_rows}
    annotations, counts, changes = [], {}, []
    for row, task in zip(rows, initial):
        pair = task['pair']
        if (row['pairId'], row['entityType'], row['evidenceHash']) != (pair['pairId'], pair['entityType'], task['evidenceHash']):
            raise ValueError('Markdown task binding mismatch or reserve included')
        prior = drafts[row['pairId']]
        if (prior['entityType'], prior['evidenceHash'], prior.get('humanDecision')) != (row['entityType'], row['evidenceHash'], None):
            raise ValueError('draft evidence mismatch or pre-filled human decision')
        revision = 'markdown-' + sha((queue['queueHash'] + '\n' + row['pairId'] + '\n' + source_set_hash).encode())
        annotations.append({'pairId': row['pairId'], 'entityType': row['entityType'], 'pairEvidenceHash': row['evidenceHash'],
                            'reviewerId': reviewer, 'revisionId': revision, 'revision': 1, 'supersedesRevisionId': None,
                            'label': row['label'], 'note': row['note'], 'annotatedAtUtc': converted_at})
        key = task['partition'] + '/' + row['entityType']
        count = counts.setdefault(key, {'same': 0, 'different': 0, 'uncertain': 0})
        count[row['label']] += 1
        if prior['proposedLabel'] != row['label']:
            changes.append(row['pairId'])
    checkpoint = {key: queue[key] for key in ('queueId', 'queueHash', 'sourcePopulationHash', 'splitHash')}
    checkpoint.update(schemaVersion='scholarchain.review-checkpoint.v1', queueSchemaVersion=queue['schemaVersion'],
                      exportedAtUtc=converted_at, annotations=annotations)
    return checkpoint, counts, changes


def convert(source, queue_path, output, reviewer, converted_at):
    if output.exists():
        raise ValueError('output already exists; refusing overwrite')
    source_names = [f'batch-{i:02}.md' for i in range(1, 13)] + ['draft-labels.json', 'progress.json', 'summary.md', 'baseline-repo-state.json']
    sources = {name: read_bytes(source / name) for name in source_names}
    queue_bytes = read_bytes(queue_path, MAX_QUEUE_BYTES)
    queue = json.loads(queue_bytes)
    draft = json.loads(sources['draft-labels.json'])
    rows = []
    for name in source_names[:12]:
        parsed = parse_batch(sources[name].decode('utf-8'))
        if len(parsed) != 20:
            raise ValueError('expected exactly 20 tasks per batch')
        for row in parsed:
            row['sourceBatch'] = name
        rows.extend(parsed)
    inventory = [{'path': name, 'bytes': len(data), 'sha256': sha(data),
                  'originalPath': str(source / name),
                  'observedFilesystemMtimeUtc': datetime.fromtimestamp((source / name).stat().st_mtime, timezone.utc).isoformat().replace('+00:00', 'Z')}
                 for name, data in sources.items()]
    source_set_hash = sha(json.dumps([{k: x[k] for k in ('path', 'bytes', 'sha256')} for x in inventory], sort_keys=True, separators=(',', ':')).encode())
    checkpoint, counts, changes = build_checkpoint(queue, draft, rows, reviewer, converted_at, source_set_hash)
    report = {'schemaVersion': 'scholarchain.markdown-label-conversion.v1', 'status': 'CONVERTED_PENDING_EXISTING_SCALA_IMPORT',
              'reviewerId': reviewer, 'convertedAtUtc': converted_at, 'queueHash': queue['queueHash'],
              'queueFileSha256': sha(queue_bytes), 'sourceSetSha256': source_set_hash,
              'initialTaskCount': len(rows), 'reserveTasksAnnotated': 0,
              'counts': dict(Counter(r['label'] for r in rows)), 'countsByPartitionAndEntity': counts,
              'aiSuggestionOverrides': len(changes), 'overriddenPairIds': changes,
              'sourceCommentCount': sum(bool(r['sourceComment']) for r in rows),
              'explicitlyAiAttributedComments': sum(r['commentAttribution'] == 'AI_SOURCE_CHECK_AS_EXPLICITLY_WRITTEN' for r in rows),
              'limitations': LIMITATIONS}
    provenance = {'schemaVersion': 'scholarchain.ai-assisted-human-label-provenance.v1', 'sourceFiles': inventory,
                  'queueFile': {'path': str(queue_path), 'bytes': len(queue_bytes), 'sha256': sha(queue_bytes)},
                  'sourceSetSha256': source_set_hash, 'reviewerId': reviewer, 'convertedAtUtc': converted_at,
                  'timestampSemantics': 'Conversion time only; not original review time. Source filesystem mtimes are observations, not authenticated annotation timestamps.',
                  'draftingAgent': draft.get('draftingAgent'), 'limitations': LIMITATIONS,
                  'taskSources': [{k: r[k] for k in ('taskNumber', 'pairId', 'evidenceHash', 'sourceBatch', 'sourceComment', 'commentAttribution')} for r in rows]}
    # Validate completely before creating anything; exclusive writes prohibit replacement.
    output.mkdir(parents=True, exist_ok=False)
    (output / 'source').mkdir()
    for name, data in sources.items():
        (output / 'source' / name).write_bytes(data)
    for name, value in [('checkpoint.json', checkpoint), ('provenance.v1.json', provenance), ('conversion-report.json', report)]:
        with (output / name).open('x', encoding='utf-8') as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
    for item in inventory:
        if read_bytes(source / item['path']) != sources[item['path']] or sha((output / 'source' / item['path']).read_bytes()) != item['sha256']:
            raise ValueError('source changed during conversion or retained copy differs')
    if read_bytes(queue_path, MAX_QUEUE_BYTES) != queue_bytes:
        raise ValueError('queue changed during conversion')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--queue', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reviewer', required=True)
    parser.add_argument('--converted-at', required=True, help='UTC conversion timestamp, not original review timestamp')
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.queue, args.output, args.reviewer, args.converted_at), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
