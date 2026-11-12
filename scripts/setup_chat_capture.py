#!/usr/bin/env python3
"""Connect AI apps to a vault so chat takeaways save into 11 AI Chats.

Run after obsidian_setup.py, with Obsidian open. The API key is read from the plugin's
settings file and written straight into each app's config. It is never printed, so an AI
running this script never sees it.

  python3 scripts/setup_chat_capture.py test "<vault>"
      Write, read back and delete a test note through the Local REST API.

  python3 scripts/setup_chat_capture.py connect "<vault>" --app claude-code
      Apps: claude-code, claude-desktop, cursor, codex. Repeat --app for several.
      Adds an MCP server named "obsidian" to the app's config (a backup is kept) and,
      where the app loads skills from a folder, copies the obsidian-chat-capture skill in.

  python3 scripts/setup_chat_capture.py watcher "<vault>"
      macOS only. Installs the clipboard watcher as a login item, so a note block copied
      from a cloud app (ChatGPT, a phone) saves itself into the vault.

  python3 scripts/setup_chat_capture.py instructions
      Print the one line to paste into an app's custom instructions for automatic capture.

Apps not listed here (Perplexity, ChatGPT, Claude on the web): see
skills/obsidian-chat-capture/references/setup.md. Standard library only.
"""
import argparse, json, os, pathlib, platform, shutil, ssl, subprocess, sys, time, urllib.error, urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "obsidian-chat-capture"
URL = "https://127.0.0.1:27124"
MCP = URL + "/mcp/"
LABEL = "com.obsidian-chat-capture.clipboard"
INSTRUCTION = ("After any substantive answer (a decision, plan, checklist, analysis, research or tasks), use the "
               "obsidian-chat-capture skill to save a short note to my Obsidian vault and tell me the path. "
               "Don't wait for the chat to end.")
CLOUD_INSTRUCTION = ("At the end of any substantive chat (decisions, plans, research or tasks), use the obsidian "
                     "chat capture skill to give me a copy-ready note block.")


def api_key(vault):
    cfg = vault / ".obsidian/plugins/obsidian-local-rest-api/data.json"
    try:
        key = json.loads(cfg.read_text()).get("apiKey")
    except (OSError, ValueError):
        key = None
    if not key:
        sys.exit("No API key yet. Open the vault in Obsidian with the Local REST API plugin enabled "
                 "(obsidian_setup.py enable), then run this again.")
    return key


def call(method, path, key, body=None):
    req = urllib.request.Request(URL + path, data=body, method=method, headers={"Authorization": f"Bearer {key}"})
    if body is not None:
        req.add_header("Content-Type", "text/markdown")
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except urllib.error.URLError as e:
        sys.exit(f"Cannot reach Obsidian at {URL} ({e.reason}). Is Obsidian open with this vault and the plugin enabled?")


def test(vault):
    key = api_key(vault)
    folder = next((p.name for p in sorted(vault.iterdir()) if p.is_dir() and p.name.endswith("AI Chats")), "AI Chats")
    rel = f"{folder}/Chat capture connection test.md"
    path = "/vault/" + urllib.request.quote(rel)
    if (vault / rel).exists():
        sys.exit(f"{rel} already exists; delete it and run the test again.")
    body = "---\ntype: ai-chat\ntags: [ai-chat]\n---\n# Chat capture connection test\n"
    steps = [("write", call("PUT", path, key, body.encode())[0] in (200, 204))]
    status, text = call("GET", path, key)
    steps.append(("read back", status == 200 and text == body))
    steps.append(("landed in the vault folder", (vault / rel).is_file()))
    steps.append(("delete", call("DELETE", path, key)[0] in (200, 204)))
    for label, ok in steps:
        print(f"  {'OK  ' if ok else 'FAIL'} {label}: {rel}")
    if not all(ok for _, ok in steps):
        sys.exit("Chat capture test failed. If 'landed in the vault folder' failed, Obsidian has a different vault open.")
    print("PASS: AI apps on this computer can save notes into " + folder)


