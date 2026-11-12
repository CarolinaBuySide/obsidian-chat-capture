---
type: map
summary: 
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
semester: 
status: active
term: ""
color: 
materials: "[[<% tp.file.title.replace(' MOC','') %> Materials]]"
cssclasses:
  - course-note
  - course-CODE
tags:
  - map
  - course
  - course/CODE
---
# <% tp.file.title.replace(" MOC","") %>: Course title

**Instructor:** 
**Meets:** 
**Grading:** 
**Files:** [[<% tp.file.title.replace(" MOC","") %> Materials]], in `12 School/<term>/<course folder>`
**Syllabus:** · [Canvas]()

## Upcoming deadlines
- [ ] Assignment, Day Mon D time [due:: YYYY-MM-DD]

## Related projects
- None yet

## Notes
- Put lecture and reading notes in `02 Literature` (for example `CODE - Lecture 3 - Topic`) and link them here.

## Notes that link here
```dataview
TABLE type AS "Type", status AS "Status"
WHERE contains(file.outlinks, this.file.link) AND file.name != this.file.name
SORT type ASC, file.mtime DESC
```

← [[School MOC]]

%%
New-course checklist (delete when done):
1. Name this note "<CODE> MOC" and keep it in 04 Maps. Replace CODE above with a slug such as busi-410.
2. Make the folder 12 School/<term>/<course folder> with subfolders 01 Syllabus & Schedule through 08 Other.
3. Add a "<CODE> Materials" note in that folder, a "<CODE> Class" note in 13 Calendar/Classes and a "<CODE> Prep" note in 13 Calendar/Prep.
Faster: run scripts/new_course.py from the blueprint repo, which does all of this.
4. Pick an unused color: copy one course block in .obsidian/snippets/color-coding.css, and add a row to Color Key and a graph color group.
%%
