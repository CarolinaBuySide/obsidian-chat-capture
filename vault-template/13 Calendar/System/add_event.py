#!/usr/bin/env python3
"""Add, change, cancel or list events in the Obsidian calendar (13 Calendar).

Any AI agent with a shell on the Mac uses this instead of hand-writing event notes.
Events appear in [[Weekly Calendar]]; every change gets one log line in [[Calendar MOC]].
Instructions for agents: 00 Home/Agent/Skills/Skill - Calendar Update.md

  cd "<your vault folder>"
  python3 "13 Calendar/System/add_event.py" add --title "Coffee chat with an analyst" \\
      --date 2026-10-14 --start 15:00 --end 15:30 --kind call --location Zoom \\
      --related "Prepare for internship recruiting" --source "2026-10-12 - Topic" --by perplexity
  python3 "13 Calendar/System/add_event.py" update "2026-10-14 - Coffee chat with an analyst" \\
      --date 2026-10-15 --start 14:00 --end 14:30 --note "moved by email"
  python3 "13 Calendar/System/add_event.py" cancel "2026-10-14 - Coffee chat with an analyst" --note "they cancelled"
  python3 "13 Calendar/System/add_event.py" list --from 2026-10-12 --to 2026-10-18

Times: "15:00", "3pm" or "3:30 pm", in your local time zone unless you converted them.
Writes files directly; if the shell may not write to the vault, it falls back to the
Obsidian Local REST API (key read from the plugin settings, never printed).
Standard library only. It never overwrites another note and never deletes anything.
"""
import argparse
import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VAULT = os.path.abspath(os.path.join(HERE, "..", ".."))
CAL_DIR = "13 Calendar"
EVENTS_DIR = "13 Calendar/Events"
LOG_NOTE = "04 Maps/Calendar MOC.md"
KINDS = ["class", "exam", "call", "meeting", "interview", "appointment", "club", "work",
         "personal", "travel", "break", "academic", "other"]
STATUSES = ["confirmed", "tentative", "cancelled"]
BAD_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]]')
DAYMAP = {"m": 1, "mo": 1, "mon": 1, "monday": 1, "t": 2, "tu": 2, "tue": 2, "tues": 2, "tuesday": 2,
          "w": 3, "we": 3, "wed": 3, "wednesday": 3, "r": 4, "th": 4, "thu": 4, "thur": 4, "thurs": 4,
          "thursday": 4, "f": 5, "fr": 5, "fri": 5, "friday": 5, "s": 6, "sa": 6, "sat": 6, "saturday": 6,
          "u": 7, "su": 7, "sun": 7, "sunday": 7}
STOP = set("the a an to of for and or in on at by with from your my our this that call meeting chat".split())


def die(msg, code=1):
    print(f"add_event: {msg}", file=sys.stderr)
    sys.exit(code)


# ---------- parsing and formatting ----------

def parse_date(s):
    s = (s or "").strip().lower()
    today = dt.date.today()
    if s == "today":
        return today.isoformat()
    if s == "tomorrow":
        return (today + dt.timedelta(days=1)).isoformat()
    try:
        return dt.date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        die(f"date must be YYYY-MM-DD, got {s!r}", 2)


def parse_time(s):
    if s is None or str(s).strip() == "":
        return None
    t = str(s).strip().lower().replace(".", "")
    if t == "noon":
        return "12:00"
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?", t)
    if not m:
        die(f"time must look like 15:00 or 3:30pm, got {s!r}", 2)
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if m.group(3):
        h = h % 12 + (12 if m.group(3).startswith("p") else 0)
    if h > 23 or mi > 59:
        die(f"invalid time {s!r}", 2)
    return f"{h:02d}:{mi:02d}"


def minutes(hhmm):
    if not hhmm:
        return None
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fmt_time(hhmm):
    h, m = map(int, hhmm.split(":"))
    ap = "pm" if h >= 12 else "am"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {ap}" if m else f"{h12} {ap}"


def fmt_range(start, end):
    if not start:
        return ""
    if not end:
        return fmt_time(start)
    a, b = fmt_time(start), fmt_time(end)
    if (minutes(start) >= 720) == (minutes(end) >= 720):
        a = re.sub(r" (am|pm)$", "", a)
    return f"{a}–{b}"


