#!/usr/bin/env python3
"""Synthetic conversion guards; these are not human review evidence."""
import copy
import tempfile
import unittest
from pathlib import Path
import convert_review_batches as c


def section(decision='☑ same ☐ different ☐ uncertain', comment=''):
    return ("## Task 1 — Work\n\n- **pairId:** `resolution-pair:" + 'a' * 64 + "`\n"
            "- **evidenceHash:** `" + 'b' * 64 + "`\n\n"
            "**Note:** AI reason that must not become the human note.\n\n"
            "**Danny's decision:** " + decision + "\n\n**Comments:**\n\n> " + comment + "\n\n---\n")


def fixture():
    tasks, rows, drafts = [], [], []
    for i in range(300):
        pid = 'resolution-pair:' + f'{i:064x}'
        et = 'Work' if i % 2 == 0 else 'Researcher'
        eh = f'{i + 1:064x}'
        task = {'pair': {'pairId': pid, 'entityType': et}, 'evidenceHash': eh,
                'role': 'initial' if i < 240 else 'reserve', 'partition': 'development' if i < 40 else 'held-out'}
        tasks.append(task)
        if i < 240:
            rows.append({'taskNumber': i + 1, 'pairId': pid, 'entityType': et, 'evidenceHash': eh, 'label': 'same', 'note': c.NOTE_PREFIX})
            drafts.append({'pairId': pid, 'entityType': et, 'evidenceHash': eh, 'humanDecision': None, 'proposedLabel': 'different'})
    queue = dict(queueId='q', queueHash='c' * 64, sourcePopulationHash='d' * 64, splitHash='e' * 64,
                 schemaVersion='scholarchain.review-queue.v1', tasks=tasks)
    draft = {'queueId': 'q', 'queueHash': 'c' * 64, 'tasks': drafts}
    return queue, draft, rows


class ConversionTests(unittest.TestCase):
    def test_single_selection_preserves_user_comment_not_ai_reason(self):
        row = c.parse_batch(section(comment='My actual comment.'))[0]
        self.assertEqual(row['label'], 'same')
        self.assertIn('My actual comment.', row['note'])
        self.assertNotIn('AI reason', row['note'])

    def test_empty_and_multiple_selections_rejected(self):
        for line in ['☐ same ☐ different ☐ uncertain', '☑ same ☑ different ☐ uncertain']:
            with self.subTest(line=line), self.assertRaises(ValueError):
                c.parse_batch(section(line))

    def test_malformed_and_repeated_decision_rejected(self):
        for text in [section().replace('☑ same', 'yes same'), section() + "**Danny's decision:** ☑ same ☐ different ☐ uncertain\n"]:
            with self.assertRaises(ValueError):
                c.parse_batch(text)

    def test_attributed_ai_comment_keeps_attribution(self):
        comment = 'Source check by Claude (2026-10-20), not Danny: unverified source.'
        row = c.parse_batch(section(comment=comment))[0]
        self.assertEqual(row['sourceComment'], comment)
        self.assertEqual(row['commentAttribution'], 'AI_SOURCE_CHECK_AS_EXPLICITLY_WRITTEN')
        self.assertIn(comment, row['note'])

    def test_oversized_note_is_rejected_not_truncated(self):
        with self.assertRaisesRegex(ValueError, '2000'):
            c.parse_batch(section(comment='x' * 2000))

    def test_valid_contract_has_conversion_timestamp_and_deterministic_revisions(self):
        q, d, r = fixture()
        first, counts, changed = c.build_checkpoint(q, d, r, 'danny', '2026-10-20T22:00:00Z', 'f' * 64)
        second, _, _ = c.build_checkpoint(q, d, r, 'danny', '2026-10-20T22:00:00Z', 'f' * 64)
        self.assertEqual(first, second)
        self.assertEqual(len(first['annotations']), 240)
        self.assertEqual(len(set(x['revisionId'] for x in first['annotations'])), 240)
        self.assertTrue(all(x['annotatedAtUtc'] == first['exportedAtUtc'] and x['revision'] == 1 and x['supersedesRevisionId'] is None for x in first['annotations']))
        self.assertEqual(len(changed), 240)
        self.assertEqual(counts['development/Work']['same'], 20)

    def test_changed_hash_and_reserve_substitution_rejected(self):
        for kind in ['hash', 'reserve', 'entity', 'queue', 'draft']:
            q, d, r = fixture()
            if kind == 'hash': r[0]['evidenceHash'] = '9' * 64
            if kind == 'reserve': r[0]['pairId'] = q['tasks'][-1]['pair']['pairId']
            if kind == 'entity': r[0]['entityType'] = 'Researcher'
            if kind == 'queue': d['queueHash'] = '9' * 64
            if kind == 'draft': d['tasks'][0]['humanDecision'] = 'same'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                c.build_checkpoint(q, d, r, 'danny', '2026-10-20T22:00:00Z', 'f' * 64)

    def test_missing_duplicate_and_out_of_order_tasks_rejected(self):
        for kind in ['missing', 'duplicate', 'order']:
            q, d, r = fixture()
            if kind == 'missing': r.pop()
            if kind == 'duplicate': r[1] = copy.deepcopy(r[0])
            if kind == 'order': r[0], r[1] = r[1], r[0]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                c.build_checkpoint(q, d, r, 'danny', '2026-10-20T22:00:00Z', 'f' * 64)

    def test_non_utc_timestamp_and_bad_reviewer_rejected(self):
        q, d, r = fixture()
        for reviewer, stamp in [('danny', '2026-10-20T22:00:00+00:00'), ('danny', 'not-a-date'), (' danny', '2026-10-20T22:00:00Z')]:
            with self.subTest(reviewer=reviewer, stamp=stamp), self.assertRaises((ValueError, TypeError)):
                c.build_checkpoint(q, d, r, reviewer, stamp, 'f' * 64)

    def test_existing_output_refused_before_source_read(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaisesRegex(ValueError, 'already exists'):
                c.convert(root / 'missing-source', root / 'missing-queue', root, 'danny', '2026-10-20T22:00:00Z')

    def test_file_bounds_and_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'file').write_bytes(b'abc')
            (root / 'link').symlink_to(root / 'file')
            for p, bound in [(root / 'file', 2), (root / 'link', 100)]:
                with self.assertRaises(ValueError): c.read_bytes(p, bound)


if __name__ == '__main__':
    unittest.main()
