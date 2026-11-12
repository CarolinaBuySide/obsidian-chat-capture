---
type: map
summary: "Example map on note-taking method that links the atomic-notes and linking-beats-filing permanent notes and explains when to start a map of content."
created: {{TODAY}}
tags:
  - map
  - example
---
# Note-taking MOC

## Overview
A map of content (MOC) is a hub note that links related ideas on one topic. Start a map when a topic has roughly five or more permanent notes.

## Core notes
- [[Atomic notes make ideas reusable]] — why each note holds one idea
- [[Linking beats filing]] — why topics live in links, not folders

## Examples
- [[Fleeting notes should expire]] · [[Ahrens - How to Take Smart Notes]]

## Open questions
- When should a map be split into smaller maps?

## Notes that link here
```dataview
TABLE type AS "Type", maturity AS "Maturity"
FROM "02 Literature" OR "03 Permanent"
WHERE (type = "literature" OR type = "permanent")
  AND (contains(file.outlinks, this.file.link) OR contains(maps, this.file.link))
SORT file.mtime DESC
```

← [[Home]]
