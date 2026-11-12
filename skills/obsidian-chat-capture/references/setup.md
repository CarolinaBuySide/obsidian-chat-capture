# Connect an AI app to the vault

Read this when the `obsidian` MCP tools are missing or the user asks how to connect an app. Walk the user through only the section for their app. Never ask the user to paste the API key into the chat. They should paste it into the config file or settings screen themselves.

## 1. Vault side (once)

1. Obsidian desktop: **Settings → Community plugins → Browse**, then install and enable **Local REST API with MCP** (by Adam Coddington, v5 or newer).
2. **Settings → Local REST API** shows the API key and the endpoints:
   - HTTPS (default): `https://127.0.0.1:27124/mcp/`, which uses a self-signed certificate
   - HTTP (optional): `http://127.0.0.1:27123/mcp/`, which is off until **Enable HTTP server** is turned on. It only listens on this computer.
3. Check it works: `curl -sk https://127.0.0.1:27124/` should return `"status": "OK"`.

Obsidian must be open for the server to answer.

## 2. App side

Replace `<API_KEY>` yourself in each config file. Restart the app afterward.

**Claude Code**
```sh
claude mcp add --scope user --transport http obsidian https://127.0.0.1:27124/mcp/ \
  --header "Authorization: Bearer <API_KEY>"
```
Install the skill: copy `skills/obsidian-chat-capture/` to `~/.claude/skills/`.

**Claude Desktop** (needs Node.js). Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Windows: `%APPDATA%\Claude\claude_desktop_config.json`):
```json
{ "mcpServers": { "obsidian": {
  "command": "npx",
  "args": ["mcp-remote@latest", "https://127.0.0.1:27124/mcp/", "--header", "Authorization: Bearer <API_KEY>"],
  "env": { "NODE_TLS_REJECT_UNAUTHORIZED": "0" }
} } }
```
The `env` line accepts the plugin's self-signed certificate. Alternatively, use the HTTP URL. Install the skill: zip the `obsidian-chat-capture` folder and upload it under **Customize → Skills**.

**Cursor**. Edit `~/.cursor/mcp.json`:
```json
{ "mcpServers": { "obsidian": {
  "url": "https://127.0.0.1:27124/mcp/",
  "headers": { "Authorization": "Bearer <API_KEY>" }
} } }
```

**Perplexity (Mac app)**. Install the **PerplexityXPC** helper when the app prompts. Then go to **Settings → Connectors → Add Connector**, open the **Simple** tab, name the server `obsidian`, and enter this command. It needs Node.js and the HTTP server enabled:
```sh
npx -y mcp-remote@latest http://127.0.0.1:27123/mcp/ --header "Authorization: Bearer <API_KEY>"
```
In Perplexity Computer, upload the skill zip under Skills.

**OpenAI Codex CLI**. Add this to `~/.codex/config.toml`, then copy the skill folder to `~/.codex/skills/`:
```toml
[mcp_servers.obsidian]
command = "npx"
args = ["-y", "mcp-remote@latest", "https://127.0.0.1:27124/mcp/", "--header", "Authorization: Bearer <API_KEY>"]
env = { NODE_TLS_REJECT_UNAUTHORIZED = "0" }
```

**ChatGPT**. ChatGPT runs in the cloud and cannot reach a vault on your computer. Custom MCP connectors need developer mode, which OpenAI offers on Pro (read-only) and on Business, Enterprise and Edu (read and write), not on Plus. Even then, the server must be reachable over the internet with OAuth, which means a tunnel plus an OAuth layer in front of the plugin. Only do that if you accept the risk of exposing your notes. On Plus, upload the skill under **Plugins → Skills → Add → Upload from your computer**. It will hand you paste-ready notes instead of saving directly.

## 3. Turn on automatic capture (apps with vault access)

Claude apps auto-save substantive chats by default; adding the line below to Claude's Profile → Preferences makes it more reliable. Other apps need it in their custom instructions (ChatGPT: Personalization; Perplexity: Profile → Introduce yourself):

> After any substantive answer (a decision, plan, checklist, analysis, research or tasks), use the obsidian-chat-capture skill to save a short note to my Obsidian vault and tell me the path. Don't wait for the chat to end.

## 4. Automatic capture from cloud apps (macOS)

Cloud apps such as ChatGPT can't reach the vault, so the skill ends with a copy-ready block whose first line is `obsidian-capture: <path>`. `scripts/clip_capture.py` watches the clipboard and saves those blocks into the vault. Click **Copy** on the block and the note appears, with a macOS notification. It only acts on the marker line, ignores everything else on the clipboard, never logs clipboard contents, and never overwrites a note. Copies from an iPhone reach it through Universal Clipboard.

Install it as a login item (replace the vault path):
```sh
mkdir -p ~/Library/Application\ Support/obsidian-clip-capture
cp scripts/clip_capture.py ~/Library/Application\ Support/obsidian-clip-capture/
cat > ~/Library/LaunchAgents/com.obsidian-chat-capture.clipboard.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.obsidian-chat-capture.clipboard</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>/Users/YOU/Library/Application Support/obsidian-clip-capture/clip_capture.py</string>
    <string>--vault</string><string>/Users/YOU/Documents/Obsidian Vault</string>
  </array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
</dict></plist>
PLIST
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.obsidian-chat-capture.clipboard.plist
```
Stop it with `launchctl bootout gui/$(id -u)/com.obsidian-chat-capture.clipboard`. The activity log is `~/Library/Logs/obsidian-clip-capture.log`.

For fully automatic capture in ChatGPT, add this to **Settings → Personalization → Custom instructions**:

> At the end of any substantive chat (decisions, plans, research or tasks), use the obsidian chat capture skill to give me a copy-ready note block.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Connection refused | Open Obsidian. Make sure the plugin is enabled. |
| 401 | Wrong key. Copy it again from Settings → Local REST API. |
| Certificate error | Use the `NODE_TLS_REJECT_UNAUTHORIZED` env line, trust `https://127.0.0.1:27124/obsidian-local-rest-api.crt`, or switch to the HTTP URL. |
| Tools appear but writes fail | Check the path is relative to the vault root and ends in `.md`. |
