"""Ordinary reading-record and offline rendering regressions; no live Zotero calls."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from paper_reader.scripts.html_note import render, THEMES
from paper_reader.scripts.reading_record import normalize_record
from paper_reader.scripts.zotero_workflow import reading_note_html

ROOT = Path(__file__).resolve().parents[1]


def record():
    return {'metadata': {'title': 'Demo paper', 'author': ['Demo author']},
            'summary': '教学测试记录。', 'highlights': ['教学测试'], 'Q & A': [],
            'completeness': {'summary': {'status': 'degraded'}},
            'others': [{'id': 'extension', 'title': '补充阅读', 'content': '可编辑内容'}]}


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.in_json = False
        self.json = ''
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == 'script' and attrs.get('id') == 'note-data':
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_json = False

    def handle_data(self, value):
        if self.in_json:
            self.json += value


class ReadOnlyZotero:
    library = 'users/0'

    def item(self, key):
        return {'data': {'itemType': 'conferencePaper', 'title': 'Demo paper'}}

    def select_uri(self, key):
        return 'zotero://select/library/items/' + key


class ReadingRecordTests(unittest.TestCase):
    def test_normalization_is_repeatable_and_does_not_mutate_input(self):
        source = record()
        original = deepcopy(source)
        first = normalize_record(source)
        self.assertEqual(source, original)
        self.assertEqual(normalize_record(first), first)
        self.assertEqual(first['others'][0]['content'], '可编辑内容')

    def test_current_named_extensions_render_without_legacy_field_fallbacks(self):
        for extensions in ('一句补充', {'补充': '内容'}, [{'title': '已有模块', 'custom': {'x': 1}}]):
            source = record()
            source['others'] = extensions
            self.assertEqual(normalize_record(source)['Q & A'], [])
            self.assertIn('教学测试记录', render(source))
        with self.assertRaises(ValueError):
            normalize_record({'title': '旧笔记', 'paper': {'title': '旧论文'}, 'summary': '旧结论'})

    def test_existing_attention_record_preserves_discussion_and_figures(self):
        path = ROOT / 'papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json'
        source = json.loads(path.read_text())
        normalized = normalize_record(source)
        self.assertEqual(normalized['Q & A'], source['Q & A'])
        doc = Document(render(source, asset_base=path.parent))
        self.assertTrue(any(t == 'img' for t, _ in doc.tags))
        self.assertEqual(json.loads(doc.json)['summary'], source['summary'])

    def test_user_content_is_escaped_in_page_summary_and_embedded_json(self):
        payload = '<script>alert("unsafe")</script><img src=x onerror=alert(1)>'
        source = record()
        source['others'][0]['content'] = payload
        source['Q & A'] = [{'question': payload, 'answer': payload}]
        page = render(source)
        summary = reading_note_html(ReadOnlyZotero(), 'PAPER001', source)
        doc = Document(page)
        self.assertEqual(sum(t == 'script' for t, _ in doc.tags), 2)
        self.assertFalse(any(t == 'img' for t, _ in doc.tags))
        self.assertNotIn(payload, page)
        self.assertNotIn(payload, summary)
        self.assertEqual(json.loads(doc.json)['others'][0]['content'], payload)

    def test_all_themes_are_offline(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                doc = Document(render(record(), theme))
                resources = [a.get('src') or a.get('href') for t, a in doc.tags
                             if 'src' in a or t == 'link']
                self.assertFalse(any(x and x.startswith(('http:', 'https:', '//')) for x in resources))
                self.assertIn("connect-src 'none'", next(a['content'] for t, a in doc.tags
                              if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy'))

    def test_relative_pdf_source_repeats_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'paper.pdf').write_bytes(b'%PDF-fixture')
            source = record()
            source['paper'] = {'file': 'paper.pdf'}
            original = deepcopy(source)
            first = render(source, asset_base=root, output_base=root)
            self.assertEqual(source, original)
            self.assertEqual(render(source, asset_base=root, output_base=root), first)
            self.assertIn('href="paper.pdf"', first)

    def test_cli_failure_and_repeated_input_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            src, out = root / 'record.json', root / 'note.html'
            src.write_text(json.dumps(record(), ensure_ascii=False))
            cmd = [sys.executable, '-B', '-m', 'paper_reader', 'render', '--file', str(src), '--out', str(out)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            expected = out.read_bytes()
            duplicate = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(duplicate.returncode, 1)
            self.assertEqual(out.read_bytes(), expected)
            forced = subprocess.run(cmd + ['--force'], capture_output=True, text=True)
            self.assertEqual(forced.returncode, 0, forced.stdout + forced.stderr)
            self.assertEqual(out.read_bytes(), expected)
            invalid = record()
            invalid.pop('metadata')
            src.write_text(json.dumps(invalid))
            failed = subprocess.run(cmd + ['--force'], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(out.read_bytes(), expected)


if __name__ == '__main__':
    unittest.main()
