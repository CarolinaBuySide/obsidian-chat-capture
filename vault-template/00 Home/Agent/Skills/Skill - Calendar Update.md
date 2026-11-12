---
type: agent-skill
name: calendar-update
command: /calendar-update
summary: "Add, move or cancel calls, meetings, exams and other dated events in the vault calendar as soon as a chat or email reveals them."
version: 1.1
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Calendar Update

> [!abstract] One job
> Keep [[Weekly Calendar]] and [[To-Do Calendar]] true. When a chat reveals a dated call, meeting, interview, appointment, exam, trip or class change, write it to `13 Calendar` in the same turn and tell the user what you added.

## When to run
- Without being asked, whenever the user mentions or confirms something with a date and time: "I have a call with Sarah Thursday at 3", "my interview moved to Monday", "the final is in Gerrard 007". Don't wait for the end of the chat.
- the user types `/calendar-update` or asks what's on their calendar (use `list`, below).
- Not for to-dos. A deadline, reading or other to-do stays a task line, `- [ ] task [due:: YYYY-MM-DD]`; see **To-dos and pre-class prep** below. Both calendars show tasks automatically.

## Steps
1. **Get the facts:** title, date, start and end ({{TIMEZONE}} unless stated; convert and note the original zone), place or join link, who or what it's about, and where you learned it. Turn "Thursday" into a date and say the date back to the user.
2. **Check for a duplicate:** `python3 "13 Calendar/System/add_event.py" list --from DATE --to DATE`, run from the vault root (`{{VAULT_PATH}}`).
3. **Add it** (shell on the Mac):
   ```bash
   python3 "13 Calendar/System/add_event.py" add --title "Coffee chat with an analyst" \
     --date 2026-10-14 --start 15:00 --end 15:30 --kind call --location "Zoom" \
     --related "Prepare for internship recruiting" --source "2026-10-14 - Coffee Chat Prep" --by perplexity
   ```
   - `--source` is this chat's note in `11 AI Chats` (save the chat first if it doesn't exist yet), or use `--source-text "Email from …, Oct 12"`.
   - Kinds: class, exam, call, meeting, interview, appointment, club, work, personal, travel, break, academic, other. Use `--course "<course> MOC"` for anything tied to a class, so it gets the course color.
   - Unsure of the date or time: `--status tentative`, and say so.
   - The script refuses near-duplicates (exit code 3). Update the existing note instead.
4. **Changes:** `add_event.py update "<event note>" --date … --start … --end … --location … --note "why"`. Cancelled: `add_event.py cancel "<event note>" --note "why"`. Never delete an event note.
5. **One class session moved, online or cancelled:** add an event with `--kind class --course "<course> MOC" --replaces "<course> Class"` on that date (add `--status cancelled` if it's not happening). A permanent room or time change: edit that class note in `13 Calendar/Classes` and append a line to the [[Calendar MOC]] event log.
6. **No shell (MCP or REST only):** `vault_read` the target first and never overwrite. Create `13 Calendar/Events/YYYY-MM-DD - Title.md` from the template below, then `vault_append` one log line to [[Calendar MOC]]: `- YYYY-MM-DD · added [[YYYY-MM-DD - Title]] · kind · Wed, Oct 14, 2026 · 3–3:30 pm · from [[chat note]]`.
7. **No vault access** (ChatGPT web, phone): in the chat note put a dated task with the time in the text, for example `- [ ] Coffee chat with an analyst, 3:00–3:30 pm, Zoom [due:: 2026-10-14]`. It shows on the calendar as a dated item; the next agent with vault access turns it into an event.
8. **Confirm in one line:** "Added to your calendar: Coffee chat with an analyst, Wed Oct 14, 3:00–3:30 pm (Zoom)."

## To-dos and pre-class prep (Monthly Calendar)
When a chat or email shows something the user has to do by a date, write one task line in the same turn and confirm it in one line, for example "Added to your to-dos: read the HBR persuasion article before ECON 101 on Tue Oct 20."
- **Where it goes:** a graded course deadline in the course map's `## Upcoming deadlines` list (for example `ECON 101 MOC`); a reading or other class prep in `13 Calendar/Prep/<course> Prep.md` under `## Before class` (for example `ECON 101 Prep`); anything else in the chat's note in `11 AI Chats`, or in [[To-Do]] when no chat note is saved.
- **Format:** `- [ ] What to do, with links [due:: YYYY-MM-DD]`. Put a time in the text only when it is the deadline ("by 9 am"). Prep with no time shows as "before class" on its own.
- **Optional fields:** `[scheduled:: YYYY-MM-DD]` instead of `due` for a suggested date that isn't a deadline, such as optional textbook readings (start those with "Optional reading:") or milestones. `[kind:: assignment|prep|exam|todo]` when the note's default is wrong. `[course:: ECON 101]` when the course isn't clear from the note or the text. Write "(tentative)" for anything unconfirmed.
- **No date yet:** tasks without a date show in a separate list only when they're in a prep note or [[To-Do]].
- **Before adding:** search the course map and prep note for the same item so it doesn't appear twice. If a source moves a date, update that task line and say so.
- **Test:** the item appears on the right day of [[To-Do Calendar]] in its course color, and checking it off there updates its note.

## Event template (MCP path)
```markdown
---
type: event
kind: call
date: 2026-10-14
start-time: "15:00"
end-time: "15:30"
location: "Zoom"
related:
  - "[[Prepare for internship recruiting]]"
status: confirmed
source: "[[2026-10-14 - Coffee Chat Prep]]"
created: {{TODAY}}
tags:
  - event
---
# Coffee chat with an analyst
← [[Weekly Calendar]] · [[Calendar MOC]]

**When:** Wed, Oct 14, 2026 · 3–3:30 pm
**Where:** Zoom
**Source:** [[2026-10-14 - Coffee Chat Prep]] · added by Claude on 2026-10-12
```
Times are 24-hour and quoted. Leave out both times for an all-day event. Optional keys: `end-date` (multi-day), `course: "`ECON 101 MOC`"`, `replaces: "`HIST 210 Class`"`, `no-class: true` (breaks), `title` (display name).

## Rules
- Only facts the user stated or a source showed. No invented times or rooms.
- People: name and organization only. No phone numbers, emails or meeting passcodes; keep a join link only if it has no passcode.
- Link only notes that exist (the script checks).
- Recurring class notes change only when a source shows the change; log it in [[Calendar MOC]].

## Test
Pass if the event shows in [[Weekly Calendar]] on the right day and time, its note links back to its source, [[Calendar MOC]] has exactly one new log line, and no duplicate exists.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
