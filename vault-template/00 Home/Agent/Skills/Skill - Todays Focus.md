---
type: agent-skill
name: todays-focus
command: /todays-focus
summary: "Morning skill: reads Top of Mind, goals, recent daily notes and open dated tasks, then writes three cited priorities and reflection questions into today's daily note."
version: 1.0
created: {{TODAY}}
tags:
  - agent
  - agent-skill
---
# Skill: Today's Focus

> [!abstract] One job
> Pick the three things that matter most today, explain why with citations, and put them in today's daily note.

## When to run
the user asks "what should I focus on today?", asks for a morning review, or types `/todays-focus`.

## Read, in this order
1. [[AGENTS]] rules, then [[Top of Mind]], [[Goals]] and [[Principles]].
2. The last three daily notes in `06 Daily/YYYY/MM/`: their "Top 3 today" and "What carries over to tomorrow?"
3. Every unchecked task with a due date (`- [ ] … [due:: YYYY-MM-DD]`) in `04 Maps`, `05 Projects` and `11 AI Chats`. Keep anything due in the next 7 days or already overdue.
4. Active projects (`05 Projects`, `status: active`): their "Next actions".
5. The three newest notes in `11 AI Chats`, for fresh commitments.
6. Optional: today's calendar, if a calendar tool is connected.

## Steps
1. Get today's date and weekday in {{TIMEZONE}}.
2. Build the candidate list from step 3 and 4. Mark overdue items "may already be done, confirm" instead of treating them as urgent.
3. Rank candidates by: hard deadline in the next 48 hours; whether others depend on it (team work, bookings that can sell out); weight toward [[Goals]]; effort that fits the day (weekends suit deep work).
4. Choose exactly three. For each, write why it matters today and a first step that takes 15 minutes or less.
5. Add "Also due soon" (next 7 days), "Probably stale" (overdue and unchecked) and 2–3 reflection questions tied to [[Principles]] or [[Goals]].
6. Save:
   - If today's daily note exists, append the output at the end as an `> [!ai] Today's focus` callout. Don't touch the user's own lines.
   - If it doesn't exist, create `06 Daily/YYYY/MM/YYYY-MM-DD.md` with the rendered structure of `09 Templates/Daily Note.md` (frontmatter, navigation links, sections, Dataview blocks), put the three priorities in "Top 3 today" as unchecked tasks, and tag the note `ai-assisted`.
7. Reply in chat with the three priorities and the note path.

## Output format
```markdown
> [!ai] Today's focus · Perplexity, 2026-10-10
> 1. **Priority**: why today. First step: … ([[Source note]])
> 2. …
> 3. …
>
> **Also due soon:** item, date ([[Source]]) · …
> **Probably stale:** item ([[Source]]) · …
> **Reflect:** question? · question?
```

## Rules
- Every priority cites a note that exists. No invented deadlines.
- Say when a date comes from an old sync (for example "Canvas sync, Sep 30").
- Never check off tasks or change project status; suggest it instead.

## Test
Pass if: exactly three priorities, each with a citation that resolves; no deadline missing from "Also due soon"; overdue items appear only under "Probably stale"; nothing outside today's daily note changed.

## Retro log
One dated line per run: what worked, what didn't, proposed fix. Newest last.
