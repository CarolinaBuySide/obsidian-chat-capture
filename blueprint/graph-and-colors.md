# Graph and colors

## Target look

A live, circular graph with **Home** pinned in the middle. Around it, each hub forms its own starburst: Calendar, AI Chats, Projects (around Top of Mind), Agent, Knowledge and Archive. Each current course is a separate starburst around its Materials note, with its course map, class note, prep note and events as satellites, all in the course color. Past courses sit together in gray around School Library. Tags and unresolved links are hidden.

## How the template gets there

1. **Graph Groups plugin** (`.obsidian/plugins/graph-groups`, bundled). Its `data.json` defines the center (`00 Home/Home.md`), the branches (folder regex → hub note), how course hubs are found (`12 School/<term>/<course>/<CODE> Materials.md`), the satellites (`04 Maps/{code} MOC.md`, `13 Calendar/Classes/{code} Class.md`, `13 Calendar/Prep/{code} Prep.md`, events whose names contain the code), and the angle for each branch. It also gives each file dot (PDF, slides, Excel) its folder's color. It only reads the folder layout, so it works on any vault built from this template.
2. **Core graph color groups** in `.obsidian/graph.json`. First match wins, so each course group goes at the top (added by `new_course.py`), then Past Courses (gray), the current term (school blue), then one group per folder.
3. **Forces** from the original: center 0.494, repel 14.33, link strength 0.88, link distance 286.
4. **CSS snippet** `color-coding.css`: one `--c-…` variable per folder and per course (between the `COURSE-VARS` markers), a block per course (between the `COURSES` markers), tag colors, and course-note title bars.

## What gets colored

The same places as the original, from the same CSS:

- **File list:** each numbered folder's name in its folder color, with a colored rail on its notes. Each current course's folder gets its own color, a ● dot and a rail down everything inside it; its course map in `04 Maps` is colored to match. Past courses are gray.
- **Course notes:** any note with `cssclasses: [course-note, course-<code>]` (course maps, Materials notes, lecture notes) gets a title bar and heading underlines in the course color.
- **Tags:** note-type tags, one color per life area, and each `#course/<code>` tag in its course color.
- **Graph:** one color group per folder and per course; file dots take their folder's color.
- **Calendars:** classes, deadlines and prep tasks in the course color, read from the course map's `color` property.

`verify_vault.py` fails if a course is missing any of these pieces, and `obsidian_setup.py check` confirms the colors are applied in the running app.

## Palette

| Folder | Color |
|---|---|
| 00 Home | Gold `#E0A526` |
| 01 Fleeting | Yellow `#E8C547` |
| 02 Literature | Blue `#4A90D9` |
| 03 Permanent | Green `#3FA66B` |
| 04 Maps | Purple `#8E6BD1` |
| 05 Projects | Orange `#E07B39` |
| 06 Daily, 07 Weekly, 13 Calendar | Teal `#2BA3A3` |
| 08 Archive | Brown `#8C7B6B` |
| 09 Templates, 10 Attachments | Slate `#6B7A8F` |
| 11 AI Chats | Pink `#D6589B` |
| 12 School, current term | School blue `#4B9CD3` |
| Past courses | Gray `#8A8F98` |

Courses take colors in order from `palette.json`: Indigo, Magenta, Amber, Emerald, Coral, then Crimson, Sky and Lime.

## Gotchas

- **Close Obsidian before editing `graph.json`**, or make the change through the running app. Obsidian keeps graph settings in memory and saves them over the file.
- If colors disappear: Settings → Appearance → CSS snippets → turn on `color-coding`.
- If the graph isn't circular, check that Graph Groups is enabled under Settings → Community plugins.
