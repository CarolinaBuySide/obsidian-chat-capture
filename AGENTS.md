# Instructions for the AI building a vault from this repo

You are helping someone get an Obsidian vault that is organized exactly like the real vault this repo was taken from, including the part where AI chats save themselves into it. Do the steps in order. A step is done only when its command prints what the step says it should.

The person you are helping may never have used Obsidian. Explain in plain words, and do the work yourself wherever you can.

## 0. Check what you can do

| You have | Do this |
|---|---|
| A shell on the user's computer (Claude Code, Codex, Cursor, a desktop agent) | Clone this repo there and run every step. |
| File access to their computer but no shell there | Run steps 1 to 3 in your own sandbox, copy every file (including hidden `.obsidian/**`, `.claude/**` and `.gitignore`) to the destination, then give the user the commands for steps 4 to 7. |
| Neither (a cloud chat app) | Run steps 1 to 3 in your sandbox if you have one and hand back a zip. Then give the user the commands for steps 4 to 7. With no sandbox, give them all the commands. |

Requirements on the user's computer: [Obsidian](https://obsidian.md/download) 1.12 or newer, Python 3.9 or newer, and `git` (optional, for local history). If Obsidian is missing, ask the user to install it; do not install apps for them without asking.

Never write into an existing vault or a non-empty folder. For that case see "Existing vault" below.

## 1. Interview the user

Ask the questions in [`blueprint/interview.md`](blueprint/interview.md), a few at a time. Write the answers to `answers.json`, shaped like [`blueprint/answers.example.json`](blueprint/answers.example.json). Show the user a short summary and get a yes before building.

## 2. Build the vault

```bash
python3 scripts/build_vault.py --answers answers.json --dest "<new folder, for example ~/Documents/Obsidian Vault>"
```

This copies [`vault-template/`](vault-template/), fills in the name, dates and term, makes one map per life area and, for students, sets up every course: a course map, a folder with eight numbered subfolders, a Materials note, a weekly class note and a prep note, plus table rows and colors. Non-students get no `12 School` folder. It ends by starting a local git history. Done when it prints `Built vault at …`.

## 3. Install the plugins

```bash
python3 scripts/install_plugins.py "<vault>" --obsidian-skills
```

Downloads Dataview, Templater, Calendar, Obsidian Git and Local REST API, and adds the Obsidian syntax skills the original vault keeps in `.claude/skills`. Graph Groups is already in the template. Add `--smart-connections` if the user asked for it in the interview. Done when it prints `Done.` with no `FAILED` line.

## 4. Open it in Obsidian and turn everything on

```bash
python3 scripts/obsidian_setup.py register "<vault>"   # Obsidian must be quit first
# open Obsidian (macOS: open -a Obsidian; Windows: start "" "%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe"). The new vault opens on its own.
python3 scripts/obsidian_setup.py enable "<vault>"
python3 scripts/obsidian_setup.py check "<vault>"      # done when it prints PASS
```

`register` backs up Obsidian's own settings file, switches on Obsidian's command-line interface and adds the vault to Obsidian's list. `enable` turns on the plugins and Templater's "Trigger Templater on new file creation". `check` looks inside the running app and confirms the plugins are loaded, the colors are on, new notes get their template, Home and both calendars render, and the Local REST API answers.

If you cannot quit or open Obsidian yourself, ask the user to do just that part. If the command-line tool is not found, pass `--cli <path>`. If it still fails, fall back to the clicks in the vault's `00 Home/Plugin Setup Checklist.md` and say so in your report.

## 5. Turn on chat capture

This is what makes AI chats land in `11 AI Chats`. Skip it only if the user said no in the interview.

```bash
python3 scripts/setup_chat_capture.py test "<vault>"                       # done when it prints PASS
python3 scripts/setup_chat_capture.py connect "<vault>" --app claude-code  # once per app the user named
python3 scripts/setup_chat_capture.py watcher "<vault>"                    # macOS, if they use ChatGPT or a phone app
python3 scripts/setup_chat_capture.py instructions
```

