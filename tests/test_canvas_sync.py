#!/usr/bin/env python3
"""End-to-end test of the Canvas sync against a fake Canvas (tests/mock_canvas.py). No school account needed.

Usage: python3 tests/test_canvas_sync.py        Prints PASS at the end, or stops at the first failure.
Runs on macOS, Windows and Linux with only the standard library.
"""
import os, pathlib, subprocess, sys, tempfile, time, urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
PORT = 8765
T = pathlib.Path(tempfile.mkdtemp())
V = T / "vault"
S = V / "13 Calendar/System/canvas-sync"
ENV = {**os.environ, "CANVAS_SYNC_CONFIG": str(T / "config.json"), "PYTHONUTF8": "1"}
server = None


def py(*args, stdin=None, quiet=True):
    r = subprocess.run([sys.executable, *map(str, args)], env=ENV, input=stdin, text=True, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(map(str, args))}\n{r.stdout}\n{r.stderr}")
    if not quiet:
        print(r.stdout.strip())
    return r.stdout


def serve(stage):
    global server
    if server:
        server.kill(); server.wait()
    server = subprocess.Popen([sys.executable, str(REPO / "tests/mock_canvas.py"), "--port", str(PORT), "--files",
                               str(REPO / "tests/fixtures"), "--stage", str(stage)])
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1); return
        except OSError:
            time.sleep(0.2)
    sys.exit("the fake Canvas did not start")


def sync(*apply_flags):
    py(S / "sync.py", "plan"); py(S / "sync.py", "apply", *apply_flags); py(S / "sync.py", "finish", "--by", "test")


def check(ok, what):
    if not ok:
        sys.exit(f"FAILED: {what}")


def git(*args):
    return subprocess.run(["git", "-C", str(V), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.quotepath=off", *args],
                          capture_output=True, text=True, encoding="utf-8").stdout


try:
    py(REPO / "scripts/build_vault.py", "--answers", REPO / "blueprint/answers.example.json", "--dest", V)
    serve(1)
    py(S / "canvas_api.py", "login", "--host", f"127.0.0.1:{PORT}", "--token-stdin", stdin="test-token\n")
    py(S / "sync.py", "setup", quiet=False)
    sync("--keep-placeholders")
    D = V / "12 School/Fall 2026/ECON 325 - Entrepreneurship"
    moc = lambda: (V / "04 Maps/ECON 325 MOC.md").read_text(encoding="utf-8")
    check((D / "02 Lecture Slides/Lecture 1 - Finding Opportunities.pptx").is_file(), "lecture deck imported")
    check((D / "02 Lecture Slides/ECON 325 - Lecture 1 - Finding Opportunities.md").is_file(), "lecture note written")
    check((D / "03 Readings & Cases/Case - Lemonade Stand.pdf").is_file(), "file linked from an announcement imported")
    check(not list(D.rglob("banner.png")), "images are skipped")
    check("Business Model Canvas" in moc() and "Attendance" not in moc(), "deadlines added, attendance ignored")
    check("Lemonade Stand" in (V / "13 Calendar/Prep/ECON 325 Prep.md").read_text(encoding="utf-8"), "reading became a prep task")
    print("ok: first sync imported files, deadlines, a lecture note and a prep task")
    git("add", "-A"); git("commit", "-qm", "after first sync")
    sync()
    changed = [l[3:].strip('"') for l in git("status", "--short").splitlines()]
    check(changed == ["13 Calendar/System/canvas-sync/state.json"], f"a no-change sync edits only state.json (got {changed})")
    print("ok: a sync with no Canvas changes edits only state.json")
    before = [l for l in moc().splitlines() if "Business Model Canvas" in l]
    serve(2)
    sync("--keep-placeholders")
    check([l for l in moc().splitlines() if "Business Model Canvas" in l] != before and "Canvas moved it" in moc(), "moved due date")
    check((D / "02 Lecture Slides/Lecture 2 - Customer Discovery.pptx").is_file(), "new deck imported")
    print("ok: a moved due date and a new deck came through")
    out = py(REPO / "scripts/verify_vault.py", V)
    check(out.strip().endswith("PASS"), "vault verifies after syncing")
    leaked = [p for p in V.rglob("*") if p.is_file() and p.suffix in {".md", ".json", ".py"} and "test-token" in p.read_text(encoding="utf-8", errors="ignore")]
    check(not leaked, f"no token in the vault (found in {leaked})")
    print("ok: vault still verifies and holds no token")
    print("PASS")
finally:
    if server:
        server.kill()
