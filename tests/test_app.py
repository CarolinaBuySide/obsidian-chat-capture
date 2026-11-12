#!/usr/bin/env python3
"""Full product test with the real Obsidian app: build a vault, turn it on, save a chat, check colors.

  python3 tests/test_app.py                      # uses the Obsidian already installed
  python3 tests/test_app.py --install            # downloads the latest Obsidian first (for CI)
  python3 tests/test_app.py --watcher            # macOS: also installs and tests the clipboard watcher (CI only:
                                                 # it replaces the login item of anyone who already uses it)
  python3 tests/test_app.py --obsidian <path to the app's executable> --cli <path to its command-line tool>

It follows the same steps as AGENTS.md, in a throwaway vault, and prints PASS at the end.
Close Obsidian before running it. Works on macOS, Windows and Linux.
"""
import argparse, json, os, pathlib, platform, shutil, subprocess, sys, tempfile, threading, time, urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
SYSTEM = platform.system()
A = argparse.ArgumentParser(); A.add_argument("--install", action="store_true"); A.add_argument("--watcher", action="store_true")
A.add_argument("--obsidian"); A.add_argument("--cli")
X = A.parse_args()
T = pathlib.Path(tempfile.mkdtemp())
V = T / f"Blueprint Test Vault {os.getpid()}"
ENV = {**os.environ, "PYTHONUTF8": "1"}
procs = []


def step(msg):
    print(f"\n== {msg}", flush=True)


def py(*args, env=None, ok_codes=(0,), stdin=None):
    r = subprocess.run([sys.executable, *map(str, args)], env=env or ENV, text=True, capture_output=True, encoding="utf-8", input=stdin)
    print((r.stdout + r.stderr).strip(), flush=True)
    if r.returncode not in ok_codes:
        sys.exit(f"FAILED: {' '.join(map(str, args))}")
    return r.stdout


def install():
    """Download and install the latest Obsidian. Returns (executable, command-line tool or None)."""
    req = urllib.request.Request("https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest")
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    rel = json.load(urllib.request.urlopen(req))
    ver = rel["tag_name"].lstrip("v")
    asset = lambda name: next(a["browser_download_url"] for a in rel["assets"] if a["name"] == name)
    dl = T / "dl"; dl.mkdir()
    def fetch(name):
        print(f"downloading {name}", flush=True)
        urllib.request.urlretrieve(asset(name), dl / name); return dl / name
    if SYSTEM == "Darwin":
        dmg = fetch(f"Obsidian-{ver}.dmg")
        out = subprocess.run(["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly"], capture_output=True, text=True, check=True).stdout
        mount = out.strip().splitlines()[-1].split("\t")[-1]
        shutil.rmtree("/Applications/Obsidian.app", ignore_errors=True)
        subprocess.run(["cp", "-R", f"{mount}/Obsidian.app", "/Applications/"], check=True)
        subprocess.run(["hdiutil", "detach", mount], capture_output=True)
        return "/Applications/Obsidian.app/Contents/MacOS/Obsidian", None
    if SYSTEM == "Windows":
        exe = fetch(f"Obsidian-{ver}.exe")
        subprocess.run([str(exe), "/S"], check=True)
        local = pathlib.Path(os.environ["LOCALAPPDATA"])
        for _ in range(60):
            found = [p for d in (local / "Programs", local) for p in d.glob("[Oo]bsidian/Obsidian.exe")]
            if found:
                print("installed files:", sorted(p.name for p in found[0].parent.iterdir())[:40], flush=True)
                return str(found[0]), None
            time.sleep(2)
        sys.exit("Obsidian's installer finished but Obsidian.exe was not found")
    arch = "-arm64" if platform.machine() in ("aarch64", "arm64") else ""
    tar = fetch(f"obsidian-{ver}{arch}.tar.gz")
    shutil.unpack_archive(tar, dl)
    d = dl / f"obsidian-{ver}{arch}"
    return str(d / "obsidian"), str(d / "obsidian-cli")


