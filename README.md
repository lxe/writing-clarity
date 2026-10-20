# Writing clarity

An agent skill for prose the reader can follow on the first reading. It steers sentence structure, reference, logical connections, imagery, and emphasis while preserving voice and factual meaning.

The [full steering prompt](skills/writing-clarity/SKILL.md) includes contextual before/after examples and examples of fragments, idioms, quotations, and literary choices worth preserving. It develops the [original clarity guide](https://gist.github.com/lxe/4cd2ca0fd3b714b25f138227c8c650d3).

## Install the skill

Requires Node.js 22.20+ for the current Vercel Skills CLI:

```sh
npx skills add lxe/writing-clarity --skill writing-clarity -a codex -a claude-code -g
```

Start a new session. Invoke `$writing-clarity` in Codex or `/writing-clarity` in Claude Code, or let the agent select the skill when drafting prose. Global installation makes it available across projects; it does not force activation on every turn.

Vercel Skills installs the skill and its bundled script. It does not register this package's global lifecycle hooks. Use the optional installer below for automatic context loading.

## Automatic loading with hooks

Requires Python 3.10+ and an agent release that supports `SessionStart`, `SubagentStart`, `UserPromptSubmit`, and JSON `additionalContext` output. Tested with Codex CLI 0.145.0 (hook configuration and trust review) and Claude Code 2.1.283 (live session-start and per-prompt context delivery). The local Codex model request was rejected by its backend, so Codex model receipt has not been verified. See the testing limits below.

From a clone of this repository:

```sh
git clone https://github.com/lxe/writing-clarity.git
cd writing-clarity
python3 skills/writing-clarity/scripts/clarity.py install --agent both
```

Alternatively, run the bundled script from your installed skill directory. The installer records that script's absolute location, so keep the clone or installed skill in place. Re-run installation if you move it or change Python installations. The script reads the current local `SKILL.md`; it makes no network requests.

The installer adds three hooks to `~/.codex/hooks.json` and/or `~/.claude/settings.json`:

- `SessionStart`: the full guide and examples, including startup, resume, clear, fork, and recovery after compaction.
- `SubagentStart`: the full guide and examples for a newly started subagent.
- `UserPromptSubmit`: a short reminder and the path to the full guide.

For maximum repetition, inject the full guide on every submitted prompt:

```sh
python3 skills/writing-clarity/scripts/clarity.py install --agent both --full-every-turn
```

Pass `--no-full-every-turn` with `enable` to return to brief reminders. This uses more context. A full guide is currently about 9,000 characters, below Claude Code's 10,000-character inline-context limit. The installer rejects an oversized guide rather than silently relying on a truncated preview.

**Codex requires hook review.** After installation, start Codex and open `/hooks` to review and trust the writing-clarity entries. New or changed definitions may require renewed review. The installer does not alter trust records, disable safeguards, or enable hooks if your configuration explicitly disables them. If a host app uses a different configuration directory/runtime, install there and verify its hook support separately.

Claude Code loads the user hooks from `~/.claude/settings.json`; start a new session after installation. Managed policy, restricted/safe modes, or disabled hooks can prevent execution. These hooks add writing preference context. They do not replace the system prompt, rewrite streamed responses, or guarantee compliance with every style instruction.

Existing settings and unrelated hooks are preserved. Changed files receive timestamped backups; writes use atomic replacement. Invalid JSON causes installation to stop before modifying either agent's configuration. No prompts or transcripts are stored by the hook.

## Enable, disable, inspect, remove

Use `--agent codex`, `--agent claude-code`, or `--agent both`:

```sh
python3 skills/writing-clarity/scripts/clarity.py status --agent both
python3 skills/writing-clarity/scripts/clarity.py disable --agent both
python3 skills/writing-clarity/scripts/clarity.py enable --agent both
python3 skills/writing-clarity/scripts/clarity.py uninstall --agent both
```

`disable` leaves the hooks registered and emits a withdrawal of this package's optional preference on the next prompt. `enable` restores hook registration and the saved injection mode. `uninstall` removes only this package's tagged handlers. The skill itself remains available until you remove it separately:

```sh
npx skills remove writing-clarity -g -a codex -a claude-code
```

Uninstall hooks **before** removing or moving their script. Already injected instructions remain in conversation history. A new session gives a clean unload; disabling does not erase old context. Turning the hooks off does not stop an agent explicitly invoking the installed skill.

For testing without touching your real user configuration, all commands accept `--home /path/to/temporary/home`.

## Verify behavior

```sh
python3 -m unittest discover -s tests -v
```

The tests execute the configured commands for both agents, check complete context delivery for session/compaction sources, test short and full per-turn modes, toggle state, preserve unrelated settings, verify idempotence and removal, and check malformed input/configuration handling. They prove the script's output contract and configuration behavior; they do not prove that an agent host executed it or that a model followed the guide.

To verify a live installation, inspect the agent's hook diagnostics/debug logs and confirm the writing-clarity handler ran. Then use the cases in [evals/cases.jsonl](evals/cases.jsonl) to compare real outputs with hooks enabled and disabled. Prefer blind comparison. Evaluate each case for identifiable references, explicit necessary relationships, natural rhythm, preserved voice, and factual fidelity. Reject edits that invent missing information or damage valid short replies and quotations. Repeat after agent/model updates and after compaction. The cases are prompts and criteria, not claimed evaluation results.

Recorded checks and limits are in [evals/verification.md](evals/verification.md).

## References

- [Vercel Skills: creation and discovery](https://github.com/vercel-labs/skills/blob/main/docs/creating-skills.md)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks)

## License

MIT.