def when_text(date, end_date=None, start=None, end=None):
    d = dt.date.fromisoformat(date)
    if end_date and end_date != date:
        e = dt.date.fromisoformat(end_date)
        return f"{d:%a, %b} {d.day} – {e:%a, %b} {e.day}, {e.year}" + (f" · {fmt_range(start, end)}" if start else " (all day)")
    base = f"{d:%a, %b} {d.day}, {d.year}"
    return f"{base} · {fmt_range(start, end)}" if start else f"{base} (all day)"


def yq(s):
    return json.dumps(str(s), ensure_ascii=False)


def tokens(s):
    return {w for w in re.sub(r"[^a-z0-9 ]+", " ", s.lower()).split() if len(w) > 2 and w not in STOP}


def similar(a, b):
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return a.strip().lower() == b.strip().lower()
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.6


# ---------- frontmatter ----------

def split_fm(text):
    if not text.startswith("---"):
        return [], text
    lines = text.split("\n")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return [], text


def fm_dict(fm_lines):
    out, key = {}, None
    for line in fm_lines:
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


def fm_set(fm_lines, key, value_line):
    """Replace `key:` (and any block-list lines under it) with value_line, or insert before tags."""
    out, i, done = [], 0, False
    while i < len(fm_lines):
        line = fm_lines[i]
        if re.match(rf"^{re.escape(key)}:", line):
            i += 1
            while i < len(fm_lines) and re.match(r"^\s+-\s+", fm_lines[i]):
                i += 1
            if value_line is not None:
                out.append(value_line)
            done = True
            continue
        out.append(line)
        i += 1
    if not done and value_line is not None:
        idx = next((j for j, l in enumerate(out) if l.startswith("tags:")), len(out))
        out.insert(idx, value_line)
    return out


def link_target(v):
    m = re.search(r"\[\[([^\]|#]+)", v or "")
    return m.group(1).strip() if m else (v or "").strip()


# ---------- vault access ----------

class Vault:
    def __init__(self, root):
        self.root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(os.path.join(self.root, ".obsidian")):
            die(f"not an Obsidian vault: {self.root}")
        self._names = None
        self._rest = None

    def abs(self, rel):
        return os.path.join(self.root, rel)

    def exists(self, rel):
        return os.path.exists(self.abs(rel))

    def read(self, rel):
        with open(self.abs(rel), encoding="utf-8") as f:
            return f.read()

    def names(self):
        if self._names is None:
            self._names = {}
            for dirpath, dirs, files in os.walk(self.root):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for fn in files:
                    if fn.endswith(".md") and not fn.startswith("._"):
                        rel = os.path.relpath(os.path.join(dirpath, fn), self.root).replace(os.sep, "/")
                        self._names.setdefault(fn[:-3].lower(), []).append(rel)
        return self._names

    def resolve(self, name):
        """Return (link name, path) for an existing note, or (None, None)."""
        t = link_target(name)
        if t.lower().endswith(".md"):
            t = t[:-3]
        if not t:
            return None, None
        if "/" in t and self.exists(t + ".md"):
            return os.path.basename(t), t + ".md"
        hits = self.names().get(os.path.basename(t).lower())
        if hits:
            path = sorted(hits, key=len)[0]
            return os.path.basename(path)[:-3], path
        return None, None

    # writes: direct file access first, Local REST API if the shell is sandboxed
    def _api(self):
        if self._rest is None:
            key = os.environ.get("OBSIDIAN_API_KEY")
            if not key:
                cfg = self.abs(".obsidian/plugins/obsidian-local-rest-api/data.json")
                try:
                    with open(cfg) as f:
                        key = json.load(f).get("apiKey")
                except (OSError, ValueError):
                    die("cannot write to the vault and cannot read the Local REST API key")
            base = os.environ.get("OBSIDIAN_URL", "https://127.0.0.1:27124").rstrip("/")
            self._rest = (base, key, ssl._create_unverified_context())
        return self._rest

    def _call(self, method, rel, body=None):
        base, key, ctx = self._api()
        req = urllib.request.Request(f"{base}/vault/{urllib.parse.quote(rel)}", method=method,
                                     data=body.encode("utf-8") if body is not None else None,
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "text/markdown"})
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except urllib.error.URLError as e:
            die(f"vault not writable from this shell and Obsidian is unreachable ({e.reason}); open Obsidian and retry")

    def create(self, rel, text):
        if self.exists(rel):
            die(f"refusing to overwrite {rel}")
        try:
            os.makedirs(os.path.dirname(self.abs(rel)), exist_ok=True)
            with open(self.abs(rel), "x", encoding="utf-8") as f:
                f.write(text)
            return "file"
        except PermissionError:
            s = self._call("PUT", rel, text)
            if s not in (200, 204):
                die(f"REST create failed ({s}) for {rel}")
            return "rest"

    def replace(self, rel, text):
        """Rewrite one event note in place (only used for notes in 13 Calendar)."""
        if not rel.startswith(CAL_DIR + "/"):
            die(f"refusing to rewrite a note outside {CAL_DIR}: {rel}")
        try:
            tmp = self.abs(rel) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, self.abs(rel))
            return "file"
        except PermissionError:
            s = self._call("PUT", rel, text)
            if s not in (200, 204):
                die(f"REST update failed ({s}) for {rel}")
            return "rest"

    def append(self, rel, text):
        if not self.exists(rel):
            return None
        current = self.read(rel)
        chunk = ("" if current.endswith("\n") else "\n") + text.rstrip("\n") + "\n"
        try:
            with open(self.abs(rel), "a", encoding="utf-8") as f:
                f.write(chunk)
            return "file"
        except PermissionError:
            s = self._call("POST", rel, chunk)
            if s not in (200, 204):
                die(f"REST append failed ({s}) for {rel}")
            return "rest"


