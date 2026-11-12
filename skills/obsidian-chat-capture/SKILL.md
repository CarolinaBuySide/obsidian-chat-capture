---
name: obsidian-chat-capture
description: "Save AI chat takeaways to an Obsidian vault as linked notes via Local REST API: memory-first setup, append-only, secrets redacted. Use for 'save this chat to Obsidian', 'log this conversation', connecting an AI app, and, in Claude apps, right after any substantive answer. Not for importing chat exports."
license: MIT
compatibility: "Needs Obsidian desktop with the 'Local REST API with MCP' plugin (v5+) and an MCP client connected to it, or Python 3 for the fallback script. Works in any Agent Skills host."
metadata:
  author: Marc Rainone
  version: "1.5.1"
---

# Obsidian Chat Capture

Turn the useful part of a conversation into one short, linked note in the user's Obsidian vault. Capture decisions, insights and next steps, not transcripts.

## When to save

- The user says "save this", "log this", "add to Obsidian", or similar: save now.
- **Claude apps** (Claude Desktop, Claude Code, claude.ai on web or mobile): auto-save without being asked, even with no custom instructions. Save right after your first substantive answer in a chat (a decision, plan, checklist, analysis, research findings or tasks); don't wait for the chat to end, because chats rarely signal an end. Hosts that merely run a Claude model, such as Perplexity, don't count.
- **Other apps**: auto-save that way only when the user's custom instructions ask for automatic capture.
- Keep one note per chat: if a saved chat continues with new substance, append to that note. Skip small talk, one-line lookups, and scheduled or automated runs with no one chatting, unless the task asks to save.
- Otherwise, offer once near the end of a substantive chat. Never nag.

## Check memory first

Before choosing a write path or mentioning setup, search the host's memory and notes for the user's Obsidian setup: vault path, plugin, capture folder, clipboard watcher and hub notes such as `AI Context`.
- If memory says it is installed, use it. Never give install or connection steps, and never ask for a URL or API key.
- If this session cannot reach the vault, name what is unreachable, use path 3 below, and do not blame the setup.

## Pick the write path

1. **MCP tools available** (`vault_list`, `vault_read`, `vault_write`, `vault_append`, `search_simple` from the `obsidian` server): use them.
2. **Shell on the same computer as Obsidian, including a paired-device shell, but no MCP**: run `scripts/save_note.py`; read `references/fallback-script.md` first for its key and append options. A cloud code sandbox is not that computer.
3. **Neither** (for example ChatGPT on the web, or a phone app): cloud-hosted apps cannot reach `localhost`, so do not ask for a URL, API key or tunnel, and do not say the save failed. Output one Markdown code block whose first line is `obsidian-capture: <target path>`, followed by the finished note. Tell the user to click **Copy**: if they run the `scripts/clip_capture.py` clipboard watcher on their Mac, the note saves itself without overwriting; otherwise they paste it into a new note at that path.
4. **Memory has no setup and tools are missing, or the user asks how to connect an app**: read `references/setup.md`.

## Save a note

1. **Find the folder.** `vault_list` the vault root. Use the existing folder whose name ends in `AI Chats` (for example `11 AI Chats`). If there isn't one, create notes in `AI Chats/`.
2. **Name the file** `YYYY-MM-DD - <Topic in Title Case>.md`, using today's date and a 3–7 word topic. Strip `\ / : * ? " < > | # ^ [ ]`.
3. **Find links.** Run `search_simple` for 2–4 key names from the chat, such as a project, course, company or person. Link only to notes that exist, as `[[Exact Note Name]]`. Never invent links.
4. **Fill `templates/chat-note.md`.** Keep the body under about 300 words. Write tasks as `- [ ] task [due:: YYYY-MM-DD]` only when a date was stated.
5. **Never overwrite.** This applies to every write: chat, literature and hub notes. `vault_read` the target path first. Call `vault_write` only when the read finds no note; never rewrite an existing note, even with its old text included, and never edit its frontmatter. If the note exists, `vault_append` instead: a `## Update HH:MM` section for new content, or one bare line for a pointer added to a hub note.
6. **Confirm** in one line with the vault path, for example `Saved to Obsidian: 11 AI Chats/2026-09-29 - HFAC Pitch Catalysts.md`.

## Dated events

If the chat revealed a dated call, meeting, interview, appointment, exam or class change, save the note first, then read `references/calendar.md` and add the event to the vault's calendar. Deadlines stay dated tasks in the note.

## Never save

- API keys, passwords, tokens, recovery phrases, card numbers, government ID numbers or account numbers. Replace them with `[redacted]`.
- Third parties' private details (client data, health or financial information) unless the user explicitly asks. Ask first when unsure.
- Raw transcripts, or quotes longer than two sentences.

Do not delete, move or rename existing vault notes as part of capture.
