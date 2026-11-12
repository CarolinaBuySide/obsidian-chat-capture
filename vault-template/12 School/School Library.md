---
type: map
summary: "Every course file, by course: active courses in color, past courses in gray, each with a Materials note."
created: {{TODAY}}
cssclasses:
  - course-note
  - course-term
tags:
  - map
  - course/materials
---
# School Library

Every file from every course lives in this `12 School` folder. Active courses have their own color; past courses are gray. Each course has a **Materials** note listing its files by type. Deadlines, grading and meeting times live in the course maps in `04 Maps`.

## {{TERM}} (active)
| | Course | Title | Materials | Course map |
|---|---|---|---|---|
{{LIBRARY_ROWS}}
Every course folder, active or past, uses the same numbered subfolders: `01 Syllabus & Schedule`, `02 Lecture Slides`, `03 Readings & Cases`, `04 Assignments`, `05 Models & Data`, `06 Exams & Review`, `07 My Work`, `08 Other`. Active courses have all eight (some stay empty until you add files); past courses only need the ones they use. Put a searchable text copy of each syllabus in `01`.

## Past courses
All gray. [[About Past Courses]]

```dataview
LIST
FROM "12 School/Past Courses"
WHERE type = "materials"
SORT file.name ASC
```

## When a course ends
1. Drag its folder from `12 School/{{TERM}}` to `12 School/Past Courses`, ideally inside Obsidian so links update. The folder turns gray automatically.
2. In its course note in `04 Maps`, change `status: active` to `status: past` and the tag `course/<code>` to `course/past`.
3. Optional: to gray out the course note too, delete that course's block in `.obsidian/snippets/color-coding.css` (each block is labeled with the course code).

← [[School MOC]] · [[Home]]
