#!/usr/bin/env python3
"""Exercise the workflow's version step against offline temporary remotes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import textwrap
import unittest

REPO = Path(__file__).resolve().parent.parent


class ReleaseVersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.clone = self.root / 'clone'
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
                        GIT_AUTHOR_NAME='Test', GIT_COMMITTER_NAME='Test',
                        GIT_AUTHOR_EMAIL='test@example.invalid',
                        GIT_COMMITTER_EMAIL='test@example.invalid',
                        GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='0')
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                    'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                    'GIT_CONFIG', 'GIT_CONFIG_PARAMETERS'):
            self.env.pop(key, None)
        self.git('init', '--bare', '--initial-branch=main', str(self.remote), cwd=self.root)
        self.git('clone', str(self.remote), str(self.clone), cwd=self.root)
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', '/dev/null')
        manifest = self.clone / '.codex-plugin/plugin.json'
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({'version': '2.5.1'}) + '\n')
        helper = REPO / 'scripts/release-version.sh'
        if helper.exists():
            (self.clone / 'scripts').mkdir()
            shutil.copy2(helper, self.clone / 'scripts/release-version.sh')
        self.git('add', '.')
        self.git('commit', '-m', 'baseline')
        self.git('push', 'origin', 'main')
        self.merge = self.git('rev-parse', 'HEAD').stdout.strip()
        workflow = (REPO / '.github/workflows/auto-release.yml').read_text()
        block = workflow.split('      - name: Bump version, commit and tag\n', 1)[1]
        block = block.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
        self.step = textwrap.dedent(block)

    def git(self, *args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd or self.clone, env=self.env,
                              capture_output=True, text=True, check=True)

    def release(self, merge=None, bump='patch', cwd=None):
        output = self.root / 'output'
        output.write_text('')
        env = dict(self.env, BUMP=bump, MERGE_SHA=merge or self.merge,
                   GITHUB_OUTPUT=str(output))
        result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', self.step],
                                cwd=cwd or self.clone, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return output.read_text().strip()

    def intercept_push(self, action):
        real_git = shutil.which('git')
        stub_dir = self.root / 'bin'
        stub_dir.mkdir()
        marker = self.root / 'intercepted'
        wrapper = stub_dir / 'git'
        wrapper.write_text('#!/usr/bin/env python3\n' + textwrap.dedent(f"""\
            import pathlib
            import subprocess
            import sys
            args = sys.argv[1:]
            marker = pathlib.Path({str(marker)!r})
            if args[:2] == ['push', '--atomic'] and not marker.exists():
                marker.touch()
        """) + textwrap.indent(action, '    ') +
            f"\nsys.exit(subprocess.run([{real_git!r}, *args]).returncode)\n")
        wrapper.chmod(0o755)
        self.env['PATH'] = str(stub_dir) + os.pathsep + self.env['PATH']
        return real_git

    def test_lost_push_response_reuses_remote_release(self):
        real_git = shutil.which('git')
        self.intercept_push(f"subprocess.run([{real_git!r}, *args], check=True)\nsys.exit(1)\n")
        self.assertEqual(self.release(), 'version=2.5.2')
        self.assertEqual(self.git('tag').stdout.strip(), 'v2.5.2')
        self.assertEqual(self.git('log', '--format=%s', '--grep=^release:').stdout.splitlines(),
                         ['release: v2.5.2'])

    def test_competing_release_retries_from_new_remote_tip(self):
        competitor = self.root / 'competitor'
        self.git('clone', str(self.remote), str(competitor), cwd=self.root)
        manifest = competitor / '.codex-plugin/plugin.json'
        manifest.write_text(json.dumps({'version': '2.5.2'}) + '\n')
        self.git('add', '.', cwd=competitor)
        self.git('-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                 'commit', '-m', 'release: v2.5.2', cwd=competitor)
        self.git('-c', 'tag.gpgsign=false', 'tag', 'v2.5.2', cwd=competitor)
        real_git = shutil.which('git')
        self.intercept_push(
            f"subprocess.run([{real_git!r}, '-C', {str(competitor)!r}, 'push', "
            "'--atomic', 'origin', 'main', 'refs/tags/v2.5.2'], check=True)\n")
        self.assertEqual(self.release(), 'version=2.5.3')
        self.assertEqual(self.git('tag').stdout.split(), ['v2.5.2', 'v2.5.3'])
        self.assertEqual(self.release(), 'version=2.5.3')

    def test_same_event_reuses_version_and_tag(self):
        first = self.release()
        head = self.git('rev-parse', 'HEAD').stdout
        self.assertEqual(first, 'version=2.5.2')
        self.assertEqual(self.release(), first)
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout, head)
        self.assertEqual(self.git('tag').stdout.strip(), 'v2.5.2')

    def test_retry_in_fresh_checkout_after_later_release(self):
        first = self.release()
        (self.clone / 'next.txt').write_text('another PR\n')
        self.git('add', '.')
        self.git('commit', '-m', 'next merged PR')
        later = self.git('rev-parse', 'HEAD').stdout.strip()
        self.git('push', 'origin', 'main')
        self.assertEqual(self.release(later, 'minor'), 'version=2.6.0')
        retry = self.root / 'retry'
        self.git('clone', '--depth=1', self.remote.as_uri(), str(retry), cwd=self.root)
        # Mirrors the workflow checkout requirement needed to find old markers.
        self.git('fetch', '--unshallow', 'origin', cwd=retry)
        self.assertEqual(self.release(cwd=retry), first)
        self.assertEqual(self.git('tag').stdout.split(), ['v2.5.2', 'v2.6.0'])


if __name__ == '__main__':
    unittest.main()
