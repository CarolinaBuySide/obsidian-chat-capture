#!/usr/bin/env python3
"""Clipboard capture for Obsidian (macOS). Copy a note, and it lands in your vault.

When the clipboard starts with a line like
    obsidian-capture: AI Chats/2026-09-29 - Topic.md
the rest of the clipboard is saved to that path inside the vault's capture
folder. An existing note is never overwritten: new text is appended under
"## Update HH:MM". Anything else on the clipboard is ignored and never logged.

Usage:
    python3 clip_capture.py --vault "/path/to/Vault" [--folder "11 AI Chats"]
    python3 clip_capture.py --vault ... --once      # process the current clipboard once
Runs on macOS (uses pbpaste and osascript). Standard library only; Python 3.8+.
"""
import argparse, datetime, hashlib, os, re, subprocess, sys, time

MARKER = re.compile(r"^\s*obsidian-capture:\s*(.+?\.md)\s*$", re.I)
SECRET = re.compile(
    r"(sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"
    r"|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|Bearer\s+[A-Za-z0-9._-]{24,}|\b\d{3}-\d{2}-\d{4}\b)")
BAD = re.compile(r'[\\:*?"<>|#^\[\]]')
MAX_BYTES = 200_000


def clipboard():
    try:
        return subprocess.run(["pbpaste"], capture_output=True, timeout=5).stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def notify(msg):
    subprocess.run(["osascript", "-e", 'on run argv', "-e",
                    'display notification (item 1 of argv) with title "Obsidian capture"', "-e", "end run", msg],
                   capture_output=True, timeout=10)


def log(logfile, msg):
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}\t{msg}\n")


def target_path(vault, folder, raw):
    """Map the marker path into <vault>/<folder>/<file>.md, refusing anything outside it."""
    name = raw.strip().replace("\\", "/").split("/")[-1]  # keep only the file name
    stem = BAD.sub("-", name[:-3]).strip(" .")
    if not stem:
        return None
    base = os.path.realpath(os.path.join(vault, folder))
    path = os.path.realpath(os.path.join(base, stem + ".md"))
    return path if os.path.dirname(path) == base else None


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def index_note(vault, path, moc="04 Maps/AI Chats MOC.md", heading="## Copied in from other apps"):
    """List a new note in the vault's AI Chats map, if it has one, so the note is not left unlinked."""
    moc_path = os.path.join(vault, moc)
    stem = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(moc_path, encoding="utf-8") as f:
            text = f.read()
        if f"[[{stem}" in text:
            return
        line = f"- [[{stem}]]\n"
        if heading in text:
            head, rest = text.split(heading, 1)
            first, _, after = rest.partition("\n")
            text = head + heading + first + "\n" + line + after
        elif "\n← [[Home]]" in text:
            head, tail = text.rsplit("\n← [[Home]]", 1)
            text = head.rstrip("\n") + f"\n\n{heading}\n{line}\n← [[Home]]" + tail
        else:
            text = text.rstrip("\n") + f"\n\n{heading}\n{line}"
        with open(moc_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    except OSError:
        pass


def handle(text, vault, folder, logfile, notify_fn=notify):
    """Return a short status string. Writes at most one file."""
    vault = os.path.realpath(vault)
    lines = text.lstrip("\ufeff").split("\n", 1)
    m = MARKER.match(lines[0]) if lines else None
    if not m:
        return "ignored"
    body = (lines[1] if len(lines) > 1 else "").strip("\n")
    body = re.sub(r"^```[a-z]*\n|\n```\s*$", "", body)  # tolerate copied code fences
    if not body.strip():
        return "empty"
    if len(body.encode()) > MAX_BYTES:
        notify_fn("Not saved: the note is too large.")
        log(logfile, "skipped (too large)")
        return "too-large"
    if SECRET.search(body):
        notify_fn("Not saved: the note looks like it contains a key or ID number. Remove it and copy again.")
        log(logfile, "skipped (possible secret)")
        return "secret"
    path = target_path(vault, folder, m.group(1))
    if not path:
        log(logfile, "skipped (bad path)")
        return "bad-path"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rel = os.path.relpath(path, vault)
    if os.path.exists(path):
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Update {datetime.datetime.now():%H:%M}\n\n{strip_frontmatter(body).strip()}\n")
        action = "Added to"
    else:
        with open(path, "x", encoding="utf-8") as f:
            f.write(body.rstrip() + "\n")
        action = "Saved"
        index_note(vault, path)
    log(logfile, f"{action.lower()}\t{rel}")
    notify_fn(f"{action} {rel}")
    return action.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--folder", default="11 AI Chats")
    ap.add_argument("--interval", type=float, default=1.5)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--log", default=os.path.expanduser("~/Library/Logs/obsidian-clip-capture.log"))
    a = ap.parse_args()
    vault = os.path.realpath(os.path.expanduser(a.vault))
    if not os.path.isdir(os.path.join(vault, ".obsidian")):
        sys.exit(f"Not an Obsidian vault: {vault}")
    if a.once:
        print(handle(clipboard(), vault, a.folder, a.log))
        return
    seen = hashlib.sha256(clipboard().encode()).hexdigest()  # don't re-save whatever is already copied
    log(a.log, f"started, watching for 'obsidian-capture:' -> {a.folder}")
    while True:
        time.sleep(a.interval)
        text = clipboard()
        h = hashlib.sha256(text.encode()).hexdigest()
        if h == seen:
            continue
        seen = h
        try:
            handle(text, vault, a.folder, a.log)
        except Exception as e:  # keep running; never log clipboard contents
            log(a.log, f"error: {type(e).__name__}")


if __name__ == "__main__":
    main()
