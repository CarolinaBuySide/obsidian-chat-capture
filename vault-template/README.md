---
type: guide
summary: "Human guide to the vault: what each numbered folder holds, how school files are organized, the habits that keep the graph tidy and which plugins are installed."
tags:
  - guide
---
# How this vault is organized

This is {{USER_NAME}}'s vault: {{AREA_LIST}} and saved AI chats, linked together. Start at [[Home]]. For AI tools, the one-page summary is [[AI Context]].

## Folders
| Folder | What goes in it | Color |
|---|---|---|
| `00 Home` | [[Home]] dashboard, [[About me]], [[AI Context]], [[Color Key]] | Gold |
| `01 Fleeting` | Quick captures. New notes land here; process them into literature or permanent notes | Yellow |
| `02 Literature` | Notes on something you read, watched or heard | Blue |
| `03 Permanent` | Your own ideas, written to stand alone | Green |
| `04 Maps` | Hub notes (MOCs) for each area and each active course | Purple |
| `05 Projects` | Work with an outcome and an end date | Orange |
| `06 Daily`, `07 Weekly` | Daily notes (`06 Daily/YYYY/MM/`) and weekly reviews | Teal |
| `08 Archive` | Finished projects and old reference guides | Brown |
| `09 Templates` | Templates used by Templater and Daily notes (hidden from search and graph) | Slate |
| `10 Attachments` | Images and files pasted into notes | Slate |
| `11 AI Chats` | Takeaways saved from AI chats, grouped by topic in [[AI Chats MOC]] | Pink |
| `12 School` | Every course file: syllabi, slides, readings, assignments and your work | School-blue hub; each active course its own color; past courses gray | <!-- if:school -->
| `13 Calendar` | Event notes behind [[Weekly Calendar]]: weekly class meetings, calls, meetings, exams and university dates. `System/` holds the calendar code | Teal |

Full color list: [[Color Key]].

## School <!-- if:school -->
- **Where to look first:** [[School MOC]] (deadlines and course notes) and [[School Library]] (every file, by course). <!-- if:school -->
- `12 School/{{TERM}}` holds the active courses. Each has the same eight folders: `01 Syllabus & Schedule`, `02 Lecture Slides`, `03 Readings & Cases`, `04 Assignments`, `05 Models & Data`, `06 Exams & Review`, `07 My Work`, `08 Other`, plus a **Materials** note listing every file. <!-- if:school -->
- `12 School/Past Courses` holds past courses, sorted into the same numbered folders and shown in gray. <!-- if:school -->
- When a course ends, follow the three steps at the bottom of [[School Library]]. <!-- if:school -->

## Habits that keep it tidy
1. Capture in a daily note or a new fleeting note; link it to a map with `[[double brackets]]`.
2. Save course files into the matching numbered folder of that course.
3. Once a week, run the weekly review in `07 Weekly` and empty `01 Fleeting`.
4. Every note should link to at least one map, so nothing floats loose in the graph.
5. Every course file should be linked from that course's Materials note. When you save a new version of a file, keep the newest at the top of its folder, move older drafts into an `Older versions` subfolder, and list both in the Materials note.
6. Office makes hidden `~$` lock files while a document is open. They're excluded from search and the graph (Settings → Files and links → Excluded files), so they never show up as loose nodes.

## Plugins
Dataview (tables and calendars), Templater (templates), Calendar (daily notes), Obsidian Git (local undo history) and Graph Groups (colored starburst graph centered on Home). Local REST API lets AI apps read and write the vault, which is how chats get saved into `11 AI Chats`. Setup steps: [[Plugin Setup Checklist]].

## AI agents
- Agents start at [[AGENTS]], the operating manual: read order, permissions, conventions and skills. Claude Code reads it through [[CLAUDE]].
- For agents: [[USER]] (who you are), [[Top of Mind]] (this week) and [[Agent Memory]] (lessons learned). Everything in one place: [[AI Agent MOC]].
- AI drafts and reports land in `01 Fleeting/AI Drafts`. Notes an agent touched carry the `ai-assisted` tag until you review them.
- Git backup: the Git plugin commits text notes and settings locally every 30 minutes (no remote; PDFs and Office files aren't tracked). Review or undo changes from **Git: Open history view**.
