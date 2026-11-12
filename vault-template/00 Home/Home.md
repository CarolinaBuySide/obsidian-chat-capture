---
type: dashboard
summary: "Vault dashboard: links to every area map plus live Dataview tables for active courses, deadlines in the next 14 days, the inbox, projects and recent AI chats."
cssclasses:
  - wide
tags:
  - dashboard
---
# Home

**Today:** open the Calendar in the right sidebar and click today, or run *Daily notes: Open today's daily note* from the command palette (`Ctrl/Cmd + P`).

**This week:** [[Weekly Calendar]]: classes with rooms, calls, meetings, exams and due dates in one view. Mention a call or meeting in any AI chat and it lands there.

**This month:** [[To-Do Calendar]]: assignments, exams, readings and other to-dos day by day, with checkboxes. Mention a deadline or reading in any AI chat and it lands there.

**Capture:** create a new note (`Ctrl/Cmd + N`) — it lands in `01 Fleeting` and Templater asks for a title.

**Areas:** {{SCHOOL_LINKS_INLINE}}{{AREA_LINKS_INLINE}}[[AI Chats MOC|AI chats]] · [[Calendar MOC|Calendar]]

**AI Context:** [[AI Context]] (read first; the shared brain for every AI app) · [[About me]]

**Guides:** [[README]] · [[Plugin Setup Checklist]] · [[Color Key]] · [[Knowledge Base.base|Knowledge Base (table view)]] · [[About Archive|Archive]]

> [!info] This page uses Dataview
> If you see code blocks instead of tables, Dataview is not installed or enabled yet — see [[Plugin Setup Checklist]].

## Active courses <!-- if:school -->
```dataview
TABLE WITHOUT ID file.link AS "Course", term AS "Term", materials AS "Files"
FROM "04 Maps"
WHERE status = "active" AND contains(file.tags, "#course")
SORT file.name ASC
```

## Due in the next 14 days
```dataview
TASK
FROM "04 Maps" OR "05 Projects" OR "11 AI Chats"
WHERE !completed AND contains(text, "due::") AND due <= date(today) + dur(14 days)
SORT due ASC
```

## Inbox — fleeting notes to process
```dataview
TABLE created AS "Captured", captured AS "From daily note"
FROM "01 Fleeting"
WHERE type = "fleeting" AND status = "inbox"
SORT created ASC
```

## Literature notes in progress
```dataview
TABLE source-type AS "Type", author AS "Author", status AS "Status"
FROM "02 Literature"
WHERE type = "literature" AND status != "processed"
SORT file.mtime DESC
```

## Recently updated permanent notes
```dataview
TABLE maturity AS "Maturity", length(file.inlinks) AS "Backlinks", file.mtime AS "Updated"
FROM "03 Permanent"
WHERE type = "permanent"
SORT file.mtime DESC
LIMIT 10
```

## Orphans — permanent notes with no links in or out
```dataview
LIST
FROM "03 Permanent"
WHERE type = "permanent" AND (length(file.inlinks) = 0 OR length(file.outlinks) = 0)
```

## Active projects
```dataview
TABLE status AS "Status", due AS "Due"
FROM "05 Projects"
WHERE type = "project" AND status = "active"
SORT due ASC
```

## Recent AI chats
```dataview
TABLE created AS "Saved", source AS "From"
FROM "11 AI Chats"
SORT file.ctime DESC
LIMIT 8
```

## Open tasks from AI chats
```dataview
TASK
FROM "11 AI Chats"
WHERE !completed
GROUP BY file.link
```
## Vault at a glance
```dataview
TABLE WITHOUT ID key AS "Note type", length(rows) AS "Count"
FROM "01 Fleeting" OR "02 Literature" OR "03 Permanent" OR "04 Maps" OR "05 Projects" OR "06 Daily" OR "07 Weekly"
WHERE type AND type != "folder-guide"
GROUP BY type
```

## AI agents
[[Top of Mind]] (this week) · [[AGENTS]] (rules for AI tools) · [[USER]] · [[Agent Memory]] · [[AI Agent MOC]] (skills, review queue, git backup)

