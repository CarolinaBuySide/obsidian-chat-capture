#!/usr/bin/env python3
"""Canvas -> Obsidian sync, run from a terminal on the computer that holds the vault.

Any AI that can run commands here (or you) uses the same five commands. Full procedure:
"00 Home/Agent/Skills/Skill - Canvas Sync.md".

  python3 sync.py setup                 match your Canvas courses to the vault's courses (writes courses.json)
  python3 sync.py plan                  read Canvas, work out what should change, download new files
  python3 sync.py apply                 copy the files in and write the notes (after a Git checkpoint)
  python3 sync.py finish --by "<who>"   save the sync state and log the run
  python3 sync.py status                connection, courses and the last run

plan changes nothing in the vault: it writes a plan folder and prints the report. Read the
report, fill in the lecture notes it lists, then run apply. Canvas itself is never changed.

Canvas is read with a personal access token (canvas_api.py login). An AI that drives a
logged-in browser tab instead can pass its own reading: plan --canvas canvas.json
[--downloads <folder>]. Standard library only.
"""
import argparse, datetime as dt, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tarfile, tempfile

HERE = pathlib.Path(__file__).resolve().parent
VAULT = HERE.parents[2]
COURSES = HERE / "courses.json"
STATE = HERE / "state.json"
WORK = pathlib.Path(tempfile.gettempdir()) / ("obsidian-canvas-sync-" + hashlib.sha256(str(VAULT).encode()).hexdigest()[:10])
PLAN = WORK / "plan"
PLACEHOLDER = "KEY-IDEAS-PLACEHOLDER"
DEFAULTS = {
    "ignore": [r"^attendance\b", r"^in-class activity", r"^class \d+$"],
    "skip_files": ["seating chart", "roster", "banner", "^screenshot", r"^untitled\b"],
    "skip_extensions": ["png", "jpg", "jpeg", "gif", "svg", "webp", "heic", "bmp", "tif", "tiff", "mp4", "mov", "m4v", "mp3", "m4a", "wav", "zip"],
    "courses": [], "watch_only": [],
    "notes": "slides_are_prep: set it to true for a course whose instructor posts lecture notes before class, so each new deck "
             "becomes a 'read before class' task. Other courses' decks are imported and listed without a task.",
}

sys.path.insert(0, str(HERE))
import canvas_api  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(args, **kw):
    return subprocess.run([sys.executable, *map(str, args)], **kw)


