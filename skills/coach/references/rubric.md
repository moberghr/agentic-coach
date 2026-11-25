# Agentic habits rubric (version 2.2)

Eight dimensions, each scored 0–4 by `analyze_sessions.py`. The scores are
heuristics from transcript signals. Treat them as a starting point for the
conversation, not a grade. Always read the raw `signals` too, and say when a
score rests on very few sessions.

Overall level: average of the eight scores. Below 1.5 is level 1 (getting
started), below 2.75 is level 2 (building habits), otherwise level 3
(extending and scaling). These match the three levels of the team learning
path.

Every dimension points the same way: away from typing instructions one step
at a time, towards designing the work, handing over bigger pieces, and making
the agent prove the result. Each one borrows a practice from people who do
this well, listed with its source.

---

## 1. design: design before building

**Signals:** share of multi-file sessions (or editing sessions, if there were
none) that started from a spec, a `/goal` condition or a Claude interview;
sessions that wrote or asked for a diagram; share of opening prompts that
name a check.

**Scores:** 10 / 25 / 45 / 65 % for 1–4, plus one point if diagrams appear.

**Low looks like:** "add SEPA payments" typed straight into a session, then
several rounds of "no, not like that".

**Borrow:** Anthropic's best practices: for larger features, have Claude
interview you and write a spec, then build in a fresh session. Useful specs
name the files and interfaces involved, say what is out of scope, and end
with an end-to-end check.

**Push towards:**
- A four-line brief on every task: what done looks like, the check that
  proves it, what is out of scope, constraints that must not change.
- A Mermaid graph of the area before changing it, corrected and committed.
- Acceptance criteria turned into a `/goal`: one measurable end state, a
  stated check, constraints, and a turn limit.

## 2. explore: ground it first

**Signals:** share of editing sessions where Read/Grep/Glob ran before the
first edit. Scores at 20 / 40 / 60 / 80 %.

**Borrow:** Simon Willison's Agentic Engineering Patterns includes "First run
the tests" as an opening move. Anthropic's best practices: ask Claude the
questions you'd ask a senior engineer, and send broad investigation to
subagents so the main context stays clean.

## 3. verify: make Claude prove it

**Signals:** editing sessions that ran tests, a build, lint or type checks
after editing, or drove a browser or app; sessions that asked for test-first.
Scores at 15 / 30 / 50 / 70 %.

**Borrow:** Boris Cherny, who leads Claude Code, describes verification as
whether the agent can run the thing, not only whether unit tests pass (as
summarised by The Neuron, June 2026). Anthropic's power user tips call
giving Claude a way to check its own output the most important tip. Simon
Willison's "Use red/green TDD" is a four-word way to ask for test-first.

**Push towards:** name the check in the prompt; ask for evidence, not a
claim; let Claude start the app and click through the change where possible.

## 4. review: maker and checker

**Signals:** share of multi-file sessions with a second-opinion step: a
reviewer subagent after edits, `/code-review`, `/simplify`,
`/security-review`, or a prompt asking for a review of the diff.
Scores at 5 / 15 / 30 / 50 %.

**Borrow:** the Claude Code team's review process: Claude runs tests, builds
and linters, then a separate agent reviews in a fresh context before the pull
request. Human approval scales with risk, and review stops after three rounds
so the author rethinks the approach. Addy Osmani's rule is the same: keep the
writer separate from the verifier.

**Push towards:** "Use a subagent to review the diff against SPEC.md. Report
only gaps that affect correctness or the requirements."

## 5. delegate: delegate and parallelise

**Signals:** subagent calls per 10 sessions, overlapping sessions, worktree
use. One point each for any subagent use, ≥1 per 10 sessions, ≥3 per 10
sessions, and parallel work (≥15 % overlap or worktrees).

**Borrow:** Anthropic's power user tips: run three to five sessions at once,
each in its own git worktree; use `/batch` for migrations.

## 6. steer: steer and recover