def launch(exe):
    if SYSTEM == "Darwin":
        subprocess.run(["open", "-a", "Obsidian"], check=True)
    elif SYSTEM == "Windows":
        procs.append(subprocess.Popen([exe or "Obsidian.exe"], creationflags=0x00000008 | 0x00000200))
    else:
        cmd = [exe or "obsidian", "--no-sandbox", "--disable-gpu"]
        if not os.environ.get("DISPLAY"):
            cmd = ["xvfb-run", "-a", "-s", "-screen 0 1600x1000x24", *cmd]
        procs.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))


def quit_obsidian():
    if SYSTEM == "Windows":
        subprocess.run(["taskkill", "/F", "/IM", "Obsidian.exe"], capture_output=True)
    else:
        subprocess.run(["pkill", "-x", "-i", "obsidian"], capture_output=True)
    time.sleep(3)


def forget_vault():
    """Take the test vault back out of Obsidian's vault list, so a rerun does not reopen it."""
    home = pathlib.Path.home()
    for cfg in (home / "Library/Application Support/obsidian/obsidian.json", home / ".config/obsidian/obsidian.json",
                pathlib.Path(os.environ.get("APPDATA", home)) / "obsidian/obsidian.json"):
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            data["vaults"] = {k: v for k, v in data.get("vaults", {}).items() if pathlib.Path(v.get("path", "")) != V}
            cfg.write_text(json.dumps(data), encoding="utf-8")
        except (OSError, ValueError):
            pass


def mcp_roundtrip(config_path, note):
    """Do what an AI app does through the config that `connect` wrote: list, read, write, append, read back."""
    srv = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))["mcpServers"]["obsidian"]
    p = subprocess.Popen([srv["command"], *srv["args"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         env={**os.environ, **srv.get("env", {})}, text=True, encoding="utf-8")
    threading.Timer(180, p.kill).start()
    n = [0]
    def rpc(method, params=None, notify=False):
        n[0] += 1
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notify:
            msg["id"] = n[0]
        p.stdin.write(json.dumps(msg) + "\n"); p.stdin.flush()
        while not notify:
            line = p.stdout.readline()
            if not line:
                sys.exit("FAILED: the MCP bridge closed (is Node.js installed?)")
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("id") == n[0]:
                return m
    def tool(name, **args):
        r = rpc("tools/call", {"name": name, "arguments": args})
        if "error" in r:
            return None, True
        res = r["result"]
        return "".join(c.get("text", "") for c in res.get("content", [])), bool(res.get("isError"))
    rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "blueprint-test", "version": "1"}})
    rpc("notifications/initialized", notify=True)
    names = {t["name"] for t in rpc("tools/list")["result"]["tools"]}
    need = {"vault_list", "vault_read", "vault_write", "vault_append", "search_simple"}
    if not need <= names:
        sys.exit(f"FAILED: MCP server is missing tools {need - names}")
    listing, _ = tool("vault_list", path="")
    assert "11 AI Chats" in listing, "vault_list shows the capture folder"
    _, missing = tool("vault_read", path=note)
    assert missing, "the test note does not exist yet"
    body = "---\ntype: ai-chat\ntags: [ai-chat]\n---\n# MCP Test Chat\n\n## Takeaways\n- Saved through MCP.\n\n- Related: [[AI Chats MOC]]\n"
    _, err = tool("vault_write", path=note, content=body); assert not err, "vault_write"
    _, err = tool("vault_append", path=note, content="\n\n## Update 12:00\n\n- Appended, not overwritten.\n"); assert not err, "vault_append"
    text, err = tool("vault_read", path=note)
    assert not err and "Saved through MCP." in text and "Appended, not overwritten." in text, "read back both parts"
    # The skill's last step: one pointer line per chat in the map, so the note is not an orphan.
    _, err = tool("vault_append", path="04 Maps/AI Chats MOC.md",
                  content="\n- [[2026-01-01 - MCP Test Chat]] → [[Home]]\n- [[2026-01-02 - Script Test Chat]] → [[Home]]\n")
    assert not err, "pointer lines appended to the AI Chats map"
    p.kill()


