---
type: map
summary: "Hub for the vault's AI layer: the operating manual, the user's agent profile, shared memory, the skills, reports, the git backup and the queue of AI-written content awaiting review."
created: {{TODAY}}
tags:
  - map
  - agent
---
# AI Agent MOC

How AI tools work in this vault, in one place. Agents start at [[AGENTS]]; Claude Code enters through [[CLAUDE]].

## Context agents read
- [[AGENTS]]: operating manual (read order, rules, permissions, conventions, skills)
- [[USER]]: who {{USER_NAME}} is and what good output looks like · [[Goals]] · [[Principles]] · [[Writing Style]]
- [[Top of Mind]]: current priorities, refreshed weekly
- [[AI Context]]: shared background for every AI app
- [[Agent Memory]]: dated lessons agents have learned

## Skills
| Command | Skill note |
|---|---|
| `/todays-focus` | [[Skill - Todays Focus]] |
| `/weekly-review` | [[Skill - Weekly Review]] |
| `/process-notes` | [[Skill - Process Notes]] |
| `/ingest` | [[Skill - Ingest]] |
| `/vault-health` | [[Skill - Vault Health]] |
| `/write-like-me` | [[Skill - Write Like Me]] |
| `/calendar-update` | [[Skill - Calendar Update]]: keeps [[Weekly Calendar]] current from chats |
| `/canvas-sync` | [[Skill - Canvas Sync]]: keeps course deadlines, files and readings current from Canvas | <!-- if:school -->
| obsidian-chat-capture (optional) | saves chats to `11 AI Chats`; index in [[AI Chats MOC]] |

Folder guide: [[About AI Drafts]]

## Where agents write
- `01 Fleeting/AI Drafts/`: drafts, proposals and reports for {{USER_NAME}} to review
- `11 AI Chats/`: one note per chat, appended as it continues
- Today's daily note and this week's review: appended only

## Backup and undo
The vault is a local git repository; nothing is pushed anywhere. The Git plugin commits text notes and settings every 30 minutes. PDFs and Office files are left out of git; `.gitignore` lists exactly what's tracked.
- **Review changes:** command palette → `Git: Open source control view` or `Git: Open history view`.
- **Undo a file:** open the history view, pick the earlier commit and restore that file.

## Review queue: AI-written content
Notes an agent created or edited carry the `ai-assisted` tag. Skim, fix anything off, then remove the tag (or ask an agent to clear the tags you've approved).

```dataview
TABLE WITHOUT ID file.link AS "Note", summary AS "Summary", file.folder AS "Folder"
FROM #ai-assisted
SORT file.folder ASC, file.name ASC
```

## Reports
```dataview
LIST
FROM "01 Fleeting/AI Drafts"
SORT file.name DESC
```

← [[Home]]
