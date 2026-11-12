---
type: ai-context
summary: "Shared starting point for every AI app: who {{USER_NAME}} is, current focus areas, how to work with them and where things live."
created: {{TODAY}}
tags:
  - ai-context
---
# AI Context

> [!info] For AI assistants
> Read this first. It's the shared starting point for Perplexity, Claude, ChatGPT and any other assistant, so each one knows what {{USER_NAME}} is working on. For live deadlines, use the "Due in the next 14 days" list on [[Home]]. Save new durable context back to the vault (for example with the obsidian-chat-capture skill), not into app-only memory.

## Who I am
{{USER_NAME}}: {{USER_ROLE}}. Details are in [[About me]].

## What I'm working on
| Area | Current focus | Note |
|---|---|---|
{{AREA_TABLE_ROWS}}| School | {{TERM}} courses | [[School MOC]] · [[School Library]] | <!-- if:school -->

## How to work with me
- {{ANSWER_STYLE}}
- **Define before recommending.** State the problem and key terms, give the evidence, then recommend.
- **Verify important conclusions** and say when an assumption isn't supported.
- **Pilot before automating.** Show a concrete test before installing agents, scheduling runs or sending anything.
- **Privacy:** never store or repeat keys, passwords, account numbers or other people's private details.

## How AI chats get saved
- Apps that can reach the vault (Claude Code, Claude Desktop, Cursor, Codex, Perplexity on this computer) use the `obsidian-chat-capture` skill: one short note per chat in `11 AI Chats`, linked to existing notes and listed in [[AI Chats MOC]].
- Cloud apps (ChatGPT, phone apps) end with a copy-ready note block. On a Mac the clipboard watcher saves it into `11 AI Chats`; otherwise paste it into a new note.
- Apps set up so far: {{CAPTURE_APPS}}

## Where things live
- **Areas:** {{AREA_LINKS_INLINE}}[[Color Key]]
- **Calendar:** [[Weekly Calendar]] (classes, calls, meetings, exams) · [[To-Do Calendar]] (everything due, by month)
- **AI chat notes:** `11 AI Chats`, grouped in [[AI Chats MOC]]
- **Rules for agents:** [[AGENTS]]

← [[Home]]
