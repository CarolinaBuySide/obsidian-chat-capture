---
type: agent-skill
name: ingest
command: /ingest
summary: "Turns a URL, PDF, export or folder into one literature note plus draft atomic ideas in AI Drafts, linked to the right map, without writing permanent notes in the user's voice."
version: 1.0
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Ingest

> [!abstract] One job
> Bring a source into the vault as a literature note, propose the atomic ideas it supports, and connect it to the graph.

## When to run
the user shares a URL, PDF, report, folder or export and says "add this to my vault", "ingest this" or `/ingest`. For AI chats, use obsidian-chat-capture instead.

## Steps
1. **Check for duplicates:** search `02 Literature` for the URL (`url` property) and title. If a note exists, append an `## Update YYYY-MM-DD` section instead of creating a new one.
2. **Decide the depth.** "Save this for later" means a bookmark: a short fleeting note with the link and one line on why it matters, not a full-text copy. Full summaries only when the user wants the source processed.
3. **Extract clean text:** for web pages, use Defuddle or a reader view; for PDFs, extract text and keep page numbers.
4. **Write the literature note** in `02 Literature/` following `09 Templates/Literature Note.md`:
   - Title: `Author - Title`, or `Ticker - Source - Period` for company documents.
   - Frontmatter: `type: literature`, `source-type`, `author`, `year`, `url`, `status: unprocessed`, `created`, `summary`, `tags: [literature, ai-assisted, <area tag>]`.
   - Sections from the template. Paraphrase key ideas with page numbers or timestamps; at most two short quotes. Label the summary "AI draft".
5. **Draft atomic ideas:** propose one to five claims the source supports. Save each as a short draft in `01 Fleeting/AI Drafts/` titled as the claim, with the evidence and a link back. the user promotes the ones they agrees with to `03 Permanent`.
6. **Connect:** link the note to at least one map, and append a one-line pointer to that map or the related project.
7. Reply with the paths created and the proposed claims.

## Rules
- Paraphrase; never paste whole articles unless the user asks for a research package.
- Investing sources: record the data date and label fact, estimate or inference.
- Respect paywalls and confidentiality; employer and client materials never enter the vault.

## Test
Pass if there is exactly one literature note with a resolving map link, drafts sit only in `AI Drafts`, no permanent note was created or edited, and the duplicate check ran.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
