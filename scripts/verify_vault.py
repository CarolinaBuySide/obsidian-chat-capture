#!/usr/bin/env python3
"""Read-only health check for a blueprint vault. Exit code 0 = pass.

Checks: required folders, JSON configs parse, frontmatter is well formed, wikilinks resolve,
no orphan notes, no leftover {{PLACEHOLDERS}}, ai-assisted notes link to a map, no likely secrets,
and color coding: every folder color, and for each course a CSS variable, a file-explorer block,
a note title color and a graph color group.
Usage: python3 scripts/verify_vault.py "<vault>" [--json]
"""
import os
import json, pathlib, re, sys

REQUIRED = ["00 Home", "01 Fleeting/AI Drafts", "02 Literature", "03 Permanent", "04 Maps", "05 Projects", "06 Daily",
            "07 Weekly", "08 Archive", "09 Templates", "10 Attachments", "11 AI Chats", "13 Calendar/Classes", "13 Calendar/Events",
            "13 Calendar/Prep", "13 Calendar/System/calendar-view", "13 Calendar/System/task-calendar"]
CORE = ["AGENTS.md", "00 Home/Home.md", "00 Home/AI Context.md", "00 Home/Top of Mind.md", "00 Home/Weekly Calendar.md",
        "00 Home/To-Do Calendar.md", "13 Calendar/To-Do.md", "13 Calendar/System/add_event.py",
        ".obsidian/plugins/graph-groups/main.js", ".obsidian/templates.json", ".obsidian/snippets/color-coding.css", "04 Maps/AI Chats MOC.md", "04 Maps/Calendar MOC.md", "04 Maps/AI Agent MOC.md"]
LINK = re.compile(r"(?<!!)\[\[([^\]|#^]+)(?:[#^][^\]|]*)?(?:\|[^\]]*)?\]\]|!\[\[([^\]|#^]+)")
SECRET = re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[bap]-[A-Za-z0-9-]{10,})")
SKIP_ORPHAN = {"Home", "AGENTS", "CLAUDE", "README"}
SKIP_ORPHAN_DIRS = {"09 Templates", "06 Daily", "07 Weekly"}