**Signals:** sessions that ended on an interrupt, hit three or more tool
errors in a row, or contained three or more correction prompts ("no", "still
failing", "you forgot"). Score is 4 minus the band at 6 / 12 / 20 / 30 %.
Interrupting is good. Ending right after one, or correcting the same thing
three times, usually is not.

**Borrow:** Anthropic's best practices: after two failed corrections, clear
the session and start again with a better prompt that includes what you
learned. Anthropic's research found experienced users interrupt more often,
and recover instead of abandoning.

## 7. compound: teach Claude once

**Signals:** one point each for a CLAUDE.md in most projects; any skills,
hooks or custom agents; at least one edit to CLAUDE.md, a rule or a skill
during the window; and three or more such edits (or 10 % of sessions).

**Borrow:** Anthropic's power user tips: keep one shared CLAUDE.md in git and
add a rule whenever Claude makes a mistake. Rules that must always hold
belong in hooks and permissions, not in CLAUDE.md.

## 8. loops: build loops

**Signals:** one point each for a median of 3+ tool calls per prompt; a
median of 6+ or any run of 25+ tool calls on one prompt; any use of `/goal`,
`/loop`, `/schedule` or `/batch`; and automatic approval in 30 % of sessions.

High is only good if verify and review are also healthy. Read them together.

**Borrow:** Addy Osmani's Loop Engineering: design the system that prompts
the agent, with a stop condition it can check, and keep reading what the
loop produces so you still understand it. Boris Cherny frames the same
progression as source code, then agent, then loop.

**Push towards:** a `/goal` with a turn limit for long tasks; `/loop` or a
scheduled routine for recurring chores. For client repositories, check what
an unattended agent is allowed to run before using automatic approval.

---

## The attribute sheet

Under the eight scores sit about 50 attributes: specific habits, each with a
strength from 0 to 100. The report shows them as a character sheet, grouped
by the eight dimensions. They add detail and do not change the eight scores
or the level.

How strength is worked out:

- **Most attributes** are a share of the sessions where the habit could have
  shown up (editing sessions, multi-file sessions, or all sessions). Each has
  a share that counts as fully trained, stored as `full_at_pct`. Strength is
  the share divided by that target, capped at 100. "Runs the product" is full
  at 25 % of editing sessions, because nobody needs a browser run for every
  change. "Reads before editing" is full at 80 %.
- **Things to avoid** (correction loops, error spirals, compaction) run the
  other way: 100 at zero, falling to 0 once the share reaches `zero_at_pct`.
- **Setup attributes** (skills, hooks, custom agents, a personal CLAUDE.md)
  come from files on disk, not from sessions.
- With fewer than three applicable sessions the strength is `null` and the
  report shows "no data".

Ranks: 0 untrained, 1–33 emerging, 34–66 developing, 67–99 strong, 100
mastered. The "class" in the report is named after the dimension with the
highest average strength. It is a bit of fun, not a result.

Read them with care:

- They are matched by simple text and tool-name rules. A habit practised in
  words the rules don't know (another language, an unusual test runner) will
  read low. If the user says a bar is wrong, believe them.
- Not every bar should be full. Which attributes matter depends on the work.
- The targets are judgement calls made for this rubric, not published
  thresholds. They are in `analyze_sessions.py`, next to each attribute, and
  are meant to be tuned.

The full list, with what each one looks for, is the `attributes` array in
`metrics.json` (`name`, `what`, `raw`).

---

## Sources

- Best practices for Claude Code: https://code.claude.com/docs/en/best-practices
- Keep Claude working toward a goal: https://code.claude.com/docs/en/goal
- Claude Code power user tips: https://support.claude.com/en/articles/14554000-claude-code-power-user-tips
- How the Claude Code team does code review: https://claude.dev/blog/solving-code-review-at-anthropic/
  (summary: https://www.infoq.com/news/2026/11/claude-code-review/)
- Boris Cherny and Cat Wu on agent loops, summarised by The Neuron:
  https://www.theneuron.ai/explainer-articles/claude-code-creators-boris-cherny-and-cat-wu-explain-how-to-use-agent-loops/
- Simon Willison, Agentic Engineering Patterns:
  https://simonwillison.net/guides/agentic-engineering-patterns/red-green-tdd/
- Addy Osmani, Loop Engineering: https://addyosmani.com/blog/loop-engineering/
- Kent Beck, Augmented coding: beyond the vibes (warning signs: loops, unrequested
  functionality, cheating on tests): https://newsletter.kentbeck.com/p/augmented-coding-beyond-the-vibes
- Mitchell Hashimoto, My AI adoption journey (engineer a fix for every agent mistake):
  https://mitchellh.com/writing/my-ai-adoption-journey
- Anthropic, Effective context engineering for AI agents:
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Thariq Shihipar, Lessons from building Claude Code: how we use skills:
  https://claude.dev/blog/lessons-from-building-claude-code-how-we-use-skills/
- Agentic coding and persistent returns to expertise:
  https://www.anthropic.com/research/claude-code-expertise
- Measuring agent autonomy in practice:
  https://www.anthropic.com/research/measuring-agent-autonomy
