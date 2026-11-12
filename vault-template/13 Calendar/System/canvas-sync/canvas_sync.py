#!/usr/bin/env python3
"""Plan a Canvas -> Obsidian sync for this vault (version 2.1).

Part of the Canvas sync (see "00 Home/Agent/Skills/Skill - Canvas Sync.md"). It only plans changes; sync.py
(or an agent) writes them. Nothing here talks to Canvas or changes the vault.

Usage
  python3 canvas_sync.py --canvas canvas.json --vault <extracted inputs> --out <plan dir>
                         [--downloads <dir>] [--backfill-notes "ECON 101"] [--init] [--now 2026-10-12T21:00]

  --canvas     JSON from fetch_canvas.js: one object per Canvas host, as a list or as {"hosts": [...]}
  --vault      folder holding the files pack_inputs.py packed (notes plus vault_manifest.json)
  --out        where the plan goes
  --downloads  folder with downloaded Canvas files as <downloads>/<file id>/<file name>. Run the planner once
               without it to get imports.json, download those files, then run it again with --downloads so it can
               count slides and write lecture notes.
  --backfill-notes  also write lecture notes for decks already in the vault for these course codes (comma
               separated), when the deck is in --downloads
  --init       mark every current announcement, file and calendar event as already seen
  --now        local time override, for tests

Changes
  2.1  a soft line break inside a slide paragraph now counts as a space, and "Lecture #N" / "Lecture Notes N"
                    prefixes are dropped from lecture-note topics.

Plan (in --out)
  files/<vault path>  new contents for each note that changes or is created
  changes.json        [{path, sha256_before, sha256_after, edits}]: write each file with expected_sha256 = sha256_before
                      (sha256_before is null for a new note: write it only if the path doesn't exist yet)
  imports.json        [{course, host, file_id, name, size, updated_at, dest, replaces, reason, category}]: Canvas files
                      to copy into the vault. When "replaces" is set, first move that vault file to "replaces_to".
  state.json          the new sync state, saved to 13 Calendar/System/canvas-sync/state.json after the writes succeed
  report.md           what changed, plus new announcements, files, links and events for the agent to read
  summary.json        counts, for the run summary

What it changes
  - Course map "## Upcoming deadlines": adds upcoming assignments the map is missing, moves a task when Canvas moves
    its due date, checks a task off when Canvas shows it submitted or graded, and takes the date off a task whose
    Canvas due date was removed (with a note saying so). It never deletes a line and never touches checked-off tasks.
  - Course files: every Canvas file that isn't in the course folder yet (matched by name and size) is imported into
    the matching numbered folder and listed in the course's Materials note. A file Canvas re-uploaded with new
    contents replaces the vault copy, which moves to "Older versions".
  - Readings and lecture notes: a new reading becomes a "Read ..." task for the class it belongs to (its week, or
    the next class), and so does a new lecture deck in courses where the instructor posts notes before class
    (slides_are_prep in courses.json). A matching "(tentative)" placeholder task is rewritten instead.
  - Lecture notes in Obsidian: each new deck (PowerPoint or PDF) gets a note next to it, "<code> - Lecture N - Topic",
    with the slide outline as searchable text, the deck's links, a Key ideas callout for the agent to fill and a
    "My notes" section for you. The course map's "## Notes" section gets a pointer line.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = "13 Calendar/System/canvas-sync/state.json"
HEADING = "## upcoming deadlines"
WEEKDAY = r"(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?"
MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
TIME = r"\d{1,2}(?::\d{2})?\s*(?:am|pm)"
DATE_MENTION = re.compile(rf",?\s*\b{WEEKDAY},?\s+{MONTH}\s+\d{{1,2}}\b(?:,?\s*\d{{4}})?(?:\s+{TIME}(?:\s*[–-]\s*{TIME})?)?", re.I)
TASK = re.compile(r"^(\s*[-*+]\s+\[)([ xX])(\]\s+)(.*)$")
LIST_ITEM = re.compile(r"^\s*[-*+]\s+")
DUE = re.compile(r"\s*\[due::\s*(\d{4}-\d{2}-\d{2})\s*\]")
ANY_DATE = re.compile(r"\[(?:due|scheduled)::\s*(\d{4}-\d{2}-\d{2})\s*\]")
INLINE_FIELD = re.compile(r"\s*\[(?:due|scheduled|kind|course|time)::[^\]]*\]")
NEW_WINDOW_DAYS = 3  # a course seen for the first time reports announcements from the last 3 days
PREP_WINDOW_DAYS = 10  # files posted longer ago than this don't get a new prep task
DAYMAP = {"mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thur": 3, "thurs": 3, "fri": 4, "sat": 5, "sun": 6}

CATEGORY = {
    "01": "01 Syllabus & Schedule", "02": "02 Lecture Slides", "03": "03 Readings & Cases", "04": "04 Assignments",
    "05": "05 Models & Data", "06": "06 Exams & Review", "07": "07 My Work", "08": "08 Other",
}
SECTION = {  # Materials note heading for each folder
    "01": "## Syllabus & schedule", "02": "## Lecture slides", "03": "## Readings & cases", "04": "## Assignments",
    "05": "## Models & data", "06": "## Exams & review", "07": "## My work", "08": "## Other",
}
KIND_NAME = {
    "pdf": "PDF", "pptx": "PowerPoint", "ppt": "PowerPoint", "key": "Keynote", "docx": "Word", "doc": "Word",
    "xlsx": "Excel", "xls": "Excel", "xlsm": "Excel", "csv": "CSV", "txt": "Text", "html": "Web page", "htm": "Web page",
}
DECK_EXT = {"pptx", "ppt", "key"}


# ---------------------------------------------------------------- small helpers

def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm(s):
    s = re.sub(r"\([^)]*\)", " ", s or "")
    s = s.replace("&", " and ").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def norm_file(name):
    """Normalized file stem plus extension, for matching Canvas names to vault names."""
    base, ext = os.path.splitext(name or "")
    base = re.sub(r"\s*\(\d+\)$", "", base)  # "file (1).pdf"
    base = base.replace("&", " and ").lower()
    base = re.sub(r"[^a-z0-9]+", " ", base)
    return " ".join(base.split()), ext.lower().lstrip(".")


def label_of(text):
    t = INLINE_FIELD.sub("", text)
    m = DATE_MENTION.search(t)
    if m and m.start() > 0:
        t = t[: m.start()]
    return t.strip(" ,;:-")


def fmt_time(d):
    h = d.hour % 12 or 12
    return f"{h}{':%02d' % d.minute if d.minute else ''} {'am' if d.hour < 12 else 'pm'}"


def fmt_day(d):
    return f"{d.strftime('%a')} {d.strftime('%b')} {d.day}"


def fmt_md(d):
    return f"{d.strftime('%b')} {d.day}"


def fmt_due(d):
    return f"{fmt_day(d)} {fmt_time(d)}"


def fmt_size(n):
    if n is None:
        return "?"
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB"
    return f"{max(1, round(n / 1024))} KB"


def parse_utc(s):
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return None


def safe_name(s):
    s = re.sub(r"[\\/:*?\"<>|#^\[\]]+", " ", s)
    return re.sub(r"\s+", " ", s).strip(" .")


def frontmatter(text):
    """Tiny YAML reader for the flat properties these notes use (scalars, [a, b] lists and '- item' lists)."""
    out = {}
    if not text or not text.startswith("---"):
        return out
    end = text.find("\n---", 3)
    if end < 0:
        return out
    key = None
    for line in text[3:end].split("\n"):
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                out[key] = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
            elif val == "":
                out[key] = []
            else:
                out[key] = val.strip("\"'")
        elif key and re.match(r"^\s+-\s+", line):
            if not isinstance(out.get(key), list):
                out[key] = []
            out[key].append(re.sub(r"^\s+-\s+", "", line).strip().strip("\"'"))
    return out


def section_bounds(lines, heading):
    h = heading.strip().lower()
    start = next((i for i, l in enumerate(lines) if l.strip().lower() == h), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#{1,2}\s", lines[i])), len(lines))
    return start, end


def read_tasks(lines, bounds):
    start, end = bounds
    tasks = []
    for i in range(start + 1, end):
        m = TASK.match(lines[i])
        if not m:
            continue
        body = m.group(4)
        due = DUE.search(body)
        lab = label_of(body)
        tasks.append({"i": i, "checked": m.group(2).lower() == "x", "body": body, "due": due.group(1) if due else None,
                      "label": lab, "norm": norm(lab)})
    return tasks


def find_match(name, tasks, used):
    cn = norm(name)
    if not cn:
        return None
    for t in tasks:  # exact label first
        if t["i"] not in used and t["norm"] == cn:
            return t
    for t in tasks:  # the map's label starts with the Canvas name ("Financial Brief" ~ "Financial Brief (team), ...")
        if t["i"] not in used and t["norm"].startswith(cn + " ") and (len(cn.split()) >= 2 or len(cn) >= 8):
            return t
    for t in tasks:  # the Canvas name starts with the map's label
        if t["i"] not in used and len(t["norm"].split()) >= 2 and cn.startswith(t["norm"] + " "):
            return t
    return None


def is_done(a):
    s = a.get("submission") or {}
    return bool(s.get("submitted_at") or s.get("excused") or (s.get("state") == "graded" and s.get("score") is not None))


def redate(body, when, old_due, today):
    """Return body with its date text and [due::] field moved to `when` (a local datetime)."""
    new_date = when.date().isoformat()
    core = DUE.sub("", body)
    m = DATE_MENTION.search(core)
    if m:
        lead = ", " if m.group(0).lstrip().startswith(",") or m.start() > 0 else ""
        core = core[: m.start()] + lead + fmt_due(when) + core[m.end():]
    else:
        core = core.rstrip() + ", " + fmt_due(when)
    if old_due:
        old = dt.date.fromisoformat(old_due)
        core = core.rstrip() + f" (Canvas moved it from {fmt_day(old)}, noticed {fmt_day(today)})"
    return core.rstrip() + f" [due:: {new_date}]"


def undate(body, today):
    core = DUE.sub("", body).rstrip()
    return core + f" (Canvas has no due date as of {fmt_day(today)})"


def insert_dated(lines, bounds, new_line, date_iso):
    """Insert a task line into a section, before the first task dated later; else after the section's last list item."""
    start, end = bounds
    at = None
    for i in range(start + 1, end):
        m = ANY_DATE.search(lines[i]) if TASK.match(lines[i]) else None
        if m and m.group(1) > date_iso:
            at = i
            break
    if at is None:
        items = [i for i in range(start + 1, end) if LIST_ITEM.match(lines[i])]
        at = (items[-1] + 1) if items else start + 1
        if not items and at < len(lines) and lines[at].strip() == "":
            at += 1
    lines.insert(at, new_line)
    return at


