#!/usr/bin/env python3
"""Reversible context hooks for Codex and Claude Code. Python standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import time

SKILL = Path(__file__).resolve().parents[1] / 'SKILL.md'
MARKER = '--writing-clarity-hook'
EVENTS = ('SessionStart', 'SubagentStart', 'UserPromptSubmit')
LABELS = {
    'SessionStart': 'Writing clarity: load full guide',
    'SubagentStart': 'Writing clarity: guide subagents',
    'UserPromptSubmit': 'Writing clarity: reinforce each prompt',
}
REMINDER = (
    'The user prefers the writing-clarity guide supplied at session start. '
    'For prose, keep subjects and references identifiable; explain necessary logical '
    'connections; keep reasons and qualifications with their claims; state the point '
    'directly; use concrete actions and natural sentence boundaries. Avoid repeated '
    'fragment/reveal cadence and images or labels that replace explanations. '
    'Preserve factual meaning, quotations, requested formats, voice, and useful brevity. '
    'Silently check the response before sending it. The full guide with examples is at '
)


def guide():
    text = SKILL.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise ValueError('SKILL.md is missing frontmatter')
    return text.split('---\n', 2)[2].strip()


def paths(home, agent):
    config = home / ('.codex/hooks.json' if agent == 'codex' else '.claude/settings.json')
    state = home / '.config/writing-clarity' / (agent + '.json')
    return config, state


def load(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(str(path) + ' must contain a JSON object')
    return data


def write(path, data):
    """Atomic replacement; retain existing permissions and a recoverable backup."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()
    if path.exists() and path.read_bytes() == content:
        return
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    if path.exists():
        backup = path.with_name(path.name + '.writing-clarity-backup-' + str(time.time_ns()))
        backup.write_bytes(path.read_bytes())
        backup.chmod(mode)
    fd, tmp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(content)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def owned(handler):
    if not isinstance(handler, dict):
        raise ValueError('Hook handler must be an object')
    command = handler.get('command', '')
    if not isinstance(command, str):
        return False
    try:
        return MARKER in shlex.split(command)
    except ValueError:
        return False


def without_ours(config):
    """Remove only tagged handlers, preserving other handlers and group metadata."""
    result = dict(config)
    hooks = result.get('hooks', {})
    if not isinstance(hooks, dict):
        raise ValueError('hooks must be an object; configuration left unchanged')
    clean = {}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError('Hook event groups must be arrays')
        keep = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get('hooks'), list):
                raise ValueError('Invalid hook group; configuration left unchanged')
            handlers = [h for h in group['hooks'] if not owned(h)]
            if handlers or not group['hooks']:
                keep.append(dict(group, hooks=handlers))
        if keep or not groups:
            clean[event] = keep
    if clean:
        result['hooks'] = clean
    else:
        result.pop('hooks', None)
    return result


def install_config(config, home, agent):
    result = without_ours(config)
    command = shlex.join([
        sys.executable, str(Path(__file__).resolve()), 'emit', '--agent', agent,
        '--home', str(home), MARKER,
    ])
    hooks = result.setdefault('hooks', {})
    for event in EVENTS:
        handler = {'type': 'command', 'command': command, 'timeout': 5}
        if agent == 'codex':
            handler['additionalContextLimit'] = 5000
            handler['statusMessage'] = LABELS[event]
        hooks.setdefault(event, []).append({'hooks': [handler]})
    return result


def emit(args):
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('Hook input must be a JSON object')
        event = payload.get('hook_event_name')
        if event not in EVENTS:
            return
        _, state_path = paths(args.home, args.agent)
        state = load(state_path)
        if not state:
            return
        if not state.get('enabled', False):
            context = (
                'The writing-clarity package is now disabled. Its optional style '
                'guidance from earlier hook messages no longer applies. '
                'Continue following the current request and other applicable instructions.'
            )
        elif event == 'UserPromptSubmit' and not state.get('full_every_turn', False):
            context = REMINDER + str(SKILL) + '.'
        else:
            context = 'User writing preference: writing-clarity\n\n' + guide()
        # Claude passes >10,000-character reminders through a preview file instead.
        if len(context) > 9900:
            raise ValueError('Guide exceeds inline hook limit; shorten it before enabling')
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': event, 'additionalContext': context,
        }}, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        # Style preferences must never block the user's work or leak prompt content.
        print('writing-clarity: ' + str(exc), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'enable', 'disable', 'status', 'uninstall', 'emit'))
    parser.add_argument('--agent', choices=('codex', 'claude-code', 'both'), default='both')
    parser.add_argument('--home', type=Path, default=Path.home(), help='Alternate user home for isolated testing')
    parser.add_argument('--full-every-turn', action=argparse.BooleanOptionalAction, default=None, help='Inject the full guide at every prompt; --no-full-every-turn restores brief reminders')
    parser.add_argument(MARKER, action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.home = args.home.expanduser().resolve()
    if args.action == 'emit':
        if args.agent == 'both':
            parser.error('emit requires one agent')
        emit(args)
        return
    agents = ('codex', 'claude-code') if args.agent == 'both' else (args.agent,)
    # Validate every target before writing any target.
    pending = []
    for agent in agents:
        config_path, state_path = paths(args.home, agent)
        config, state = load(config_path), load(state_path)
        without_ours(config)
        if args.action == 'status':
            count = sum(owned(h) for gs in config.get('hooks', {}).values() for g in gs for h in g['hooks'])
            print(json.dumps({'agent': agent, 'enabled': state.get('enabled', False),
                              'registered_handlers': count, 'config': str(config_path),
                              'full_every_turn': state.get('full_every_turn', False),
                              'guide_sha256': hashlib.sha256(guide().encode()).hexdigest()}))
            continue
        if args.action in ('install', 'enable'):
            if len(guide()) + 100 > 9900:
                raise ValueError('Guide exceeds inline hook limit')
            new_config = install_config(config, args.home, agent)
            new_state = {'enabled': True, 'full_every_turn': state.get('full_every_turn', False) if args.full_every_turn is None else args.full_every_turn}
        elif args.action == 'disable':
            new_config = config
            new_state = dict(state, enabled=False)
        else:
            new_config = without_ours(config)
            new_state = dict(state, enabled=False)
        pending.append((agent, config_path, new_config, state_path, new_state))
    for agent, cp, conf, sp, state in pending:
        write(cp, conf)
        write(sp, state)
        print(agent + ': ' + args.action + ' complete')
    if args.action in ('install', 'enable'):
        print('Start a new agent session. Codex requires hook review/trust via /hooks; no trust settings were changed.')
    if args.action in ('disable', 'uninstall'):
        print('Previously injected text remains in existing history. Disable sends a reminder on the next prompt; use a new session for a clean unload.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        print('writing-clarity: ' + str(exc), file=sys.stderr)
        sys.exit(1)
