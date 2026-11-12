---
type: agent-skill
name: process-notes
command: /process-notes
summary: "Turns a transcript, lecture recording notes or rough meeting notes into one structured, linked literature note with decisions and action items, and logs it on the related project or course."
version: 1.0
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Process Notes

> [!abstract] One job
> Raw notes in, one clean linked note out: decisions, action items, open questions and links to the right project or course.

## When to run
the user pastes a transcript or rough notes (meeting, lecture, client call, interview, club meeting) or points to a file, or types `/process-notes`.

## Steps
1. **Identify** the type (meeting, lecture, call, interview), date, the course or project it belongs to, and the people involved (names and roles only).
2. **Find links:** search the vault for the project, course, company and people named. Link only to notes that exist.
3. **Extract:** decisions; action items with owner, and a due date only when one was stated; open questions; key facts and numbers. Paraphrase; quote at most two short lines.
4. **Write one note** in `02 Literature/`:
   - Title: `YYYY-MM-DD - <Meeting or CODE - Lecture N> - <Topic>`.
   - Frontmatter: `type: literature`, `source-type: meeting | lecture | call | interview`, `status: unprocessed`, `created`, `summary` (one sentence), `tags: [literature, ai-assisted, <area tag>]`.
   - Sections: Summary · Decisions · Action items · Open questions · Key facts · Links.
5. **Log it where it belongs (append only):**
   - Project: append `- YYYY-MM-DD: <one line> → [[new note]]` to its `## Log`. If the user owns action items with dates, append them under a new heading `## Actions from YYYY-MM-DD` as `- [ ] task [due:: YYYY-MM-DD]` so they appear on [[Home]].
   - Course: append a pointer line to the course MOC in `04 Maps`.
6. Reply with the note path, the decisions and the user's action items.

## Rules
- No private details about third parties (contact info, health, finances) unless the user asks.
- Course AI policies apply: check the course MOC before processing graded work.

## Test
Pass if the note has every section, every action item names an owner, dates appear only where stated, links resolve, and the only other change is the appended log line.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
