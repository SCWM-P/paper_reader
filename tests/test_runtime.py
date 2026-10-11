"""Workspace runtime tests; fake Zotero responses, no network or real credentials."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/zotero/scripts'
from paper_reader.scripts.zotero_client import Zotero, config_dir, key_path
from paper_reader.scripts.zotero_index import LiteratureIndex, index_path, index_status


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def fake_api(self, method, path, **kwargs):
    if method != 'GET' or path != '/api/':
        raise AssertionError('Unexpected API operation')
    return 200, {'zotero-server-id': 'test-server', 'zotero-api-version': '3'}, b''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'paper_reader'
        self.project.mkdir()
        environment = os.environ.copy()
        environment.pop('ZOTERO_AGENT_HOME', None)
        environment.pop('ZOTERO_LOCAL_API_KEY', None)
        environment.pop('APPDATA', None)
        environment.pop('XDG_CONFIG_HOME', None)
        self.env = patch.dict(os.environ, environment, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fake_home = self.root / 'fake-user'
        self.fake_home.mkdir()
        home = patch('paper_reader.scripts.zotero_client.Path.home', return_value=self.fake_home)
        home.start()
        self.addCleanup(home.stop)

    def client(self):
        with patch.object(Zotero, '_raw', fake_api):
            return Zotero(base='http://127.0.0.1:23119')

    def test_default_runtime_is_created_in_working_directory_on_every_platform(self):
        for platform in ('darwin', 'win32', 'linux'):
            with self.subTest(platform=platform), working_directory(self.project), patch('paper_reader.scripts.zotero_client.sys.platform', platform):
                runtime = config_dir()
                self.assertEqual(runtime, self.project / '.runtime/zotero_agent')
                self.assertTrue(runtime.is_dir())
                self.assertEqual(key_path(), runtime / 'local_api_key.json')

    def test_authorization_survives_another_client_without_another_request(self):
        with working_directory(self.project):
            first = self.client()
            saved = first.save_key('fake-local-key', True)
            second = self.client()
            self.assertEqual(saved, self.project / '.runtime/zotero_agent/local_api_key.json')
            self.assertEqual(second._key, 'fake-local-key')
            self.assertTrue(second._remember)

    def test_other_workspace_does_not_reuse_credentials_or_index(self):
        other = self.root / 'another_reader'
        other.mkdir()
        with working_directory(self.project):
            self.client().save_key('fake-local-key', True)
            index = LiteratureIndex('test-server')
            try:
                first_index_path = index.path
                with index.db:
                    index.db.execute('INSERT INTO meta VALUES (?, ?)', ('library', 'users/0'))
            finally:
                index.close()
        with working_directory(other):
            self.assertIsNone(self.client()._key)
            self.assertEqual(index_status(), [])
            self.assertNotEqual(index_path('test-server', 'users/0'), first_index_path)

    def test_legacy_user_data_is_neither_loaded_nor_changed(self):
        legacy_home = self.root / 'legacy-user'
        legacy = legacy_home / 'Library/Application Support/zotero-agent'
        legacy.mkdir(parents=True)
        old_key = legacy / 'local_api_key.json'
        original = json.dumps({'format': 2, 'servers': {'test-server': {'key': 'legacy-fake-key', 'remember': True}}})
        old_key.write_text(original)
        with working_directory(self.project), patch('paper_reader.scripts.zotero_client.Path.home', return_value=legacy_home):
            self.assertIsNone(self.client()._key)
            self.assertEqual(config_dir(), self.project / '.runtime/zotero_agent')
        self.assertEqual(old_key.read_text(), original)

    def test_explicit_absolute_override_can_share_runtime_between_workspaces(self):
        shared = self.root / 'shared-runtime'
        other = self.root / 'another_reader'
        other.mkdir()
        with patch.dict(os.environ, {'ZOTERO_AGENT_HOME': str(shared)}):
            with working_directory(self.project):
                self.client().save_key('fake-shared-key', True)
                self.assertEqual(config_dir(), shared)
            with working_directory(other):
                self.assertEqual(self.client()._key, 'fake-shared-key')
        self.assertFalse((self.project / '.runtime').exists())
        self.assertFalse((other / '.runtime').exists())

    def test_relative_override_resolves_from_working_directory(self):
        with working_directory(self.project), patch.dict(os.environ, {'ZOTERO_AGENT_HOME': 'local-runtime'}):
            self.assertEqual(config_dir(), self.project / 'local-runtime')
            self.assertTrue((self.project / 'local-runtime').is_dir())
            self.assertFalse((self.project / '.runtime').exists())

    def test_index_is_persistent_and_partitioned_inside_runtime(self):
        with working_directory(self.project):
            index = LiteratureIndex('test-server')
            try:
                self.assertEqual(index.path.parent, self.project / '.runtime/zotero_agent/indexes')
                row = index._row({'key': 'NOTE0001', 'version': 1, 'data': {'itemType': 'note', 'note': '<p>归一化权重</p>'}})
                with index.db:
                    index.db.execute('INSERT INTO objects VALUES (?,?,?,?,?,?,?,?)', row)
                saved_path = index.path
            finally:
                index.close()
            reopened = LiteratureIndex('test-server', create=False)
            try:
                self.assertEqual(reopened.recall('归一化')['matches'][0]['matched_key'], 'NOTE0001')
            finally:
                reopened.close()
            self.assertEqual(index_path('test-server', 'users/0'), saved_path)
            self.assertNotEqual(index_path('test-server', 'groups/1'), saved_path)

    @unittest.skipUnless(shutil.which('git'), 'git is needed to verify runtime exclusion')
    def test_runtime_assets_are_ignored_in_a_fresh_clone_without_root_gitignore(self):
        subprocess.run(['git', 'init', '--quiet', str(self.project)], check=True, capture_output=True)
        with working_directory(self.project):
            self.client().save_key('fake-local-key', True)
            index = LiteratureIndex('test-server')
            index.close()
            self.assertTrue((self.project / '.runtime/zotero_agent/local_api_key.json').is_file())
            wiki = self.project / '.runtime/llm_wiki'
            wiki.mkdir()
            (wiki / 'concept.md').write_text('Fake teaching record')
        output = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=self.project,
                                check=True, capture_output=True, text=True).stdout
        self.assertEqual(output, '')

    def test_existing_runtime_ignore_rules_are_preserved(self):
        runtime = self.project / '.runtime/zotero_agent'
        runtime.mkdir(parents=True)
        ignore = runtime / '.gitignore'
        ignore.write_text('*\n# User comment\n')
        with working_directory(self.project):
            config_dir()
        self.assertEqual(ignore.read_text(), '*\n# User comment\n')

    @unittest.skipIf(os.name == 'nt', 'POSIX file permissions')
    def test_new_runtime_and_credentials_have_private_permissions(self):
        with working_directory(self.project):
            saved = self.client().save_key('fake-local-key', True)
            self.assertEqual(stat.S_IMODE((self.project / '.runtime').stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(saved.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)

    def test_index_status_cli_reuses_working_directory_across_processes(self):
        wrapper = ('import runpy, sys; from pathlib import Path; from unittest.mock import patch; '
                   'fake_home = Path(sys.argv.pop(1)); sys.argv = ["paper", *sys.argv[1:]]; '
                   ''
                   'patcher = patch("pathlib.Path.home", return_value=fake_home); patcher.start(); '
                   'runpy.run_module("paper_reader", run_name="__main__")')
        command = [sys.executable, '-B', '-c', wrapper, str(self.fake_home),
                   'zotero', 'index', 'status']
        for _ in range(2):
            result = subprocess.run(command, cwd=self.project, env=os.environ.copy(), check=True,
                                    capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout), [])
            self.assertTrue((self.project / '.runtime/zotero_agent').is_dir())


if __name__ == '__main__':
    unittest.main()
