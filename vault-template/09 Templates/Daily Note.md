---
type: daily
date: <% tp.date.now("YYYY-MM-DD", 0, tp.file.title, "YYYY-MM-DD") %>
tags:
  - daily
---
# <% tp.date.now("dddd, MMMM D, YYYY", 0, tp.file.title, "YYYY-MM-DD") %>

← [[06 Daily/<% tp.date.now("YYYY/MM/YYYY-MM-DD", -1, tp.file.title, "YYYY-MM-DD") %>|Yesterday]] · [[07 Weekly/<% tp.date.now("GGGG-[W]WW", 0, tp.file.title, "YYYY-MM-DD") %>|This week]] · [[06 Daily/<% tp.date.now("YYYY/MM/YYYY-MM-DD", 1, tp.file.title, "YYYY-MM-DD") %>|Tomorrow]] →

## Schedule
```dataviewjs
await dv.view("13 Calendar/System/calendar-view", {mode: "day"})
```

## Top 3 today
- [ ] <% tp.file.cursor() %>
- [ ] 
- [ ] 

## Log
- 

## Captures
Quick thoughts go here or into a new fleeting note (`01 Fleeting`). Link them with `[[Note name]]`.

## End-of-day review
- What did I learn?
- Which fleeting notes did I process?
- What carries over to tomorrow?

---
### Open tasks from earlier days
```dataview
TASK
FROM "06 Daily"
WHERE !completed AND file.day < this.file.day
SORT file.day DESC
GROUP BY file.link
LIMIT 10
```

### Notes created today
```dataview
LIST
FROM "01 Fleeting" OR "02 Literature" OR "03 Permanent" OR "04 Maps" OR "05 Projects"
WHERE type
  AND date(default(created, file.ctime)) >= this.file.day
  AND date(default(created, file.ctime)) < this.file.day + dur(1 day)
SORT file.ctime ASC
```
