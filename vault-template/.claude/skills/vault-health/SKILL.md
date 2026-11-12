---
name: vault-health
description: "Run the read-only vault health checker plus judgment checks (stale, contradictory or duplicate notes) and write a dated report with ranked fixes. Use monthly, after batch edits, or when the user types /vault-health."
---

# vault-health

This file only points to the canonical instructions, which the user edits in Obsidian:

`00 Home/Agent/Skills/Skill - Vault Health.md` (relative to the vault root)

1. Read that note in full and follow it exactly.
2. Follow the vault rules in `AGENTS.md` (permissions, the `ai-assisted` tag, citations).
3. After the run, append one dated line to the note's `## Retro log`.

The checker script sits next to this file: `scripts/vault_health.py` (read-only, standard library). Run it with the vault path as the only argument; add `--json` for machine-readable output.

If the note is missing, stop and tell the user instead of improvising.
