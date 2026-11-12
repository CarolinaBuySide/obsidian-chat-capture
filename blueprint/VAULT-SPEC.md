# Vault spec

The design this repo reproduces, taken from a real vault used every day for school, investing, career and AI work. `vault-template/` holds that vault's actual system files with personal content removed. Read this to understand why it's shaped this way, or to rebuild it by hand.

## Principles

1. **One center.** Everything links back to `00 Home/Home.md`, directly or through a hub. Nothing floats loose.
2. **Hubs, not deep folders.** Each area has one hub note: a map in `04 Maps`, a course's Materials note, Calendar MOC, Top of Mind. Notes link to their hub and hubs link to Home. The Graph Groups plugin turns that into a circular graph with Home in the middle and one colored starburst per hub and per course.
3. **Numbered folders by note type**, not by topic. Topics live in maps.
4. **AI is a guest with rules.** `AGENTS.md` sets the read order, a permissions table, how AI work is marked, batch-edit snapshots, note conventions, the skills and the calendar rules. Anything an agent writes is tagged `ai-assisted` until reviewed.
5. **Dates live in notes.** Classes, events and tasks are notes and task lines with properties. The calendars are views over them, never lists kept by hand.
6. **Nothing is lost.** Append, don't overwrite. Superseded files go in `Older versions`. Obsidian Git takes local snapshots every 30 minutes.

## Folders

| Folder | Purpose | Hub |
|---|---|---|
| `00 Home` | Home, Weekly Calendar, To-Do Calendar, AI Context, About me, Top of Mind, Goals, Principles, Writing Style, Color Key, Plugin Setup Checklist, `Agent/` (USER, Agent Memory, `Skills/`) | Home |
| `01 Fleeting` | Inbox; new notes land here. `AI Drafts/` holds agent proposals and reports | Note-taking MOC |
| `02 Literature` | Notes on sources, lectures and meetings (`Author - Title`, `CODE - Lecture N - Topic`) | Note-taking MOC |
| `03 Permanent` | Your own ideas, titled as claims | Note-taking MOC / area maps |
| `04 Maps` | One map per life area, one **course map** (`CODE MOC`) per course, plus AI Chats, Calendar, AI Agent, Note-taking and School MOCs | Home |
| `05 Projects` | Work with an outcome; titles start with a verb | Top of Mind |
| `06 Daily` · `07 Weekly` | `YYYY/MM/YYYY-MM-DD` daily notes and `GGGG-[W]WW` weekly reviews | Calendar MOC |
| `08 Archive` | Finished projects and old reference material | Home |
| `09 Templates` | Templater templates, including `Course` (hidden from search and graph) | — |
| `10 Attachments` | Images and files pasted into notes | — |
| `11 AI Chats` | `YYYY-MM-DD - Topic` chat takeaways, indexed in AI Chats MOC | AI Chats MOC |
| `12 School/<Term>/<CODE - Name>/` | Every file for a current course, in eight numbered subfolders, plus `CODE Materials.md` | the Materials note |
| `12 School/Past Courses/` | Finished courses, moved whole, all gray | School Library |
| `13 Calendar/` | `Classes/` (one weekly-repeating note per course), `Events/` (`YYYY-MM-DD - Title`), `Prep/` (one per course), `To-Do.md`, and `System/` (calendar code) | Calendar MOC |

## A course

Adding a course creates five things, all in the same color:

- `04 Maps/CODE MOC.md`: the course hub, with instructor, meeting time, grading and `## Upcoming deadlines` (graded work as `[due::]` tasks).
- `12 School/<Term>/CODE - Name/` with `01 Syllabus & Schedule`, `02 Lecture Slides`, `03 Readings & Cases`, `04 Assignments`, `05 Models & Data`, `06 Exams & Review`, `07 My Work`, `08 Other`.
- `CODE Materials.md` in that folder. It links every file, which makes it the center of the course's starburst.
- `13 Calendar/Classes/CODE Class.md`: `kind: class`, `repeat: weekly`, `days`, `date` and `end-date`, `start-time`, `end-time`, `location`, and `skip` for single cancelled sessions.
- `13 Calendar/Prep/CODE Prep.md`: readings and prep under `## Before class`.

It also adds a row to School MOC, School Library, Calendar MOC and Color Key, a graph color group, and a CSS block. `scripts/new_course.py` does all of this.

**When a course ends:** move its folder into `12 School/Past Courses` from inside Obsidian (so links update), set the map to `status: past` with the tag `course/past`, and delete its CSS block. It turns gray.

## Calendar

- **Weekly Calendar** (`dv.view("13 Calendar/System/calendar-view")`): a time grid of classes, calls, meetings, exams and breaks, with due dates along the top. It has a `+ Add event` form, and you can double-click a slot to add one. Event kinds are class, exam, call, meeting, interview, appointment, club, work, personal, travel, break, academic and other. Breaks (`no-class: true`) hide classes automatically. An event with `replaces: "[[CODE Class]]"` moves or cancels one session.
- **To-Do Calendar** (`dv.view("13 Calendar/System/task-calendar")`): a month grid of every dated task, sorted into assignments, exams, prep and to-dos. It has filters, a day-by-day list, check-off in place and `+ Add to-do`. Optional fields: `[scheduled:: date]`, `[kind:: …]`, `[course:: CODE]`, `[time:: HH:MM]`.
- **add_event.py**: the command-line tool agents use to add, update, cancel or list events. It writes event notes and appends one line to the Calendar MOC event log. If the shell can't write, it falls back to the Local REST API.
- **Where dates go:** graded deadlines go in the course map, readings in the Prep note, timed commitments become event notes, and anything else goes in the chat note or `To-Do.md`.

## Agent layer

