---
type: agent-policy
summary: "Operating manual for any AI agent in this vault: read order, ground rules, what agents may edit, how to mark AI work, note conventions and the vault skills."
tags:
  - agent
---
# AGENTS.md: operating manual for AI agents

This is {{USER_NAME}}'s Obsidian vault (`{{VAULT_PATH}}`). Every agent (Claude Code, Claude Desktop, Codex, Cursor, Perplexity, or ChatGPT via copy blocks) reads this file first and follows it. The human tour of the vault is [[README]]; everything agent-related is listed in [[AI Agent MOC]].

## 1. Read order
1. This file.
2. [[USER]]: who {{USER_NAME}} is, how they decide, what good output looks like.
3. [[Top of Mind]]: current priorities and deadlines. Check its `updated` date.
4. [[AI Context]]: shared background. Its project table is older than Top of Mind.
5. [[Agent Memory]]: preferences and decisions agents have learned. Newer entries win.
6. Then only the notes the task needs. Navigate from [[Home]] and the maps in `04 Maps` before running a full-vault search.

## 2. Ground rules
- **Cite notes.** Every claim about {{USER_NAME}}, their work or their deadlines cites the note it came from as a `[[wikilink]]` to a note that exists. If no note supports it, write "not in the vault" instead of guessing.
- **Notes are snapshots.** Say how old a fact is when it matters (for example "ECON 101 MOC, checked Sep 30"). An unchecked task with a past due date may already be done: ask, don't assume.
- **Fact, estimate or inference.** Label investing and research claims and cite dated sources.
- **Define before recommending.** State the problem and key terms, give the evidence, then recommend (see [[Principles]]).
- **No secrets.** Never write keys, passwords, tokens, account numbers or ID numbers into the vault; write `[redacted]`. Never read `.obsidian/plugins/obsidian-local-rest-api/` except to authenticate a local API call, and never print the key.
- **Confidential and third-party material.** Employer and client confidential materials stay out of the vault. Add private details about clients, classmates or contacts only when {{USER_NAME}} asks.
- **Pilot before automating.** Show {{USER_NAME}} a concrete test before scheduling recurring runs, installing agents or sending anything outside the vault.

## 3. Permissions
| Area | Agents may | Agents may not |
|---|---|---|
| Whole vault | Read, search, check links | Delete, move or rename anything without an explicit request |
| `01 Fleeting/AI Drafts/` | Create notes freely: drafts, proposals, reports | — |
| `11 AI Chats/` | Create one note per chat; append `## Update HH:MM` sections | Rewrite or overwrite an existing chat note |
| `13 Calendar/` | Add, move or cancel event notes with [[Skill - Calendar Update]]; fix a class note's room or time when a source shows the change; append log lines to [[Calendar MOC]]; add, re-date or check off tasks in `13 Calendar/Prep/` notes and [[To-Do]] | Delete event notes (cancel them instead); edit `13 Calendar/System/` code unless {{USER_NAME}} asks |
| `06 Daily/`, `07 Weekly/` | Create today's or this week's note from its template; append to it | Edit earlier days or weeks |
| `00 Home/Top of Mind.md`, `00 Home/Agent/Agent Memory.md` | Update Top of Mind; append dated lines to Agent Memory | Delete {{USER_NAME}}'s own lines |
| `04 Maps/`, `05 Projects/`, other `00 Home/` notes, [[README]] | Append a dated log or pointer line; add missing properties (`summary`, `status`, `tags`) | Rewrite existing text or reverse {{USER_NAME}}'s decisions |
| `02 Literature/`, `03 Permanent/` | Add a `summary` property; propose changes as an AI Draft | Rewrite evergreen notes or write "original insight" in {{USER_NAME}}'s voice |
| [[USER]], [[Goals]], [[Principles]], [[Writing Style]], this file | Propose edits in an AI Draft | Edit directly unless {{USER_NAME}} asks |
| `09 Templates/`, `.obsidian/`, `.claude/`, course files in `12 School/` | Read | Edit unless {{USER_NAME}} asks |

When unsure, write a proposal to `01 Fleeting/AI Drafts/` and link it instead of editing in place.

## 4. Marking AI work
- Add the tag `ai-assisted` to every note an agent creates, or whose content or `summary` an agent writes or changes. {{USER_NAME}} removes the tag once they have reviewed the note. The review queue lives in [[AI Agent MOC]].
- Generated text added inside one of {{USER_NAME}}'s notes goes in a callout: `> [!ai] Added by <agent>, YYYY-MM-DD`.
- Frontmatter stays YAML at the top. Never delete a property or change a list's format.

## 5. Batch edits
A batch is more than 3 files.
- **Before:** snapshot. The vault is a git repository (Git plugin, local only, no remote). Run the `Git: Commit all changes` command, or `git -C "{{VAULT_PATH}}" add -A && git -C "{{VAULT_PATH}}" commit -m "checkpoint: before <task>"`. Without git access, copy the files into `~/Documents/_Organizer/<date>-<task>/`.
- **After:** run `python3 .claude/skills/vault-health/scripts/vault_health.py "{{VAULT_PATH}}"`, report counts that changed, then commit again.

