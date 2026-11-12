# Interview

Ask a few questions at a time, in plain language. Skip what the user already told you. Record answers in `answers.json` (see `answers.example.json`).

## About you
1. What should the vault call you? → `name`
2. One line on what you do (student, analyst, founder…)? → `role`
3. Your time zone? → `timezone`
4. How do you like AI answers: short and direct, detailed, bullet points? → `answer_style`

## Life areas
5. What are the 2–6 big areas of your life you want notes for? Examples: Investing, Career, Clubs, Health, Side projects, Work. → `areas[]` (name + one-line description). Each becomes `04 Maps/<Area> MOC.md`, linked from Home.

## School (skip if not a student)
6. Are you a student right now? → `student`
7. What is this term called (e.g. "Fall 2026")? → `term`
8. For each course: code, name, meeting days (Mon–Sun), start and end time (24-hour `HH:MM`), room, instructor, first and last day of class. → `courses[]`. Pasting a registration table is fine; parse it.
9. Any course color preferences? Otherwise colors come from `palette.json` in order (Indigo, Magenta, Amber, Emerald, Coral…). → `courses[].color` and `color_name`
9b. School breaks, last day of classes and exam dates? Add them after the build with `add_event.py --kind break --no-class`.

## Destination
10. Where should the vault go? Default `~/Documents/<Name>'s Vault`. Must be a new or empty folder.

## AI chats
11. Should AI chats save into the vault? Default yes. → `chat_capture`
12. Which AI apps do you use? (Claude Code, Claude Desktop, Cursor, Codex, Perplexity, ChatGPT, others) → `ai_apps[]`. You connect each one in step 5 of `AGENTS.md`.

## Optional
13. Local version history (the Git plugin commits text notes every 30 minutes; nothing is uploaded)? Default yes. → `local_history`
14. Smart Connections (finds related notes with an AI model that runs on your computer)? The original vault has it; default no because it downloads a model. → `smart_connections`
