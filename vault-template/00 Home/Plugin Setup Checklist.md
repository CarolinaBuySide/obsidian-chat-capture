---
type: dashboard
summary: "One-time setup steps for the community plugins, Templater's automatic templates, a quick functionality check and optional hotkeys."
tags:
  - setup
---
# Plugin Setup Checklist

Tick these off the first time you open the vault. Full explanations are in the blueprint repo's README; how this vault is organized is in [[README]].

## 1. Turn on community plugins
- [ ] If Obsidian asked "Do you trust the author of this vault?", choose **Trust author and enable plugins**.
- [ ] Otherwise: **Settings → Community plugins → Turn on community plugins** (this turns off Restricted mode).

## 2. Install the plugins
Skip this if the vault was built with the blueprint's `install_plugins.py` and `obsidian_setup.py` scripts; they do steps 1 to 3 for you.
- [ ] **Settings → Community plugins → Browse** → search **Dataview** → Install → Enable
- [ ] Search **Templater** → Install → Enable
- [ ] Search **Calendar** (by Liam Cain) → Install → Enable
- [ ] Search **Git** (by Vinzent) → Install → Enable (local undo history)
- [ ] Search **Local REST API with MCP** → Install → Enable (lets AI apps save chats into `11 AI Chats`)
- [ ] **Graph Groups** ships inside this vault: just switch it on under **Community plugins → Installed plugins**.

The settings for all of them are already included in this vault, so you do not need to configure folders or formats.

## 3. Enable Templater's automatic templates (one switch, once per device)
- [ ] **Settings → Templater → Trigger Templater on new file creation → On** (confirm the warning).

This switch is stored per device for safety, so it cannot ship pre-enabled. Without it, new notes will be created blank.

## 4. Check it works
- [ ] Press `Ctrl/Cmd + N` → you should be asked for a title and the note should appear in `01 Fleeting` with properties filled in.
- [ ] Open today's daily note from the Calendar → dates and Yesterday/Tomorrow links should be filled in.
- [ ] Open [[Home]] → the code blocks should render as tables.

## 5. Optional hotkeys (Settings → Hotkeys)
- [ ] `Templater: Create new note from template` → e.g. `Ctrl/Cmd + Shift + N`
- [ ] `Daily notes: Open today's daily note` → e.g. `Ctrl/Cmd + D`
- [ ] `Note composer: Extract current selection` → e.g. `Ctrl/Cmd + Shift + E` (great for turning a paragraph into its own permanent note)
