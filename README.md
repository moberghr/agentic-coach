# agentic-coach

A Claude Code plugin that reads your own Claude Code sessions, scores your working habits and builds an interactive report with what to try next. Everything runs on your computer.

It goes with the [Claude Code learning path](https://claude.ai/artifact/QEQb3VQKwMiBipPVx5hCYs).

## Install

You need Claude Code and Python 3.8 or later.

```
/plugin marketplace add moberghr/moberg-plugins
/plugin install agentic-coach@moberg-plugins
```

## Run it

```
/agentic-coach:coach
```

- `/agentic-coach:coach 90` looks at the last 90 days instead of 30.
- `/agentic-coach:coach private` keeps no snippets of your prompts in the report, only counts.

Claude asks one question about the kind of work you have been doing, then opens the report in your browser.

## What you get

- Three experiments for this week, with prompts you can copy
- A score from 0 to 4 for eight habits: design before building, ground it first, make Claude prove it, maker and checker, delegate, steer and recover, teach Claude once, build loops
- Two of your own sessions replayed: one that went well and one that got stuck, with what made the difference
- What changed since your last run
- Suggested CLAUDE.md lines and skills, taken from instructions you keep repeating

Try the experiments, then run it again in two or three weeks. Claude Code's built-in `/insights` command gives a second view of where sessions get stuck.

## Privacy

- Nothing is uploaded. The analyzer is plain Python with no network calls and no dependencies outside the standard library.
- The plugin keeps one small file, `~/.claude/agentic-coach/history.jsonl`, with your scores from each run. It holds no prompts.
- The report quotes short snippets of your prompts, with emails, links, keys, IBANs and long numbers blanked out. Keep the report on your machine.
- If you work with client data, use `private`.
- The scores are rough estimates for your own learning. They are not a performance measure.

## Update

Maintainers: change the files, bump `version` in `.claude-plugin/plugin.json`, and push to the default branch. Users get the new version with `/plugin marketplace update moberg-plugins`.

## Layout

```
.claude-plugin/plugin.json
skills/coach/SKILL.md                    the steps Claude follows
skills/coach/references/rubric.md        how each habit is scored, with sources
skills/coach/scripts/analyze_sessions.py reads transcripts, computes scores
skills/coach/scripts/build_report.py     builds the HTML report
```

## Licence and disclaimer

MIT licensed, see `LICENSE`. Provided as is, with no warranty. Not produced or endorsed by Anthropic.