# ---------------------------------------------------------------- class schedule

def load_breaks(vault):
    out = []
    d = os.path.join(vault, "13 Calendar", "Events")
    if not os.path.isdir(d):
        return out
    for n in os.listdir(d):
        if not n.endswith(".md"):
            continue
        fm = frontmatter(read_text(os.path.join(d, n)) or "")
        if str(fm.get("kind", "")).lower() == "break" and fm.get("date"):
            try:
                a = dt.date.fromisoformat(str(fm["date"])[:10])
                b = dt.date.fromisoformat(str(fm.get("end-date") or fm["date"])[:10])
                out.append((a, b))
            except ValueError:
                pass
    return out


def class_schedule(vault, course, tz, breaks):
    """List of class meeting datetimes (local) for a course, from its class note."""
    path = course.get("class")
    text = read_text(os.path.join(vault, path)) if path else None
    fm = frontmatter(text or "")
    try:
        start = dt.date.fromisoformat(str(fm.get("date"))[:10])
        end = dt.date.fromisoformat(str(fm.get("end-date"))[:10])
    except (TypeError, ValueError):
        return []
    days = fm.get("days") or []
    if isinstance(days, str):
        days = re.split(r"[\s,/]+", days)
    wd = {DAYMAP.get(str(x).strip().lower()[:3]) for x in days}
    wd.discard(None)
    hh, mm = 9, 0
    m = re.match(r"(\d{1,2}):(\d{2})", str(fm.get("start-time") or ""))
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
    skip = set()
    for s in fm.get("skip") or []:
        try:
            skip.add(dt.date.fromisoformat(str(s)[:10]))
        except ValueError:
            pass
    out = []
    d = start
    while d <= end:
        if d.weekday() in wd and d not in skip and not any(a <= d <= b for a, b in breaks):
            out.append(dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz))
        d += dt.timedelta(days=1)
    return out


def next_class(meetings, after):
    return next((m for m in meetings if m > after), None)


def week_class(meetings, week):
    """First meeting of course week N (week 1 = the week of the first meeting, counted Monday to Sunday)."""
    if not meetings:
        return None
    first = meetings[0].date() - dt.timedelta(days=meetings[0].weekday())
    for m in meetings:
        if (m.date() - first).days // 7 + 1 == week:
            return m
    return None


# ---------------------------------------------------------------- file sorting and text extraction

def week_of(text):
    """Week number in a file or folder name ("Week 3", "Course_Week 3 - Name"), or None."""
    m = re.search(r"(?:^|[^a-z0-9])week\s*(\d{1,2})(?!\d)", (text or "").replace("_", " "), re.I)
    return int(m.group(1)) if m else None


