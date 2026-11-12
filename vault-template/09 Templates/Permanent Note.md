---
type: permanent
summary: 
maturity: seedling
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
sources: []
maps: []
tags:
  - permanent
---
<%*
// Ask for a title when the note was created as "Untitled"; fall back to a timestamp.
let title = tp.file.title;
if (title.startsWith("Untitled")) {
  const input = await tp.system.prompt("State the idea as a short claim (e.g. 'Linking beats filing')");
  title = (input && input.trim()) ? input.trim() : "Idea " + tp.date.now("YYYY-MM-DD HHmm");
  title = title.replace(/[\\/:*?"<>|#^\[\]]/g, "-");
  await tp.file.rename(title);
}
-%>
# <% title %>

<% tp.file.cursor() %>

## Why it matters
- 

## Evidence and sources
- From [[ ]] — 

## Connections
- Supports:: 
- Contradicts:: 
- Extends:: 

---
> [!note] Permanent note checklist
> One idea · written in full sentences · understandable without the source · linked to at least one other note and one map.