def load(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return m.group(1) if m else ""


def local_timezone():
    try:
        link = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in link:
            return link.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    return os.environ.get("TZ") or "UTC"


def vault_courses():
    """Active courses in the vault: [{code, map, prep, folder, materials, class}] with vault-relative paths."""
    out = []
    for moc in sorted((VAULT / "04 Maps").glob("* MOC.md")):
        fm = frontmatter(moc.read_text(encoding="utf-8", errors="ignore"))
        if not re.search(r"(?m)^\s*-\s*course\s*$", fm) or re.search(r"(?m)^status:\s*past", fm):
            continue
        code = moc.stem[:-4]
        mats = [p for p in (VAULT / "12 School").glob(f"*/*/{code} Materials.md") if "Past Courses" not in p.parts]
        if not mats:
            continue
        rel = lambda p: p.relative_to(VAULT).as_posix()
        c = {"code": code, "map": rel(moc), "folder": rel(mats[0].parent), "materials": rel(mats[0])}
        for key, p in (("prep", VAULT / "13 Calendar/Prep" / f"{code} Prep.md"), ("class", VAULT / "13 Calendar/Classes" / f"{code} Class.md")):
            if p.is_file():
                c[key] = rel(p)
        out.append(c)
    return out


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def setup(x):
    cfg = load(COURSES) or {}
    for k, v in DEFAULTS.items():
        cfg.setdefault(k, v)
    if not cfg.get("timezone") or "{{" in cfg["timezone"]:
        cfg["timezone"] = local_timezone()
    hosts = list(canvas_api.load_config().get("hosts", {}))
    if not hosts:
        sys.exit("No Canvas site is connected yet. In your own terminal run:\n"
                 f'  python3 "{HERE / "canvas_api.py"}" login --host <your school\'s Canvas address>')
    canvas = []
    for h in hosts:
        rows = canvas_api.list_courses(h)
        if rows is None:
            sys.exit(f"Canvas at {h} didn't answer. Run: canvas_api.py status")
        canvas += [{**r, "host": h} for r in rows]
    manual = {}
    for m in x.map or []:
        code, _, cid = m.partition("=")
        manual[code.strip()] = cid.strip()
    old = {c["code"]: c for c in cfg["courses"]}
    courses, unmatched = [], []
    for vc in vault_courses():
        code, hit = vc["code"], None
        if code in manual:
            hit = next((c for c in canvas if str(c["id"]) == manual[code]), None)
            if not hit:
                sys.exit(f"--map {code}={manual[code]}: no active Canvas course has that id. See: canvas_api.py courses")
        elif code in old and any(str(c["id"]) == str(old[code].get("id")) for c in canvas):
            hit = next(c for c in canvas if str(c["id"]) == str(old[code]["id"]))
        else:
            found = [c for c in canvas if norm(code) in norm(c["code"] + " " + c["name"])]
            hit = found[0] if len(found) == 1 else None
        if not hit:
            unmatched.append(code); continue
        courses.append({"code": code, "host": hit["host"], "id": hit["id"], **{k: v for k, v in vc.items() if k != "code"},
                        "slides_are_prep": bool(old.get(code, {}).get("slides_are_prep", False))})
        print(f"  OK   {code}  ->  {hit['name']} ({hit['host']}, id {hit['id']})")
    cfg["courses"] = courses
    COURSES.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    for code in unmatched:
        print(f"  ??   {code}: no single Canvas course matches. Pick its id below and rerun with --map \"{code}=<id>\"")
    if unmatched:
        used = {str(c["id"]) for c in courses}
        print("Canvas courses not matched yet:")
        for c in canvas:
            if str(c["id"]) not in used:
                print(f"  {c['id']}\t{c['code']}\t{c['name']}\t{c['term']}")
        sys.exit(1)
    if not courses:
        sys.exit("The vault has no active courses yet. Add them with the blueprint's new_course.py, then run setup again.")
    print(f"Wrote {COURSES.relative_to(VAULT).as_posix()} with {len(courses)} course(s). Next: sync.py plan")


def plan(x):
    if not (load(COURSES) or {}).get("courses"):
        sys.exit("No courses are mapped to Canvas yet. Run: sync.py setup")
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "vault").mkdir(parents=True)
    r = run([HERE / "pack_inputs.py", "--out", WORK / "inputs.tgz"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("Could not read the vault:\n" + r.stderr)
    with tarfile.open(WORK / "inputs.tgz") as tar:
        tar.extractall(WORK / "vault")
    if x.canvas:
        shutil.copy2(x.canvas, WORK / "canvas.json")
    else:
        data = canvas_api.fetch_all(COURSES, x.since_days)
        (WORK / "canvas.json").write_text(json.dumps(data), encoding="utf-8")
        bad = [h["host"] for h in data["hosts"] if not h["logged_in"]]
        if bad:
            sys.exit("Canvas didn't accept the saved token for: " + ", ".join(bad) +
                     "\nIn your own terminal run: canvas_api.py login --host <that address>. Nothing was changed.")
    downloads = pathlib.Path(x.downloads) if x.downloads else WORK / "downloads"

    def planner(with_downloads):
        if PLAN.exists():
            shutil.rmtree(PLAN)
        cmd = [HERE / "canvas_sync.py", "--canvas", WORK / "canvas.json", "--vault", WORK / "vault", "--out", PLAN, "--config", COURSES]
        cmd += ["--downloads", downloads] if with_downloads else []
        cmd += ["--init"] if x.init else []
        cmd += ["--backfill-notes", x.backfill_notes] if x.backfill_notes else []
        cmd += ["--now", x.now] if x.now else []
        r = run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("The planner stopped:\n" + (r.stderr or r.stdout))

    planner(downloads.is_dir())
    imports = load(PLAN / "imports.json", [])
    if imports and not x.canvas:
        print(f"Downloading {len(imports)} new Canvas file(s)...")
        if not canvas_api.download(PLAN / "imports.json", downloads):
            print("Some files could not be downloaded; they are left for the next sync.")
        planner(True)
    elif imports and not downloads.is_dir():
        print(f"{len(imports)} file(s) to import. Download them to <folder>/<file id>/<name> (file_links.js), then run plan again "
              f"with --canvas and --downloads <folder>.")
    print((PLAN / "report.md").read_text(encoding="utf-8"))
    todo = [c["path"] for c in load(PLAN / "changes.json", []) if PLACEHOLDER in (PLAN / "files" / c["path"]).read_text(encoding="utf-8")]
    print(f"\nPlan folder: {PLAN}")
    if todo:
        print("Before apply, replace the KEY-IDEAS-PLACEHOLDER line with 3 to 5 bullets in these planned notes (edit them in the plan folder's files/):")
        for p in todo:
            print(f"  {PLAN / 'files' / p}")
    print("Nothing in the vault has changed yet. Next: sync.py apply")


def checkpoint():
    if (VAULT / ".git").exists() and shutil.which("git"):
        subprocess.run(["git", "-C", str(VAULT), "add", "-A"], capture_output=True)
        ident = [] if subprocess.run(["git", "-C", str(VAULT), "config", "user.email"], capture_output=True, text=True).stdout.strip() \
            else ["-c", "user.name=Vault", "-c", "user.email=vault@localhost"]
        subprocess.run(["git", "-C", str(VAULT), *ident, "commit", "-q", "-m", "checkpoint: before Canvas sync"], capture_output=True)
        return "Git checkpoint made."
    r = run([HERE / "obsidian_api.py", "run", "obsidian-git:commit"], capture_output=True, text=True)
    return "Git checkpoint made through Obsidian." if r.returncode == 0 else "No checkpoint (the vault isn't a git repository and Obsidian isn't reachable)."


def apply(x):
    changes, imports = load(PLAN / "changes.json"), load(PLAN / "imports.json", [])
    if changes is None:
        sys.exit("There is no plan. Run: sync.py plan")
    left = [c["path"] for c in changes if PLACEHOLDER in (PLAN / "files" / c["path"]).read_text(encoding="utf-8")]
    if left and not x.keep_placeholders:
        sys.exit("These planned lecture notes still have the KEY-IDEAS-PLACEHOLDER line. Fill it in (in the plan folder), or pass "
                 "--keep-placeholders to leave it for later:\n  " + "\n  ".join(left))
    downloads = pathlib.Path(x.downloads) if x.downloads else WORK / "downloads"
    print(checkpoint())
    problems = 0
    for i in imports:
        src, dest = downloads / str(i["file_id"]) / i["name"], VAULT / i["dest"]
        if not src.is_file():
            problems += 1; print(f"  SKIP  {i['dest']}: not downloaded"); continue
        if i.get("replaces"):
            old, older = VAULT / i["replaces"], VAULT / i["replaces_to"]
            if old.is_file() and not older.exists():
                older.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(older))
                print(f"  moved {i['replaces']} -> {i['replaces_to']}")
        if dest.exists():
            print(f"  have  {i['dest']}"); continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        if sha(dest.read_bytes()) != sha(src.read_bytes()):
            problems += 1; dest.unlink(); print(f"  FAIL  {i['dest']}: copy didn't match"); continue
        print(f"  file  {i['dest']}")
    for c in changes:
        dest, new = VAULT / c["path"], (PLAN / "files" / c["path"]).read_bytes()
        if c.get("sha256_before") is None:
            if dest.exists():
                problems += 1; print(f"  SKIP  {c['path']}: a note is already there"); continue
        elif not dest.is_file() or sha(dest.read_bytes()) != c["sha256_before"]:
            problems += 1; print(f"  SKIP  {c['path']}: it changed since the plan was made. Run plan and apply again"); continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(new)
        print(f"  note  {c['path']}" + (" (new)" if c.get("sha256_before") is None else ""))
    (PLAN / "applied.json").write_text(json.dumps({"problems": problems, "at": dt.datetime.now().isoformat(timespec="minutes")}))
    print(f"Applied {len(imports)} file(s) and {len(changes)} note change(s)" + (f", {problems} skipped" if problems else "") + ".")
    print("Next: add any prep tasks, announcement deadlines and class changes from the report (steps in the skill note), then: sync.py finish --by \"<who>\"")
    sys.exit(1 if problems else 0)


def finish(x):
    state = load(PLAN / "state.json")
    if state is None:
        sys.exit("There is no plan. Run: sync.py plan")
    changes, imports = load(PLAN / "changes.json", []), load(PLAN / "imports.json", [])
    if (changes or imports) and not (PLAN / "applied.json").is_file():
        sys.exit("The plan has changes that were not applied. Run: sync.py apply")
    changed = bool(changes or imports or x.summary)
    summary = x.summary or state.get("summary") or "no changes"
    if not changed:
        summary = "No changes; the vault already matches Canvas"
    state["summary"] = summary + (f". Run by {x.by}" if x.by else "")
    STATE.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    moc = VAULT / "04 Maps/Calendar MOC.md"
    if changed and moc.is_file():
        lines = moc.read_text(encoding="utf-8").split("\n")
        try:
            at = next(i for i, l in enumerate(lines) if l.strip().lower() == "## event log")
        except StopIteration:
            at = None
        if at is not None:
            end = next((i for i in range(at + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
            while end > at + 1 and not lines[end - 1].strip():
                end -= 1
            lines.insert(end, f"- {dt.date.today().isoformat()} · Canvas sync: {summary}" + (f" (run by {x.by})" if x.by else ""))
            moc.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved the sync state: {state['summary']}")


def status(_):
    hosts = list(canvas_api.load_config().get("hosts", {}))
    print("Canvas sites: " + (", ".join(hosts) or "none connected (canvas_api.py login --host <address>)"))
    cfg = load(COURSES) or {}
    for c in cfg.get("courses", []):
        print(f"  {c['code']}  ->  {c['host']} id {c['id']}")
    if not cfg.get("courses"):
        print("  no courses mapped (sync.py setup)")
    st = load(STATE)
    print(f"Last sync: {st['last_run']} · {st.get('summary', '')}" if st and st.get("last_run") else "Last sync: never")


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = a.add_subparsers(dest="step", required=True)
    s = sub.add_parser("setup"); s.add_argument("--map", action="append", metavar='"CODE=canvas id"')
    p = sub.add_parser("plan")
    p.add_argument("--canvas", help="a reading saved by fetch_canvas.js, instead of using the access token")
    p.add_argument("--downloads", help="folder with files downloaded as <file id>/<name>")
    p.add_argument("--init", action="store_true", help="mark everything on Canvas as already seen")
    p.add_argument("--backfill-notes", help="course codes whose existing decks should also get lecture notes")
    p.add_argument("--since-days", type=int, default=21)
    p.add_argument("--now", help=argparse.SUPPRESS)
    ap = sub.add_parser("apply"); ap.add_argument("--downloads"); ap.add_argument("--keep-placeholders", action="store_true")
    f = sub.add_parser("finish"); f.add_argument("--summary"); f.add_argument("--by", help="who ran it, e.g. Claude")
    sub.add_parser("status")
    x = a.parse_args()
    {"setup": setup, "plan": plan, "apply": apply, "finish": finish, "status": status}[x.step](x)


if __name__ == "__main__":
    main()
