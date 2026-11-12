#!/usr/bin/env python3
"""Download the community plugins the vault uses, so they load the first time it opens.

Usage:
  python3 scripts/install_plugins.py "<vault>"                       # the standard set
  python3 scripts/install_plugins.py "<vault>" --smart-connections   # plus Smart Connections
  python3 scripts/install_plugins.py "<vault>" --obsidian-skills     # plus kepano's Obsidian syntax skills

It reads <vault>/.obsidian/community-plugins.json and installs every listed plugin it knows.
Graph Groups ships inside the template, so it is never downloaded. Like Obsidian's plugin
browser, it reads each plugin's manifest.json on GitHub and downloads that release's files.
Standard library only; works on macOS, Windows and Linux.
"""
import os
import argparse, io, json, pathlib, sys, tarfile, urllib.request

if os.name == "nt":  # Obsidian notes use plain \n line endings; stop Windows from writing \r\n
    def _write_lf(self, data, encoding="utf-8", errors=None, newline=None):
        with open(self, "w", encoding=encoding, errors=errors, newline="\n") as f:
            return f.write(data)
    pathlib.Path.write_text = _write_lf

REPOS = {
    "dataview": "blacksmithgu/obsidian-dataview",
    "templater-obsidian": "SilentVoid13/Templater",
    "calendar": "liamcain/obsidian-calendar-plugin",
    "obsidian-git": "Vinzent03/obsidian-git",
    "obsidian-local-rest-api": "coddingtonbear/obsidian-local-rest-api",
    "smart-connections": "brianpetro/obsidian-smart-connections",
}
BUNDLED = {"graph-groups"}
SKILLS_REPO = "kepano/obsidian-skills"
SKILLS = ["obsidian-markdown", "obsidian-bases", "json-canvas"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "obsidian-vault-blueprint"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def install(plugin_dir, pid):
    repo = REPOS[pid]
    version = json.loads(get(f"https://raw.githubusercontent.com/{repo}/HEAD/manifest.json"))["version"]
    dest = plugin_dir / pid
    dest.mkdir(parents=True, exist_ok=True)
    base = f"https://github.com/{repo}/releases/download/{version}"
    for name, required in (("main.js", True), ("manifest.json", True), ("styles.css", False)):
        try:
            (dest / name).write_bytes(get(f"{base}/{name}"))
        except Exception:
            if required:
                raise
    return version


def install_skills(vault):
    """Copy kepano/obsidian-skills (MIT) into .claude/skills, as in the original vault."""
    dest = vault / ".claude" / "skills"
    tar = tarfile.open(fileobj=io.BytesIO(get(f"https://codeload.github.com/{SKILLS_REPO}/tar.gz/HEAD")), mode="r:gz")
    done = set()
    for m in tar.getmembers():
        parts = pathlib.PurePosixPath(m.name).parts[1:]
        if not m.isfile() or not parts:
            continue
        if parts == ("LICENSE",):
            out = dest / "KEPANO-OBSIDIAN-SKILLS-LICENSE.txt"
        elif "skills" in parts[:-2] and parts[parts.index("skills") + 1] in SKILLS:
            i = parts.index("skills") + 1  # works wherever the repo keeps its skills folder
            out = dest.joinpath(*parts[i:]); done.add(parts[i])
        else:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(tar.extractfile(m).read())
    if not done:
        raise RuntimeError(f"no skills found in {SKILLS_REPO}; its layout may have changed")
    return sorted(done)


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("vault")
    a.add_argument("--smart-connections", action="store_true", help="also install and list Smart Connections")
    a.add_argument("--obsidian-skills", action="store_true", help="also add kepano/obsidian-skills to .claude/skills")
    x = a.parse_args()
    vault = pathlib.Path(x.vault).expanduser()
    cp = vault / ".obsidian" / "community-plugins.json"
    if not cp.is_file():
        sys.exit(f"Could not find {cp}. Pass the vault folder.")
    ids = json.loads(cp.read_text())
    if x.smart_connections and "smart-connections" not in ids:
        ids.insert(ids.index("obsidian-git") if "obsidian-git" in ids else len(ids), "smart-connections")
        cp.write_text(json.dumps(ids, indent=2) + "\n")
    failed = []
    for pid in ids:
        if pid in BUNDLED:
            print(f"  bundled    {pid}")
        elif pid not in REPOS:
            print(f"  skipped    {pid} (unknown; install it from Obsidian's plugin browser)")
        else:
            try:
                print(f"  installed  {pid} {install(vault / '.obsidian' / 'plugins', pid)}")
            except Exception as e:
                failed.append(pid); print(f"  FAILED     {pid}: {e}")
    if x.obsidian_skills:
        try:
            print(f"  skills     {', '.join(install_skills(vault))} (kepano/obsidian-skills)")
        except Exception as e:
            failed.append("obsidian-skills"); print(f"  FAILED     obsidian-skills: {e}")
    if failed:
        sys.exit("Could not download: " + ", ".join(failed) + ". Install those from Settings → Community plugins → Browse.")
    print("Done. Next: python3 scripts/obsidian_setup.py \"<vault>\" (registers the vault and turns the plugins on).")


if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    main()
