import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from caption_converter.core import (
    convert_content, convert_file, parse_srt_cues, parse_vtt_cues,
)
from caption_converter.validation import CaptionParseError, prepare_caption_content


CASES = json.loads((Path(__file__).parent / 'fixtures/caption_cases.json').read_text())


class CaptionValidationTests(unittest.TestCase):
    def test_shared_regressions(self):
        for case in CASES:
            with self.subTest(case=case['name']):
                parser = parse_srt_cues if case['format'] == 'srt' else parse_vtt_cues
                if 'error' in case:
                    with self.assertRaisesRegex(CaptionParseError, case['error']) as result:
                        convert_content(case['source'], case['format'], True, True, False)
                    self.assertRegex(str(result.exception), r'source line \d+')
                    self.assertIn('Text to review:', str(result.exception))
                    self.assertIn('original file unchanged', str(result.exception))
                    continue
                self.assertEqual(convert_content(case['source'], case['format'], True, True, False), case['expected_python'])
                for keep_biu in [False, True]:
                    expected = case['expected_keep_biu'] if keep_biu else case['expected_cues']
                    cues = parser(case['source'], keep_biu)
                    self.assertEqual(len(cues), len(expected))
                    for cue, target in zip(cues, expected):
                        self.assertEqual(cue.text, target['text'])
                        self.assertAlmostEqual(cue.start, target['start'], places=8)
                        self.assertAlmostEqual(cue.end, target['end'], places=8)
                if case['name'].startswith('clean_'):
                    self.assertEqual(prepare_caption_content(case['source'], case['format']), case['source'])

    def test_repair_keeps_source_times_before_normalization(self):
        for case in CASES:
            if 'error' in case:
                continue
            with self.subTest(case=case['name']):
                prepared = prepare_caption_content(case['source'], case['format'])
                self.assertEqual(prepared.splitlines(), case['repaired_source'].splitlines())

    def test_file_workflow_names_and_source_preservation(self):
        for case in CASES:
            with self.subTest(case=case['name']), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / f"captions.{case['format']}"
                source.write_text(case['source'], encoding='utf-8')
                before = source.read_bytes()
                if 'error' in case:
                    # Even pre-existing output files must survive a failed conversion.
                    existing = Path(directory) / 'captions.normalized.srt'
                    existing.write_text('previous output')
                    with self.assertRaises(CaptionParseError):
                        convert_file(source, True, True, True)
                    self.assertEqual(existing.read_text(), 'previous output')
                    self.assertEqual(set(Path(directory).iterdir()), {source, existing})
                else:
                    written = convert_file(source, True, True, False)
                    expected_names = [f'captions.normalized.{ext}' if ext == case['format'] else f'captions.{ext}' for ext in ['srt', 'vtt']]
                    self.assertEqual([p.name for p in written], expected_names)
                    for output in written:
                        self.assertEqual(output.read_text(), case['expected_python'][output.suffix[1:]])
                self.assertEqual(source.read_bytes(), before)

    def test_cli_reports_file_and_continues_batch(self):
        from caption_converter.cli import main
        case = next(c for c in CASES if c['name'] == 'ambiguous_tail')
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'review.srt'
            good = Path(directory) / 'good.srt'
            bad.write_text(case['source'])
            good.write_text('1\n00:00:01,000 --> 00:00:02,000\nKeep me.\n')
            error, output = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(error), contextlib.redirect_stdout(output):
                status = main(['--to-vtt', str(bad), str(good)])
            self.assertEqual(status, 1)
            self.assertIn('review.srt', error.getvalue())
            self.assertIn('cue 1, source line 4', error.getvalue())
            self.assertIn('Detached dialogue at EOF.', error.getvalue())
            self.assertFalse(bad.with_suffix('.vtt').exists())
            self.assertIn('Keep me.', good.with_suffix('.vtt').read_text())

    def test_gui_uses_existing_warning_flow_and_continues_batch(self):
        from caption_converter.gui import CaptionConverterApp
        class Value:
            def get(self): return True
            def set(self, value): self.value = value
        case = next(c for c in CASES if c['name'] == 'ambiguous_tail')
        with tempfile.TemporaryDirectory() as directory:
            bad, good = Path(directory) / 'review.srt', Path(directory) / 'good.srt'
            bad.write_text(case['source'])
            good.write_text('1\n00:00:01,000 --> 00:00:02,000\nKeep me.\n')
            app = CaptionConverterApp.__new__(CaptionConverterApp)
            app.files = [bad, good]
            app.to_srt = app.to_vtt = app.to_ttml = Value()
            app.status = Value()
            messages = []
            app.append_log = messages.append
            with patch('caption_converter.gui.messagebox.showwarning') as warning, patch('caption_converter.gui.messagebox.showinfo') as info:
                app.convert()
            warning.assert_called_once()
            info.assert_not_called()
            self.assertIn('Success: 1. Failed: 1.', app.status.value)
            self.assertTrue(any('review.srt' in line and 'Text to review:' in line for line in messages))
            self.assertTrue(good.with_suffix('.vtt').exists())
            self.assertFalse(bad.with_suffix('.vtt').exists())


if __name__ == '__main__':
    unittest.main()
