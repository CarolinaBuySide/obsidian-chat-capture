#!/usr/bin/env python3
"""Small helper for Obsidian's Local REST API (run on the vault's computer while Obsidian is open).

The API key is read from the plugin's settings at run time and never printed or stored anywhere else.
Usage: python3 "<vault>/13 Calendar/System/canvas-sync/obsidian_api.py" <action> [arg]
  commands <filter>      list command ids containing <filter>
  run <command-id>       run a command, e.g. obsidian-git:commit (a Git checkpoint)
  open <vault path>      open a note in Obsidian (add "new" to open it in a new tab)
Exit code 2 means Obsidian (or its Local REST API plugin) isn't reachable.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SETTINGS = os.path.join(VAULT, ".obsidian", "plugins", "obsidian-local-rest-api", "data.json")
BASE = "https://127.0.0.1:27124"
CTX = ssl._create_unverified_context()  # the plugin uses a self-signed certificate on localhost


def call(method, path):
    with open(SETTINGS, encoding="utf-8") as f:
        key = json.load(f).get("apiKey")
    req = urllib.request.Request(BASE + path, method=method, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]


def main():
    args = sys.argv[1:]
    act = args[0] if args else ""
    try:
        if act == "commands":
            status, body = call("GET", "/commands/")
            flt = (args[1] if len(args) > 1 else "").lower()
            for c in json.loads(body).get("commands", []):
                if flt in (c["id"] + " " + c["name"]).lower():
                    print(c["id"], "|", c["name"])
        elif act == "run" and len(args) > 1:
            status, body = call("POST", "/commands/" + urllib.parse.quote(args[1], safe="") + "/")
            print("status", status, body[:200])
        elif act == "open" and len(args) > 1:
            extra = "?newLeaf=true" if len(args) > 2 and args[2] == "new" else ""
            status, body = call("POST", "/open/" + urllib.parse.quote(args[1]) + extra)
            print("status", status, body[:200])
        else:
            print(__doc__)
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        print("Obsidian isn't reachable:", e)
        sys.exit(2)


if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    main()
