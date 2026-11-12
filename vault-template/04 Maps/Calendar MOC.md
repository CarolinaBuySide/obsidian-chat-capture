---
type: map
summary: "Calendar hub: the weekly calendar, each class meeting series, university dates, exams and a log of every event added, moved or cancelled from chats or email."
created: {{TODAY}}
tags:
  - map
  - calendar
---
# Calendar MOC
← [[Home]] · [[Weekly Calendar]] · [[School MOC]]

**Open the calendar:** [[Weekly Calendar]]. Event notes live in `13 Calendar`; agents add to them with [[Skill - Calendar Update]].

**To-dos by month:** [[To-Do Calendar]] shows assignments, exams, pre-class prep (one Prep note per course, listed under Classes) and other dated to-dos ([[To-Do]]).

**Canvas sync:** any AI with a terminal on this computer can pull new Canvas deadlines, date changes, files, readings and class changes into the course maps and prep notes ([[Skill - Canvas Sync]]). <!-- if:school -->

## Classes <!-- if:school -->
| | Class | Meets | Room | Prep | <!-- if:school -->
|---|---|---|---|---| <!-- if:school -->
{{CLASS_TABLE_ROWS}}
## School dates <!-- if:school -->
Add breaks, the last day of classes and exam periods as events with `kind: break` and `no-class: true` (classes skip them automatically). <!-- if:school -->

## Other events
- [[{{TODAY}} - Vault created]]

## Coming up
```dataview
TABLE WITHOUT ID file.link AS "Event", date AS "Date", row["start-time"] AS "Start", location AS "Where", status AS "Status"
FROM "13 Calendar/Events"
WHERE type = "event" AND status != "cancelled" AND (date >= date(today) OR row["end-date"] >= date(today))
SORT date ASC, row["start-time"] ASC
LIMIT 20
```

## Event log
One line per event added, moved or cancelled, newest last. Agents and the calendar's **+ Add event** form append here.
- {{TODAY}} · calendar created from the Obsidian AI Vault blueprint