# ---------- events ----------

def load_events(vault):
    events = []
    base = vault.abs(CAL_DIR)
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("._"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), vault.root).replace(os.sep, "/")
            fm = fm_dict(split_fm(vault.read(rel))[0])
            if str(fm.get("type", "")).lower() != "event" or not fm.get("date"):
                continue
            fm["_path"], fm["_name"] = rel, fn[:-3]
            events.append(fm)
    return events


def title_of(ev):
    return ev.get("title") or re.sub(r"^\d{4}-\d{2}-\d{2}\s*-\s*", "", ev["_name"])


def daterange(a, b):
    d, e = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    while d <= e:
        yield d.isoformat()
        d += dt.timedelta(days=1)


def expand(vault, events, d1, d2):
    """Occurrences between d1 and d2, mirroring the calendar view's rules."""
    no_class, replaced, out = set(), set(), []
    singles = [e for e in events if str(e.get("repeat", "")).lower() != "weekly"]
    for e in singles:
        last = e.get("end-date") or e["date"]
        if str(e.get("no-class", "")).lower() == "true" and e.get("status") != "cancelled":
            no_class.update(daterange(e["date"], max(last, e["date"])))
        if e.get("replaces"):
            _, p = vault.resolve(e["replaces"])
            if p:
                replaced.add((p, e["date"]))
    for e in singles:
        last = max(e.get("end-date") or e["date"], e["date"])
        for d in daterange(e["date"], last):
            if d1 <= d <= d2:
                out.append((d, e.get("start-time") or "", e.get("end-time") or "", e))
    for e in events:
        if str(e.get("repeat", "")).lower() != "weekly":
            continue
        days = {DAYMAP.get(str(x).strip().lower()) for x in (e.get("days") or [])}
        skip = set(e.get("skip") or [])
        for d in daterange(max(d1, e["date"]), min(d2, e.get("end-date") or d2)):
            if dt.date.fromisoformat(d).isoweekday() not in days or d in skip:
                continue
            if (e["_path"], d) in replaced:
                continue
            if e.get("kind") == "class" and d in no_class:
                continue
            out.append((d, e.get("start-time") or "", e.get("end-time") or "", e))
    return sorted(out, key=lambda o: (o[0], o[1] or "00:00"))


