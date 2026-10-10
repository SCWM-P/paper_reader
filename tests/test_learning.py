"""Offline behavior tests; no Zotero writes, external APIs or model calls."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/zotero/scripts'
from paper_reader.scripts.html_note import render, THEMES
from paper_reader.scripts.learning_record import normalize_learning, _route_issues
from paper_reader.scripts.learning_note import learning_content
from paper_reader.scripts.reading_record import normalize_record
from paper_reader.scripts.zotero_workflow import reading_note_html


def learning():
    return {
        'anchor': {'locator': '§3.2.1, Equation (1)', 'excerpt': 'Attention(Q,K,V)',
                   'page': 4, 'url': 'https://example.org/paper.pdf'},
        'reader': {'starting_point': '基础算术', 'basis': 'assumed'},
        'goal': '读懂加权合成',
        'concepts': [{'id': 'average', 'term': '加权平均', 'state': 'explained',
                      'lesson': [{'kind': 'teaching', 'title': '两个数', 'text': '10 与 20 各占一半，得到 15。'}],
                      'check': {'question': '各占一半得到多少？', 'reference_answer': '15。'}}],
        'next': {'action': 'return_to_paper', 'reason': '检验可跳过，继续读原句。'},
    }


def record(value=None):
    return {'metadata': {'title': 'Demo paper', 'author': ['Demo author']},
            'summary': '教学测试记录。', 'highlights': ['教学测试'], 'Q & A': [],
            'completeness': {'summary': {'status': 'degraded'}},
            'others': [{'id': 'lesson', 'title': '原文卡点', 'learning': value or learning()}]}


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.data = []
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
        self.data.append(value)
        if self.in_json:
            self.json += value


class ReadOnlyZotero:
    library = 'users/0'

    def item(self, key):
        return {'data': {'itemType': 'conferencePaper', 'title': 'Demo paper'}}

    def select_uri(self, key):
        return 'zotero://select/library/items/' + key


class LearningTests(unittest.TestCase):
    def test_normalization_is_repeatable_and_does_not_mutate_input(self):
        source = record()
        original = deepcopy(source)
        first = normalize_record(source)
        self.assertEqual(source, original)
        self.assertEqual(normalize_record(first), first)
        self.assertEqual(first['others'][0]['learning']['concepts'][0]['state'], 'explained')

    def test_current_named_extensions_render_without_legacy_field_fallbacks(self):
        for extensions in ('一句补充', {'补充': '内容'}, [{'title': '已有模块', 'custom': {'x': 1}}]):
            source = record()
            source['others'] = extensions
            self.assertEqual(normalize_record(source)['Q & A'], [])
            self.assertIn('教学测试记录', render(source))
        with self.assertRaises(ValueError):
            normalize_record({'title': '旧笔记', 'paper': {'title': '旧论文'}, 'summary': '旧结论'})

    def test_existing_attention_record_renders_without_learning(self):
        path = ROOT / 'papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json'
        source = json.loads(path.read_text())
        normalized = normalize_record(source)
        self.assertEqual(normalized['Q & A'], source['Q & A'])
        self.assertTrue(all('learning' not in x for x in normalized['others']))
        doc = Document(render(source, asset_base=path.parent))
        self.assertTrue(any(t == 'img' for t, _ in doc.tags))
        self.assertEqual(json.loads(doc.json)['summary'], source['summary'])

    def test_all_states_are_legal_but_none_is_inferred(self):
        for state in ('unknown', 'uncertain', 'explained', 'confirmed', 'skipped'):
            with self.subTest(state=state):
                source = learning()
                node = source['concepts'][0]
                node['state'] = state
                if state == 'confirmed':
                    node['check'].update(user_answer='15，因为各占一半。', assessment='pass', feedback='计算与解释正确。')
                normalized = normalize_learning(source)
                self.assertEqual(normalized['concepts'][0]['state'], state)
                if state != 'confirmed':
                    self.assertTrue(normalized['issues'])

    def test_confirmation_requires_actual_answer_and_passing_feedback(self):
        for update in ({}, {'assessment': 'pass'}, {'assessment': 'pass', 'user_answer': '15'},
                       {'assessment': 'retry', 'user_answer': '20', 'feedback': '请再试'}):
            with self.subTest(update=update):
                source = learning()
                source['concepts'][0]['state'] = 'confirmed'
                source['concepts'][0]['check'].update(update)
                with self.assertRaises(ValueError):
                    normalize_learning(source)

    def test_skipping_and_returning_need_no_answer(self):
        source = learning()
        source['concepts'][0]['state'] = 'skipped'
        source['concepts'][0].pop('check')
        normalized = normalize_learning(source)
        self.assertEqual(normalized['next']['action'], 'return_to_paper')
        page = learning_content(normalized)
        self.assertIn('data-state="skipped"', page)
        self.assertNotIn('data-state="confirmed"', page)
        self.assertIn('打开卡点原文', page)

    def test_confirmation_can_be_withdrawn_and_derived_warnings_refresh(self):
        source = learning()
        node = source['concepts'][0]
        node['state'] = 'confirmed'
        node['check'].update(user_answer='15', assessment='pass', feedback='计算正确')
        confirmed = normalize_learning(source)
        self.assertFalse(confirmed['issues'])
        confirmed['concepts'][0].update(state='uncertain', revision='用户发现仍说不清权重意义，撤回确认。')
        withdrawn = normalize_learning(confirmed)
        self.assertTrue(withdrawn['issues'])
        self.assertEqual(withdrawn['concepts'][0]['check']['user_answer'], '15')
        withdrawn['concepts'][0]['state'] = 'confirmed'
        self.assertFalse(normalize_learning(withdrawn)['issues'])

    def test_missing_or_blank_original_anchor_blocks_export(self):
        for anchor in (None, {}, {'locator': '§3.2.1'}, {'locator': '', 'excerpt': '句子'},
                       {'locator': '§3.2.1', 'excerpt': ' '}):
            with self.subTest(anchor=anchor):
                source = learning()
                source['anchor'] = anchor
                with self.assertRaises(ValueError):
                    render(record(source))

    def test_bad_types_states_budgets_and_urls_are_rejected(self):
        mutations = [
            lambda x: x.update(version=True),
            lambda x: x['reader'].update(basis='guess'),
            lambda x: x.update(goal=[]),
            lambda x: x['anchor'].update(page=True),
            lambda x: x['anchor'].update(page=0),
            lambda x: x['anchor'].update(url='javascript:alert(1)'),
            lambda x: x['anchor'].update(url='https://user:password@example.org/'),
            lambda x: x.update(concepts={}),
            lambda x: x.update(unresolved='不懂'),
            lambda x: x.update(budget={'max_depth': 0, 'max_nodes': 5}),
            lambda x: x.update(budget={'max_depth': 2, 'max_nodes': True}),
            lambda x: x.update(budget={'max_depth': 4, 'max_nodes': 5}),
            lambda x: x.update(budget={'max_depth': 2, 'max_nodes': 9}),
            lambda x: x['concepts'][0].update(state='mastered'),
            lambda x: x['concepts'][0].update(state=[]),
            lambda x: x['concepts'][0].update(depends_on='other'),
            lambda x: x['concepts'][0].update(depends_on=['other', 'other']),
            lambda x: x['concepts'][0].update(lesson=[]),
            lambda x: x['concepts'][0].update(check=None),
            lambda x: x['concepts'][0]['lesson'][0].update(kind='verified_fact'),
            lambda x: x['concepts'][0]['lesson'][0].update(kind='paper'),
            lambda x: x['concepts'][0]['check'].update(assessment='automatic'),
            lambda x: x['next'].update(action='mastered'),
        ]
        for i, mutation in enumerate(mutations):
            with self.subTest(case=i):
                source = learning()
                mutation(source)
                with self.assertRaises(ValueError):
                    normalize_learning(source)

    def test_duplicate_concept_ids_are_rejected(self):
        source = learning()
        source['concepts'].append(deepcopy(source['concepts'][0]))
        with self.assertRaisesRegex(ValueError, 'unique'):
            normalize_learning(source)

    def test_cycle_and_missing_prerequisite_are_visible_and_can_return(self):
        for dependencies, text in ((['average'], '循环'), (['missing'], '未闭合')):
            with self.subTest(dependencies=dependencies):
                source = learning()
                source['concepts'][0]['depends_on'] = dependencies
                normalized = normalize_learning(source)
                self.assertTrue(any(text in x for x in normalized['issues']))
                page = learning_content(normalized)
                self.assertIn(text, page)
                self.assertIn('打开卡点原文', page)
                self.assertEqual(normalize_learning(normalized), normalized)

    def test_node_and_depth_budgets_stop_expansion(self):
        source = learning()
        source['budget'] = {'max_depth': 1, 'max_nodes': 2}
        source['concepts'] = [
            {'id': 'a', 'term': 'A', 'state': 'unknown', 'depends_on': ['b']},
            {'id': 'b', 'term': 'B', 'state': 'unknown', 'depends_on': ['c']},
            {'id': 'c', 'term': '不可展开的第三概念', 'state': 'unknown'},
        ]
        bounded = normalize_learning(source)
        self.assertTrue(any('节点预算' in x for x in bounded['issues']))
        doc = Document(learning_content(bounded))
        self.assertEqual(sum(t == 'article' for t, _ in doc.tags), 2)
        source['budget']['max_nodes'] = 3
        deep = normalize_learning(source)
        self.assertTrue(any('深度预算' in x for x in deep['issues']))

    def test_self_reference_in_a_dense_route_terminates(self):
        source = learning()
        source['budget'] = {'max_depth': 3, 'max_nodes': 8}
        ids = [f'node-{i}' for i in range(8)]
        source['concepts'] = [{'id': key, 'term': key, 'state': 'unknown', 'depends_on': ids} for key in ids]
        normalized = normalize_learning(source)
        self.assertTrue(any('循环' in x for x in normalized['issues']))
        self.assertLessEqual(len(normalized['issues']), len(ids) + 5)
        page = learning_content(normalized)
        self.assertLess(len(page.encode('utf-8')), 12000)
        self.assertIn('返回原文', page)

    def test_dense_route_work_is_bounded_by_nodes_edges_and_depth(self):
        counter = {'edges': 0}

        class CountedEdges(list):
            def __iter__(self):
                for value in super().__iter__():
                    counter['edges'] += 1
                    yield value

            def __getitem__(self, key):
                value = super().__getitem__(key)
                return CountedEdges(value) if isinstance(key, slice) else value

        ids = [f'node-{i}' for i in range(8)]
        concepts = [{'id': key, 'term': key, 'state': 'unknown', 'depends_on': CountedEdges(ids)} for key in ids]
        budget = {'max_nodes': 8, 'max_depth': 3}
        issues = _route_issues(concepts, budget)
        self.assertTrue(any('循环' in x for x in issues))
        # Count actual edge inspections rather than a timing threshold or hidden output.
        self.assertLessEqual(counter['edges'], len(ids) ** 2 * (budget['max_depth'] + 4))

    def test_depth_check_reuses_shared_prerequisites_without_losing_longer_routes(self):
        source = learning()
        source['budget'] = {'max_nodes': 4, 'max_depth': 2}
        source['concepts'] = [
            {'id': 'base', 'term': '基础', 'state': 'unknown', 'depends_on': []},
            {'id': 'shared', 'term': '共用先修', 'state': 'unknown', 'depends_on': ['base']},
            {'id': 'middle', 'term': '中间概念', 'state': 'unknown', 'depends_on': ['shared']},
            {'id': 'target', 'term': '当前概念', 'state': 'unknown', 'depends_on': ['middle', 'shared']},
        ]
        shallow = normalize_learning(source)
        self.assertEqual(sum('深度预算' in x for x in shallow['issues']), 1)
        source['budget']['max_depth'] = 3
        self.assertFalse(any('深度预算' in x for x in normalize_learning(source)['issues']))

    def test_large_manual_unresolved_list_has_bounded_presentation(self):
        source = learning()
        source['unresolved'] = [f'人工未解决项 {i}' for i in range(100)]
        normalized = normalize_learning(source)
        page = learning_content(normalized)
        doc = Document(page)
        self.assertLessEqual(sum(tag == 'li' for tag, _ in doc.tags), 16)
        self.assertIn('另有', page)
        self.assertEqual(len(normalized['unresolved']), 100)

    def test_sources_stay_attributed_in_page_and_searchable_summary(self):
        source = learning()
        source['concepts'][0]['lesson'] = [
            {'kind': kind, 'title': kind, 'text': '来源内容', 'locator': 'Chapter 1', 'url': 'https://example.org/'}
            for kind in ('paper', 'background', 'teaching', 'inference')
        ]
        page = render(record(source))
        summary = reading_note_html(ReadOnlyZotero(), 'PAPER001', record(source))
        for label in ('论文原文 / 概述', '外部背景', '教学示例', '教学推断'):
            self.assertIn(label, page)
            self.assertIn(label, summary)
        self.assertIn('自测参考解答', summary)
        self.assertIn('待作答', summary)

    def test_user_content_is_escaped_in_page_summary_and_embedded_json(self):
        payload = '<script>alert("unsafe")</script><img src=x onerror=alert(1)>'
        source = learning()
        source['anchor']['excerpt'] = payload
        source['concepts'][0]['lesson'][0]['text'] = payload
        source['concepts'][0]['check']['reference_answer'] = payload
        page = render(record(source))
        summary = reading_note_html(ReadOnlyZotero(), 'PAPER001', record(source))
        doc = Document(page)
        self.assertEqual(sum(t == 'script' for t, _ in doc.tags), 2)
        self.assertFalse(any(t == 'img' for t, _ in doc.tags))
        self.assertNotIn(payload, page)
        self.assertNotIn(payload, summary)
        self.assertEqual(json.loads(doc.json)['others'][0]['learning']['anchor']['excerpt'], payload)

    def test_all_themes_are_offline_and_reference_answers_are_optional(self):
        for theme in THEMES:
            with self.subTest(theme=theme):
                doc = Document(render(record(), theme))
                resources = [a.get('src') or a.get('href') for t, a in doc.tags
                             if 'src' in a or t == 'link']
                self.assertFalse(any(x and x.startswith(('http:', 'https:', '//')) for x in resources))
                references = [a for t, a in doc.tags if t == 'details' and a.get('class') == 'learning-reference']
                self.assertEqual(len(references), 1)
                self.assertNotIn('open', references[0])
                self.assertIn('connect-src \'none\'', next(a['content'] for t, a in doc.tags if t == 'meta' and a.get('http-equiv') == 'Content-Security-Policy'))

    def test_relative_pdf_anchor_repeats_without_mutating_source(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / 'paper.pdf').write_bytes(b'%PDF-fixture')
            source = record()
            source['paper'] = {'file': 'paper.pdf'}
            original = deepcopy(source)
            first = render(source, asset_base=root, output_base=root)
            self.assertEqual(source, original)
            self.assertEqual(render(source, asset_base=root, output_base=root), first)
            self.assertIn('href="paper.pdf#page=4"', first)

    def test_zotero_pdf_anchor_uses_physical_page_query(self):
        source = learning()
        source['anchor']['url'] = 'zotero://open-pdf/library/items/PAPER001?page=1'
        page = learning_content(normalize_learning(source))
        self.assertIn('href="zotero://open-pdf/library/items/PAPER001?page=4"', page)

    def test_summary_and_page_share_paper_pdf_fallback_without_anchor_url(self):
        cases = (
            ('zotero://open-pdf/library/items/ABC12345', 'zotero://open-pdf/library/items/ABC12345?page=4'),
            ('https://example.org/paper.pdf', 'https://example.org/paper.pdf#page=4'),
        )
        for pdf_url, expected in cases:
            with self.subTest(pdf_url=pdf_url):
                source = record()
                source['others'][0]['learning']['anchor'].pop('url')
                source['paper'] = {'pdf_url': pdf_url}
                original = deepcopy(source)
                page = Document(render(source))
                summary = Document(reading_note_html(ReadOnlyZotero(), 'PAPER001', source))
                for document in (page, summary):
                    self.assertEqual(sum(tag == 'a' and attrs.get('href') == expected for tag, attrs in document.tags), 2)
                self.assertEqual(source, original)

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
            invalid['others'][0]['learning'].pop('anchor')
            src.write_text(json.dumps(invalid))
            failed = subprocess.run(cmd + ['--force'], capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(out.read_bytes(), expected)


if __name__ == '__main__':
    unittest.main()
