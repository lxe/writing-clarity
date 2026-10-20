# Verification on 2026-10-20

- Skill frontmatter passed the Codex skill validator.
- Vercel Skills 1.7.4 discovered and installed the skill for Codex and Claude Code.
- Eight Python integration tests passed. They execute the registered hook command against isolated user homes, including configuration preservation, invalid configuration handling, idempotence, enable/disable, full/brief prompt modes, and complete startup context under the `compact` source.
- Claude Code 2.1.283 debug output confirmed 8,377 characters of guide context from `SessionStart` and a 598-character `UserPromptSubmit` reminder. A tool-disabled model request identified contextual examples from the guide without reading the skill file.
- A separate Claude request connected the failed-job explanation, retained uncertainty about who would review, kept the short reply “Twice. She didn't answer.”, and preserved the requested exact quotation. This is a small smoke test, including examples already present in the guide, without a disabled baseline. It does not establish general writing-quality improvement.
- Codex CLI 0.145.0 accepted the hook configuration. The three authored hook definitions were reviewed and trusted through its normal interactive hook-review flow. A noninteractive model delivery test failed because the backend rejected the configured model; Codex model receipt has not been established.

Actual compaction and subagent delivery inside either host have not been exercised. The script's output for those event inputs is covered by tests. No model quality guarantee or reliable AI-authorship detector is claimed.
