#!/usr/bin/env python3
"""Register a built vault with Obsidian, turn its plugins on, and check that it renders.

Run these in order. Nothing here needs the user to click through Obsidian's settings.

  python3 scripts/obsidian_setup.py register "<vault>"   # Obsidian must be quit
  (open Obsidian; the vault opens on its own)
  python3 scripts/obsidian_setup.py enable "<vault>"     # Obsidian must be running
  python3 scripts/obsidian_setup.py check "<vault>"      # Obsidian must be running

register  backs up Obsidian's obsidian.json, turns on its command-line interface
          (Settings -> General -> Advanced -> Command line interface) and adds the vault
          to the vault list so it opens next launch. Existing vaults are left alone.
enable    turns Restricted mode off for this vault, enables every plugin listed in
          .obsidian/community-plugins.json and turns on Templater's
          "Trigger Templater on new file creation".
check     looks inside the running app: plugins loaded, color snippet on, a new note gets
          its template, Home and both calendars render, the graph plugin is live and, if
          installed, the Local REST API answers. Exit code 0 means everything passed.

Needs Obsidian 1.12 or newer (the first version with the command-line interface).
Standard library only. Run end to end on Linux; the same Obsidian commands were used by hand
on macOS. Windows paths are included but untested.
"""
import argparse, json, os, pathlib, platform, secrets, shutil, ssl, subprocess, sys, time, urllib.request

SYSTEM = platform.system()


def config_dir():
    if SYSTEM == "Darwin":
        return pathlib.Path.home() / "Library/Application Support/obsidian"
    if SYSTEM == "Windows":
        return pathlib.Path(os.environ.get("APPDATA", pathlib.Path.home() / "AppData/Roaming")) / "obsidian"
    return pathlib.Path(os.environ.get("XDG_CONFIG_HOME", pathlib.Path.home() / ".config")) / "obsidian"


def obsidian_running():
    try:
        if SYSTEM == "Windows":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Obsidian.exe"], capture_output=True, text=True).stdout
            return "Obsidian.exe" in out
        return subprocess.run(["pgrep", "-x", "-i", "obsidian"], capture_output=True).returncode == 0
    except OSError:
        return False


def find_cli(override=None):
    if override:
        return override
    home, local = pathlib.Path.home(), pathlib.Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        "/Applications/Obsidian.app/Contents/MacOS/obsidian-cli",
        home / "Applications/Obsidian.app/Contents/MacOS/obsidian-cli",
        local / "Programs/Obsidian/Obsidian.com", local / "Obsidian/Obsidian.com",
        "/opt/Obsidian/obsidian-cli", "/usr/lib/obsidian/obsidian-cli",
    ]
    for c in candidates:
        if str(c) not in ("", ".") and pathlib.Path(c).is_file():
            return str(c)
    for name in ("obsidian-cli", "obsidian", "Obsidian.com"):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit("Could not find Obsidian's command-line tool. Pass it with --cli <path> "
             "(macOS: /Applications/Obsidian.app/Contents/MacOS/obsidian-cli), or use the manual steps in "
             "00 Home/Plugin Setup Checklist.")


class App:
    def __init__(self, vault, cli):
        self.vault, self.name, self.cli = vault, vault.name, find_cli(cli)

    def run(self, *args, timeout=90):
        r = subprocess.run([self.cli, f"vault={self.name}", *args], capture_output=True, text=True,
                           timeout=timeout, cwd=pathlib.Path.home())
        return (r.stdout + r.stderr).strip()

    def js(self, code, timeout=90):
        out = self.run("eval", "code=" + code, timeout=timeout)
        if "=> " not in out:
            raise RuntimeError(out or "no answer from Obsidian")
        return json.loads(out.split("=> ", 1)[1])

    def require(self):
        out = self.run("vaults")
        if "not enabled" in out.lower():
            sys.exit("Obsidian's command-line interface is off. Quit Obsidian and run the register step first.")
        if self.name not in [line.strip() for line in out.splitlines()]:
            sys.exit(f'Obsidian is not running with the vault "{self.name}" known to it. Run the register step, '
                     f"then open Obsidian.\nObsidian said: {out[:300]}")


