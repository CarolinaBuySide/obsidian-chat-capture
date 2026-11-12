<%*
const start = moment(tp.file.title, "GGGG-[W]WW").startOf("isoWeek");
const end = start.clone().endOf("isoWeek");
const s = start.format("YYYY-MM-DD");
const e = end.format("YYYY-MM-DD");
-%>
---
type: weekly
week: <% tp.file.title %>
start: <% s %>
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
cssclasses:
  - weekly-calendar
tags:
  - weekly
---
# Week <% tp.file.title %> · <% start.format("MMM D") %>–<% end.format("MMM D, YYYY") %>

## Days
<%* for (let i = 0; i < 7; i++) { const d = start.clone().add(i, "days"); -%>
- [[06 Daily/<% d.format("YYYY/MM/YYYY-MM-DD") %>|<% d.format("ddd D") %>]]
<%* } -%>

## Calendar
```dataviewjs
await dv.view("13 Calendar/System/calendar-view", {mode: "week", week: "<% tp.file.title %>"})
```

## Review (20 minutes)
1. **Empty the inbox** — process or delete every note in `01 Fleeting` (see the table below).
2. **Literature → permanent** — for each source you read, write at least one permanent note.
3. **Connect** — add each new permanent note to a map in `04 Maps`.
4. **Projects** — update next actions and status in `05 Projects`.
5. **Plan** — pick 1–3 priorities for next week.

## Wins
- <% tp.file.cursor() %>

## Priorities for next week
- [ ] 

---
### Fleeting notes still in the inbox
```dataview
TABLE created AS "Captured"
FROM "01 Fleeting"
WHERE type = "fleeting" AND status = "inbox"
SORT created ASC
```

### Knowledge notes created this week
```dataview
TABLE type AS "Type"
FROM "02 Literature" OR "03 Permanent" OR "04 Maps"
WHERE type
  AND date(default(created, file.ctime)) >= date(<% s %>)
  AND date(default(created, file.ctime)) < date(<% e %>) + dur(1 day)
SORT created ASC
```

### Tasks completed this week
```dataview
TASK
FROM "06 Daily"
WHERE completed AND file.day >= date(<% s %>) AND file.day <= date(<% e %>)
GROUP BY file.link
```