- `AGENTS.md` (root, the real operating manual), and `CLAUDE.md` (`@AGENTS.md`).
- Context: `00 Home/AI Context.md`, `Agent/USER.md`, `Top of Mind.md`, append-only `Agent/Agent Memory.md`, and `Goals`, `Principles` and `Writing Style`.
- Skills: the notes in `00 Home/Agent/Skills/` are the canonical instructions: Todays Focus, Weekly Review, Process Notes, Ingest, Vault Health, Write Like Me, Calendar Update and, for students, Canvas Sync. `.claude/skills/<name>/SKILL.md` are small pointers, so Claude Code gets `/todays-focus` and the rest. `vault-health/scripts/vault_health.py` does the checking. Each skill note ends with a `## Retro log`.
- Free-write zones are `01 Fleeting/AI Drafts`, `11 AI Chats`, `13 Calendar` (through the calendar skill), today's daily note and Top of Mind. Everywhere else, agents append or propose.

## Properties

Every note has `type`, `tags` and `created`. Hubs, projects, literature and permanent notes also have a one-sentence `summary`. The types are dashboard, profile, ai-context, guide, fleeting, literature, permanent, map, project, daily, weekly, ai-chat, materials, agent-policy, agent-skill, agent-memory, event, task-list and folder-guide.

## Plugins and settings

- **Community plugins:** Dataview (JS on), Templater (folder templates for 01–07), Calendar (Monday start, weekly notes in `07 Weekly`), Obsidian Git (30-minute local commits, push off), Local REST API (how AI apps read and write the vault) and **Graph Groups**, a custom plugin bundled in the template. Graph Groups colors file dots by folder, pins Home in the center and lays each hub and course out as its own starburst.
- **Optional:** Smart Connections (on in the original; off by default here because it downloads a model).
- **Settings:** new notes go to `01 Fleeting`, attachments to `10 Attachments`, links update automatically, and `09 Templates` and Office `~$` lock files are excluded.
- **CSS snippet `color-coding`:** folder colors, a colored rail on each note, tag colors, and course title bars set by `cssclasses: [course-note, course-<code>]`.

## Chat capture

How AI chats end up in `11 AI Chats`, as in the original:

- The **Local REST API** plugin serves the vault to apps on the same computer at `https://127.0.0.1:27124` (an MCP server at `/mcp/`). Its key and certificate stay in the plugin folder, which `.gitignore` and `.claude/settings.json` both block.
- The **`obsidian-chat-capture` skill** is installed in each AI app. It writes one `YYYY-MM-DD - Topic.md` note per chat (question, takeaways, decisions, next steps, links), links only to notes that exist, appends instead of overwriting, redacts secrets, and adds dated events to the calendar.
- One line in each app's **custom instructions** makes it automatic.
- **Cloud apps** can't reach the computer, so the skill ends with a copy-ready block that starts `obsidian-capture: <path>`. On macOS a small login item (`clip_capture.py`) watches the clipboard and saves those blocks.
- `scripts/setup_chat_capture.py` sets all of this up and tests it.

## Canvas sync

For students. It makes the vault match Canvas, as in the original: assignment deadlines go into each course map (added, moved, checked off), new files go into the course's numbered folders and its Materials note, each new lecture deck gets a searchable note, readings become prep tasks, and new announcements are listed for the AI to turn into tasks and class changes. Canvas is only ever read.

- **Any AI with a terminal can run it.** `13 Calendar/System/canvas-sync/sync.py` has five commands: `setup`, `plan`, `apply`, `finish`, `status`. `plan` changes nothing; `apply` makes a Git checkpoint first, never overwrites a file and skips any note edited since the plan.
- **Canvas is read with the user's own access token** (`canvas_api.py login`), stored outside the vault in `~/.config/obsidian-canvas-sync/config.json`. Any Canvas site works; several sites can be connected.
- **Browser reader:** `fetch_canvas.js` and `file_links.js` read the same data from a logged-in Canvas tab, for schools that turn off tokens. Both readers produce the same file.
- **Different from the original:** the original starts from a button wired to a Perplexity automation and reads Canvas through a logged-in browser. Here the token reader is the default, and the button on the To-Do Calendar copies a request to paste into any AI. The planner (`canvas_sync.py`) is the original's, unchanged apart from names. The Perplexity webhook still works if its config file exists.

## How close this is to the original

The template was last compared file by file with the live vault on **2026-11-11**.

**The same:** the fourteen numbered folders; every dashboard in `00 Home`; the vault `AGENTS.md`, `CLAUDE.md` and `.claude/settings.json`; the skill notes and their slash-command pointers; the Canvas sync planner; `vault_health.py`; every template in `09 Templates`; both calendar views and `add_event.py`; the Graph Groups plugin and its layout; graph forces and color groups; the `color-coding` CSS snippet; Dataview, Templater, Calendar and Git plugin settings; app, appearance, core-plugin, daily-note, template, bookmark and property-type settings; `.gitignore`. Differences in those files are only names, example course codes and dates.

**Yours instead of the original's:** your name, areas, courses, term and colors, taken from the interview. `About me`, `Goals`, `Principles`, `Writing Style`, `USER`, `Top of Mind` and `Agent Memory` start as short drafts.

**Left out on purpose:**

| Left out | Why |
|---|---|
| Notes, course files, chats and events | Personal |
| `.chat-sync/` ledger | Bookkeeping for a nightly Perplexity scheduled task that swept the day's chats into the vault. It only works in Perplexity; here each chat saves itself through the skill |
| `12 School/_Admin & Calendars`, `_Course not identified`, `_Duplicates to review` | Leftovers from importing years of old files; a new vault has nothing to sort |
| Smart Connections | Optional (`--smart-connections`) |
| Workspace layout (open tabs, sidebar state) | Per-device; Obsidian creates it on first open |
