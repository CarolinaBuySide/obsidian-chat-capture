#!/usr/bin/env python3
"""Add a course to a blueprint vault, the same way the original vault organizes courses.

Creates:
  04 Maps/<CODE> MOC.md                          course map: instructor, meeting time, deadlines (the course hub)
  12 School/<Term>/<CODE - Name>/                with 01 Syllabus & Schedule ... 08 Other
  12 School/<Term>/<CODE - Name>/<CODE> Materials.md   lists every file (center of the course's graph starburst)
  13 Calendar/Classes/<CODE> Class.md            weekly class meetings on the Weekly Calendar
  13 Calendar/Prep/<CODE> Prep.md                readings and prep on the To-Do Calendar
and adds the course to School MOC, School Library, Calendar MOC, Color Key, the graph color groups and color-coding.css.

Usage:
  python3 scripts/new_course.py "<vault>" --code "ECON 325" --name "Entrepreneurship" --term "Fall 2026" \\
      --days Tue Thu --start 11:00 --end 12:15 --location "Fetzer 109" --instructor "Prof. Name" \\
      --term-start 2026-08-17 --term-end 2026-12-02 --color "#B83DBA" --color-name Magenta

Close Obsidian first, or it may save its in-memory graph settings over graph.json.
Standard library only. Never overwrites an existing course.
"""
import os
import argparse, datetime, json, pathlib, re, sys

SUBFOLDERS = ["01 Syllabus & Schedule", "02 Lecture Slides", "03 Readings & Cases", "04 Assignments",
              "05 Models & Data", "06 Exams & Review", "07 My Work", "08 Other"]
DAY_WORDS = {"Mon": "Mondays", "Tue": "Tuesdays", "Wed": "Wednesdays", "Thu": "Thursdays", "Fri": "Fridays", "Sat": "Saturdays", "Sun": "Sundays"}

def slug(code):
    return re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")

def ampm(hhmm):
    if not hhmm: return ""
    h, m = map(int, hhmm.split(":"))
    s = f"{(h - 1) % 12 + 1}:{m:02d}"
    return s + (" pm" if h >= 12 else " am")

def meets(days, start, end, location):
    d = " & ".join(DAY_WORDS.get(x, x) for x in days)
    t = f"{ampm(start)}–{ampm(end)}" if start and end else ""
    return ", ".join(x for x in [" ".join(y for y in [d, t] if y), location] if x)

def insert_after_table_header(text, header_regex, row):
    m = re.search(header_regex + r"\n\|[-| ]+\|[^\n]*\n((?:\|[^\n]*\n)*)", text)
    if not m: return text + "\n" + row + "\n"
    return text[:m.end()] + row + "\n" + text[m.end():]

