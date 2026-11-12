---
type: agent-skill
name: write-like-me
command: /write-like-me
summary: "Drafts emails, Slack messages, résumé bullets and memo paragraphs in the user's voice from their Writing Style guide and samples, listing every fact used and its source."
version: 1.0
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Write Like Me

> [!abstract] One job
> Draft text that sounds like the user and only says things their notes support.

## When to run
the user asks for a draft (email, Slack message, résumé bullet, cover-letter paragraph, LinkedIn post, memo section) or types `/write-like-me`.

## Steps
1. **Clarify** the genre, audience, goal and length if they aren't obvious.
2. **Read** [[Writing Style]] (rules and "My samples"), [[USER]], and the notes that hold the facts (for example [[About me]], the project note).
3. **Draft** using the genre rules in [[Writing Style]]. Slack: plain text, no asterisks. Résumé: strong verb + task with specifics + impact.
4. **Check facts:** list every factual claim with its source note. Flag unconfirmed items, such as résumé facts marked unconfirmed in [[About me]].
5. **Deliver** the draft in chat, then the fact list. If the user wants it saved, put it in `01 Fleeting/AI Drafts/` with the `ai-assisted` tag.

## Rules
- Never send, post or submit anything; the user does that.
- Don't invent experiences, numbers or relationships.
- Check the course's AI policy before drafting graded coursework.
- If "My samples" in [[Writing Style]] is empty, say the draft follows the rules only.

## Test
Pass if every claim in the draft appears in the fact list with a resolving source, genre rules are met, and nothing was sent.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
