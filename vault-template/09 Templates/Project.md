---
type: project
summary: 
status: active
start: <% tp.date.now("YYYY-MM-DD") %>
due:
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
tags:
  - project
---
<%*
// Ask for a title when the note was created as "Untitled"; fall back to a timestamp.
let title = tp.file.title;
if (title.startsWith("Untitled")) {
  const input = await tp.system.prompt("Project name");
  title = (input && input.trim()) ? input.trim() : "Project " + tp.date.now("YYYY-MM-DD HHmm");
  title = title.replace(/[\\/:*?"<>|#^\[\]]/g, "-");
  await tp.file.rename(title);
}
-%>
# <% title %>

## Outcome
What does "done" look like?
<% tp.file.cursor() %>

## Next actions
- [ ] 

## Reference notes
- [[ ]]

## Log
- <% tp.date.now("YYYY-MM-DD") %> — Project created.

## Notes that mention this project
```dataview
LIST
WHERE contains(file.outlinks, this.file.link) AND file.name != this.file.name
SORT file.mtime DESC
```
