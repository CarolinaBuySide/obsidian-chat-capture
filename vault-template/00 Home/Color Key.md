---
type: guide
summary: "Legend for every color in the file explorer, graph and tags: one per folder, one per active course, gray for past courses."
created: {{TODAY}}
tags:
  - guide
---
# Color Key

Colors come from the CSS snippet `color-coding` (file explorer, tags, course notes), the graph's color groups, and the Graph Groups plugin (file dots and starburst layout). If colors vanish: Settings → Appearance → CSS snippets → turn on `color-coding`.

## Folders
| | Folder | Color |
|---|---|---|
| <span style="color:#E0A526">■</span> | `00 Home` and root notes | Gold `#E0A526` |
| <span style="color:#E8C547">■</span> | `01 Fleeting` | Yellow `#E8C547` (gray is reserved for past courses) |
| <span style="color:#4A90D9">■</span> | `02 Literature` | Blue `#4A90D9` |
| <span style="color:#3FA66B">■</span> | `03 Permanent` | Green `#3FA66B` |
| <span style="color:#8E6BD1">■</span> | `04 Maps` | Purple `#8E6BD1` |
| <span style="color:#E07B39">■</span> | `05 Projects` | Orange `#E07B39` |
| <span style="color:#2BA3A3">■</span> | `06 Daily`, `07 Weekly`, `13 Calendar` | Teal `#2BA3A3` |
| <span style="color:#8C7B6B">■</span> | `08 Archive` | Brown `#8C7B6B` |
| <span style="color:#6B7A8F">■</span> | `09 Templates`, `10 Attachments` | Slate `#6B7A8F` |
| <span style="color:#D6589B">■</span> | `11 AI Chats` | Pink `#D6589B` |
| <span style="color:#4B9CD3">■</span> | `12 School`, current term, [[School Library]] | School blue `#4B9CD3` |
| <span style="color:#8A8F98">■</span> | `12 School/Past Courses` | Gray `#8A8F98` |

## Active courses <!-- if:school -->
Each active course has one color across its folder, course map, class, prep note and events. <!-- if:school -->
| | Course | Color | <!-- if:school -->
|---|---|---| <!-- if:school -->
{{COURSE_COLOR_ROWS}}
When a course ends it moves to Past Courses and turns gray ([[School Library]] → "When a course ends"). <!-- if:school -->

← [[Home]] · [[README]]