def register(vault, force=False):
    if obsidian_running() and not force:
        sys.exit("Quit Obsidian first (it rewrites its settings on exit and would undo this), then run register again.")
    cfg_dir = config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg_dir / "obsidian.json"
    data = json.loads(cfg.read_text()) if cfg.is_file() and cfg.read_text().strip() else {}
    if cfg.is_file():
        backup = cfg.with_name(f"obsidian.json.backup-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(cfg, backup)
        print(f"Backed up Obsidian's settings to {backup}")
    data["cli"] = True
    vaults = data.setdefault("vaults", {})
    for v in vaults.values():
        v.pop("open", None)
    existing = [k for k, v in vaults.items() if pathlib.Path(v.get("path", "")).expanduser() == vault]
    vid = existing[0] if existing else secrets.token_hex(8)
    vaults[vid] = {"path": str(vault), "ts": int(time.time() * 1000), "open": True}
    cfg.write_text(json.dumps(data))
    print(f"Registered {vault} and turned on Obsidian's command-line interface.")
    print("Now open Obsidian (macOS: open -a Obsidian). The vault opens on its own. Then run the enable step.")


def enable(app):
    app.require()
    wanted = json.loads((app.vault / ".obsidian/community-plugins.json").read_text())
    if "on" in app.run("plugins:restrict").lower().split():
        print(app.run("plugins:restrict", "off"))
        time.sleep(6)
    for attempt in range(3):
        on = set(app.run("plugins:enabled", "filter=community").split())
        missing = [p for p in wanted if p not in on and (app.vault / ".obsidian/plugins" / p / "main.js").is_file()]
        if not missing:
            break
        for p in missing:
            print(app.run("plugin:enable", f"id={p}", "filter=community"))
        time.sleep(3)
    not_installed = [p for p in wanted if not (app.vault / ".obsidian/plugins" / p / "main.js").is_file()]
    if not_installed:
        print("Not installed, so not enabled: " + ", ".join(not_installed) + " (run install_plugins.py).")
    # Templater keeps this switch per device in the app's local storage, not in data.json.
    app.js("(()=>{const k='templater-local-settings'; app.saveLocalStorage(k, Object.assign({}, "
           "app.loadLocalStorage(k)||{}, {trigger_on_file_creation:true})); return true;})()")
    app.run("plugin:reload", "id=templater-obsidian")
    time.sleep(2)
    print("Plugins are on and Templater fills in new notes. Next: the check step.")


CHECK_JS = r"""
(async()=>{
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const out = {};
  out.loaded = Object.keys(app.plugins.plugins);
  out.snippet = !!(app.customCss.enabledSnippets && app.customCss.enabledSnippets.has('color-coding'));
  out.restricted = !app.plugins.isEnabled();
  const t = '01 Fleeting/Templater test.md';
  const old = app.vault.getAbstractFileByPath(t); if (old) await app.vault.delete(old, true);
  await app.vault.create(t, ''); await wait(3000);
  const f = app.vault.getAbstractFileByPath(t);
  out.templater = (await app.vault.read(f)).startsWith('---\ntype: fleeting');
  await app.vault.delete(f, true);
  out.views = {};
  for (const [p, sel] of [['00 Home/Home.md', '.dataview'], ['00 Home/Weekly Calendar.md', "[class*='mwc-']"],
                          ['00 Home/To-Do Calendar.md', "[class*='mtc-']"]]) {
    const file = app.vault.getAbstractFileByPath(p);
    if (!file) { out.views[p] = {missing: true}; continue; }
    const leaf = app.workspace.getLeaf(false);
    await leaf.openFile(file, {state: {mode: 'preview'}}); await wait(5000);
    const el = leaf.view.containerEl;
    out.views[p] = {rendered: el.querySelectorAll(sel).length, errors: el.querySelectorAll('.dataview-error').length};
  }
  const home = app.vault.getAbstractFileByPath('00 Home/Home.md');
  if (home) await app.workspace.getLeaf(false).openFile(home, {state: {mode: 'preview'}});
  return JSON.stringify(out);
})()
"""


def check(app):
    app.require()
    wanted = json.loads((app.vault / ".obsidian/community-plugins.json").read_text())
    r = app.js(CHECK_JS, timeout=150)
    results = []
    for p in wanted:
        results.append((f"plugin loaded: {p}", p in r["loaded"]))
    results.append(("Restricted mode is off", not r["restricted"]))
    results.append(("color-coding snippet is on", r["snippet"]))
    results.append(("a new note gets its template (Templater)", r["templater"]))
    for path, v in r["views"].items():
        ok = not v.get("missing") and v["rendered"] > 0 and v["errors"] == 0
        results.append((f"renders without errors: {path}", ok))
    if "obsidian-local-rest-api" in wanted:
        try:
            req = urllib.request.Request("https://127.0.0.1:27124/")
            with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=10) as resp:
                ok = json.loads(resp.read()).get("status") == "OK"
        except Exception:
            ok = False
        results.append(("Local REST API answers on https://127.0.0.1:27124", ok))
    for label, ok in results:
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
    bad = [label for label, ok in results if not ok]
    print("PASS" if not bad else f"{len(bad)} check(s) failed")
    sys.exit(0 if not bad else 1)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("step", choices=["register", "enable", "check"])
    a.add_argument("vault")
    a.add_argument("--cli", help="path to Obsidian's command-line tool, if it is not found automatically")
    a.add_argument("--force", action="store_true", help="register even if Obsidian seems to be running")
    x = a.parse_args()
    vault = pathlib.Path(x.vault).expanduser().resolve()
    if not (vault / ".obsidian").is_dir():
        sys.exit(f"{vault} is not an Obsidian vault (no .obsidian folder).")
    if x.step == "register":
        register(vault, x.force)
    elif x.step == "enable":
        enable(App(vault, x.cli))
    else:
        check(App(vault, x.cli))


if __name__ == "__main__":
    main()
