# Personalize

## Add a course
```bash
python3 scripts/new_course.py "<vault>" --code "ECON 325" --name "Entrepreneurship" --term "Fall 2026" \
  --days Tue Thu --start 11:00 --end 12:15 --location "Fetzer 109" --instructor "Prof. Name" \
  --term-start 2026-08-17 --term-end 2026-12-02 --color "#B83DBA" --color-name Magenta
```
Close Obsidian first, because it rewrites `graph.json` from memory. To do it by hand instead, follow the checklist at the bottom of `09 Templates/Course.md`.

## File course material
Save the file in the matching numbered subfolder, then add a line under that folder's heading in the course's Materials note, for example `- [[Lecture 3.pptx|Lecture 3]] · PowerPoint`. Keep the newest version at the top and move older drafts into an `Older versions` subfolder.

## Canvas
- **Connect or reconnect:** `python3 "13 Calendar/System/canvas-sync/canvas_api.py" login --host <school>.instructure.com` (you type the token), then `python3 "13 Calendar/System/canvas-sync/sync.py" setup`.
- **Sync:** ask any AI with a terminal on your computer to "sync from Canvas"; it follows `Skill - Canvas Sync`.
- **New term:** add the courses, then run `sync.py setup` again.
- **Disconnect:** `canvas_api.py logout --host …`, and delete the token in Canvas.

## Add a break, exam or class change
```bash
python3 "13 Calendar/System/add_event.py" add --title "Fall Break" --date 2026-10-15 --end-date 2026-10-16 --kind break --no-class
python3 "13 Calendar/System/add_event.py" add --title "ECON 325 on Zoom" --date 2026-10-13 --start 11:00 --end 12:15 --kind class --replaces "ECON 325 Class"
```
Run with `--help` to see every option. Or just tell an AI with vault access; it follows `Skill - Calendar Update`.

## Retire a course
See "When a course ends" in `12 School/School Library.md`. In short: move the folder inside Obsidian to `Past Courses`, set the map to `status: past` and tag it `course/past`, and delete its CSS block.

## Add a life area
Create `04 Maps/<Area> MOC.md` from the Map of Content template, then link it from the Areas line on Home, from AI Context, and from a `## <Area>` section in AI Chats MOC. You can add a tag color under `/* Area tags */` in `color-coding.css`.

## Change colors
Edit the variable in `color-coding.css`, the matching graph color group, and the Color Key row. Keep all three in sync.

## Connect AI apps
- **Chat capture for Claude Code, Claude Desktop, Cursor or Codex:** `python3 scripts/setup_chat_capture.py connect "<vault>" --app <app>`, with Obsidian open. Other apps: `skills/obsidian-chat-capture/references/setup.md`.
- **Claude Code inside the vault:** run `claude` in the vault folder. It reads `CLAUDE.md` → `AGENTS.md` and gets `/todays-focus`, `/weekly-review` and the other skills from `.claude/skills/`.
- **Other apps with file access** (Codex, Cursor, Perplexity on your computer): point them at the vault's `AGENTS.md`.
- **Cloud apps (ChatGPT, phones):** upload the `obsidian-chat-capture` skill, and on a Mac run `python3 scripts/setup_chat_capture.py watcher "<vault>"` so copied note blocks save themselves.
