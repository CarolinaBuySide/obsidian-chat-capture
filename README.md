# Obsidian AI Vault

A blueprint your AI can use to build you an organized Obsidian vault. It's taken from a real student vault that's used every day: the template holds that vault's actual calendar code, graph plugin, settings, templates and AI operating manual, with the personal content removed. You get numbered folders, a circular graph centered on Home with one colored starburst per area and per course, weekly and monthly calendars, a standard folder for every course, and rules that tell every AI app how to read and write your notes safely.

It also includes [`obsidian-chat-capture`](skills/obsidian-chat-capture/), a skill that saves the useful parts of AI chats into the vault.

## Use it

Give this repo to an AI that can run code on your computer (Claude Code, Codex, Cursor, Perplexity Computer and others) and say:

> Read AGENTS.md in this repo and build me an Obsidian vault.

The AI asks you a few questions (your life areas, which AI apps you use and, if you're a student, your courses). Then it builds the vault, installs and turns on the plugins, connects your AI apps so chats save into the vault, and runs three checks before handing it over. You need [Obsidian](https://obsidian.md/download) 1.12 or newer and Python 3.9 or newer.

To do it yourself:

```bash
cp blueprint/answers.example.json my-answers.json          # edit it
V="$HOME/Documents/Obsidian Vault"
python3 scripts/build_vault.py --answers my-answers.json --dest "$V"
python3 scripts/install_plugins.py "$V" --obsidian-skills
python3 scripts/obsidian_setup.py register "$V"            # with Obsidian quit; then open Obsidian
python3 scripts/obsidian_setup.py enable "$V"
python3 scripts/obsidian_setup.py check "$V"               # should print PASS
python3 scripts/setup_chat_capture.py test "$V"            # should print PASS
python3 scripts/setup_chat_capture.py connect "$V" --app claude-code
python3 scripts/verify_vault.py "$V"                       # should print PASS
```

The scripts use only Python's standard library. If you'd rather click, skip the two `obsidian_setup.py` lines after `register`, open the folder in Obsidian, and follow `00 Home/Plugin Setup Checklist`.

## What you get

| | |
|---|---|
| **Folders** | `00 Home` · `01 Fleeting` · `02 Literature` · `03 Permanent` · `04 Maps` · `05 Projects` · `06 Daily` · `07 Weekly` · `08 Archive` · `09 Templates` · `10 Attachments` · `11 AI Chats` · `12 School` · `13 Calendar` |
| **Home** | Dashboard with every area, active courses, deadlines for the next 14 days, inbox, projects and recent AI chats |
| **Weekly Calendar** | A time grid of classes (repeating weekly, with breaks skipped), calls, meetings and exams, with an Add event form |
| **To-Do Calendar** | A month grid of every dated task (assignments, exams, readings, to-dos), with filters and check-off in place |
| **Courses** | Each course gets a course map, a folder with eight numbered subfolders, a Materials note linking every file, a class note and a prep note, all in one color. Finished courses move to Past Courses and turn gray |
| **Graph** | The bundled Graph Groups plugin pins Home in the center and lays out each area and course as its own colored starburst |
| **AI layer** | `AGENTS.md` (read order, permissions table, how AI work is marked, conventions), AI Context, USER, Top of Mind, an append-only Agent Memory, and seven skills (Todays Focus, Weekly Review, Process Notes, Ingest, Vault Health, Write Like Me, Calendar Update), also available as Claude Code slash commands |
| **Calendar tool** | `add_event.py`, so any AI with a shell can add, move, cancel or list events and log each change |
| **Safety net** | Agents append instead of overwriting, anything they write is tagged `ai-assisted` until you review it, and Obsidian Git takes local snapshots every 30 minutes |

The full design is in [`blueprint/VAULT-SPEC.md`](blueprint/VAULT-SPEC.md).

## Repo layout

```
AGENTS.md                  step-by-step instructions for the AI doing the build
blueprint/                 spec, interview questions, colors, how to personalize
vault-template/            the vault itself, with {{PLACEHOLDERS}}
scripts/
  build_vault.py           template + answers.json → new vault
  new_course.py            add a course (map, folder, Materials, class, prep, colors)
  verify_vault.py          read-only check: links, orphans, placeholders, secrets
  install_plugins.py       Dataview, Templater, Calendar, Git, Local REST API (Graph Groups is bundled)
  obsidian_setup.py        register the vault, turn plugins on, check it renders in the app
  setup_chat_capture.py    test saving, connect AI apps, install the clipboard watcher
skills/
  obsidian-vault-builder/  Agent Skill wrapper for this blueprint
  obsidian-chat-capture/   Agent Skill that saves chat takeaways into 11 AI Chats
```

## Chat capture

AI chats save into `11 AI Chats` as short notes: the question, takeaways, decisions and next steps, linked to notes that already exist. Notes are never overwritten and secrets are redacted.

- **Apps on your computer** (Claude Code, Claude Desktop, Cursor, Codex, Perplexity) reach the vault through the Local REST API plugin. `setup_chat_capture.py connect` writes the connection into each app's config without showing the key to anyone.
- **Cloud apps** (ChatGPT, phone apps) can't reach your computer, so they end with a note block to copy. On a Mac, `setup_chat_capture.py watcher` installs a login item that saves copied blocks on its own.
- One line in an app's custom instructions makes saving automatic (`setup_chat_capture.py instructions`).

Details for each app are in [`setup.md`](skills/obsidian-chat-capture/references/setup.md).

## What's tested

Built on Linux with Obsidian 1.15.0 on 2026-11-11: student and non-student builds pass `verify_vault.py`; `obsidian_setup.py check` passes inside the running app (all six plugins loaded, colors on, Templater filling new notes, Home and both calendars rendering, REST API answering); `setup_chat_capture.py test` writes, reads back and deletes a note; `add_event.py` adds and lists events. Not yet run: `obsidian_setup.py` and the clipboard-watcher installer on a Mac (the Obsidian commands they use were run by hand on macOS with Obsidian 1.13.7, and the watcher's login item matches the one on the original Mac), and anything on Windows.

## Privacy

The template has no personal data. `build_vault.py`, `install_plugins.py` and `verify_vault.py` only touch the destination folder, and the build refuses a folder that already has files. `obsidian_setup.py register` edits Obsidian's own settings file and `setup_chat_capture.py connect` edits the AI app's config; both keep a backup. Nothing is uploaded. Never commit API keys; `.gitignore` covers common config files.

## License

MIT