def main():
    vault = pathlib.Path(sys.argv[1]).expanduser()
    issues = {k: [] for k in ["missing", "json", "frontmatter", "broken_links", "orphans", "placeholders", "ai_unmapped", "secrets", "colors"]}
    for d in REQUIRED:
        if not (vault / d).is_dir(): issues["missing"].append(d + "/")
    for f in CORE:
        if not (vault / f).is_file(): issues["missing"].append(f)
    for j in (vault / ".obsidian").rglob("*.json"):
        try: json.loads(j.read_text())
        except Exception as e: issues["json"].append(f"{j.relative_to(vault)}: {e}")

    files = [p for p in vault.rglob("*") if p.is_file() and not ({".obsidian", ".git", ".claude", ".trash", "System"} & set(p.parts))]
    md = [p for p in files if p.suffix == ".md"]
    names = {}
    for p in files:
        rel = p.relative_to(vault).as_posix()
        for key in {p.name, p.stem if p.suffix == ".md" else p.name, rel, rel[:-3] if rel.endswith(".md") else rel}:
            names.setdefault(key.lower(), p)
    inbound = {p: 0 for p in md}
    for p in md:
        rel = p.relative_to(vault).as_posix()
        t = p.read_text(errors="ignore")
        tmpl = "09 Templates" in p.parts
        if t.startswith("---") and not tmpl and not re.match(r"^---\n.*?\n---\n", t, re.S):
            issues["frontmatter"].append(rel)
        if tmpl: continue
        if re.search(r"\{\{[A-Z_0-9]+\}\}", t): issues["placeholders"].append(rel)
        if SECRET.search(t): issues["secrets"].append(rel)
        body = re.sub(r"```.*?```|`[^`]*`", "", t, flags=re.S)
        targets = [(m.group(1) or m.group(2)).strip().rstrip("\\").strip() for m in LINK.finditer(body)]
        maps_linked = False
        for tg in targets:
            if not tg: continue
            hit = names.get(tg.lower()) or names.get((tg + ".md").lower())
            if not hit: issues["broken_links"].append(f"{rel} → [[{tg}]]"); continue
            if hit != p and hit in inbound: inbound[hit] += 1
            if "04 Maps" in hit.parts: maps_linked = True
        fm = re.match(r"^---\n(.*?)\n---\n", t, re.S)
        if fm and re.search(r"(?m)^\s*-\s*ai-assisted\s*$|tags:\s*\[[^\]]*ai-assisted", fm.group(1)) and not maps_linked and "04 Maps" not in p.parts:
            issues["ai_unmapped"].append(rel)
    for p, n in inbound.items():
        if n == 0 and p.stem not in SKIP_ORPHAN and not (SKIP_ORPHAN_DIRS & set(p.parts)):
            issues["orphans"].append(p.relative_to(vault).as_posix())

    # Color coding: the snippet is on, the shared rules are present, and every course has all four pieces.
    css_path = vault / ".obsidian/snippets/color-coding.css"
    css = css_path.read_text() if css_path.is_file() else ""
    try:
        if "color-coding" not in json.loads((vault / ".obsidian/appearance.json").read_text()).get("enabledCssSnippets", []):
            issues["colors"].append("color-coding snippet is not enabled in appearance.json")
        groups = " ".join(g.get("query", "") for g in json.loads((vault / ".obsidian/graph.json").read_text()).get("colorGroups", []))
    except Exception as e:
        groups = ""; issues["colors"].append(f"cannot read appearance.json or graph.json: {e}")
    for need in ["--c-home", "--c-fleeting", "--c-lit", "--c-perm", "--c-map", "--c-proj", "--c-daily", "--c-ai",
                 ".course-note .inline-title", ".course-note h2", "--graph-node-attachment", 'data-path="13 Calendar"']:
        if need not in css: issues["colors"].append(f"color-coding.css is missing {need}")
    if "{{" in css: issues["colors"].append("color-coding.css has a leftover placeholder")
    for folder in ["00 Home", "01 Fleeting", "02 Literature", "03 Permanent", "04 Maps", "05 Projects", "08 Archive", "11 AI Chats"]:
        if f'path:"{folder}"' not in groups: issues["colors"].append(f"graph.json has no color group for {folder}")
    for moc in sorted((vault / "04 Maps").glob("* MOC.md")):
        fm = re.match(r"^---\n(.*?)\n---\n", moc.read_text(errors="ignore"), re.S)
        if not fm or not re.search(r"(?m)^\s*-\s*course\s*$", fm.group(1)) or re.search(r"(?m)^status:\s*past", fm.group(1)): continue
        code = moc.stem[:-4]; s = re.sub(r"[^a-z0-9]+", "-", code.lower()).strip("-")
        checks = {f"CSS variable --c-{s}": f"--c-{s}:" in css, f"note title color .course-{s}": f".course-{s} {{" in css,
                  "file-explorer block": f'04 Maps/{code} MOC.md"]' in css, f"cssclass course-{s} on the course map": f"course-{s}" in fm.group(1),
                  "graph color group": f'file:"{code} MOC"' in groups}
        issues["colors"] += [f"{code}: missing {k}" for k, ok in checks.items() if not ok]

    total = sum(len(v) for v in issues.values())
    if "--json" in sys.argv:
        print(json.dumps({"notes": len(md), "files": len(files), "issues": issues}, indent=2))
    else:
        print(f"Vault: {vault}\nNotes: {len(md)}  Files: {len(files)}")
        for k, v in issues.items():
            print(f"  {'OK  ' if not v else 'FAIL'} {k}: {len(v)}")
            for i in v[:15]: print(f"       - {i}")
        print("PASS" if total == 0 else f"{total} issue(s)")
    sys.exit(0 if total == 0 else 1)

if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    main()
