---
type: map
summary: "School hub: the {{TERM}} course table with meeting times and materials, deadlines for the next three weeks and every past course."
created: {{TODAY}}
cssclasses:
  - course-note
  - course-term
tags:
  - map
---
# School MOC

**All course files:** [[School Library]]: syllabi, slides, readings and assignments for every course, stored under `12 School`. Active courses each have a color; past courses are gray. See [[Color Key]].

## {{TERM}} courses
| | Course | Title | Meets | Files |
|---|---|---|---|---|
{{COURSE_TABLE_ROWS}}
**Week view:** [[Weekly Calendar]] shows these classes with their rooms, plus breaks, exams and due dates.

## Due in the next 3 weeks
```dataview
TASK
FROM "04 Maps" OR "05 Projects" OR "11 AI Chats" OR "13 Calendar/Prep"
WHERE !completed AND contains(text, "due::") AND due <= date(today) + dur(21 days)
SORT due ASC
```

## Past courses (gray)
Every past course's folder is in `12 School/Past Courses`.

```dataview
TABLE WITHOUT ID file.link AS "Course", term AS "Term", materials AS "Files"
FROM "04 Maps"
WHERE contains(file.tags, "#course/past")
SORT file.name ASC
```

← [[Home]]