## 6. Note conventions
- **Properties:** every note has `type`, `tags` and `created`. Hubs, projects, literature and permanent notes also have `summary`: one plain sentence of 30 words or fewer that says what the note is for.
- **Types:** dashboard, profile, ai-context, guide, fleeting, literature, permanent, map, project, daily, weekly, ai-chat, materials, agent-policy, agent-skill, agent-memory, event, task-list.
- **Titles:** permanent notes are claims ("Linking beats filing"); literature is `Author - Title`, `Ticker - Source - Period` or `CODE - Lecture N - Topic`; chats are `YYYY-MM-DD - Topic`; projects start with a verb.
- **Links:** `[[Exact Note Name]]` only to notes that exist. Every new note links to at least one map in `04 Maps`. Add new chats to [[AI Chats MOC]].
- **Course files** go in the course's numbered folder and are listed in its `<course> Materials` note. Superseded drafts move to `Older versions`.
- **Tasks:** `- [ ] task [due:: YYYY-MM-DD]`, only with a stated date. [[Home]] lists due tasks from `04 Maps`, `05 Projects` and `11 AI Chats`; [[To-Do Calendar]] shows every dated task from those folders plus `13 Calendar`, `00 Home`, `06 Daily` and `07 Weekly`. Optional fields: `[scheduled:: YYYY-MM-DD]` instead of `due` for a suggested date that isn't a deadline (optional readings, milestones), `[kind:: assignment|prep|exam|todo]`, `[course:: ECON 101]` and `[time:: 15:30]`.
- **Obsidian syntax** (callouts, embeds, properties, Bases, Canvas): follow the `obsidian-markdown`, `obsidian-bases` and `json-canvas` skills from [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) if they are installed in `.claude/skills/`.

## 7. Folders
`00 Home` dashboards and these agent notes · `01 Fleeting` inbox (process weekly) · `02 Literature` notes on sources, lectures and meetings · `03 Permanent` {{USER_NAME}}'s own ideas · `04 Maps` hubs for areas and courses · `05 Projects` work with an outcome · `06 Daily` (`YYYY/MM/YYYY-MM-DD`) and `07 Weekly` (`GGGG-[W]WW`) · `08 Archive` finished work · `09 Templates` · `10 Attachments` · `11 AI Chats` saved chat takeaways · `12 School` every course file · `13 Calendar` event notes behind [[Weekly Calendar]], plus course prep notes (`Prep/`) and [[To-Do]] behind [[To-Do Calendar]]. Details: [[README]].

## 8. Skills
Each skill does one job. The canonical instructions are notes in `00 Home/Agent/Skills/`, so {{USER_NAME}} can edit them in Obsidian. Claude Code also exposes them as slash commands through small pointer files in `.claude/skills/`. Other agents: when {{USER_NAME}} names a skill, read its note and follow it.

| Command | Job | Instructions |
|---|---|---|
| `/todays-focus` | Three cited priorities for today, plus reflection questions, in today's daily note | [[Skill - Todays Focus]] |
| `/weekly-review` | Run the weekly review, refresh [[Top of Mind]], plan next week | [[Skill - Weekly Review]] |
| `/process-notes` | Turn a transcript or rough notes into a structured, linked note with action items | [[Skill - Process Notes]] |
| `/ingest` | Turn a URL, PDF, export or folder into a literature note and draft atomic ideas | [[Skill - Ingest]] |
| `/vault-health` | Find broken links, orphans, missing summaries, stale items and contradictions | [[Skill - Vault Health]] |
| `/write-like-me` | Draft text in {{USER_NAME}}'s voice from [[Writing Style]] and their own notes | [[Skill - Write Like Me]] |
| `/calendar-update` | Add, move or cancel calls, meetings, exams and other dated events in [[Weekly Calendar]] | [[Skill - Calendar Update]] |
| `/canvas-sync` | Pull new Canvas deadlines, date changes, files, readings and class changes into the course maps, folders, prep notes and calendars | [[Skill - Canvas Sync]] | <!-- if:school -->
| `obsidian-chat-capture` | Save a chat's takeaways to `11 AI Chats` (a skill installed in each AI app, not in the vault) | `skills/obsidian-chat-capture` in the blueprint repo |

## 9. Feedback loop
- After running a skill, append one dated line to that skill note's `## Retro log`: what worked, what didn't, and a proposed fix. Apply the fix only after {{USER_NAME}} agrees.
- Durable lessons about {{USER_NAME}} go into [[Agent Memory]]: one dated line with its source.
- At the end of a substantive chat, save it with obsidian-chat-capture and report the path.

## 10. Calendar
- When a chat reveals a dated call, meeting, interview, appointment, exam, trip or class change, add it to the calendar in the same turn with [[Skill - Calendar Update]] (`13 Calendar/System/add_event.py`), then tell {{USER_NAME}} in one line what you added. Don't wait to be asked.
- Deadlines stay tasks written `- [ ] task [due:: YYYY-MM-DD]`; [[Weekly Calendar]] and [[To-Do Calendar]] show them automatically.
- When a chat reveals anything {{USER_NAME}} has to do by a date (an assignment, a pre-class reading, a form, an errand), write the task in the same turn and tell them in one line: course deadlines in the course map, readings and class prep in `13 Calendar/Prep/<course> Prep.md`, anything else in the chat's note or, with no chat note, [[To-Do]]. Details: the to-dos section of [[Skill - Calendar Update]].
- Canvas refreshes follow [[Skill - Canvas Sync]], which any agent with a terminal on this computer can run. During a run, an agent may also add, re-date or check off tasks in a course map's `## Upcoming deadlines`, add new course files to the course folders in `12 School`, and save `13 Calendar/System/canvas-sync/state.json`. New readings and class prep go in the course's prep note; optional readings get `[scheduled:: …]` instead of `due`. <!-- if:school -->
- Asked about their schedule, read the calendar first (`add_event.py list --from DATE --to DATE`).
