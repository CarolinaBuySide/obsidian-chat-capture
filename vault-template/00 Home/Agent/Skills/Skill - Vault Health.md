---
type: agent-skill
name: vault-health
command: /vault-health
summary: "Runs the read-only vault_health.py checker, adds judgment checks for stale and contradictory notes, and writes a dated report with fixes to AI Drafts."
version: 1.0
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Vault Health

> [!abstract] One job
> Find what makes the vault harder for the user and their agents to use, and propose fixes ranked by value.

## When to run
Monthly, before a big reorganization, after a batch edit, or when the user types `/vault-health`.

## Steps
1. **Run the checker** (read-only, standard library Python):
   `python3 "{{VAULT_PATH}}/.claude/skills/vault-health/scripts/vault_health.py" "{{VAULT_PATH}}"`
   It reports broken links, unresolved daily links, isolated notes, notes with no backlinks, notes not connected to a map, missing frontmatter and summaries, long notes without summaries, stale inbox items, duplicate lines in maps, the `ai-assisted` review queue, leftover example notes, possible secrets (line numbers only) and unlinked course files. Add `--json` for machine-readable output.
2. **Judgment checks** the script can't do:
   - Contradictions: a project marked active whose `due` date has passed; course MOCs still active after the course ended; [[AI Context]] or [[Top of Mind]] disagreeing with project notes.
   - Staleness: Canvas syncs older than 7 days (when Canvas is connected); `updated` dates older than 14 days on hubs.
   - Duplicates: two notes on the same source or idea.
3. **Write the report** to `01 Fleeting/AI Drafts/YYYY-MM-DD Vault Health Report.md`: the counts table, then fixes in three groups:
   - **Safe fixes** (agents may apply): add a missing `summary`, add a missing map link by appending a pointer line, remove an exact duplicate line in a map.
   - **Needs the user:** status changes, archiving finished courses, deleting example notes, anything in `03 Permanent`.
   - **Security:** possible secrets with file and line, never the value.
4. Apply safe fixes only if the user asked for fixes in this run; commit a checkpoint first.

## Rules
- The checker never modifies the vault. Don't edit the report's numbers by hand.
- Unresolved links to future daily notes are expected; don't report them as broken.

## Test
Pass if the report exists with today's date, its counts match the script's output, and no note changed unless the user asked for fixes.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
