---
type: dashboard
summary: "Live weekly calendar: classes with rooms, calls and meetings, exams, university breaks and due dates, drawn from 13 Calendar event notes and dated tasks."
created: {{TODAY}}
cssclasses:
  - weekly-calendar
  - calendar-dashboard
tags:
  - dashboard
  - calendar
---
# Weekly Calendar

```dataviewjs
await dv.view("13 Calendar/System/calendar-view", {mode: "week"})
```

## Due this week
```dataview
TASK
FROM "04 Maps" OR "05 Projects" OR "11 AI Chats" OR "13 Calendar"
WHERE !completed AND due AND due >= date(sow) AND due <= date(eow)
SORT due ASC
```

> [!info]- How this calendar works
> **What shows up**
> - **Classes:** one note per course in `13 Calendar/Classes`. See [[Calendar MOC]] for the list. They repeat weekly and skip university breaks on their own.
> - **Calls, meetings, exams and other events:** one note each in `13 Calendar/Events`, named `YYYY-MM-DD - Title`.
> - **Due dates:** any task written `- [ ] task [due:: YYYY-MM-DD]` in a course map, project or AI chat. Check them off in the list above or in their own note.
> - **Colors:** each course keeps its color from the [[Color Key]]. Gray means no classes; dashed or striped means tentative.
>
> **Adding things**
> - Click **+ Add event** (or double-click an empty time slot), fill in the form and save.
> - Or just mention it in any AI chat ("I have a call with … Thursday at 3"). Perplexity and Claude add it here and log it in the [[Calendar MOC]], following [[Skill - Calendar Update]].
> - To move or cancel one class session, add an event that `replaces` that class. To change a room for good, edit the class note.
>
> **Today's schedule** also appears at the top of each new daily note, and each weekly review shows its week.

← [[Home]] · [[Calendar MOC]] · [[School MOC]]
