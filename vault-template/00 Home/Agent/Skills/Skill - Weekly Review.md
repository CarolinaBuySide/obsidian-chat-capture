---
type: agent-skill
name: weekly-review
command: /weekly-review
summary: "Weekly skill: prepares the review in 07 Weekly (inbox, literature to permanent, links, projects, next-week plan) and refreshes Top of Mind, proposing changes rather than making them."
version: 1.0
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Weekly Review

> [!abstract] One job
> Prepare the 20-minute weekly review so the user only has to decide, then refresh [[Top of Mind]].

## When to run
Sunday or Monday, when the user asks for a weekly review or types `/weekly-review`.

## Read
[[AGENTS]], [[Top of Mind]], [[Goals]], this week's daily notes, every note in `01 Fleeting` (including `AI Drafts`), notes created this week, active projects in `05 Projects`, and the latest [[Skill - Vault Health]] report if one exists.

## Steps
Follow the five steps of `09 Templates/Weekly Review.md`, preparing each one:
1. **Inbox:** list every note in `01 Fleeting` and `01 Fleeting/AI Drafts`, with its age and a proposed action: promote to literature or permanent, link to a map, or delete. Delete nothing yourself.
2. **Literature to permanent:** for each literature note with `status` other than processed, propose one or two permanent-note claims (titles only).
3. **Connect:** list notes created this week that don't link to any map, with the map each should join.
4. **Projects:** for each active project, flag past `due` dates, logs untouched for 14 days and next actions that look done. Propose status changes; don't apply them.
5. **Plan:** propose 1–3 priorities for next week, ranked against [[Goals]].

## Save
- Create `07 Weekly/GGGG-[W]WW.md` if it is missing, using the rendered structure of the Weekly Review template (fill the dates yourself). Append the prepared review as an `> [!ai] Prepared review` callout. Tag the note `ai-assisted`.
- Refresh [[Top of Mind]]: this week's table, coming up, active projects and "Probably stale". Set `updated` to today.
- Append one dated line to `## Retro log` below.

## Rules
- Propose; the user decides. The only notes you rewrite are Top of Mind and the new weekly note.
- Cite the note behind every item.

## Test
Pass if every fleeting note appears with an action, every active project appears once, Top of Mind's `updated` date is today and no other note changed.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