def find_event(vault, name):
    t = link_target(name)
    if t.lower().endswith(".md"):
        t = t[:-3]
    for cand in (t + ".md", f"{EVENTS_DIR}/{t}.md"):
        if cand.startswith(CAL_DIR + "/") and vault.exists(cand):
            return cand
    _, path = vault.resolve(t)
    if path and path.startswith(CAL_DIR + "/"):
        return path
    want = t.lower()
    hits = [e["_path"] for e in load_events(vault)
            if re.sub(r"^\d{4}-\d{2}-\d{2}\s*-\s*", "", e["_name"]).lower() == want or title_of(e).lower() == want]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        die("several events match; pass the full note name:\n  " + "\n  ".join(sorted(hits)), 2)
    die(f"no event note named {name!r} in {CAL_DIR}")


def log(vault, action, link, kind, when, source):
    line = f"- {dt.date.today().isoformat()} · {action} [[{link}]] · {kind} · {when}"
    if source:
        line += f" · from {source}"
    vault.append(LOG_NOTE, line)


def source_ref(vault, args):
    if args.source:
        name, _ = vault.resolve(args.source)
        if name:
            return f"[[{name}]]", f'"[[{name}]]"'
        print(f"add_event: note {args.source!r} not found; storing it as text", file=sys.stderr)
        return args.source, yq(args.source)
    if args.source_text:
        return args.source_text, yq(args.source_text)
    return "", None


def cmd_add(args, vault):
    date = parse_date(args.date)
    end_date = parse_date(args.end_date) if args.end_date else None
    start, end = parse_time(args.start), parse_time(args.end)
    if end and not start:
        die("--end needs --start", 2)
    if start and not end:
        m = min(minutes(start) + (30 if args.kind in ("call", "interview") else 60), 23 * 60 + 59)
        end = f"{m // 60:02d}:{m % 60:02d}"
    if start and end and minutes(end) <= minutes(start):
        die("--end must be after --start", 2)
    title = re.sub(r"\s+", " ", args.title).strip()
    if not args.force:
        for d, s, _, e in expand(vault, load_events(vault), date, end_date or date):
            if e.get("repeat") == "weekly":
                continue
            if similar(title_of(e), title) and (not start or not s or abs(minutes(s) - minutes(start)) <= 90):
                print(f"possible duplicate: {e['_path']} ({title_of(e)}, {d}{' ' + s if s else ''})")
                print("Use `update` to change it, or rerun with --force if this is a different event.")
                sys.exit(3)
    safe = BAD_CHARS.sub(" ", title)
    safe = re.sub(r"\s+", " ", safe).strip()[:80]
    rel = f"{EVENTS_DIR}/{date} - {safe}.md"
    n = 2
    while vault.exists(rel):
        rel = f"{EVENTS_DIR}/{date} - {safe} ({n}).md"
        n += 1
    src_body, src_fm = source_ref(vault, args)
    fm = ["---", "type: event", f"kind: {args.kind}", f"date: {date}"]
    if end_date and end_date != date:
        fm.append(f"end-date: {end_date}")
    if start:
        fm += [f'start-time: "{start}"', f'end-time: "{end}"']
    if args.location:
        fm.append(f"location: {yq(args.location)}")
    course_link = None
    if args.course:
        course_link, _ = vault.resolve(args.course)
        if course_link:
            fm.append(f'course: "[[{course_link}]]"')
        else:
            print(f"add_event: course note {args.course!r} not found; skipped", file=sys.stderr)
    related = []
    for r in args.related or []:
        name, _ = vault.resolve(r)
        if name:
            related.append(name)
        else:
            print(f"add_event: related note {r!r} not found; skipped", file=sys.stderr)
    if related:
        fm.append("related:")
        fm += [f'  - "[[{r}]]"' for r in related]
    fm.append(f"status: {args.status}")
    if args.replaces:
        name, _ = vault.resolve(args.replaces)
        if not name:
            die(f"--replaces note {args.replaces!r} not found", 2)
        fm.append(f'replaces: "[[{name}]]"')
    if args.no_class:
        fm.append("no-class: true")
    if src_fm:
        fm.append(f"source: {src_fm}")
    fm.append(f"created: {dt.datetime.now():%Y-%m-%dT%H:%M}")
    fm += ["tags:", "  - event"] + ([] if args.by == "marc" else ["  - ai-assisted"]) + ["---"]
    when = when_text(date, end_date, start, end)
    body = ["", f"# {title}", "← [[Weekly Calendar]] · [[Calendar MOC]]", "", f"**When:** {when}"]
    if args.location:
        body.append(f"**Where:** {args.location}")
    if course_link:
        body.append(f"**Course:** [[{course_link}]]")
    if related:
        body.append("**Related:** " + " · ".join(f"[[{r}]]" for r in related))
    if args.status != "confirmed":
        body.append(f"**Status:** {args.status}")
    who = {"me": "Me", "perplexity": "Perplexity", "claude": "Claude", "chatgpt": "ChatGPT"}.get(args.by, args.by)
    body.append(f"**Source:** {src_body + ' · ' if src_body else ''}added by {who} on {dt.date.today():%Y-%m-%d}")
    if args.notes:
        body += ["", "## Notes", args.notes.strip()]
    text = "\n".join(fm + body) + "\n"
    if args.dry_run:
        print(f"[dry-run] would create {rel}\n{text}")
        return
    how = vault.create(rel, text)
    log(vault, "added", os.path.basename(rel)[:-3], args.kind, when, src_body)
    print(f"Added to calendar ({how}): {rel}\n  {title} · {when}" + (f" · {args.location}" if args.location else ""))


