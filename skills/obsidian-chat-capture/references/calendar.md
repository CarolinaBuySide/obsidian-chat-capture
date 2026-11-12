# Calendar events from a chat

Read this when a chat revealed a dated call, meeting, interview, appointment, exam, trip or class change. Deadlines (work due by a date) stay tasks in the chat note instead.

1. Look for a vault calendar: a `13 Calendar/` folder and a calendar skill listed in the vault's `AGENTS.md` (for example `00 Home/Agent/Skills/Skill - Calendar Update.md`). If there is none, write the event as a dated task under Next steps and stop.
2. Save the chat note first, so the event can link back to it.
3. Add the event the way that skill says:
   - **Shell on the Obsidian computer:** from the vault root run
     `python3 "13 Calendar/System/add_event.py" add --title "…" --date YYYY-MM-DD --start HH:MM --end HH:MM --kind call --location "…" --source "<chat note name>" --by <host>`.
     It writes directly or through the Local REST API. Exit code 3 means a similar event already exists: run `update` on that note instead of adding a second one.
   - **MCP only:** `vault_read` the target first, `vault_write` `13 Calendar/Events/YYYY-MM-DD - Title.md` from the event template in that skill, then `vault_append` one log line to the calendar map it names.
   - **Path 3 (copy block):** put the event under Next steps as `- [ ] Title, 3:00–3:30 pm, place [due:: YYYY-MM-DD]`. It shows on the calendar as a dated item until an agent with vault access converts it.
4. Resolve relative dates ("Thursday") against today's date and say the date back. If a detail is uncertain, mark the event tentative.
5. Add it to the confirmation line, for example `Saved to Obsidian: 11 AI Chats/2026-10-14 - Topic.md · Added to calendar: Coffee chat, Wed Oct 14, 3–3:30 pm`.

Event notes in `13 Calendar` follow the vault's calendar skill, which allows `update` and `cancel` through its script; the never-overwrite rule still covers chat, literature and hub notes.

Record names and organizations only: no phone numbers, emails or meeting passcodes.