def add_course(vault, code, name, term, days, start, end, location, instructor, term_start, term_end, color, color_name=""):
    v = pathlib.Path(vault).expanduser()
    s = slug(code)
    folder_name = f"{code} - {name}" if name else code
    folder = v / "12 School" / term / folder_name
    moc = v / "04 Maps" / f"{code} MOC.md"
    if folder.exists() or moc.exists():
        sys.exit(f"Refusing: {code} already exists.")
    today = datetime.date.today().isoformat()
    label = f"{color_name} " if color_name else ""
    swatch = f'<span style="color:{color}">■</span>'
    when = meets(days, start, end, location)

    for sub in SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)

    moc.write_text(f"""---
type: map
summary: "Course hub for {code} {name} ({term}): meeting time, grading, deadlines and links to materials."
created: {today}
semester: {term}
status: active
term: "{term}"
color: "{color}"
materials: "[[{code} Materials]]"
cssclasses:
  - course-note
  - course-{s}
tags:
  - map
  - course
  - course/{s}
---
# {code}: {name}

{swatch} **Active · {label}**· {term}

**Instructor:** {instructor}
**Meets:** {when}
**Grading:** 
**Files:** [[{code} Materials]]: every syllabus, slide deck, reading and assignment, in `12 School/{term}/{folder_name}`
**Class and prep:** [[{code} Class]] · [[{code} Prep]]
**Syllabus:** 

## Upcoming deadlines
Graded work only, one line each: `- [ ] Assignment [due:: YYYY-MM-DD]`. Readings go in [[{code} Prep]].

## Related projects
- None yet

## Notes
- Put lecture and reading notes in `02 Literature` (for example `{code} - Lecture 3 - Topic`) and link them here.

## Notes that link here
```dataview
TABLE type AS "Type", status AS "Status"
WHERE contains(file.outlinks, this.file.link) AND file.name != this.file.name
SORT type ASC, file.mtime DESC
```

← [[School MOC]]
""")

    sections = "\n\n".join(f"## {sub[3:]}\n" for sub in SUBFOLDERS)
    (folder / f"{code} Materials.md").write_text(f"""---
type: materials
course: "{code}"
status: active
term: "{term}"
color: "{color}"
cssclasses:
  - course-note
  - course-{s}
tags:
  - course/materials
  - course/{s}
---
# {code} Materials

{swatch} **Active course · {label}**· {term}

Every file for {code} ({name}): syllabus, slides, readings, assignments and your own work, in the eight folders next to this note. Link each file under its folder's heading, for example `- [[Lecture 3.pptx|Lecture 3]] · PowerPoint`. Older drafts go in an `Older versions` subfolder.

- **Course map (deadlines, grading, instructor):** [[{code} MOC]]

{sections}
""")

    cls = v / "13 Calendar" / "Classes" / f"{code} Class.md"
    cls.parent.mkdir(parents=True, exist_ok=True)
    cls.write_text(f"""---
type: event
kind: class
title: "{name or code}"
repeat: weekly
days: [{", ".join(days)}]
date: {term_start or today}
end-date: {term_end or term_start or today}
start-time: "{start}"
end-time: "{end}"
location: "{location}"
course: "[[{code} MOC]]"
instructor: "{instructor}"
skip: []
status: confirmed
created: {today}
tags:
  - event
  - course/{s}
---
# {code} class meetings
← [[Weekly Calendar]] · [[Calendar MOC]] · [[{code} MOC]]

**When:** {meets(days, start, end, "")}
**Where:** {location}
**Dates:** {term_start} to {term_end}
**Course:** [[{code} MOC]] · {instructor}

> [!info] Changing this class
> - Breaks (events with `no-class: true`) are skipped automatically.
> - One session cancelled: add its date to `skip`, for example `skip: [2026-11-05]`.
> - One session moved, online or special: add an event with `replaces: "[[{code} Class]]"` on that date (see [[Skill - Calendar Update]]).
> - Room or time changed for good: edit `location` or the times above and add a line to the Calendar MOC event log.
""")

    prep = v / "13 Calendar" / "Prep" / f"{code} Prep.md"
    prep.parent.mkdir(parents=True, exist_ok=True)
    prep.write_text(f"""---
type: task-list
summary: "{code} readings and other things to do before class, by date. Graded deadlines stay in the course map."
course: "[[{code} MOC]]"
task-kind: prep
created: {today}
tags:
  - task-list
  - calendar
---
# {code} Prep
← [[To-Do Calendar]] · [[{code} MOC]]

Readings and other things to do before class ({when}). Graded deadlines stay in [[{code} MOC]]. Both show on the [[To-Do Calendar]].

## Before class
""")

    # hub tables
    rows = {
        "04 Maps/School MOC.md": (r"## [^\n]* courses\n\| \| Course \| Title \| Meets \| Files \|",
                                  f"| {swatch} | [[{code} MOC\\|{code}]] | {name} | {when} | [[{code} Materials\\|Materials]] |"),
        "12 School/School Library.md": (r"## [^\n]*\(active\)\n\| \| Course \| Title \| Materials \| Course map \|",
                                        f"| {swatch} | **{code}** | {name} | [[{code} Materials]] | [[{code} MOC]] |"),
        "04 Maps/Calendar MOC.md": (r"\| \| Class \| Meets \| Room \| Prep \|[^\n]*",
                                    f"| {swatch} | [[{code} Class]] | {meets(days, start, end, '')} | {location} | [[{code} Prep]] |"),
        "00 Home/Color Key.md": (r"\| \| Course \| Color \|[^\n]*",
                                 f"| {swatch} | [[{code} MOC]] | {label}`{color}` |"),
    }
    for rel, (hdr, row) in rows.items():
        p = v / rel
        if p.exists():
            t = p.read_text()
            if row not in t: p.write_text(insert_after_table_header(t, hdr, row))

    # graph color group (inserted first: first match wins, so it beats the generic School groups)
    gp = v / ".obsidian" / "graph.json"
    if gp.exists():
        g = json.loads(gp.read_text())
        q = f'path:"12 School/{term}/{folder_name}" OR file:"{code} MOC" OR tag:#course/{s} OR (path:"13 Calendar" file:"{code}")'
        if not any(c["query"] == q for c in g.get("colorGroups", [])):
            g.setdefault("colorGroups", []).insert(0, {"query": q, "color": {"a": 1, "rgb": int(color.lstrip("#"), 16)}})
            gp.write_text(json.dumps(g, indent=2) + "\n")

    # CSS: variable + block
    css = v / ".obsidian" / "snippets" / "color-coding.css"
    if css.exists():
        t = css.read_text()
        var = f"--c-{s}"
        if var not in t:
            t = t.replace("  /* COURSE-VARS:END */", f"  {var}: {color};  /* {code} ({color_name or color}) */\n  /* COURSE-VARS:END */")
            p_ = f"12 School/{term}/{folder_name}"
            block = (f"/* {code} · {color_name or color} */\n"
                     f'.nav-folder-title[data-path="{p_}"] {{ color: var({var}); opacity: 1; font-weight: 700; border-left: 3px solid var({var}); }}\n'
                     f'.nav-folder-title[data-path="{p_}"] .nav-folder-title-content::before {{ content: "● "; }}\n'
                     f':is(.nav-folder-title,.nav-file-title)[data-path^="{p_}/"] {{ color: var(--text-normal); opacity: 1; border-left: 3px solid var({var}); }}\n'
                     f'.nav-file-title[data-path="04 Maps/{code} MOC.md"] {{ color: var({var}); font-weight: 600; border-left: 3px solid var({var}); }}\n'
                     f".course-{s} {{ --course-color: var({var}); }}\n"
                     f'.tag[href="#course/{s}"] {{ --tag-color: var({var}); --tag-background: color-mix(in srgb, var({var}) 15%, transparent); }}\n')
            t = t.replace("/* COURSES:END */", block + "/* COURSES:END */")
            css.write_text(t)
    return folder

if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("vault"); a.add_argument("--code", required=True); a.add_argument("--name", default="")
    a.add_argument("--term", required=True); a.add_argument("--days", nargs="*", default=[])
    a.add_argument("--start", default=""); a.add_argument("--end", default=""); a.add_argument("--location", default="")
    a.add_argument("--instructor", default=""); a.add_argument("--term-start", default=""); a.add_argument("--term-end", default="")
    a.add_argument("--color", default="#5A67D8"); a.add_argument("--color-name", default="")
    x = a.parse_args()
    print("Created", add_course(x.vault, x.code, x.name, x.term, x.days, x.start, x.end, x.location, x.instructor,
                                x.term_start, x.term_end, x.color, x.color_name))