def categorize(f):
    name = f.get("name") or ""
    folder = (f.get("folder") or "").strip()
    stem, ext = norm_file(name)
    low_folder = folder.lower()
    sub = ""
    wk = week_of(f"{folder} {name}")
    if re.search(r"lecture|slide|class session|deck", low_folder):
        cat = "02"
        cs = re.search(r"class sessions?/(\d{1,2})", low_folder)
        if cs:
            sub = f"Class {int(cs.group(1)):02d}"
    elif re.search(r"reading|case|article|pre-?read", low_folder) and not re.search(r"syllab|calendar", stem):
        cat = "03"
    elif re.search(r"assignment|homework|project", low_folder):
        cat = "04"
        leaf = folder.split("/")[-1]
        leaf = re.sub(r"\s*assignments?$", "", leaf, flags=re.I).strip()
        if leaf and leaf.lower() not in ("assignments", "assignment"):
            sub = leaf
    elif re.search(r"exam|review|quiz", low_folder):
        cat = "06"
    elif re.search(r"syllab|course overview|course resources|course calendar|schedule|course information", stem):
        cat = "01"
    elif re.search(r"\b(exam|midterm|final|practice|solutions?|answer key|review)\b", stem):
        cat = "06"
    elif re.search(r"\b(reading|readings|article|chapter|case|pre ?read|podcast)\b", stem):
        cat = "03"
    elif re.search(r"\b(lecture|lectures|slides|deck|notes)\b", stem) or ext in DECK_EXT:
        cat = "02"
    elif re.search(r"\b(assignment|homework|problem set|template|instructions|rubric|memo|quiz prep)\b", stem):
        cat = "04"
    elif ext in ("xlsx", "xls", "xlsm", "csv"):
        cat = "05"
    elif wk and ext == "pdf":
        cat = "02"  # "Course Title_Week 3 - Instructor.pdf": weekly slides exported to PDF
    elif ext in ("pdf", "docx", "doc"):
        cat = "03"
    else:
        cat = "08"
    if cat == "03" and wk:
        sub = f"Week {wk}"
    return cat, sub


def deck_number(name):
    stem = os.path.splitext(name)[0].replace("_", " ")
    for pat, kind in ((r"lecture\s*notes?\s*#?\s*(\d{1,2})", "Lecture"), (r"lecture\s*#?\s*(\d{1,2})", "Lecture"),
                      (r"\bweek\s*(\d{1,2})", "Week"), (r"\bclass\s*(\d{1,2})", "Class"), (r"\bday\s*(\d{1,2})", "Day"),
                      (r"^\s*(\d{1,2})\s+[A-Za-z]", "Lecture")):
        m = re.search(pat, stem, re.I)
        if m:
            return kind, int(m.group(1))
    return None, None


def _xml(z, name):
    try:
        return ET.fromstring(z.read(name))
    except (KeyError, ET.ParseError):
        return None


A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def para_text(para):
    """Text of one slide paragraph. A soft line break (<a:br>) counts as a space."""
    parts = []
    for x in para.iter():
        if x.tag == A + "t":
            parts.append(x.text or "")
        elif x.tag == A + "br":
            parts.append(" ")
    return re.sub(r" {2,}", " ", "".join(parts)).strip()


def extract_pptx(path):
    """[{n, title, lines:[(level, text)], links:[url]}] in slide order, using only the standard library."""
    slides = []
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError):
        return slides
    pres = _xml(z, "ppt/presentation.xml")
    rels = _xml(z, "ppt/_rels/presentation.xml.rels")
    order = []
    if pres is not None and rels is not None:
        rmap = {r.get("Id"): r.get("Target") for r in rels.iter(PR + "Relationship") if r.get("Type", "").endswith("/slide")}
        for sld in pres.iter(P + "sldId"):
            tgt = rmap.get(sld.get(R + "id"))
            if tgt:
                t = tgt.lstrip("/")
                order.append(t if t.startswith("ppt/") else "ppt/" + t)
    if not order:
        order = sorted([n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)], key=lambda n: int(re.findall(r"\d+", n)[-1]))
    for n, name in enumerate(order, 1):
        root = _xml(z, name)
        if root is None:
            continue
        title, lines = "", []
        for sp in root.iter():
            if sp.tag not in (P + "sp", P + "graphicFrame"):
                continue
            ph = sp.find(f".//{P}nvPr/{P}ph")
            is_title = ph is not None and ph.get("type") in ("title", "ctrTitle")
            tbl = sp.find(f".//{A}tbl")
            if tbl is not None:
                for tr in tbl.iter(A + "tr"):
                    cells = [" ".join(para_text(p_) for p_ in tc.iter(A + "p")).strip()
                             for tc in tr.iter(A + "tc")]
                    cells = [x_ for x_ in cells if x_]
                    if cells:
                        lines.append((0, " · ".join(cells)))
                continue
            for para in sp.iter(A + "p"):
                t = para_text(para)
                if not t:
                    continue
                ppr = para.find(A + "pPr")
                lvl = int(ppr.get("lvl", "0")) if ppr is not None else 0
                if is_title:
                    title = (title + " " + t).strip() if title else t
                else:
                    lines.append((lvl, t))
        links = []
        rel_name = name.replace("slides/", "slides/_rels/") + ".rels"
        rr = _xml(z, rel_name)
        if rr is not None:
            for r in rr.iter(PR + "Relationship"):
                if r.get("Type", "").endswith("/hyperlink") and r.get("TargetMode") == "External":
                    u = r.get("Target") or ""
                    if u.startswith("http") and u not in links:
                        links.append(u)
        slides.append({"n": n, "title": title, "lines": lines, "links": links})
    return slides


def extract_pdf(path):
    pages = []
    if shutil.which("pdftotext"):
        try:
            out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=60).stdout
            pages = [p for p in out.split("\f")]
        except (subprocess.SubprocessError, OSError):
            pages = []
    if not pages:
        try:
            import pypdf  # optional
            pages = [p.extract_text() or "" for p in pypdf.PdfReader(path).pages]
        except Exception:  # noqa: BLE001 - extraction is best effort
            pages = []
    slides = []
    for n, txt in enumerate(pages, 1):
        rows = [re.sub(r"\s{2,}", "  ", l).strip() for l in txt.split("\n")]
        rows = [r for r in rows if r and not re.fullmatch(r"\d{1,3}", r)]
        if not rows and n == len(pages):
            continue
        slides.append({"n": n, "title": rows[0] if rows else "", "lines": [(0, r) for r in rows[1:]], "links": []})
    return slides


def extract_docx_links(path):
    out = []
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError):
        return out
    rels = _xml(z, "word/_rels/document.xml.rels")
    rmap = {r.get("Id"): r.get("Target") for r in rels.iter(PR + "Relationship")} if rels is not None else {}
    doc = _xml(z, "word/document.xml")
    if doc is None:
        return out
    for h in doc.iter(W + "hyperlink"):
        url = rmap.get(h.get(R + "id"))
        t = "".join(x.text or "" for x in h.iter(W + "t")).strip()
        if url and url.startswith("http"):
            out.append((t or url, url))
    return out


def deck_topic(slides, stem):
    if slides:
        first = [slides[0]["title"]] + [t for _, t in slides[0]["lines"][:4]]
        for t in first:
            m = re.match(r"^\s*(?:lecture\s*)?\d{1,2}\s*[.):-]\s*(.+)$", t, re.I)
            if m and len(m.group(1)) > 3:
                return m.group(1).strip()
        cand = [t for t in first if t and len(t) > 3]
        if len(cand) >= 2:
            return cand[-1].strip()
        if cand:
            return cand[0].strip()
    return re.sub(r"[_]+", " ", stem).strip()


