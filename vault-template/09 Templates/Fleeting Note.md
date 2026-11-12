---
type: fleeting
status: inbox
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
captured: "[[06 Daily/<% tp.date.now("YYYY/MM/YYYY-MM-DD") %>|<% tp.date.now("YYYY-MM-DD") %>]]"
tags:
  - fleeting
---
<%*
// Ask for a title when the note was created as "Untitled"; fall back to a timestamp.
let title = tp.file.title;
if (title.startsWith("Untitled")) {
  const input = await tp.system.prompt("Fleeting note title (leave blank for a timestamp)");
  title = (input && input.trim()) ? input.trim() : "Fleeting " + tp.date.now("YYYY-MM-DD HHmm");
  title = title.replace(/[\\/:*?"<>|#^\[\]]/g, "-");
  await tp.file.rename(title);
}
-%>
# <% title %>

<% tp.file.cursor() %>

---
> [!tip] Process within 1–2 days
> Turn this into a **literature note** (if it came from a source) or a **permanent note** (if it is your own idea), then set `status: processed` or delete it.
