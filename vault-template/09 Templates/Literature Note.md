<%*
// Ask for a title when the note was created as "Untitled"; fall back to a timestamp.
let title = tp.file.title;
if (title.startsWith("Untitled")) {
  const input = await tp.system.prompt("Source title (e.g. 'Ahrens - How to Take Smart Notes')");
  title = (input && input.trim()) ? input.trim() : "Source " + tp.date.now("YYYY-MM-DD HHmm");
  title = title.replace(/[\\/:*?"<>|#^\[\]]/g, "-");
  await tp.file.rename(title);
}
-%>
<%*
const sourceType = await tp.system.suggester(
  ["Book", "Article", "Paper", "Video", "Podcast", "Course", "Other"],
  ["book", "article", "paper", "video", "podcast", "course", "other"],
  false, "What kind of source is this?"
) ?? "other";
const author = (await tp.system.prompt("Author(s) — comma separated (optional)")) ?? "";
-%>
---
type: literature
summary: 
source-type: <% sourceType %>
author:
<%* for (const a of author.split(",").map(s => s.trim()).filter(Boolean)) { -%>
  - <% a %>
<%* } -%>
year:
url:
status: reading
created: <% tp.date.now("YYYY-MM-DDTHH:mm") %>
tags:
  - literature
---
# <% title %>

## Summary in my own words
<% tp.file.cursor() %>

## Key ideas
- (p. / timestamp) Idea, paraphrased — not copied.

## Quotes worth keeping
> Use sparingly. Always add a page number or timestamp.

## My questions and reactions
- What surprised me?
- Where do I disagree?

## Permanent notes created from this source
- [[ ]]

## Related
- 
