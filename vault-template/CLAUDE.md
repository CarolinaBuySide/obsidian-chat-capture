---
type: agent-policy
summary: "Claude Code entry point for the vault: imports AGENTS.md and adds Claude-specific notes on slash commands, permissions and chat capture."
updated: 2026-10-12
tags:
  - agent
---
# CLAUDE.md

@AGENTS.md

## Claude Code specifics
- Start from the vault root so the project skills and settings load: `cd ~/Documents/"Obsidian Vault" && claude`.
- Slash commands: `/todays-focus`, `/weekly-review`, `/process-notes`, `/ingest`, `/vault-health`, `/write-like-me`, `/calendar-update`. Each file in `.claude/skills/<name>/SKILL.md` only points to the canonical note in `00 Home/Agent/Skills/`. Improve the note, not the pointer.
- Obsidian syntax skills from kepano/obsidian-skills (MIT): `obsidian-markdown`, `obsidian-bases`, `json-canvas`.
- `.claude/settings.json` asks before edits to protected areas (permanent notes, templates, settings, archive, course files, the profile and these manuals) and blocks the Local REST API key folder.
- Chat capture: the personal `obsidian-chat-capture` skill in `~/.claude/skills` saves substantive chats to `11 AI Chats`.
- Git: you can run git directly. Commit a checkpoint before any batch edit and again after it.