def md_escape(t):
    return t.replace("\n", " ").replace("|", "\\|").strip()


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canvas", required=True)
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=os.path.join(HERE, "courses.json"))
    ap.add_argument("--downloads")
    ap.add_argument("--backfill-notes", default="")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--now")
    args = ap.parse_args()

    cfg = load_json(args.config, None)
    if not cfg:
        sys.exit(f"missing config {args.config}")
    try:
        tz = ZoneInfo(cfg.get("timezone") or "UTC")
    except Exception:  # unknown name, or no time zone database (Windows without the tzdata package)
        tz = dt.datetime.now().astimezone().tzinfo
    now = dt.datetime.fromisoformat(args.now).replace(tzinfo=tz) if args.now else dt.datetime.now(tz)
    today = now.date()
    ignore = [re.compile(p, re.I) for p in cfg.get("ignore", [])]
    skip_pats = [re.compile(p, re.I) for p in cfg.get("skip_files", [])]
    skip_ext = {e.lower() for e in cfg.get("skip_extensions", [])}
    backfill = {c.strip() for c in args.backfill_notes.split(",") if c.strip()}
    stamp_created = now.strftime("%Y-%m-%dT%H:%M")

    raw = load_json(args.canvas, None)
    if raw is None:
        sys.exit(f"missing canvas data {args.canvas}")
    hosts = raw.get("hosts", []) if isinstance(raw, dict) else raw
    by_course, host_status, host_version = {}, {}, {}
    for h in hosts:
        host = h.get("host", "?")
        host_status[host] = bool(h.get("logged_in"))
        host_version[host] = h.get("version", 1)
        for cid, c in (h.get("courses") or {}).items():
            by_course[str(cid)] = {**c, "_host": host}

    manifest = load_json(os.path.join(args.vault, "vault_manifest.json"), {})
    old_state = load_json(os.path.join(args.vault, STATE_PATH), {"version": 1, "courses": {}})
    state = {"version": 2, "last_run": now.isoformat(timespec="minutes"), "courses": {}}
    breaks = load_breaks(args.vault)

    notes = {}  # vault path -> {"before": text or None, "lines": [...], "edits": [...]}

    def note(path):
        if path not in notes:
            before = read_text(os.path.join(args.vault, path))
            notes[path] = {"before": before, "lines": before.split("\n") if before is not None else None, "edits": []}
        return notes[path]

    report_changes, attention, imports, prep_added, notes_created = [], [], [], [], []
    present_all = set()
    new_ann, new_files, new_events, new_links, watch_lines = [], [], [], [], []
    counts = {"added": 0, "moved": 0, "checked": 0, "undated": 0, "imported": 0, "updated_files": 0, "prep": 0, "lecture_notes": 0}
    os.makedirs(os.path.join(args.out, "files"), exist_ok=True)

    for course in cfg.get("courses", []) + [dict(w, watch=True) for w in cfg.get("watch_only", [])]:
        cid, code = str(course["id"]), course["code"]
        c = by_course.get(cid)
        prev = old_state.get("courses", {}).get(cid)
        if c is None:
            attention.append(f"{code}: no Canvas data (host {course['host']} {'logged in' if host_status.get(course['host']) else 'not logged in or not fetched'}).")
            if prev:
                state["courses"][cid] = prev
            continue
        errs = {k: v for k, v in (c.get("errors") or {}).items() if not (k in ("files", "events", "modules") and v in (401, 403, 404))}
        if errs:  # a hidden Files page (401/403/404) is normal and not worth a flag
            attention.append(f"{code}: Canvas returned errors for {', '.join(f'{k} ({v})' for k, v in errs.items())}.")

        assignments = []
        for a in c.get("assignments", []):
            if not a.get("published", True) or any(p.search(a.get("name", "")) for p in ignore):
                continue
            due = parse_utc(a.get("due_at"))
            assignments.append({**a, "_due": due.astimezone(tz) if due else None, "_done": is_done(a)})

        # ---- seen announcements, files, events, module items and pages
        first_sight = prev is None
        seen = {k: set(map(str, (prev or {}).get(k, []))) for k in ("seen_announcements", "seen_files", "seen_events", "seen_links")}
        upgrading = (prev or {}).get("v", 1) < 2  # first run of v2 for this course: module items and pages count as seen
        cutoff = now - dt.timedelta(days=NEW_WINDOW_DAYS)
        for x in c.get("announcements", []):
            xid = str(x["id"])
            posted = parse_utc(x.get("posted_at"))
            fresh = first_sight and posted and posted >= cutoff
            if xid not in seen["seen_announcements"] and not args.init and (fresh or not first_sight):
                new_ann.append((code, x))
            seen["seen_announcements"].add(xid)
        files_new_ids = set()
        for x in c.get("files", []):
            # a re-uploaded file counts as new; modified_at only changes with the contents (updated_at also moves on
            # metadata changes such as publishing or renaming)
            xid = f"{x['id']}@{x.get('modified_at') or x.get('updated_at') or ''}"
            legacy = f"{x['id']}@{x.get('updated_at') or ''}"  # how version 1 recorded it
            if xid not in seen["seen_files"] and legacy not in seen["seen_files"] and not args.init and not first_sight:
                files_new_ids.add(str(x["id"]))
                new_files.append((code, x))
            seen["seen_files"].add(xid)
        for x in c.get("events", []):
            xid = str(x["id"])
            if xid not in seen["seen_events"] and not args.init and not first_sight:
                new_events.append((code, x))
            seen["seen_events"].add(xid)
        for m in c.get("modules", []):
            for i in m.get("items", []):
                if i.get("type") not in ("ExternalUrl", "Page", "File", "ExternalTool"):
                    continue
                xid = f"module-item {i['id']}"
                if xid not in seen["seen_links"] and not args.init and not first_sight and not upgrading:
                    new_links.append((code, f"Module \"{m.get('name')}\": {i.get('type')} \"{i.get('title')}\"", i.get("url") or ""))
                seen["seen_links"].add(xid)
        for p in c.get("pages", []):
            xid = f"page {p.get('url')}@{p.get('updated_at')}"
            if xid not in seen["seen_links"] and not args.init and not first_sight and not upgrading:
                new_links.append((code, f"Page \"{p.get('title')}\" (updated)", p.get("html_url") or ""))
            seen["seen_links"].add(xid)

        prev_assign = (prev or {}).get("assignments", {})
        imported_prev = dict((prev or {}).get("imported_files", {}))
        cstate = {
            "code": code, "v": 2,
            "seen_announcements": sorted(seen["seen_announcements"])[-400:],
            "seen_files": sorted(seen["seen_files"])[-600:],
            "seen_events": sorted(seen["seen_events"])[-600:],
            "seen_links": sorted(seen["seen_links"])[-600:],
            "assignments": {str(a["id"]): {"name": a["name"], "due_at": a.get("due_at"), "done": a["_done"]} for a in assignments},
            "imported_files": imported_prev,
            "skipped_files": (prev or {}).get("skipped_files", []),
        }
        state["courses"][cid] = cstate

        for a in assignments:
            s = a.get("submission") or {}
            if s.get("missing") and a["_due"] and (today - a["_due"].date()).days <= 21 and not a["_done"]:
                attention.append(f"{code}: Canvas marks \"{a['name']}\" missing (due {fmt_due(a['_due'])}).")

        # ---- course files: what's on Canvas but not in the vault
        folder = course.get("folder")
        vault_files = manifest.get(folder, []) if folder else []
        by_size = {}
        by_name = {}
        for vf in vault_files:
            stem, ext = norm_file(os.path.basename(vf["path"]))
            by_size.setdefault((vf["size"], ext), []).append(vf)
            by_name.setdefault((stem, ext), []).append(vf)
        canvas_files = []
        seen_ids = set()
        for x in c.get("files", []):
            if str(x["id"]) in seen_ids:
                continue
            seen_ids.add(str(x["id"]))
            canvas_files.append(x)
        missing = []
        present_ids = set()
        if folder and manifest:
            for x in canvas_files:
                name = x.get("name") or ""
                stem, ext = norm_file(name)
                if x.get("locked") or ext in skip_ext or any(p.search(name) for p in skip_pats) \
                        or str(x["id"]) in map(str, cstate["skipped_files"]):
                    continue
                if not ext and "." not in name:
                    ext = {"application/pdf": "pdf"}.get(x.get("content_type", ""), "")
                same_size = by_size.get((x.get("size"), ext), [])
                same_name = by_name.get((stem, ext), [])
                if same_size:
                    present_ids.add(str(x["id"]))
                    up = parse_utc(x.get("modified_at") or x.get("updated_at"))
                    newest = max(v["mtime"] for v in same_size)
                    if str(x["id"]) in files_new_ids and up and up.timestamp() > newest + 60 and not first_sight:
                        attention.append(f"{code}: Canvas re-uploaded \"{name}\" ({fmt_day(up.astimezone(tz))}) with the same size as the vault copy "
                                         f"({same_size[0]['path']}). Download it and compare sha256 with the vault copy; if they differ, import it as an update.")
                    continue  # already in the vault (maybe under another name)
                done = imported_prev.get(str(x["id"]))
                if done and done in (x.get("modified_at"), x.get("updated_at")):
                    continue  # imported before; the user may have moved or renamed it
                if same_name:
                    vf = sorted(same_name, key=lambda v: v["mtime"])[-1]
                    if "/older versions/" in vf["path"].lower():
                        pass
                    else:
                        up = parse_utc(x.get("modified_at") or x.get("updated_at"))
                        if up and up.timestamp() > vf["mtime"]:
                            missing.append((x, "updated", vf))
                        else:
                            attention.append(f"{code}: \"{name}\" on Canvas differs in size from the vault copy ({vf['path']}), but the vault copy is newer, so it wasn't replaced.")
                        continue
                missing.append((x, "new", None))
        elif not course.get("watch"):
            if folder:
                attention.append(f"{code}: vault_manifest.json has no listing for {folder}, so files weren't compared.")
        present_all.update(f"{cid}:{i}" for i in present_ids)

        if course.get("watch"):
            for x, why, _ in missing:
                watch_lines.append(f"{code}: Canvas file \"{x.get('name')}\" ({fmt_size(x.get('size'))}) isn't in `{folder}` ({why}); copy it there if it's needed.")
            for a in assignments:
                p = prev_assign.get(str(a["id"]))
                if a["_due"] and a["_due"].date() >= today and not a["_done"] and (p is None or p.get("due_at") != a.get("due_at")):
                    what = "new" if p is None else "date changed"
                    watch_lines.append(f"{code}: {a['name']}, {fmt_due(a['_due'])} [due:: {a['_due'].date().isoformat()}] ({what}; add it to [[{os.path.splitext(os.path.basename(course['note']))[0]}]] if it isn't there)")
            continue

        meetings = class_schedule(args.vault, course, tz, breaks)

        # ---- plan imports, Materials entries, prep tasks and lecture notes
        mat_path = course.get("materials")
        prep_path = course.get("prep")
        map_path = course.get("map")
        materials = note(mat_path) if mat_path else None
        prep = note(prep_path) if prep_path else None
        dl = args.downloads

        def downloaded(fid, name):
            if not dl:
                return None
            p = os.path.join(dl, str(fid), name)
            return p if os.path.isfile(p) else None

        def companion_for(deck_name):
            """Existing lecture note (vault path) whose source links this deck."""
            for vf in vault_files:
                if not vf["path"].endswith(".md"):
                    continue
                t = read_text(os.path.join(args.vault, vf["path"])) or ""
                fm = frontmatter(t)
                if deck_name in str(fm.get("source", "")):
                    return vf["path"]
            for path, n in notes.items():
                if n["before"] is None and n["lines"] and deck_name in "\n".join(n["lines"][:15]):
                    return path
            return None

        planned = []  # (canvas file, reason, old vault file, dest path)
        for x, why, old in missing:
            cat, sub = categorize(x)
            if why == "updated":
                dest = old["path"]
                base, ext = os.path.splitext(os.path.basename(old["path"]))
                older = os.path.join(os.path.dirname(old["path"]), "Older versions",
                                     f"{base} (before {today.isoformat()}){ext}")
            else:
                dest = os.path.join(folder, CATEGORY[cat], sub, x["name"]) if sub else os.path.join(folder, CATEGORY[cat], x["name"])
                older = None
            planned.append((x, why, old, dest, cat))
            imports.append({"course": code, "host": c["_host"], "file_id": x["id"], "name": x["name"], "size": x.get("size"),
                            "updated_at": x.get("updated_at"), "dest": dest, "category": CATEGORY[cat], "reason": why,
                            "replaces": old["path"] if old else None, "replaces_to": older, "via": x.get("via", "files")})
            counts["imported" if why == "new" else "updated_files"] += 1
            cstate["imported_files"][str(x["id"])] = x.get("modified_at") or x.get("updated_at")

        # backfill lecture notes for decks already in the vault
        backfill_decks = []
        if code in backfill and dl:
            for x in canvas_files:
                stem, ext = norm_file(x.get("name") or "")
                if any(p[0] is x for p in planned):
                    continue
                cat, _ = categorize(x)
                if cat != "02" or not downloaded(x["id"], x["name"]):
                    continue
                hit = by_size.get((x.get("size"), ext), [])
                if hit and not companion_for(x["name"]):
                    backfill_decks.append((x, hit[0]["path"]))

        def lecture_note(x, deck_path, src):
            """Plan a lecture note next to the deck. Returns (note path, title, slide count, topic)."""
            stem, ext = norm_file(x["name"])
            slides = extract_pptx(src) if ext == "pptx" else extract_pdf(src) if ext == "pdf" else []
            if not slides:
                return None
            kind, num = deck_number(x["name"])
            topic = deck_topic(slides, os.path.splitext(x["name"])[0])
            topic = re.sub(r"^\s*(?:lecture(?:\s*notes?)?|week|class|day)\s*#?\s*\d+\s*[:.\-\u2013\u2014]?\s*", "", topic, flags=re.I) or topic
            topic = topic[:1].upper() + topic[1:]
            label = f"{kind} {num}" if kind else None
            title = safe_name(f"{code} - {label} - {topic}" if label else f"{code} - {topic}")[:120]
            path = os.path.join(os.path.dirname(deck_path), title + ".md")
            posted = parse_utc(x.get("created_at") or x.get("updated_at"))
            posted_l = posted.astimezone(tz) if posted else now
            nxt = next_class(meetings, posted_l)
            slug = code.lower().replace(" ", "-")
            unit = "slides" if ext == "pptx" else "pages"
            links = []
            for s in slides:
                for u in s["links"]:
                    links.append((s["n"], u))
            out = ["---", "type: literature", f"course: \"[[{code} MOC]]\""]
            if num is not None:
                out.append(f"{kind.lower()}: {num}")
            out += [f"topic: \"{topic.replace(chr(34), chr(39))}\"", f"source: \"[[{x['name']}]]\"", f"posted: {posted_l.date().isoformat()}"]
            if nxt:
                out.append(f"class-date: {nxt.date().isoformat()}")
            out += [f"{unit}: {len(slides)}",
                    f"summary: \"Outline of {os.path.splitext(x['name'])[0]} for {code} ({topic.replace(chr(34), chr(39))}): searchable slide text, key ideas and space for class notes.\"",
                    f"created: {stamp_created}", "cssclasses:", "  - course-note", f"  - course-{slug}", "tags:", "  - literature",
                    f"  - course/{slug}", "  - ai-assisted", "---",
                    f"# {code} · {label + ' · ' if label else ''}{topic}", "",
                    f"← [[{os.path.splitext(os.path.basename(mat_path))[0]}]] · [[{code} MOC]] · [[{os.path.splitext(os.path.basename(prep_path))[0]}]]", "",
                    f"**Deck:** [[{x['name']}|{os.path.splitext(x['name'])[0]}]] · {len(slides)} {unit} · posted on Canvas {fmt_day(posted_l)}"
                    + (f" · first class after posting: {fmt_day(nxt)}" if nxt else ""), "",
                    "## Key ideas", "> [!ai] Key ideas (AI draft)", "> - KEY-IDEAS-PLACEHOLDER", "",
                    "## My notes", "- ", "",
                    "## Slide outline",
                    f"Text copied from the {'deck' if ext == 'pptx' else 'PDF'} so it's searchable in Obsidian. Charts, images and tables aren't copied; the {'deck' if ext == 'pptx' else 'PDF'} is the authority.", ""]
            for s in slides:
                head = md_escape(s["title"]) or (md_escape(s["lines"][0][1]) if s["lines"] else "")
                out.append(f"### {s['n']}. {head[:150]}")
                body = s["lines"] if s["title"] else s["lines"][1:]
                for lvl, t in body[:40]:
                    out.append(f"{'  ' * min(lvl, 3)}- {md_escape(t)}")
                out.append("")
            if links:
                out += ["## Links in the deck"] + [f"- {unit[:-1].capitalize()} {n}: <{u}>" for n, u in links] + [""]
            out += ["> [!info] Source", f"> Made by the Canvas sync on {fmt_day(now)}, {now.year} from the Canvas file. Edit freely; the sync never rewrites this note.", ""]
            n = note(path)
            if n["before"] is not None:
                return None
            n["lines"] = out
            n["edits"].append({"kind": "lecture-note", "title": title})
            notes_created.append(f"{code}: [[{title}]] ({len(slides)} {unit})")
            counts["lecture_notes"] += 1
            return path, title, len(slides), topic

        def materials_entry(x, cat, ln, why, dest):
            stem, ext = norm_file(x["name"])
            kindname = KIND_NAME.get(ext, ext.upper() or "File")
            posted = parse_utc(x.get("updated_at") if why == "updated" else (x.get("created_at") or x.get("updated_at")))
            posted_l = posted.astimezone(tz) if posted else now
            bits = [f"{kindname}, {fmt_size(x.get('size'))}" + (f", {ln[2]} {'slides' if ext == 'pptx' else 'pages'}" if ln else "")]
            if ln:
                kind, num = deck_number(x["name"])
                topic = ln[3][:1].lower() + ln[3][1:]
                bits.append(f"{kind} {num}: {topic}" if kind else ln[3])
            bits.append(f"{'updated' if why == 'updated' else 'posted'} on Canvas {fmt_md(posted_l)}")
            if ln:
                bits.append(f"notes: [[{ln[1]}]]")
            sub = os.path.relpath(os.path.dirname(dest), folder)
            where = f" (in `{sub}`)" if sub.count("/") >= 1 else ""
            return f"- [[{x['name']}|{os.path.splitext(x['name'])[0]}]] · " + " · ".join(bits) + where

        def add_materials(x, cat, ln, why, dest):
            if not materials or materials["lines"] is None:
                attention.append(f"{code}: Materials note {mat_path} not found; list \"{x['name']}\" there by hand.")
                return
            lines = materials["lines"]
            if any(f"[[{x['name']}" in l for l in lines):
                for i, l in enumerate(lines):
                    if f"[[{x['name']}" in l and why == "updated" and "updated on Canvas" not in l:
                        posted = parse_utc(x.get("updated_at"))
                        lines[i] = l.rstrip() + f" · updated on Canvas {fmt_md(posted.astimezone(tz)) if posted else ''} (older copy in `Older versions`)"
                        materials["edits"].append({"kind": "materials-updated", "file": x["name"]})
                    elif f"[[{x['name']}" in l and ln and "notes: [[" not in l:
                        lines[i] = l.rstrip() + f" · notes: [[{ln[1]}]]"
                        materials["edits"].append({"kind": "materials-notes-link", "file": x["name"]})
                return
            entry = materials_entry(x, cat, ln, why, dest)
            src = downloaded(x["id"], x["name"])
            if src and src.lower().endswith(".docx"):
                found = extract_docx_links(src)[:40]
                if found:
                    entry += "\n" + "\n".join(f"  - [{md_escape(t).replace('[', '(').replace(']', ')')}]({u})" for t, u in found)
            b = section_bounds(lines, SECTION[cat])
            if b is None:
                anchor = next((i for i, l in enumerate(lines) if l.startswith("**Empty for now:**") or l.startswith("## Not included")
                               or l.startswith("> [!info] Source") or l.startswith("← [[School Library]]")), len(lines))
                lines[anchor:anchor] = [SECTION[cat], "", entry, ""]
            else:
                s, e = b
                items = [i for i in range(s + 1, e) if LIST_ITEM.match(lines[i])]
                at = (items[-1] + 1) if items else s + 2
                if not items and (s + 1 >= len(lines) or lines[s + 1].strip() != ""):
                    lines.insert(s + 1, "")
                    at = s + 2
                lines.insert(at, entry)
            for i, l in enumerate(lines):  # the folder isn't empty any more
                if l.startswith("**Empty for now:**") and f"`{CATEGORY[cat]}`" in l:
                    rest = [t for t in re.findall(r"`[^`]+`", l) if t != f"`{CATEGORY[cat]}`"]
                    lines[i] = ("**Empty for now:** " + " · ".join(rest) + ". Save new files for this course into the matching folder.") if rest else "Save new files for this course into the matching folder."
            materials["edits"].append({"kind": "materials-added", "file": x["name"]})

        def add_prep(x, cat, ln, why):
            if why != "new" or not prep or prep["lines"] is None:
                return
            stem, ext = norm_file(x["name"])
            is_deck = cat == "02"
            if is_deck and not course.get("slides_are_prep"):
                return
            if cat not in ("02", "03"):
                return
            posted = parse_utc(x.get("created_at") or x.get("updated_at"))
            posted_l = posted.astimezone(tz) if posted else now
            if (now - posted_l).days > PREP_WINDOW_DAYS:
                return
            wk = week_of(f"{x.get('folder', '')} {x['name']}")
            when = week_class(meetings, wk) if (wk and not is_deck) else None
            if when is None or when < posted_l:
                when = next_class(meetings, posted_l)
            if when is None or when.date() < today:
                return
            lines = prep["lines"]
            joined = "\n".join(lines)
            mapt = note(map_path)["lines"] if map_path else None
            if f"[[{x['name']}" in joined or (mapt and f"[[{x['name']}" in "\n".join(mapt)):
                return
            disp = os.path.splitext(x["name"])[0]
            if is_deck:
                kind, num = deck_number(x["name"])
                short = f"{'Lecture Notes' if 'notes' in stem else kind or 'Slides'} {num}" if num is not None else disp
                topic = f" ({ln[3][:1].lower() + ln[3][1:]})" if ln else ""
                text = f"Read [[{x['name']}|{short}]]{topic} before class" + (f" · [[{ln[1]}|notes]]" if ln else "")
            elif re.search(r"reading (assignments?|list)|pre-?reads?", stem):
                w = f"Week {wk} " if wk else ""
                text = f"{w}pre-reads: everything on the [[{x['name']}|reading list]]"
            else:
                text = f"Read [[{x['name']}|{disp}]]"
            date_iso = when.date().isoformat()
            new_line = f"- [ ] {text} (posted {fmt_md(posted_l)}) [due:: {date_iso}]"
            # a placeholder like "Week 3 pre-reads ... (tentative)" is rewritten instead of adding a second task
            if wk and not is_deck:
                for i, l in enumerate(lines):
                    m = TASK.match(l)
                    if m and m.group(2) == " " and "tentative" in l.lower() and week_of(l) == wk:
                        d = ANY_DATE.search(l)
                        keep = d.group(1) if d else date_iso
                        lines[i] = f"- [ ] {text} (posted {fmt_md(posted_l)}) [due:: {keep}]"
                        prep["edits"].append({"kind": "prep-placeholder", "task": text, "to": keep})
                        prep_added.append(f"{code}: {text} → {fmt_day(dt.date.fromisoformat(keep))} (replaced the tentative placeholder)")
                        counts["prep"] += 1
                        return
            b = section_bounds(lines, "## Before class")
            if b is None:
                anchor = next((i for i, l in enumerate(lines) if l.strip().lower() in ("## no date yet", "## sources")), len(lines))
                lines[anchor:anchor] = ["## Before class", ""]
                b = section_bounds(lines, "## Before class")
            insert_dated(lines, b, new_line, date_iso)
            prep["edits"].append({"kind": "prep", "task": text, "to": date_iso})
            shown = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", text)
            prep_added.append(f"{code}: {shown} → {fmt_day(when)}, before the {fmt_time(when)} class")
            counts["prep"] += 1

        def add_map_note_pointer(ln):
            if not map_path or not ln:
                return
            mp = note(map_path)
            if mp["lines"] is None:
                return
            b = section_bounds(mp["lines"], "## Notes")
            if b is None or any(f"[[{ln[1]}]]" in l for l in mp["lines"]):
                return
            s, e = b
            items = [i for i in range(s + 1, e) if LIST_ITEM.match(mp["lines"][i])]
            at = (items[-1] + 1) if items else s + 1
            mp["lines"].insert(at, f"- [[{ln[1]}]] · lecture outline and space for your notes (added by Canvas sync {fmt_md(now)})")
            mp["edits"].append({"kind": "notes-pointer", "note": ln[1]})

        for x, deck_path in sorted(backfill_decks, key=lambda b: b[0]["name"]):
            ln = lecture_note(x, deck_path, downloaded(x["id"], x["name"]))
            if ln:
                add_materials(x, "02", ln, "present", deck_path)
                add_map_note_pointer(ln)
        for x, why, old, dest, cat in planned:
            src = downloaded(x["id"], x["name"])
            ln = None
            if src and cat == "02":
                ln = lecture_note(x, dest, src)
            add_materials(x, cat, ln, why, dest)
            add_prep(x, cat, ln, why)
            add_map_note_pointer(ln)
            if why == "new":
                report_changes.append(f"{code}: import \"{x['name']}\" → `{dest}`")
            else:
                report_changes.append(f"{code}: Canvas has a newer \"{x['name']}\"; import it to `{dest}` after moving the vault copy to `Older versions`")

        # ---- course map deadlines (unchanged from v1)
        path = map_path
        full = os.path.join(args.vault, path)
        if not os.path.exists(full):
            attention.append(f"{code}: course map {path} not found.")
            continue
        mp = note(path)
        lines = mp["lines"]
        if section_bounds(lines, HEADING) is None:
            attention.append(f"{code}: {path} has no \"## Upcoming deadlines\" section, so nothing was changed there.")
            continue
        edits, used = [], set()
        tasks = read_tasks(lines, section_bounds(lines, HEADING))
        unmatched = []
        for a in sorted(assignments, key=lambda a: -len(norm(a["name"]))):
            t = find_match(a["name"], tasks, used)
            if t is None:
                unmatched.append(a)
                continue
            used.add(t["i"])
            if t["checked"]:
                continue
            m = TASK.match(lines[t["i"]])
            if a["_done"]:
                lines[t["i"]] = f"{m.group(1)}x{m.group(3)}{m.group(4)}"
                edits.append({"kind": "checked", "task": t["label"], "detail": "Canvas shows it submitted or graded"})
                counts["checked"] += 1
            elif a["_due"] and t["due"] != a["_due"].date().isoformat():
                lines[t["i"]] = f"{m.group(1)}{m.group(2)}{m.group(3)}{redate(m.group(4), a['_due'], t['due'], today)}"
                edits.append({"kind": "moved", "task": t["label"], "from": t["due"], "to": a["_due"].date().isoformat()})
                counts["moved"] += 1
            elif not a["_due"] and t["due"]:
                lines[t["i"]] = f"{m.group(1)}{m.group(2)}{m.group(3)}{undate(m.group(4), today)}"
                edits.append({"kind": "undated", "task": t["label"], "from": t["due"]})
                counts["undated"] += 1
        for a in sorted(unmatched, key=lambda a: (a["_due"] or now)):
            if not a["_due"] or a["_due"].date() < today or a["_done"]:
                continue
            new_line = f"- [ ] {a['name']}, {fmt_due(a['_due'])} [due:: {a['_due'].date().isoformat()}]"
            start, end = section_bounds(lines, HEADING)
            current = read_tasks(lines, (start, end))
            later = [t for t in current if t["due"] and t["due"] > a["_due"].date().isoformat()]
            if later:
                at = later[0]["i"]
            else:
                items = [i for i in range(start + 1, end) if LIST_ITEM.match(lines[i])]
                at = (items[-1] + 1) if items else start + 1
            lines.insert(at, new_line)
            edits.append({"kind": "added", "task": a["name"], "to": a["_due"].date().isoformat(), "line": new_line})
            counts["added"] += 1
        mp["edits"] += edits
        for e in edits:
            if e["kind"] == "added":
                report_changes.append(f"{code}: added \"{e['task']}\", due {fmt_day(dt.date.fromisoformat(e['to']))}")
            elif e["kind"] == "moved":
                frm = fmt_day(dt.date.fromisoformat(e["from"])) if e.get("from") else "no date"
                report_changes.append(f"{code}: moved \"{e['task']}\" from {frm} to {fmt_day(dt.date.fromisoformat(e['to']))}")
            elif e["kind"] == "checked":
                report_changes.append(f"{code}: checked off \"{e['task']}\" ({e['detail']})")
            else:
                report_changes.append(f"{code}: Canvas removed the due date for \"{e['task']}\" (was {fmt_day(dt.date.fromisoformat(e['from']))})")

    # ---- write the planned notes
    changes = []
    for path, n in sorted(notes.items()):
        if not n["edits"] or n["lines"] is None:
            continue
        after = "\n".join(n["lines"])
        if n["before"] is not None and after == n["before"]:
            continue
        out_file = os.path.join(args.out, "files", path)
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(after if after.endswith("\n") or n["before"] is not None else after + "\n")
        with open(out_file, encoding="utf-8") as f:
            written = f.read()
        changes.append({"path": path, "sha256_before": sha256(n["before"]) if n["before"] is not None else None,
                        "sha256_after": sha256(written), "new": n["before"] is None, "edits": n["edits"]})

    # ---- report
    stamp = f"{fmt_day(now)}, {now.year}, {fmt_time(now)}"
    hosts_line = " · ".join(f"{h} {'ok' if ok else 'NOT LOGGED IN'}" for h, ok in host_status.items()) or "no Canvas data"
    old_reader = [h for h, v in host_version.items() if v < 2]
    if old_reader:
        attention.append(f"Canvas data from {', '.join(old_reader)} came from the old reader (no folders, modules or linked files). Use fetch_canvas.js version 2.")
    r = [f"# Canvas sync plan · {stamp}", "", f"Canvas: {hosts_line}", ""]
    r += [f"## Course map and file changes ({len(report_changes)})"] + ([f"- {x}" for x in report_changes] or ["- None. The course maps and folders already match Canvas."]) + [""]
    r += [f"## Files to import ({len(imports)})"]
    if imports:
        r.append("sync.py plan downloads these with the access token. With the browser reader, download each one (file_links.js), then plan again with --downloads so lecture notes and slide counts are added.")
        for i in imports:
            r.append(f"- {i['course']}: {i['name']} ({fmt_size(i['size'])}, file {i['file_id']}) → `{i['dest']}`" + (f" (move `{i['replaces']}` to `{i['replaces_to']}` first)" if i["replaces"] else ""))
    else:
        r.append("- None.")
    r += ["", f"## Prep tasks added ({len(prep_added)})"] + ([f"- {x}" for x in prep_added] or ["- None."])
    r += ["", f"## Lecture notes created ({len(notes_created)})"]
    if notes_created:
        r.append("Fill the Key ideas callout in each one (3–5 short bullets from its outline) before writing it.")
    r += [f"- {x}" for x in notes_created] or ["- None."]
    r += ["", f"## New announcements ({len(new_ann)})",
          "Read each one. Add pre-class prep to the course's prep note, deadlines to the course map, and class changes to the calendar (see the skill). Skip anything already there.", ""]
    for code, x in new_ann:
        posted = parse_utc(x.get("posted_at"))
        when = f"{fmt_day(posted.astimezone(tz))} {fmt_time(posted.astimezone(tz))}" if posted else "?"
        r += [f"### {code} · {x.get('title', '').strip()} · {when}", f"<{x.get('url', '')}>", "", (x.get("text") or "").strip(), ""]
    if not new_ann:
        r += ["- None.", ""]
    r += [f"## New or updated files on Canvas ({len(new_files)})"]
    code_to_id = {c["code"]: str(c["id"]) for c in cfg.get("courses", []) + cfg.get("watch_only", [])}
    for code, x in new_files:
        up = parse_utc(x.get("updated_at"))
        where = " · already in the vault" if f"{code_to_id.get(code)}:{x['id']}" in present_all else ""
        where = where or (" · importing" if any(i["file_id"] == x["id"] for i in imports) else "")
        r.append(f"- {code}: {x.get('name')} ({fmt_day(up.astimezone(tz)) if up else '?'}){(' · folder ' + x['folder']) if x.get('folder') else ''}{where}")
    if not new_files:
        r.append("- None.")
    r += ["", f"## New readings and links in modules or pages ({len(new_links)})",
          "Readings posted as links don't arrive as files. Turn each reading into a task in the course's prep note, due before the class it's for."]
    r += [f"- {code}: {what} <{url}>" for code, what, url in new_links] or ["- None."]
    r += ["", f"## New Canvas calendar events ({len(new_events)})"]
    for code, x in new_events:
        st = parse_utc(x.get("start_at"))
        r.append(f"- {code}: {x.get('title')} · {fmt_due(st.astimezone(tz)) if st else 'no time'}{(' · ' + x['location']) if x.get('location') else ''}{(' · ' + x['text'][:200]) if x.get('text') else ''}")
    if not new_events:
        r.append("- None.")
    if watch_lines:
        r += ["", f"## Watched courses ({len(watch_lines)})"] + [f"- {x}" for x in watch_lines]
    r += ["", f"## Needs a look ({len(attention)})"] + ([f"- {x}" for x in attention] or ["- Nothing."])
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(r) + "\n")

    summary = {"run": now.isoformat(timespec="minutes"), "hosts": host_status, **counts,
               "changed_files": [c["path"] for c in changes], "imports": len(imports), "new_announcements": len(new_ann),
               "new_files": len(new_files), "new_links": len(new_links), "new_events": len(new_events), "watch": len(watch_lines),
               "attention": attention}
    bits = [f"{counts[k]} {label}" for k, label in (("added", "added"), ("moved", "moved"), ("checked", "checked off"), ("undated", "undated"),
                                                     ("imported", "file" + ("s" if counts["imported"] != 1 else "") + " imported"),
                                                     ("updated_files", "file" + ("s" if counts["updated_files"] != 1 else "") + " updated"),
                                                     ("lecture_notes", "lecture note" + ("s" if counts["lecture_notes"] != 1 else "")),
                                                     ("prep", "prep task" + ("s" if counts["prep"] != 1 else ""))) if counts[k]]
    state["summary"] = (", ".join(bits) if bits else "no changes") + (f"; {len(new_ann)} new announcement{'s' if len(new_ann) != 1 else ''}" if new_ann else "")
    with open(os.path.join(args.out, "changes.json"), "w", encoding="utf-8") as f:
        json.dump(changes, f, indent=2)
    with open(os.path.join(args.out, "imports.json"), "w", encoding="utf-8") as f:
        json.dump(imports, f, indent=2)
    with open(os.path.join(args.out, "state.json"), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
