import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from submission import build_evidence as evidence


class EvidenceTests(unittest.TestCase):
    def test_every_viewer_record_matches_original_line(self):
        traces = evidence.collect()[-1]
        raw = evidence.read_rows(evidence.STUDY / 'runs/formal_v0.6.0_test/trajectories.jsonl')
        requests = {r['case_id']: r for r in evidence.read_rows(evidence.STUDY / 'data/public/test_requests.jsonl')}
        self.assertEqual(len(traces), 260)
        for trace, original in zip(traces, raw):
            self.assertEqual(trace['trajectory'], original)
            self.assertEqual(raw[trace['source_line'] - 1], original)
            self.assertEqual(trace['request'], requests[original['case_id']])

    def test_missing_or_duplicate_rows_are_rejected(self):
        real_read = evidence.read_rows
        for duplicate in (False, True):
            def altered(path):
                rows = real_read(path)
                if path.name == 'trajectories.jsonl':
                    return rows[:-1] + ([rows[0]] if duplicate else [])
                return rows
            with self.subTest(duplicate=duplicate), patch.object(evidence, 'read_rows', side_effect=altered):
                with self.assertRaisesRegex(ValueError, 'Incomplete or duplicate'):
                    evidence.collect()

    def test_corrupted_score_is_not_republished(self):
        real_read = evidence.read_rows
        def altered(path):
            rows = real_read(path)
            if path.name == 'trajectories.jsonl':
                rows[0]['score']['quality'] = 0.123
            return rows
        with patch.object(evidence, 'read_rows', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'Saved score differs'):
                evidence.collect()

    def test_export_is_deterministic_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / 'one', Path(folder) / 'two'
            evidence.export(first)
            evidence.export(second)
            for path in first.iterdir():
                self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
            with self.assertRaises(FileExistsError):
                evidence.export(first)

    def test_conversation_text_cannot_end_data_script(self):
        data = evidence.collect()
        payload = '</script><script>window.INJECTED=true</script>&<b>'
        data[-1][0]['request']['initial_request'] = payload
        with tempfile.TemporaryDirectory() as folder, patch.object(evidence, 'collect', return_value=data):
            out = Path(folder) / 'safe'
            evidence.export(out)
            html = (out / 'trace_viewer.html').read_text(encoding='utf-8')
            self.assertNotIn(payload, html)
            embedded = html.split('id="records">', 1)[1].split('</script>', 1)[0]
            self.assertEqual(json.loads(embedded)[0]['request']['initial_request'], payload)


if __name__ == '__main__':
    unittest.main()
