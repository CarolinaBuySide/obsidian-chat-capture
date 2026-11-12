#!/usr/bin/env python3
"""Read-only health check for an Obsidian vault.

Usage:
  python3 vault_health.py "/path/to/vault"            # Markdown report to stdout
  python3 vault_health.py "/path/to/vault" --json     # machine-readable summary
  python3 vault_health.py "/path/to/vault" --out report.md

Never modifies the vault. Standard library only. Secrets are reported by file
and line number only; their values are never printed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from urllib.parse import unquote

SKIP_DIRS = {".obsidian", ".git", ".trash", ".smart-env", ".claude", "node_modules"}
TEMPLATE_DIR = "09 Templates"
DRAFTS_DIR = "01 Fleeting/AI Drafts"  # agent drafts and reports: checked for broken links, not counted as graph links
SUMMARY_FOLDERS = ("00 Home", "02 Literature", "03 Permanent", "04 Maps", "05 Projects")
DAILY_RE = re.compile(r"^06 Daily/\d{4}/\d{2}/\d{4}-\d{2}-\d{2}$")
WIKILINK_RE = re.compile(r"(!?)\[\[([^\[\]\n]+?)\]\]")
MDLINK_RE = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+(?:\s[^)]*)?)\)")
FENCE_RE = re.compile(r"^(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
SECRET_PATTERNS = [
    ("OpenAI-style key", re.compile(r"(?<![\w/\-.])sk-(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Z])[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Password assignment", re.compile(r"(?i)\b(password|passwd|api[_ -]?key|secret|token)\s*[:=]\s*[\"']?[^\s\"'`]{8,}")),
]


def parse_frontmatter(text: str):
    """Return (frontmatter_text or None, body). Minimal YAML parsing for the keys we need."""
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None, text
    end = re.search(r"^---\s*$", text[4:], re.M)
    if not end:
        return None, text
    fm = text[4 : 4 + end.start()]
    body = text[4 + end.end() :]
    return fm, body


def fm_value(fm: str, key: str):
    m = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", fm, re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if val:
        return val.strip("\"'")
    # block list
    items = []
    for line in fm[m.end() :].splitlines()[1:]:
        if re.match(r"^\s+-\s+", line):
            items.append(re.sub(r"^\s+-\s+", "", line).strip().strip("\"'"))
        elif line.strip() == "":
            continue
        else:
            break
    return items if items else ""


def fm_tags(fm: str):
    v = fm_value(fm, "tags")
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [t.lstrip("#") for t in v]
    v = v.strip("[]")
    return [t.strip().strip("\"'").lstrip("#") for t in v.split(",") if t.strip()]


def strip_code(text: str) -> str:
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else INLINE_CODE_RE.sub("", line))
    return "\n".join(out)


def collect(vault: str):
    notes, others = {}, []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f.startswith("._") or f.startswith("~$") or f == ".DS_Store":
                continue
            rel = os.path.relpath(os.path.join(root, f), vault).replace(os.sep, "/")
            if f.lower().endswith(".md"):
                with open(os.path.join(root, f), encoding="utf-8", errors="replace") as fh:
                    notes[rel] = fh.read()
            else:
                others.append(rel)
    return notes, others


class Resolver:
    def __init__(self, note_paths, other_paths):
        self.by_name = defaultdict(list)
        self.by_path = {}
        for p in note_paths:
            stem = p[:-3]
            self.by_name[os.path.basename(stem).lower()].append(p)
            self.by_path[stem.lower()] = p
            self.by_path[p.lower()] = p
        for p in other_paths:
            self.by_name[os.path.basename(p).lower()].append(p)
            self.by_path[p.lower()] = p

    def resolve(self, target: str):
        t = target.strip().replace("\\", "/")
        if not t:
            return None
        t = t.split("#")[0].split("^")[0].strip()
        if not t:
            return "__self__"
        low = t.lower().lstrip("./")
        if low in self.by_path:
            return self.by_path[low]
        if low + ".md" in self.by_path:
            return self.by_path[low + ".md"]
        if "/" in low:
            for key, p in self.by_path.items():
                if key.endswith("/" + low) or key.endswith("/" + low + ".md"):
                    return p
            base = os.path.basename(low)
        else:
            base = low
        cands = self.by_name.get(base) or self.by_name.get(base[:-3] if base.endswith(".md") else base)
        if cands:
            return sorted(cands, key=len)[0]
        return None


def extract_links(text: str):
    """Return list of (target, kind, line_no). kind is 'wiki' or 'md'."""
    links = []
    clean = strip_code(text)
    for i, line in enumerate(clean.splitlines(), 1):
        for m in WIKILINK_RE.finditer(line):
            target = m.group(2).split("|")[0].rstrip("\\")
            links.append((target, "wiki", i))
        for m in MDLINK_RE.finditer(line):
            href = m.group(1).split()[0].strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#"):
                continue  # external (http, file, obsidian, mailto) or same-note anchor
            links.append((unquote(href), "md", i))
    return links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    args = ap.parse_args()
    vault = os.path.abspath(os.path.expanduser(args.vault))
    today = dt.date.fromisoformat(args.today)

    notes, others = collect(vault)
    res = Resolver(notes.keys(), others)
    meta = {}
    inbound = defaultdict(set)
    outbound = defaultdict(set)
    broken, daily_unresolved = [], []
    for path, text in notes.items():
        fm, body = parse_frontmatter(text)
        info = {
            "has_fm": fm is not None,
            "type": (fm_value(fm, "type") if fm else None) or None,
            "summary": bool(fm and fm_value(fm, "summary")),
            "tags": fm_tags(fm) if fm else [],
            "status": (fm_value(fm, "status") if fm else None),
            "created": (fm_value(fm, "created") if fm else None),
            "updated": (fm_value(fm, "updated") if fm else None),
            "words": len(re.findall(r"\w+", body)),
        }
        meta[path] = info
        if path.startswith(TEMPLATE_DIR + "/"):
            continue  # template placeholders are not real links
        for target, kind, line in extract_links(text):
            r = res.resolve(target)
            if r == "__self__":
                continue
            if r is None:
                t = target.split("#")[0].split("|")[0].strip()
                if DAILY_RE.match(t) or re.match(r"^07 Weekly/\d{4}-W\d{2}$", t):
                    daily_unresolved.append((path, t, line))
                else:
                    broken.append((path, t, line))
                continue
            if r != path and not path.startswith(DRAFTS_DIR + "/"):
                outbound[path].add(r)
                inbound[r].add(path)

    is_map = lambda p: (meta.get(p, {}).get("type") == "map") or p.startswith("04 Maps/")
    exempt_orphan = lambda p: p.startswith((TEMPLATE_DIR + "/", DRAFTS_DIR + "/")) or p in ("README.md", "AGENTS.md", "CLAUDE.md")

    orphans = sorted(p for p in notes if not inbound[p] and not exempt_orphan(p))
    isolated = sorted(p for p in notes if not inbound[p] and not outbound[p] and not exempt_orphan(p))
    no_map = sorted(
        p for p in notes
        if not is_map(p) and not exempt_orphan(p) and not p.startswith("06 Daily/")
        and not any(is_map(q) for q in outbound[p] | inbound[p])
    )
    no_fm = sorted(p for p in notes if not meta[p]["has_fm"] and not p.startswith(TEMPLATE_DIR + "/"))
    no_type = sorted(p for p in notes if meta[p]["has_fm"] and not meta[p]["type"] and not p.startswith(TEMPLATE_DIR + "/"))
    need_summary = sorted(
        (p for p in notes if p.startswith(SUMMARY_FOLDERS) and not meta[p]["summary"]),
        key=lambda p: (-len(inbound[p]), p),
    )
    long_no_summary = sorted(
        (p for p in notes if meta[p]["words"] > 2500 and not meta[p]["summary"] and not p.startswith(TEMPLATE_DIR + "/")),
        key=lambda p: -meta[p]["words"],
    )
    ai_review = sorted(p for p in notes if "ai-assisted" in meta[p]["tags"])
    examples = sorted(p for p in notes if "example" in meta[p]["tags"])

    stale_inbox = []
    for p in notes:
        if p.startswith("01 Fleeting/") and meta[p]["status"] == "inbox" and meta[p]["created"]:
            try:
                c = dt.date.fromisoformat(str(meta[p]["created"])[:10])
                if (today - c).days > 7:
                    stale_inbox.append((p, (today - c).days))
            except ValueError:
                pass
    stale_hubs = []
    for p in notes:
        if p.startswith(("00 Home/", "04 Maps/")) and meta[p]["updated"]:
            try:
                u = dt.date.fromisoformat(str(meta[p]["updated"])[:10])
                if (today - u).days > 14:
                    stale_hubs.append((p, (today - u).days))
            except ValueError:
                pass

    dup_lines = []
    for p in notes:
        if not is_map(p):
            continue
        seen = defaultdict(list)
        for i, line in enumerate(strip_code(notes[p]).splitlines(), 1):
            s = line.strip()
            if len(s) > 12 and (s.startswith("- ") or s.startswith("* ")):
                seen[s].append(i)
        for s, lines in seen.items():
            if len(lines) > 1:
                dup_lines.append((p, lines, s[:90]))

    secrets = []
    for p, text in notes.items():
        for i, line in enumerate(text.splitlines(), 1):
            for label, rx in SECRET_PATTERNS:
                if rx.search(line):
                    secrets.append((p, i, label))
                    break

    linked_targets = set(inbound)
    unlinked_files = sorted(
        o for o in others
        if o.startswith("12 School/") and o not in linked_targets
        and not o.lower().endswith((".ds_store",)) and "/_Duplicates to review/" not in o
    )

    summary = {
        "date": today.isoformat(),
        "notes": len(notes),
        "other_files": len(others),
        "broken_links": len(broken),
        "unresolved_daily_or_weekly_links": len(daily_unresolved),
        "orphans_no_inbound": len(orphans),
        "isolated_no_links": len(isolated),
        "not_connected_to_a_map": len(no_map),
        "missing_frontmatter": len(no_fm),
        "missing_type": len(no_type),
        "hub_notes_missing_summary": len(need_summary),
        "long_notes_missing_summary": len(long_no_summary),
        "ai_assisted_review_queue": len(ai_review),
        "example_notes_left": len(examples),
        "stale_inbox_items": len(stale_inbox),
        "stale_hub_updated_dates": len(stale_hubs),
        "duplicate_lines_in_maps": len(dup_lines),
        "possible_secrets": len(secrets),
        "school_files_not_linked": len(unlinked_files),
    }
    if args.json:
        out = json.dumps({"summary": summary, "broken": broken, "orphans": orphans, "no_map": no_map,
                          "need_summary": need_summary, "secrets": secrets}, indent=2)
    else:
        L = []
        w = L.append
        w(f"Vault health check · {today.isoformat()} · {len(notes)} notes, {len(others)} other files\n")
        w("| Check | Count |\n|---|---|")
        for k, v in summary.items():
            if k in ("date", "notes", "other_files"):
                continue
            w(f"| {k.replace('_', ' ')} | {v} |")

        def section(title, rows, fmt, limit=40):
            w(f"\n### {title} ({len(rows)})")
            if not rows:
                w("- None")
                return
            for r in rows[:limit]:
                w("- " + fmt(r))
            if len(rows) > limit:
                w(f"- ...and {len(rows) - limit} more")

        link = lambda p: f"[[{p[:-3]}|{os.path.basename(p)[:-3]}]]" if p.endswith(".md") else f"`{p}`"
        section("Broken links (target note does not exist)", broken, lambda r: f"{link(r[0])} line {r[2]} → `{r[1]}`")
        section("Unresolved daily/weekly links (usually expected: days not written yet)", daily_unresolved, lambda r: f"{link(r[0])} → `{r[1]}`", 10)
        section("Isolated notes (no links in or out)", isolated, link)
        section("Notes with no inbound links", orphans, link)
        section("Notes not connected to any map", no_map, link)
        section("Missing frontmatter", no_fm, link)
        section("Hub/knowledge notes missing a summary (most-linked first)", need_summary, lambda p: f"{link(p)} · {len(inbound[p])} backlinks")
        section("Long notes (>2,500 words) missing a summary", long_no_summary, lambda p: f"{link(p)} · {meta[p]['words']:,} words")
        section("Fleeting notes older than 7 days still in the inbox", stale_inbox, lambda r: f"{link(r[0])} · {r[1]} days")
        section("Hub notes whose `updated` date is over 14 days old", stale_hubs, lambda r: f"{link(r[0])} · {r[1]} days")
        section("Duplicate list lines in maps", dup_lines, lambda r: f"{link(r[0])} lines {r[1]}: {r[2]}")
        section("AI-assisted notes awaiting your review (remove the tag once reviewed)", ai_review, link, 60)
        section("Example notes still in the vault", examples, link)
        section("Possible secrets (values hidden; rotate and remove)", secrets, lambda r: f"{link(r[0])} line {r[1]} · {r[2]}")
        section("Course files not linked from any note", unlinked_files, lambda o: f"`{o}`", 25)
        out = "\n".join(L) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    main()
