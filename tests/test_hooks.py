import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/writing-clarity/scripts/clarity.py'


class HookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='clarity test ')
        self.home = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def run_cli(self, action, *extra, check=True):
        return subprocess.run([sys.executable, str(SCRIPT), action, '--home', str(self.home), *extra],
                              text=True, capture_output=True, check=check)

    def config(self, agent):
        return self.home / ('.codex/hooks.json' if agent == 'codex' else '.claude/settings.json')

    def invoke(self, agent, event, **payload):
        data = json.loads(self.config(agent).read_text())
        handler = data['hooks'][event][-1]['hooks'][0]
        proc = subprocess.run(shlex.split(handler['command']),
                              input=json.dumps(dict(hook_event_name=event, **payload)),
                              text=True, capture_output=True, check=True)
        return json.loads(proc.stdout)['hookSpecificOutput']

    def test_both_agents_deliver_full_guide_and_reminders(self):
        self.run_cli('install')
        for agent in ('codex', 'claude-code'):
            for source in ('startup', 'resume', 'clear', 'compact', 'fork'):
                out = self.invoke(agent, 'SessionStart', source=source)
                self.assertEqual(out['hookEventName'], 'SessionStart')
                self.assertIn('Three cancellations', out['additionalContext'])
                self.assertIn('Twice. No answer.', out['additionalContext'])
                self.assertLess(len(out['additionalContext']), 10000)
            self.assertIn('Further examples', self.invoke(agent, 'SubagentStart')['additionalContext'])
            self.assertLess(len(self.invoke(agent, 'UserPromptSubmit')['additionalContext']), 1500)

    def test_preserve_settings_idempotent_install_and_remove(self):
        original = {'permissions': {'allow': ['Read']}, 'model': 'preserve-me', 'hooks': {
            'SessionStart': [{'matcher': 'startup', 'hooks': [{'type': 'command', 'command': 'echo existing'}]}],
            'Stop': [{'hooks': [{'type': 'command', 'command': 'echo stopping'}]}]}}
        path = self.config('claude-code')
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(original))
        self.run_cli('install')
        first = path.read_text()
        self.run_cli('install')
        self.assertEqual(first, path.read_text())
        self.run_cli('uninstall')
        self.assertEqual(original, json.loads(path.read_text()))
        self.assertTrue(list(path.parent.glob('*.writing-clarity-backup-*')))

    def test_toggle_takes_effect_on_next_prompt(self):
        self.run_cli('install')
        self.run_cli('disable', '--agent', 'claude-code')
        self.assertIn('now disabled', self.invoke('claude-code', 'UserPromptSubmit')['additionalContext'])
        self.assertNotIn('now disabled', self.invoke('codex', 'UserPromptSubmit')['additionalContext'])
        self.run_cli('enable', '--agent', 'claude-code')
        self.assertIn('Silently check', self.invoke('claude-code', 'UserPromptSubmit')['additionalContext'])

    def test_full_every_turn(self):
        self.run_cli('install', '--full-every-turn')
        for agent in ('codex', 'claude-code'):
            self.assertIn('Further examples', self.invoke(agent, 'UserPromptSubmit')['additionalContext'])

    def test_full_mode_can_return_to_brief(self):
        self.run_cli('install', '--full-every-turn')
        self.run_cli('enable', '--no-full-every-turn')
        self.assertLess(len(self.invoke('codex', 'UserPromptSubmit')['additionalContext']), 1500)

    def test_invalid_second_config_does_not_modify_first(self):
        bad = self.config('claude-code')
        bad.parent.mkdir(parents=True)
        bad.write_text('{invalid json')
        result = self.run_cli('install', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.config('codex').exists())
        self.assertEqual(bad.read_text(), '{invalid json')

    def test_malformed_event_config_is_preserved(self):
        path = self.config('codex')
        path.parent.mkdir(parents=True)
        path.write_text('{"hooks":{"SessionStart":"bad"}}')
        result = self.run_cli('install', check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), '{"hooks":{"SessionStart":"bad"}}')

    def test_bad_hook_input_never_blocks_or_echoes_prompt(self):
        self.run_cli('install')
        proc = subprocess.run([sys.executable, str(SCRIPT), 'emit', '--agent', 'codex', '--home', str(self.home)],
                              input='private secret invalid json', text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, '')
        self.assertNotIn('private secret', proc.stderr)


if __name__ == '__main__':
    unittest.main()
