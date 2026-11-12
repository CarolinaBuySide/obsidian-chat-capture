#!/usr/bin/env python3
"""Create or append an Obsidian note through the Local REST API plugin.

Usage:  python3 save_note.py "<vault/relative/path.md>" [--vault DIR] [--raw] [--dry-run] < note.md
Env:    OBSIDIAN_API_KEY  (required unless --vault is given)  API key from Settings > Local REST API
        OBSIDIAN_URL      (optional)  default https://127.0.0.1:27124
        OBSIDIAN_CA       (optional)  path to the plugin's .crt; if unset, TLS
                                      verification is skipped for localhost only
--vault DIR  read the API key from DIR/.obsidian/plugins/obsidian-local-rest-api/data.json
             (never printed) when OBSIDIAN_API_KEY is unset
--raw        append the body as-is instead of under a heading (for one-line pointers)
Never overwrites: if the note exists, the body is appended under "## Update HH:MM".
"""
import datetime, json, os, ssl, sys, urllib.error, urllib.parse, urllib.request


def fail(msg, code=1):
    print(f"save_note: {msg}", file=sys.stderr)
    sys.exit(code)


def main():
    argv = sys.argv[1:]
    vault = None
    if "--vault" in argv:
        i = argv.index("--vault")
        if i + 1 >= len(argv):
            fail("--vault needs a directory", 2)
        vault = os.path.expanduser(argv[i + 1])
        del argv[i:i + 2]
    dry = "--dry-run" in argv
    raw = "--raw" in argv
    args = [a for a in argv if a not in ("--dry-run", "--raw")]
    if len(args) != 1 or not args[0].endswith(".md"):
        fail('usage: save_note.py "<folder/Note.md>" [--vault DIR] [--raw] [--dry-run] < body.md', 2)
    path = args[0].lstrip("/")
    if ".." in path.split("/"):
        fail("path must stay inside the vault", 2)
    body = sys.stdin.read()
    if not body.strip():
        fail("empty note body on stdin", 2)

    base = os.environ.get("OBSIDIAN_URL", "https://127.0.0.1:27124").rstrip("/")
    key = os.environ.get("OBSIDIAN_API_KEY")
    if not key and vault:
        cfg = os.path.join(vault, ".obsidian", "plugins", "obsidian-local-rest-api", "data.json")
        try:
            with open(cfg) as f:
                key = json.load(f).get("apiKey")
        except (OSError, ValueError):
            fail(f"cannot read the API key from the plugin settings in {vault}")
    if not key and not dry:
        fail("set OBSIDIAN_API_KEY or pass --vault <vault path>")
    host = urllib.parse.urlparse(base).hostname
    ctx = None
    if base.startswith("https"):
        ca = os.environ.get("OBSIDIAN_CA")
        if ca:
            ctx = ssl.create_default_context(cafile=ca)
        elif host in ("127.0.0.1", "localhost"):
            ctx = ssl._create_unverified_context()  # self-signed local cert
        else:
            ctx = ssl.create_default_context()

    url = f"{base}/vault/{urllib.parse.quote(path)}"
    headers = {"Authorization": f"Bearer {key}"} if key else {}

    def call(method, data=None):
        req = urllib.request.Request(url, data=data, method=method, headers=dict(headers))
        if data is not None:
            req.add_header("Content-Type", "text/markdown")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except urllib.error.URLError as e:
            fail(f"cannot reach Obsidian at {base} ({e.reason}). Is Obsidian open with the plugin enabled?")

    if dry:
        print(f"[dry-run] would create or append: {path} ({len(body)} chars)")
        return
    status, existing = call("GET")
    if status == 401:
        fail("API key rejected (401)")
    if status == 200:
        if raw:
            sep = "" if existing.endswith("\n") else "\n"
            s, _ = call("POST", f"{sep}{body.strip()}\n".encode())
        else:
            stamp = datetime.datetime.now().strftime("%H:%M")
            s, _ = call("POST", f"\n\n## Update {stamp}\n\n{body.strip()}\n".encode())
        action = "appended to"
    elif status == 404:
        s, _ = call("PUT", body.encode())
        action = "created"
    else:
        fail(f"unexpected status {status} reading {path}")
    if s not in (200, 204):
        fail(f"write failed with status {s}")
    print(f"Saved to Obsidian ({action}): {path}")


if __name__ == "__main__":
    main()
