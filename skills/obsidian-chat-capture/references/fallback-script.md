# Fallback script

`scripts/save_note.py` creates a note, or appends to it if it exists. Pipe the body to stdin:

```bash
python3 scripts/save_note.py "11 AI Chats/2026-09-29 - Topic.md" < note.md
```

- **Key:** it reads `OBSIDIAN_API_KEY`, or with `--vault <vault path>` reads the key from the plugin's settings file. Never print that file; it also holds the plugin's TLS private key.
- **Append style:** appends go under `## Update HH:MM`; add `--raw` to append the body as-is, such as a one-line pointer in a hub note.
- **Preview:** add `--dry-run`.

`scripts/clip_capture.py` is the Mac-side watcher for write path 3: it saves any copied block that starts with `obsidian-capture:` into the capture folder, never overwrites, and refuses text that looks like a key or ID number. Setup is in `references/setup.md`.