def cmd_update(args, vault, cancel=False):
    rel = find_event(vault, args.event)
    text = vault.read(rel)
    fm_lines, body = split_fm(text)
    if not fm_lines:
        die(f"{rel} has no frontmatter")
    before = fm_dict(fm_lines)
    if before.get("repeat") == "weekly" and not args.allow_recurring:
        die("that is a recurring class note; edit it by hand (and log it) or pass --allow-recurring", 2)
    changes = []
    if cancel:
        fm_lines = fm_set(fm_lines, "status", "status: cancelled")
        changes.append("cancelled")
    else:
        if args.date:
            d = parse_date(args.date)
            fm_lines = fm_set(fm_lines, "date", f"date: {d}")
            changes.append(f"date {before.get('date')} → {d}")
        if args.end_date:
            d = parse_date(args.end_date)
            fm_lines = fm_set(fm_lines, "end-date", f"end-date: {d}")
            changes.append(f"end date → {d}")
        if args.start:
            s = parse_time(args.start)
            fm_lines = fm_set(fm_lines, "start-time", f'start-time: "{s}"')
            changes.append(f"start {before.get('start-time') or 'all day'} → {s}")
        if args.end:
            e = parse_time(args.end)
            fm_lines = fm_set(fm_lines, "end-time", f'end-time: "{e}"')
            changes.append(f"end → {e}")
        if args.all_day:
            fm_lines = fm_set(fm_lines, "start-time", None)
            fm_lines = fm_set(fm_lines, "end-time", None)
            changes.append("now all day")
        if args.location is not None:
            fm_lines = fm_set(fm_lines, "location", f"location: {yq(args.location)}")
            changes.append(f"location → {args.location}")
        if args.status:
            fm_lines = fm_set(fm_lines, "status", f"status: {args.status}")
            changes.append(f"status → {args.status}")
        if args.title:
            fm_lines = fm_set(fm_lines, "title", f"title: {yq(args.title)}")
            changes.append(f"title → {args.title}")
    if not changes:
        die("nothing to change", 2)
    after = fm_dict(fm_lines)
    when = when_text(after["date"], after.get("end-date"), after.get("start-time"), after.get("end-time"))
    body = re.sub(r"^\*\*When:\*\*.*$", f"**When:** {when}", body, count=1, flags=re.M)
    location = getattr(args, "location", None)
    if location is not None and not cancel:
        if re.search(r"^\*\*Where:\*\*", body, flags=re.M):
            body = re.sub(r"^\*\*Where:\*\*.*$", f"**Where:** {location}", body, count=1, flags=re.M)
    src_body, _ = source_ref(vault, args)
    note = f"- {dt.date.today():%Y-%m-%d} · " + "; ".join(changes)
    if args.note:
        note += f" ({args.note})"
    if src_body:
        note += f" · from {src_body}"
    body = body.rstrip("\n") + ("\n\n## Changes\n" if "\n## Changes" not in body else "\n") + note + "\n"
    new = "---\n" + "\n".join(fm_lines) + "\n---\n" + body
    if args.dry_run:
        print(f"[dry-run] would update {rel}\n{new}")
        return
    vault.replace(rel, new)
    log(vault, "cancelled" if cancel else "changed", os.path.basename(rel)[:-3], after.get("kind", "event"), when, src_body)
    print(f"{'Cancelled' if cancel else 'Updated'}: {rel}\n  " + "; ".join(changes))


