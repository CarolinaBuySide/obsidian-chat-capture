---
name: obsidian-vault-builder
description: "Build a new Obsidian vault from the Obsidian AI Vault blueprint (taken from a real student vault): numbered folders, a Home-centered starburst graph, weekly and to-do calendars, color-coded courses, an AGENTS.md operating layer, and AI chats that save into the vault. Use for 'build me an Obsidian vault', 'set up Obsidian like this', 'add a course to my vault'. Not for saving one chat (use obsidian-chat-capture)."
license: MIT
compatibility: "Needs Python 3.9+ and a copy of the blueprint repo (scripts/, vault-template/, blueprint/). Steps 4 and 5 need Obsidian 1.12+ on the user's computer."
metadata:
  author: Marc Rainone
  version: "3.0.0"
---

# Obsidian Vault Builder

The full procedure is the repo's root `AGENTS.md`; read it and follow it. In short:

1. **Get the repo.** If `scripts/build_vault.py` isn't two folders above this file, clone the repo this skill came from.
2. **Interview** with `blueprint/interview.md`. Write `answers.json` like `blueprint/answers.example.json` and confirm a summary with the user.
3. **Build:** `python3 scripts/build_vault.py --answers answers.json --dest "<new folder>"`. It refuses non-empty folders.
4. **Plugins:** `python3 scripts/install_plugins.py "<vault>" --obsidian-skills`.
5. **Turn on:** `python3 scripts/obsidian_setup.py register "<vault>"` with Obsidian quit, open Obsidian, then `enable` and `check`. `check` must print `PASS`.
6. **Chat capture:** `python3 scripts/setup_chat_capture.py test "<vault>"`, then `connect --app <app>` for each app, `watcher` on macOS, and give the user the line from `instructions`.
7. **Canvas (students):** the user runs `canvas_api.py login --host <school>.instructure.com` in their own terminal; then `sync.py setup` and a first sync per the vault's `Skill - Canvas Sync` note. Never ask for the token in chat.
8. **Verify:** `python3 scripts/verify_vault.py "<vault>"` must print `PASS`.
9. **Report** the path, what passed, what you could not run, and what to open first (Home).

Add a course to a blueprint vault with `scripts/new_course.py` (close Obsidian first). Retire one with the steps in `blueprint/personalize.md`.

Never write into an existing vault unless the user asks. If they do, back up first, add only missing files, and merge settings without overwriting their values. Never print or ask for the Local REST API key.