- `connect` supports `claude-code`, `claude-desktop`, `cursor` and `codex`, and needs Node.js (it connects each app through `npx mcp-remote`). If `test` says the note did not land in the vault folder, another open vault is answering on the same port: close that vault's window and run it again.
- It writes the API key straight into the app's config. Never print the key, read the plugin's settings file aloud, or ask the user to paste the key into a chat.
- For Perplexity, ChatGPT and Claude on the web, follow that app's section in [`skills/obsidian-chat-capture/references/setup.md`](skills/obsidian-chat-capture/references/setup.md). They need the skill folder uploaded as a zip.
- Give the user the line from `instructions` to paste into each app's custom instructions. That line is what makes capture automatic.
- Prove it: in one connected app, ask it to save a short test chat, and check that a `YYYY-MM-DD - Topic.md` note appeared in `11 AI Chats`. If you can't run that app, tell the user how to try it.

## 6. Connect Canvas (students whose school uses Canvas)

This keeps course deadlines, files and readings current. It works from a terminal, so any AI can run it later. Skip it if the user isn't a student or their school doesn't use Canvas.

1. Ask the user to create a Canvas access token (Canvas → Account → Settings → **+ New access token**) and to run this **themselves, in their own terminal**, pasting the token at the hidden prompt:
   ```bash
   python3 "<vault>/13 Calendar/System/canvas-sync/canvas_api.py" login --host <school>.instructure.com
   ```
   Never ask for the token in chat, never read `~/.config/obsidian-canvas-sync/config.json`, and never print it. A user with two Canvas sites runs it once per site.
2. Then you run:
   ```bash
   python3 "<vault>/13 Calendar/System/canvas-sync/sync.py" setup    # done when every course shows OK
   ```
   If a course shows `??`, rerun with `--map "<CODE>=<canvas id>"` using the ids it lists.
3. Ask which courses post lecture notes before class, and set `slides_are_prep` to `true` for those in `courses.json`.
4. Run the first sync by following the vault's `00 Home/Agent/Skills/Skill - Canvas Sync.md` (plan, fill in lecture notes, apply, finish). Done when `sync.py status` shows a last sync time.

If the school has turned off access tokens, use the "Browser reader" section of that skill note, which needs an AI that can drive a browser the user is logged into. If neither is possible, say so in your report; the rest of the vault works without it.

## 7. Verify the files

```bash
python3 scripts/verify_vault.py "<vault>"     # done when it prints PASS
python3 "<vault>/13 Calendar/System/add_event.py" list --from <today> --to <today + 7 days>
```

`verify_vault.py` checks folders, settings, links, orphan notes, leftover placeholders and secrets. The second command should list the "Vault created" event and, for students, this week's classes.

## 8. Report

Tell the user, in a few lines:

- where the vault is, and to start at **Home**;
- which steps passed, and exactly which ones you could not run;
- that `About me`, `Goals`, `Principles` and `Writing Style` in `00 Home` are starter drafts for them to rewrite;
- which AI apps are connected and how a chat gets saved from each;
- for students, whether Canvas is connected, and that they can say "sync from Canvas" to any AI with a terminal on this computer;
- that Obsidian's command-line setting is now on, and where the settings backup is (printed by `register`);
- for students, to give you their breaks and exam dates so you can add them ([`blueprint/personalize.md`](blueprint/personalize.md)).

## Existing vault

Only when the user asks for it. Back up first (copy the vault, or commit with git). Add missing folders and notes from `vault-template/`; never overwrite or delete an existing note. Merge `.obsidian/*.json` key by key and keep the user's values. Run `verify_vault.py` and fix only what you added.

## Reference

- [`blueprint/VAULT-SPEC.md`](blueprint/VAULT-SPEC.md): the design, and what does and doesn't match the original.
- [`blueprint/graph-and-colors.md`](blueprint/graph-and-colors.md): colors and the Home-centered graph.
- [`blueprint/personalize.md`](blueprint/personalize.md): add or retire courses, add areas, change colors, connect more apps.
- Add courses later with `scripts/new_course.py` (run `--help`). Close Obsidian first.
