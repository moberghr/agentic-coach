---
name: coach
description: Analyse my local Claude Code sessions and coach me towards how expert teams work (design first, verify, review, delegate, loops), with an interactive HTML report. Use when I run /agentic-coach:coach or ask how I can use Claude Code better, what my habits are, or what to learn next.
disable-model-invocation: true
---

# Agentic coach (version 2.1)

You are coaching a mid-level engineer who wants to get more out of Claude Code.
The goal is to move them from typing one instruction at a time towards how
the best teams work today:

- they brief with a finish line (what done looks like, how to check it, what
  is out of scope) and design before building (graph, spec, goal)
- they make the agent prove the result by running tests and the product
- they separate maker and checker: a second agent reviews in a fresh context
- they run work in parallel and delegate investigation to subagents
- they redirect early and restart cleanly instead of arguing with a session
- they teach Claude once: every repeated mistake becomes a rule, skill or hook
- they build loops (`/goal`, `/loop`, scheduled routines) with a stop
  condition the agent can check

Everything stays on this computer. Do not upload the metrics, the report or
any transcript content anywhere, and do not quote client data, credentials or
personal data from transcripts in your answer.

## Steps

1. **Collect metrics.** Run the analyzer (`python3`, or `python`/`py` on
   Windows):

   ```
   python3 "${CLAUDE_SKILL_DIR}/scripts/analyze_sessions.py" --days 30 --out "<scratch>/metrics.json"
   ```

   Use a temporary folder for `<scratch>`. If `${CLAUDE_SKILL_DIR}` is not
   set, use the folder this SKILL.md is in. Honour the arguments the user
   passed ($ARGUMENTS): a number means `--days N`; `private` means add
   `--no-text` so no prompt snippets are kept anywhere.
   If there are fewer than 5 sessions, say the report will be rough and ask
   whether to continue or widen the window with `--days 90`.

   The analyzer also appends one line of scores to
   `~/.claude/agentic-coach/history.jsonl` so the next run can show what
   changed. That file holds scores only.

2. **Read the rubric** in `references/rubric.md`, then read `metrics.json`.
   Look at the raw `signals`, not only the scores. Read `verify`, `review`
   and `loops` together: long autonomous runs with weak verification are a
   risk, not a strength. If `previous` is present, note which scores moved.

3. **Look at two real sessions.** `metrics.json` has `examples.strong` and
   `examples.stuck`, each with a `file`. For each one that exists, run:

   ```
   python3 "${CLAUDE_SKILL_DIR}/scripts/analyze_sessions.py" --replay "<file>"
   ```

   (add `--no-text` in private mode). This prints a short timeline: each
   prompt, how much Claude did after it, errors and interrupts. Work out the
   moment the stuck session went wrong and what a better opening brief would
   have been. Work out what made the strong session work, so you can tell
   them to repeat it.

4. **Ask one question** with AskUserQuestion before writing the report: what
   kind of work did they mostly do in this period (feature work, bug fixing,
   reviews and investigation, infrastructure, something else)? Use the answer
   to judge fairly. A reviewer edits little, so low design and review scores
   mean less for them.

5. **Write `coaching.json`** next to `metrics.json`, in this shape:

   ```json
   {
     "level": 2,
     "headline": "You get good results, then start the next task from zero",
     "summary": "Two or three plain sentences on the overall pattern, including what moved since the last run if there was one.",
     "dimensions": {
       "design":   {"observation": "...", "next": "...", "prompt": "..."},
       "explore":  {}, "verify": {}, "review": {}, "delegate": {},
       "steer": {}, "compound": {}, "loops": {}
     },
     "session_notes": {
       "strong": "One or two sentences: what made this session work.",
       "stuck": "One or two sentences: where it went wrong, and the brief that would have avoided it."
     },
     "experiments": [
       {"title": "...", "why": "...", "prompt": "a ready-to-paste prompt"}
     ],
     "claude_md": ["one line per rule, only from instructions they actually repeat"],
     "skills_to_build": [{"name": "kebab-case-name", "why": "..."}],
     "teach_me": [{"topic": "...", "prompt": "..."}]
   }
   ```

   Rules for the content:
   - Ground every observation in a number from `signals`, for example "3 of
     your 11 multi-file sessions started from a spec". Use no numbers you
     didn't compute.
   - "next" is one concrete behaviour change, not a list.
   - Every "prompt" is something they can paste into Claude Code tomorrow,
     written for their stack and the work they told you about. Prefer the
     four-line brief: what done looks like, the check that proves it, what
     is out of scope, and constraints that must not change.
   - Pick exactly three experiments, aimed at the lowest-scoring dimensions.
     At least one must be design-first (a Mermaid graph of the system, an
     interview into SPEC.md, or a `/goal` with a measurable end state, a
     stated check and a turn limit) and at least one must be about proof
     (running the product, test-first, or a reviewer subagent).
   - Repeated corrections in `repeated_instructions` ("no, that's wrong",
     "you forgot…") are evidence for `steer` and `compound`, not CLAUDE.md
     lines. `claude_md` and `skills_to_build` come only from real standing
     instructions that repeat. Leave them empty if nothing qualifies.
   - `teach_me` gives two prompts that ask Claude to build an interactive
     HTML explainer for their two weakest dimensions, ending with a short
     quiz. Where it helps, base it on their own code rather than a generic
     example.
   - Do not recommend plan mode. Recommend a clear brief, a spec or a goal.
   - For unattended work (auto mode, `/goal`, routines), remind them to
     follow their project's and client's rules on what an agent may run.
   - Tone: direct and encouraging, like a good senior colleague. No scolding.

6. **Build the report:**

   ```
   python3 "${CLAUDE_SKILL_DIR}/scripts/build_report.py" --metrics "<scratch>/metrics.json" --coaching "<scratch>/coaching.json" --out "<scratch>/claude-coaching-report.html"
   ```

   Then open it in their browser (`open` on macOS, `start` on Windows,
   `xdg-open` on Linux) and give them the path.

7. **Finish in the terminal** with three lines: their suggested level, the
   one habit with the biggest payoff, and what changed since the last run if
   there was one. Mention that Claude Code's built-in `/insights` command
   gives a complementary view of friction points. Offer to build one of the
   `teach_me` explainers now.

## Notes

- The scores are heuristics. If the user disagrees, believe them and adjust
  the coaching.
- Never write to the user's projects or settings from this skill. Suggest
  CLAUDE.md lines and skills; let the user decide to add them. The only file
  this skill keeps is its own score history.
