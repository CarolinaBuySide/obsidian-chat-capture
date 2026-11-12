---
type: dashboard
summary: "Month view of what you need to do: assignments, exams, pre-class readings and prep, and dated to-dos from chats and projects, with a day-by-day list."
created: {{TODAY}}
cssclasses:
  - monthly-calendar
  - calendar-dashboard
tags:
  - dashboard
  - calendar
---
# Monthly Calendar

```dataviewjs
await dv.view("13 Calendar/System/task-calendar", {mode: "month"})
```

> [!info]- How this calendar works
> **What shows up**
> - **Assignments and exams:** dated tasks in each course map plus exam events from `13 Calendar`.
> - **Pre-class prep:** readings and other things to do before class, one note per course. See [[Calendar MOC]] for the list. Optional textbook readings are drawn lighter.
> - **To-dos:** any task written `- [ ] task [due:: YYYY-MM-DD]` in an AI chat note, a project or [[To-Do]].
> - **Not here:** classes, calls and meetings. Those stay on the [[Weekly Calendar]]. Turn on **Other events** to see non-class events here too.
>
> **Using it**
> - Click a day to see its full list under the grid, with links and checkboxes. **Day by day** always shows the next 7 days.
> - Checking an item off here updates its own note. The number on a day counts what's still open; orange means three or more.
> - **+ Add to-do**, or the box under the day's list, adds a dated to-do. With a course picked it goes in that course's prep note, otherwise in [[To-Do]].
> - The filter buttons show or hide each kind, and your choice is remembered.
>
> **How things get added**
> - Mention a deadline, reading or to-do with a date in any AI chat and it lands here as a task, following [[Skill - Calendar Update]].
> - **Canvas:** ask any AI that can run commands on this computer to sync from Canvas, or click **Copy sync request** above the grid and paste it into your AI. It pulls new assignments, date changes, files, readings and class changes into the course maps and prep notes, following [[Skill - Canvas Sync]]. The line above the grid shows when Canvas was last synced. <!-- if:school -->
>
> **Optional fields** in a task line: `[scheduled:: YYYY-MM-DD]` for a suggested date instead of a deadline · `[kind:: assignment]`, `prep`, `exam` or `todo` · `[course:: ECON 101]` · `[time:: 15:30]`.

← [[Home]] · [[Weekly Calendar]] · [[Calendar MOC]] · [[School MOC]]
