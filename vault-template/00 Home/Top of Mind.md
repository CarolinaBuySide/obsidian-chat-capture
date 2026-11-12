---
type: ai-context
summary: "Current priorities and deadlines for this week, refreshed by the weekly review. Agents may update it."
created: {{TODAY}}
tags:
  - ai-context
  - agent
---
# Top of Mind

Refreshed by [[Skill - Weekly Review]]. Agents may edit this note.

## This week
- [ ] 

## Deadlines (next 14 days)
```dataview
TASK
FROM "04 Maps" OR "05 Projects" OR "11 AI Chats" OR "13 Calendar"
WHERE !completed AND due AND due <= date(today) + dur(14 days)
SORT due ASC
```

## Active projects
```dataview
LIST summary
FROM "05 Projects"
WHERE type = "project" AND status = "active"
```

## Open loops
- 

← [[Home]] · [[AI Agent MOC]]