try:
    quit_obsidian()
    exe, cli = X.obsidian, X.cli
    if X.install:
        step("Install Obsidian")
        exe, cli = install()
    cli_args = ["--cli", cli] if cli else []

    step("2. Build the vault")
    py(REPO / "scripts/build_vault.py", "--answers", REPO / "blueprint/answers.example.json", "--dest", V)
    step("3. Install the plugins")
    py(REPO / "scripts/install_plugins.py", V, "--obsidian-skills")
    step("4. Register, open Obsidian, enable, check")
    py(REPO / "scripts/obsidian_setup.py", "register", V)
    launch(exe)
    deadline = time.time() + 180
    while True:
        r = subprocess.run([sys.executable, str(REPO / "scripts/obsidian_setup.py"), "enable", str(V), *cli_args], env=ENV,
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            print(r.stdout.strip(), flush=True); break
        if time.time() > deadline:
            sys.exit("FAILED: Obsidian never became reachable.\n" + r.stdout + r.stderr)
        time.sleep(5)
    time.sleep(5)
    py(REPO / "scripts/obsidian_setup.py", "check", V, *cli_args)

    step("5. Chat capture")
    py(REPO / "scripts/setup_chat_capture.py", "test", V)
    fake = T / "home"; fake.mkdir()
    fake_env = {**ENV, "HOME": str(fake), "USERPROFILE": str(fake), "APPDATA": str(fake / "AppData/Roaming")}
    py(REPO / "scripts/setup_chat_capture.py", "connect", V, "--app", "claude-desktop", "--app", "cursor", "--app", "codex", env=fake_env)
    cfg = next(p for p in fake.rglob("claude_desktop_config.json"))
    note = "11 AI Chats/2026-01-01 - MCP Test Chat.md"
    mcp_roundtrip(cfg, note)
    assert (V / note).is_file(), "the note written through MCP is in the vault folder"
    print("ok: an MCP client using the config written by `connect` listed, wrote, appended and read a chat note")
    saved = subprocess.run([sys.executable, str(REPO / "skills/obsidian-chat-capture/scripts/save_note.py"), "11 AI Chats/2026-01-02 - Script Test Chat.md",
                            "--vault", str(V)], input="---\ntype: ai-chat\ntags: [ai-chat]\n---\n# Script Test Chat\n\n- Related: [[AI Chats MOC]]\n",
                           text=True, capture_output=True, encoding="utf-8", env=ENV)
    print(saved.stdout.strip() or saved.stderr.strip())
    assert saved.returncode == 0 and (V / "11 AI Chats/2026-01-02 - Script Test Chat.md").is_file(), "save_note.py saved a chat note"

    if X.watcher and SYSTEM == "Darwin":
        step("5b. Clipboard watcher (macOS)")
        py(REPO / "scripts/setup_chat_capture.py", "watcher", V)
        block = "obsidian-capture: 11 AI Chats/2026-01-03 - Clipboard Test Chat.md\n---\ntype: ai-chat\ntags: [ai-chat]\n---\n# Clipboard Test Chat\n\n- Related: [[AI Chats MOC]]\n"
        target = V / "11 AI Chats/2026-01-03 - Clipboard Test Chat.md"
        for _ in range(12):
            subprocess.run(["pbcopy"], input=block, text=True, check=True)
            time.sleep(5)
            if target.is_file():
                break
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/com.obsidian-chat-capture.clipboard"], capture_output=True)
        assert target.is_file(), "a copied note block was saved by the clipboard watcher"
        print("ok: a copied note block landed in 11 AI Chats")

    step("6. Calendar tool")
    out = py(V / "13 Calendar/System/add_event.py", "add", "--title", "Blueprint test call", "--date", "2030-01-15", "--start", "15:00", "--end", "15:30", "--kind", "call")
    out = py(V / "13 Calendar/System/add_event.py", "list", "--from", "2030-01-14", "--to", "2030-01-16")
    assert "Blueprint test call" in out, "add_event.py adds and lists an event"

    step("7. Verify the files")
    out = py(REPO / "scripts/verify_vault.py", V)
    assert out.strip().endswith("PASS"), "verify_vault.py passes after everything above"
    print("\nPASS")
finally:
    quit_obsidian()
    forget_vault()
    for p in procs:
        try: p.kill()
        except Exception: pass