def backup(p):
    if p.is_file():
        b = p.with_name(p.name + f".backup-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(p, b)
        print(f"  backed up {p} -> {b.name}")


def merge_json(p, server):
    data = json.loads(p.read_text()) if p.is_file() and p.read_text().strip() else {}
    backup(p)
    data.setdefault("mcpServers", {})["obsidian"] = server
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")


def copy_skill(dest_root):
    dest = dest_root / "obsidian-chat-capture"
    shutil.copytree(SKILL, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    print(f"  installed the skill at {dest}")


def need_node(app):
    if not shutil.which("npx"):
        print(f"  note: {app} reaches the vault through npx, which needs Node.js. Install Node.js (nodejs.org) first.")


def connect(vault, apps):
    key = api_key(vault)
    home = pathlib.Path.home()
    bearer = f"Authorization: Bearer {key}"
    remote = {"command": "npx", "args": ["-y", "mcp-remote@latest", MCP, "--header", bearer],
              "env": {"NODE_TLS_REJECT_UNAUTHORIZED": "0"}}
    for app in apps:
        print(f"{app}:")
        if app == "claude-code":
            if not shutil.which("claude"):
                print("  skipped: the `claude` command is not installed."); continue
            subprocess.run(["claude", "mcp", "remove", "--scope", "user", "obsidian"], capture_output=True)
            r = subprocess.run(["claude", "mcp", "add", "--scope", "user", "--transport", "http", "obsidian", MCP,
                                "--header", bearer], capture_output=True, text=True)
            print("  added the obsidian MCP server" if r.returncode == 0 else "  FAILED to add the MCP server (run `claude mcp list` to inspect)")
            copy_skill(home / ".claude" / "skills")
        elif app == "claude-desktop":
            if platform.system() == "Darwin":
                p = home / "Library/Application Support/Claude/claude_desktop_config.json"
            elif platform.system() == "Windows":
                p = pathlib.Path(os.environ.get("APPDATA", home / "AppData/Roaming")) / "Claude/claude_desktop_config.json"
            else:
                p = home / ".config/Claude/claude_desktop_config.json"
            need_node(app); merge_json(p, remote)
            print(f"  added the obsidian MCP server to {p}")
            print("  still to do by hand: zip skills/obsidian-chat-capture and upload it in Claude under Customize -> Skills, then restart Claude.")
        elif app == "cursor":
            p = home / ".cursor/mcp.json"
            merge_json(p, {"url": MCP, "headers": {"Authorization": f"Bearer {key}"}})
            print(f"  added the obsidian MCP server to {p}. Restart Cursor.")
        elif app == "codex":
            p = home / ".codex/config.toml"
            text = p.read_text() if p.is_file() else ""
            if "[mcp_servers.obsidian]" in text:
                print(f"  {p} already has [mcp_servers.obsidian]; left as it is.")
            else:
                backup(p); need_node(app)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text.rstrip("\n") + ("\n\n" if text.strip() else "") + "[mcp_servers.obsidian]\n"
                             'command = "npx"\n'
                             f'args = ["-y", "mcp-remote@latest", "{MCP}", "--header", "{bearer}"]\n'
                             'env = { NODE_TLS_REJECT_UNAUTHORIZED = "0" }\n')
                print(f"  added the obsidian MCP server to {p}")
            copy_skill(home / ".codex" / "skills")
    print("\nFor automatic capture, add this line to each app's custom instructions:\n  " + INSTRUCTION)


def watcher(vault):
    if platform.system() != "Darwin":
        sys.exit("The clipboard watcher is macOS only. On other systems, paste the copied note block into a new note.")
    home = pathlib.Path.home()
    app_dir = home / "Library/Application Support/obsidian-clip-capture"
    app_dir.mkdir(parents=True, exist_ok=True)
    script = app_dir / "clip_capture.py"
    shutil.copy2(SKILL / "scripts/clip_capture.py", script)
    plist = home / "Library/LaunchAgents" / f"{LABEL}.plist"
    plist.parent.mkdir(parents=True, exist_ok=True)
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>{esc(script)}</string>
    <string>--vault</string><string>{esc(vault)}</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardErrorPath</key><string>{esc(home / 'Library/Logs/obsidian-clip-capture.err')}</string>
</dict></plist>
""")
    uid = str(os.getuid())
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{LABEL}"], capture_output=True)
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"Wrote {plist} but could not start it: {r.stderr.strip()}\nStart it with: launchctl bootstrap gui/{uid} \"{plist}\"")
    print(f"Clipboard watcher is running and starts at login. Stop it with: launchctl bootout gui/{uid}/{LABEL}")
    print("For cloud apps such as ChatGPT, add this line to the app's custom instructions:\n  " + CLOUD_INSTRUCTION)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("step", choices=["test", "connect", "watcher", "instructions"])
    a.add_argument("vault", nargs="?")
    a.add_argument("--app", action="append", choices=["claude-code", "claude-desktop", "cursor", "codex"], default=[])
    x = a.parse_args()
    if x.step == "instructions":
        print("Apps that can reach the vault:\n  " + INSTRUCTION + "\n\nCloud apps (ChatGPT and others):\n  " + CLOUD_INSTRUCTION)
        return
    if not x.vault:
        a.error("pass the vault folder")
    vault = pathlib.Path(x.vault).expanduser().resolve()
    if not (vault / ".obsidian").is_dir():
        sys.exit(f"{vault} is not an Obsidian vault (no .obsidian folder).")
    if x.step == "test":
        test(vault)
    elif x.step == "connect":
        if not x.app:
            a.error("name at least one app with --app")
        connect(vault, x.app)
    else:
        watcher(vault)


if __name__ == "__main__":
    main()
