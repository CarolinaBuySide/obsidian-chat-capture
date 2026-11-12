---
type: map
summary: 
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
tags:
  - map
---
<%*
// Ask for a title when the note was created as "Untitled"; fall back to a timestamp.
let title = tp.file.title;
if (title.startsWith("Untitled")) {
  const input = await tp.system.prompt("Topic for this map (e.g. 'Note-taking')");
  title = (input && input.trim()) ? input.trim() : "Map " + tp.date.now("YYYY-MM-DD HHmm");
  title = title.replace(/[\\/:*?"<>|#^\[\]]/g, "-");
  await tp.file.rename(title);
}
-%>
# <% title %>

## Overview
<% tp.file.cursor() %>

## Core notes
- [[ ]]

## Open questions
- 

## Notes that link here
```dataview
TABLE type AS "Type", maturity AS "Maturity"
FROM "02 Literature" OR "03 Permanent"
WHERE (type = "literature" OR type = "permanent")
  AND (contains(file.outlinks, this.file.link) OR contains(maps, this.file.link))
SORT file.mtime DESC
```
