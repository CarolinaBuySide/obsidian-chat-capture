#!/usr/bin/env python3
"""Pack the files the Canvas sync needs into one archive (run on the computer that holds the vault; it only reads the vault).

Usage: python3 "<vault>/13 Calendar/System/canvas-sync/pack_inputs.py" [--out /tmp/canvas_sync_inputs.tgz]
Prints each packed note with its sha256. Use those hashes as expected_sha256 when writing a file back.

Version 2 also packs each course's Materials note, class note and notes inside the course folder,
the event notes in 13 Calendar/Events (for breaks), and vault_manifest.json: every file in each course folder
with its size and modified time, so the planner can tell which Canvas files are already in the vault.
Course files themselves (PDF, PowerPoint, Word) are listed, not packed.
"""
import hashlib
import io
import json
import os
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/tmp/canvas_sync_inputs.tgz"
SKIP_NAMES = {".DS_Store"}

with open(os.path.join(HERE, "courses.json"), encoding="utf-8") as f:
    cfg = json.load(f)

paths = ["13 Calendar/System/canvas-sync/" + n for n in sorted(os.listdir(HERE)) if n.endswith((".py", ".js", ".json"))]
manifest = {}
for c in cfg.get("courses", []) + cfg.get("watch_only", []):
    for key in ("map", "prep", "materials", "class", "note"):
        if c.get(key):
            paths.append(c[key])
    folder = c.get("folder")
    if not folder:
        continue
    files = []
    root = os.path.join(VAULT, folder)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for n in filenames:
            if n in SKIP_NAMES or n.startswith("~$") or n.startswith("._"):
                continue
            full = os.path.join(dirpath, n)
            rel = os.path.relpath(full, VAULT)
            st = os.stat(full)
            files.append({"path": rel, "size": st.st_size, "mtime": int(st.st_mtime)})
            if n.endswith(".md"):
                paths.append(rel)
    manifest[folder] = sorted(files, key=lambda x: x["path"])
events_dir = os.path.join(VAULT, "13 Calendar", "Events")
if os.path.isdir(events_dir):
    paths += ["13 Calendar/Events/" + n for n in sorted(os.listdir(events_dir)) if n.endswith(".md")]
paths += ["04 Maps/Calendar MOC.md", "13 Calendar/To-Do.md"]

packed = []
with tarfile.open(OUT, "w:gz") as tar:
    for p in paths:
        if not p or p in packed:
            continue
        full = os.path.join(VAULT, p)
        if not os.path.isfile(full):
            print("missing", p)
            continue
        tar.add(full, arcname=p)
        packed.append(p)
        with open(full, "rb") as fh:
            print(hashlib.sha256(fh.read()).hexdigest(), p)
    data = json.dumps(manifest, indent=1).encode("utf-8")
    info = tarfile.TarInfo("vault_manifest.json")
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))
print(f"packed {len(packed)} files and vault_manifest.json ({sum(len(v) for v in manifest.values())} course files listed) into {OUT}")