def cmd_list(args, vault):
    d1 = parse_date(args.date_from or "today")
    d2 = parse_date(args.date_to) if args.date_to else (dt.date.fromisoformat(d1) + dt.timedelta(days=6)).isoformat()
    occ = expand(vault, load_events(vault), d1, d2)
    if not occ:
        print(f"No events between {d1} and {d2}.")
        return
    for d, s, e, ev in occ:
        day = dt.date.fromisoformat(d)
        when = fmt_range(s, e) if s else "all day"
        status = "" if ev.get("status", "confirmed") == "confirmed" else f" [{ev.get('status')}]"
        where = f" @ {ev['location']}" if ev.get("location") else ""
        print(f"{d} {day:%a}  {when:<17} {title_of(ev)}{where} ({ev.get('kind', 'event')}){status}  <{ev['_path']}>")


def main():
    ap = argparse.ArgumentParser(description="Manage events in the Obsidian calendar (13 Calendar).")
    ap.add_argument("--vault", default=DEFAULT_VAULT, help="vault root (default: two folders up from this script)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add a one-off event")
    a.add_argument("--title", required=True)
    a.add_argument("--date", required=True, help="YYYY-MM-DD, today or tomorrow")
    a.add_argument("--end-date", help="last day of a multi-day event")
    a.add_argument("--start", help="start time, e.g. 15:00 or 3pm (omit for all day)")
    a.add_argument("--end", help="end time (default: +30 min for calls and interviews, +60 otherwise)")
    a.add_argument("--kind", default="meeting", choices=KINDS)
    a.add_argument("--location", help="room, address or join link without a passcode")
    a.add_argument("--course", help="course hub, e.g. 'ECON 101 MOC' (sets the color)")
    a.add_argument("--related", action="append", help="existing note to link (repeatable)")
    a.add_argument("--status", default="confirmed", choices=STATUSES)
    a.add_argument("--source", help="note this came from, e.g. '2026-10-12 - Topic' (an AI chat note)")
    a.add_argument("--source-text", help="plain-text source when there is no note, e.g. 'Email from IE, Oct 12'")
    a.add_argument("--replaces", help="recurring class note this replaces on that date, e.g. 'ECON 325 Class'")
    a.add_argument("--no-class", action="store_true", help="classes are cancelled on these days (breaks)")
    a.add_argument("--notes", help="short notes for the event body")
    a.add_argument("--by", default="perplexity", help="who is adding it: perplexity, claude, chatgpt or marc")
    a.add_argument("--force", action="store_true", help="add even if a similar event exists that day")
    a.add_argument("--dry-run", action="store_true")

    for name in ("update", "cancel"):
        u = sub.add_parser(name, help=f"{name} an existing event note")
        u.add_argument("event", help="event note name, e.g. '2026-10-14 - Call with X'")
        u.add_argument("--note", help="why it changed")
        u.add_argument("--source", help="note the change came from")
        u.add_argument("--source-text", help="plain-text source of the change")
        u.add_argument("--allow-recurring", action="store_true")
        u.add_argument("--dry-run", action="store_true")
        if name == "update":
            u.add_argument("--date")
            u.add_argument("--end-date")
            u.add_argument("--start")
            u.add_argument("--end")
            u.add_argument("--all-day", action="store_true")
            u.add_argument("--location")
            u.add_argument("--status", choices=STATUSES)
            u.add_argument("--title", help="display title (the file name stays the same)")

    lst = sub.add_parser("list", help="list events, including weekly classes")
    lst.add_argument("--from", dest="date_from", help="YYYY-MM-DD (default today)")
    lst.add_argument("--to", dest="date_to", help="YYYY-MM-DD (default 6 days after --from)")

    args = ap.parse_args()
    vault = Vault(args.vault)
    if args.cmd == "add":
        cmd_add(args, vault)
    elif args.cmd == "update":
        cmd_update(args, vault)
    elif args.cmd == "cancel":
        cmd_update(args, vault, cancel=True)
    else:
        cmd_list(args, vault)


if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    main()
