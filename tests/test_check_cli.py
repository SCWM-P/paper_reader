"""Completeness rules and public CLI behavior, entirely offline."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from paper_reader.scripts.cli import main
from paper_reader.scripts.record_check import MODULES, check_record
from paper_reader.scripts.html_note import render
from paper_reader.scripts.reading_record import normalize_record
from paper_reader.scripts.zotero_workflow import reading_note_html

ROOT = Path(__file__).resolve().parents[1]


def record():
    return {'metadata': {'title': 'Test paper', 'author': ['Test author']},
            'summary': '一个阅读结论。', 'highlights': [{'title': '贡献', 'content': '一个贡献。'}],
            'Q & A': [{'question': '为什么？', 'answer': '一个讨论结论。'}]}


class ReadOnlyZotero:
    library = 'users/0'

    def item(self, key):
        return {'data': {'itemType': 'conferencePaper', 'title': 'Test paper'}}

    def select_uri(self, key):
        return 'zotero://select/library/items/' + key


class CompletenessTests(unittest.TestCase):
    def test_required_nonempty_modules_pass_without_status_declarations(self):
        source = record()
        original = deepcopy(source)
        report = check_record(source)
        self.assertEqual(report['status'], 'ok')
        self.assertEqual(set(report['modules']), set(MODULES))
        self.assertTrue(all(row == {'status': 'ok'} for row in report['modules'].values()))
        self.assertEqual(source, original)

    def test_all_missing_modules_are_reported_independently(self):
        report = check_record({})
        self.assertEqual(report['status'], 'error')
        self.assertTrue(all(row['status'] == 'error' for row in report['modules'].values()))
        for name in MODULES:
            source = record()
            del source[name]
            rows = check_record(source)['modules']
            self.assertEqual(rows[name]['status'], 'error')
            self.assertTrue(all(row['status'] == 'ok' for key, row in rows.items() if key != name))

    def test_empty_required_content_is_error_except_qa_warning(self):
        for name in MODULES:
            for empty in (None, '', ' \n ', [], {}, [' '], {'content': ''}):
                with self.subTest(module=name, empty=empty):
                    source = record()
                    source[name] = empty
                    row = check_record(source)['modules'][name]
                    self.assertEqual(row['status'], 'warning' if name == 'Q & A' else 'error')

    def test_summary_degradation_and_empty_qa_are_warnings_not_errors(self):
        source = record()
        source['completeness'] = {'summary': {'status': 'degraded'}}
        source['Q & A'] = []
        report = check_record(source)
        self.assertEqual(report['status'], 'warning')
        self.assertEqual(report['modules']['summary']['status'], 'warning')
        self.assertEqual(report['modules']['Q & A']['status'], 'warning')
        self.assertEqual(report['modules']['metadata']['status'], 'ok')
        self.assertEqual(normalize_record(source)['completeness'], source['completeness'])

    def test_warning_does_not_mask_other_modules_errors_or_empty_content(self):
        source = record()
        source.update(metadata={}, highlights=[], **{'Q & A': []})
        source['completeness'] = {'summary': {'status': 'degraded'}}
        report = check_record(source)
        self.assertEqual([report['modules'][key]['status'] for key in MODULES],
                         ['error', 'warning', 'error', 'warning'])
        source['summary'] = ''
        self.assertEqual(check_record(source)['modules']['summary']['status'], 'error')

    def test_status_is_structured_and_not_guessed_from_prose(self):
        source = record()
        source['summary'] = '这里讨论模型的性能降级，不是阅读记录的降级标签。'
        self.assertEqual(check_record(source)['status'], 'ok')
        for name in MODULES:
            source['completeness'] = {name: {'status': 'complete'}}
            self.assertEqual(check_record(source)['status'], 'ok')
            source['completeness'][name]['status'] = 'degraded'
            self.assertEqual(check_record(source)['modules'][name]['status'], 'warning')

    def test_status_has_only_complete_or_degraded_and_no_extra_fields(self):
        for state in ({'status': 'unassessed'}, {'status': True}, {'status': []}, {},
                      {'status': 'degraded', 'reasons': ['draft']}, 'degraded'):
            with self.subTest(state=state):
                source = record()
                source['completeness'] = {'summary': state}
                self.assertEqual(check_record(source)['modules']['summary']['status'], 'error')
        for malformed in (None, [], {'modules': {}}):
            source = record()
            source['completeness'] = malformed
            with self.assertRaises(ValueError):
                check_record(source)

    def test_optional_extensions_and_resource_files_are_not_checked(self):
        source = record()
        source['paper'] = {'file': 'not-present.pdf'}
        for others in (None, [], 'anything', {'custom': {'invalid': True}}, 123):
            source['others'] = others
            source['completeness'] = {'others': {'arbitrary': 'not checked'}}
            self.assertEqual(check_record(source)['status'], 'ok')

    def test_obsolete_record_aliases_do_not_supply_required_modules(self):
        source = record()
        source['qa'] = source.pop('Q & A')
        self.assertEqual(check_record(source)['modules']['Q & A']['status'], 'error')
        source['paper'] = source.pop('metadata')
        self.assertEqual(check_record(source)['modules']['metadata']['status'], 'error')
        with self.assertRaises(ValueError):
            normalize_record(source, record()['metadata'])

    def test_degraded_status_is_visible_in_html_and_zotero_summary(self):
        source = record()
        source['completeness'] = {'summary': {'status': 'degraded'}}
        page = render(source)
        summary = reading_note_html(ReadOnlyZotero(), 'PAPER001', source)
        for output in (page, summary):
            self.assertIn('WARNING · 已标记降级', output)
        self.assertEqual(source['summary'], '一个阅读结论。')


class CliTests(unittest.TestCase):
    def invoke(self, argv):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(argv)
        return code, output.getvalue()

    def test_check_directory_json_and_concise_report_exit_codes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = directory / 'assets/reading-record.json'
            path.parent.mkdir()
            source = record()
            path.write_text(json.dumps(source))
            code, output = self.invoke(['check', str(directory)])
            self.assertEqual(code, 0)
            self.assertEqual(output.splitlines(), ['OK metadata', 'OK summary', 'OK highlights', 'OK Q & A'])
            source['completeness'] = {'summary': {'status': 'degraded'}}
            source['Q & A'] = []
            path.write_text(json.dumps(source))
            code, output = self.invoke(['check', str(path), '--json'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)['status'], 'warning')
            del source['metadata']
            path.write_text(json.dumps(source))
            self.assertEqual(self.invoke(['check', str(path)])[0], 1)
            path.write_text('{invalid')
            self.assertEqual(self.invoke(['check', str(path)])[0], 2)
            self.assertFalse((directory / '.runtime').exists())

    def test_subcommand_help_routes_without_zotero_or_optional_dependencies(self):
        for command in ('check', 'zotero', 'authorize', 'render', 'metadata', 'figures'):
            with self.subTest(command=command):
                result = subprocess.run([sys.executable, '-B', '-m', 'paper_reader', command, '--help'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('paper ' + command, result.stdout)
        result = subprocess.run([sys.executable, '-B', '-m', 'paper_reader', 'unknown'], capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_copied_skill_directory_works_without_installed_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            skill = root / 'zotero'
            shutil.copytree(ROOT / '.agents/skills/zotero', skill, ignore=shutil.ignore_patterns('__pycache__'))
            source = root / 'record.json'
            source.write_text(json.dumps(record()))
            result = subprocess.run([sys.executable, '-I', '-S', str(skill), 'check', str(source)], cwd=root,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('OK summary', result.stdout)

    def test_examples_follow_current_status_conventions(self):
        example = json.loads((ROOT / 'papers/EXAMPLE/Attention Is All You Need/assets/reading-record.json').read_text())
        self.assertEqual(check_record(example)['status'], 'ok')
        self.assertEqual(example['completeness']['summary']['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
