#!/usr/bin/env python3
"""
agentic-coach v2.2: analyse your local Claude Code session transcripts.

Reads ~/.claude/projects/**/*.jsonl (the transcripts Claude Code keeps on your
machine), computes habit signals and rule-based scores, and writes them to a
JSON file. Nothing is sent anywhere. Standard library only, Python 3.8+.

Usage:
  python3 analyze_sessions.py --out metrics.json [--days 30] [--no-text]
                              [--projects-dir PATH] [--history PATH | --no-history]
  python3 analyze_sessions.py --replay SESSION.jsonl [--no-text]

--no-text     keeps no snippet of prompt text anywhere (only counts).
--history     where to keep one line of scores per run, so the next run can
              show what changed. Default: ~/.claude/agentic-coach/history.jsonl
--replay      prints a compact timeline of one session (your prompts, how much
              Claude did after each, errors and interrupts) and exits.
"""
import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = 3
MIN_SAMPLE = 3  # fewer applicable sessions than this: an attribute gets no strength

EXPLORE_TOOLS = {"Read", "Grep", "Glob", "LS"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
DELEGATE_TOOLS = {"Agent", "Task"}
AUTO_MODES = {"auto", "acceptEdits", "bypassPermissions", "dontAsk"}
LOOP_COMMANDS = {"goal", "loop", "schedule", "batch"}
REVIEW_COMMANDS = {"code-review", "review", "simplify", "security-review", "verify"}

VERIFY_RE = re.compile(
    r"\b(test|tests|pytest|jest|vitest|mocha|karma|playwright|cypress|"
    r"dotnet\s+(test|build)|mvn|gradle|npm\s+(run\s+)?(test|build|lint|check)|"
    r"yarn\s+(test|build|lint)|pnpm\s+(test|build|lint)|tsc|eslint|ruff|mypy|"
    r"flake8|go\s+(test|vet|build)|cargo\s+(test|build|check|clippy)|make\s+\w*test|"
    r"phpunit|rspec|ng\s+(test|build|lint))\b",
    re.I,
)
BROWSER_RE = re.compile(r"(chrome|playwright|browser|puppeteer|computer)", re.I)
WORKTREE_RE = re.compile(r"\bgit\s+worktree\b|--worktree\b", re.I)
SPEC_RE = re.compile(
    r"(\bspec(\.md)?\b|\bprd\b|design\s+doc|\badr\b|acceptance\s+criteria|"
    r"definition\s+of\s+done|done\s+when|out\s+of\s+scope|interview\s+me|requirements?\.md)",
    re.I,
)
DIAGRAM_RE = re.compile(
    r"(mermaid|sequence\s+diagram|architecture\s+diagram|flow\s*chart|"
    r"c4\s+(model|diagram)|component\s+diagram|data\s*flow|state\s+machine)", re.I)
REVIEW_RE = re.compile(
    r"(review\s+(the|this|my|that)\s+(diff|change|changes|pr|code|branch)|code\s+review|"
    r"second\s+opinion|reviewer|find\s+gaps|report\s+gaps|try\s+to\s+refute|audit\s+the)", re.I)
TDD_RE = re.compile(r"(red\s*/\s*green|failing\s+test\s+first|write\s+a\s+failing\s+test|\btdd\b)", re.I)
CORRECTION_RE = re.compile(
    r"^\s*(no[,.! ]|nope\b|wrong\b|that'?s\s+(not|wrong)|not\s+what|"
    r"still\s+(not|failing|broken|wrong|the\s+same)|again[,. ]|revert\b|undo\b|stop[,. !]|"
    r"you\s+(didn'?t|forgot|missed|broke|ignored))", re.I)
TEACH_PATH_RE = re.compile(
    r"(^|[\\/])(CLAUDE(\.local)?\.md)$|[\\/]\.claude[\\/](skills|rules|agents|commands|output-styles)[\\/]", re.I)
SPEC_PATH_RE = re.compile(r"(spec|design|adr|requirements|acceptance)[^\\/]*\.md$", re.I)
SCOPE_RE = re.compile(
    r"(out\s+of\s+scope|don'?t\s+(change|touch|modify|edit|refactor)|do\s+not\s+(change|touch|modify|edit|refactor)|"
    r"only\s+(change|touch|edit|modify)|without\s+(changing|touching|breaking)|must\s+not|"
    r"leave\s+.{0,40}\s+(alone|as\s+is|unchanged)|constraints?\b)", re.I)
DONE_RE = re.compile(
    r"(done\s+when|definition\s+of\s+done|acceptance\s+criteria|success\s+(criteria|looks)|"
    r"expected\s+(result|behaviou?r|output)|should\s+(return|pass|show|print|render|respond)|"
    r"so\s+that\b|the\s+goal\s+is|finish(ed)?\s+when)", re.I)
PATH_RE = re.compile(
    r"(@[\w./\\-]+|[\w.-]+[/\\][\w./\\-]+|\b[\w-]+\.(cs|py|ts|tsx|js|jsx|json|md|sql|yml|yaml|java|go|rs|rb|php|"
    r"html|css|csproj|sln|toml|xml|sh)\b)", re.I)
UNDERSTAND_RE = re.compile(
    r"^\s*(how\s+(does|do|is|are)|explain|where\s+(is|are|does)|why\s+(does|is|do)|what\s+(does|is|are)|"
    r"walk\s+me\s+through|help\s+me\s+understand|summari[sz]e|give\s+me\s+an\s+overview|trace)", re.I)
EVIDENCE_RE = re.compile(
    r"(show\s+me\s+the\s+(output|result|log|diff)|prove\s+(it|that)|evidence|paste\s+the\s+(output|result)|"
    r"run\s+it\s+and\s+show|confirm\s+(it|that|they)\s+(works?|pass(es)?)|screenshot|"
    r"don'?t\s+(just\s+)?(say|claim|tell\s+me))", re.I)
SECURITY_RE = re.compile(r"(security\s+review|vulnerabilit|owasp|injection|secrets?\s+scan|threat\s+model)", re.I)
TEST_RE = re.compile(
    r"\b(pytest|jest|vitest|mocha|karma|playwright|cypress|phpunit|rspec|unittest|dotnet\s+test|go\s+test|"
    r"cargo\s+test|mvn\s+(test|verify)|gradlew?\s+test|(npm|yarn|pnpm)\s+(run\s+)?test|ng\s+test|make\s+\w*test)\b", re.I)
BUILD_RE = re.compile(
    r"\b(dotnet\s+build|tsc|eslint|ruff|mypy|flake8|prettier|go\s+(vet|build)|cargo\s+(build|check|clippy)|"
    r"(npm|yarn|pnpm)\s+(run\s+)?(build|lint|check|typecheck)|ng\s+(build|lint)|mvn\s+(compile|package)|"
    r"gradlew?\s+build)\b", re.I)
DIFF_RE = re.compile(r"\bgit\s+(diff|status|show)\b", re.I)
DOCS_TOOL_RE = re.compile(r"(context7|docs|learn|documentation)", re.I)
TASKLIST_TOOLS = {"TodoWrite", "TaskCreate", "TaskUpdate"}
COMMAND_NAME_RE = re.compile(r"<command-name>/?([\w:.-]+)</command-name>")
INTERRUPT_MARK = "[Request interrupted by user"
COMPACT_MARK = "This session is being continued from a previous conversation"
COMMAND_RE = re.compile(r"<command-(name|message|args)>|<local-command-(stdout|caveat)>")

REDACTIONS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "<email>"),
    (re.compile(r"https?://\S+"), "<url>"),
    (re.compile(r"\b(sk|pk|rk|ghp|gho|ghs|xox[abp]|AKIA|AIza)[-_A-Za-z0-9]{10,}"), "<secret>"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"), "<iban>"),
    (re.compile(r"\b[A-Fa-f0-9]{24,}\b"), "<hex>"),
    (re.compile(r"\b[A-Za-z0-9+/=_-]{32,}\b"), "<token>"),
    (re.compile(r"\d{6,}"), "<number>"),
    (re.compile(r"(?i)(password|passwd|pwd|secret|token|apikey|api_key)\s*[:=]\s*\S+"), r"\1=<redacted>"),
]


def redact(text, limit=160):
    t = " ".join(str(text).split())
    for rx, rep in REDACTIONS:
        t = rx.sub(rep, t)
    return t[:limit] + ("…" if len(t) > limit else "")


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def user_texts(content):
    texts, results = [], []
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text":
                texts.append(b.get("text", ""))
            elif b.get("type") == "tool_result":
                results.append(b)
    return texts, results


def read_events(path):
    """Yield a simplified event stream for one transcript."""
    try:
        fh = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(e, dict):
                yield e


def analyse_file(path):
    s = {
        "file": str(path), "cwd": None, "start": None, "end": None,
        "user_turns": 0, "prompt_lengths": [], "first_prompt": None, "prompts": [],
        "interrupts": 0, "compactions": 0, "corrections": 0,
        "tool_calls": Counter(), "commands": Counter(), "modes": Counter(),
        "tool_errors": 0, "max_error_streak": 0, "edited_files": set(),
        "explore_before_edit": None, "verify_cmds": 0, "verify_after_edit": False,
        "ran_product": False, "worktree": False, "models": Counter(),
        "turn_tool_counts": [], "last_event": None,
        "spec": False, "goal": False, "diagram": False, "interview": False,
        "review": False, "tdd": False, "teach_edits": 0, "brief_has_check": False,
        # finer-grained flags behind the attribute sheet
        "op_scope": False, "op_done": False, "op_paths": False, "op_words": 0,
        "search_before_edit": False, "verify_before_edit": False, "delegate_before_edit": False,
        "understand_before_edit": False, "docs_lookup": False,
        "tests_after_edit": False, "build_after_edit": False, "evidence_ask": False,
        "verified_last": False, "review_subagent": False, "review_cmd": False, "security": False,
        "diff_after_edit": False, "parallel_subagents": False, "custom_subagent": False,
        "skill_used": False, "mcp_used": False, "tasklist": False, "loop_cmd": False,
    }
    seen_edit = seen_explore = False
    step = last_edit_step = last_verify_step = 0
    delegates_per_msg = Counter()
    err_streak = 0
    calls_this_turn = 0

    for e in read_events(path):
        if e.get("isSidechain"):
            continue
        ts = parse_ts(e.get("timestamp"))
        if ts:
            s["start"] = ts if s["start"] is None or ts < s["start"] else s["start"]
            s["end"] = ts if s["end"] is None or ts > s["end"] else s["end"]
        if e.get("cwd") and not s["cwd"]:
            s["cwd"] = e["cwd"]
        if e.get("permissionMode"):
            s["modes"][e["permissionMode"]] += 1
        etype = e.get("type")
        msg = e.get("message") or {}

        if etype == "user":
            texts, results = user_texts(msg.get("content"))
            for r in results:
                if r.get("is_error"):
                    s["tool_errors"] += 1
                    err_streak += 1
                    s["max_error_streak"] = max(s["max_error_streak"], err_streak)
                else:
                    err_streak = 0
            for t in texts:
                if not t.strip():
                    continue
                for name in COMMAND_NAME_RE.findall(t):
                    base = name.split(":")[-1].lower()
                    s["commands"][base] += 1
                    if base == "goal":
                        s["goal"] = True
                    if base in REVIEW_COMMANDS:
                        s["review"] = True
                        s["review_cmd"] = True
                    if base == "security-review":
                        s["security"] = True
                    if base in ("loop", "schedule", "batch"):
                        s["loop_cmd"] = True
                    if ":" in name:
                        s["skill_used"] = True
                if t.startswith(COMPACT_MARK):
                    s["compactions"] += 1
                    continue
                if INTERRUPT_MARK in t:
                    s["interrupts"] += 1
                    s["last_event"] = "interrupt"
                    continue
                if e.get("isMeta") or COMMAND_RE.search(t) or t.startswith("<system-reminder>"):
                    continue
                # a genuine human prompt
                if t.lstrip().startswith("/goal"):
                    s["goal"] = True
                if SPEC_RE.search(t):
                    s["spec"] = True
                if DIAGRAM_RE.search(t):
                    s["diagram"] = True
                if REVIEW_RE.search(t):
                    s["review"] = True
                if TDD_RE.search(t):
                    s["tdd"] = True
                if EVIDENCE_RE.search(t):
                    s["evidence_ask"] = True
                if SECURITY_RE.search(t):
                    s["security"] = True
                if not seen_edit and UNDERSTAND_RE.search(t):
                    s["understand_before_edit"] = True
                if s["user_turns"] and CORRECTION_RE.search(t):
                    s["corrections"] += 1
                if calls_this_turn or s["user_turns"]:
                    s["turn_tool_counts"].append(calls_this_turn)
                calls_this_turn = 0
                s["user_turns"] += 1
                s["prompt_lengths"].append(len(t.split()))
                s["prompts"].append(t)
                if s["first_prompt"] is None:
                    s["first_prompt"] = t
                    s["brief_has_check"] = bool(VERIFY_RE.search(t) or SPEC_RE.search(t) or TDD_RE.search(t)
                                                or t.lstrip().startswith("/goal"))
                    s["op_scope"] = bool(SCOPE_RE.search(t))
                    s["op_done"] = bool(DONE_RE.search(t))
                    s["op_paths"] = bool(PATH_RE.search(t))
                    s["op_words"] = len(t.split())
                s["last_event"] = "prompt"

        elif etype == "assistant":
            model = msg.get("model")
            if model and not str(model).startswith("<"):
                s["models"][model] += 1
            for b in msg.get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                name = b.get("name", "?")
                inp = b.get("input") or {}
                calls_this_turn += 1
                step += 1
                s["tool_calls"][name] += 1
                s["last_event"] = "tool"
                if name in EXPLORE_TOOLS:
                    seen_explore = True
                    if name in ("Grep", "Glob") and not seen_edit:
                        s["search_before_edit"] = True
                if name in TASKLIST_TOOLS:
                    s["tasklist"] = True
                if name == "Skill":
                    s["skill_used"] = True
                if name.startswith("mcp__"):
                    s["mcp_used"] = True
                if name in ("WebSearch", "WebFetch") or (name.startswith("mcp__") and DOCS_TOOL_RE.search(name)):
                    s["docs_lookup"] = True
                if name == "AskUserQuestion":
                    s["interview"] = True
                if name in DELEGATE_TOOLS:
                    blob = "%s %s %s" % (inp.get("description", ""), inp.get("subagent_type", ""),
                                         str(inp.get("prompt", ""))[:400])
                    if seen_edit and re.search(r"(review|verif|audit|refute|gaps)", blob, re.I):
                        s["review"] = True
                        s["review_subagent"] = True
                    if not seen_edit:
                        s["delegate_before_edit"] = True
                    if str(inp.get("subagent_type") or "").lower() not in ("", "general-purpose", "claude"):
                        s["custom_subagent"] = True
                    delegates_per_msg[msg.get("id") or id(e)] += 1
                if name in EDIT_TOOLS:
                    fp = str(inp.get("file_path") or inp.get("notebook_path") or "")
                    body = str(inp.get("content", "")) + str(inp.get("new_string", ""))
                    if TEACH_PATH_RE.search(fp):
                        s["teach_edits"] += 1
                    elif SPEC_PATH_RE.search(fp):
                        s["spec"] = True
                    else:
                        if not seen_edit:
                            s["explore_before_edit"] = seen_explore
                        seen_edit = True
                        last_edit_step = step
                        if fp:
                            s["edited_files"].add(fp)
                    if fp.lower().endswith((".mmd", ".mermaid", ".puml", ".excalidraw")) or "```mermaid" in body:
                        s["diagram"] = True
                if name == "Bash":
                    cmd = str(inp.get("command", ""))
                    if VERIFY_RE.search(cmd):
                        s["verify_cmds"] += 1
                        if seen_edit:
                            s["verify_after_edit"] = True
                            last_verify_step = step
                        else:
                            s["verify_before_edit"] = True
                    if seen_edit and TEST_RE.search(cmd):
                        s["tests_after_edit"] = True
                    if seen_edit and BUILD_RE.search(cmd):
                        s["build_after_edit"] = True
                    if seen_edit and DIFF_RE.search(cmd):
                        s["diff_after_edit"] = True
                    if WORKTREE_RE.search(cmd):
                        s["worktree"] = True
                if name.startswith("mcp__") and BROWSER_RE.search(name) and seen_edit:
                    s["ran_product"] = True
                    s["verify_after_edit"] = True
                    last_verify_step = step
    if calls_this_turn:
        s["turn_tool_counts"].append(calls_this_turn)
    s["verified_last"] = bool(last_edit_step and last_verify_step > last_edit_step)
    s["parallel_subagents"] = any(v >= 2 for v in delegates_per_msg.values())
    return s


def replay(path, no_text):
    """Print a compact timeline of one session for the coach to read."""
    calls = Counter()
    errors = 0

    def flush():
        nonlocal calls, errors
        if calls:
            top = ", ".join("%s×%d" % kv for kv in calls.most_common(5))
            print("      Claude: %d tool calls (%s)%s" % (sum(calls.values()), top,
                                                           ", %d errors" % errors if errors else ""))
        calls, errors = Counter(), 0

    n = 0
    for e in read_events(path):
        if e.get("isSidechain"):
            continue
        ts = parse_ts(e.get("timestamp"))
        stamp = ts.astimezone().strftime("%d %b %H:%M") if ts else "--"
        msg = e.get("message") or {}
        if e.get("type") == "user":
            texts, results = user_texts(msg.get("content"))
            errors += sum(1 for r in results if r.get("is_error"))
            for t in texts:
                if not t.strip() or t.startswith("<system-reminder>") or e.get("isMeta"):
                    continue
                if t.startswith(COMPACT_MARK):
                    flush(); print("[%s] -- context was compacted --" % stamp); continue
                if INTERRUPT_MARK in t:
                    flush(); print("[%s] -- you interrupted --" % stamp); continue
                cmds = COMMAND_NAME_RE.findall(t)
                if cmds:
                    flush(); print("[%s] YOU ran /%s" % (stamp, cmds[0])); continue
                if COMMAND_RE.search(t):
                    continue
                flush()
                n += 1
                words = len(t.split())
                shown = "(%d words)" % words if no_text else redact(t, 320)
                print("[%s] YOU #%d: %s" % (stamp, n, shown))
        elif e.get("type") == "assistant":
            for b in msg.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    calls[b.get("name", "?")] += 1
    flush()


def check_setup(cwd):
    out = {"claude_md": False, "skills": 0, "agents": 0, "hooks": False, "mcp_config": False}
    if not cwd:
        return out
    p = Path(cwd)
    try:
        out["claude_md"] = (p / "CLAUDE.md").exists() or (p / ".claude" / "CLAUDE.md").exists()
        sk = p / ".claude" / "skills"
        out["skills"] = len([d for d in sk.iterdir() if d.is_dir()]) if sk.is_dir() else 0
        ag = p / ".claude" / "agents"
        out["agents"] = len(list(ag.glob("*.md"))) if ag.is_dir() else 0
        for f in (p / ".claude" / "settings.json", p / ".claude" / "settings.local.json"):
            if f.exists():
                try:
                    if json.loads(f.read_text(encoding="utf-8")).get("hooks"):
                        out["hooks"] = True
                except (ValueError, OSError):
                    pass
        out["mcp_config"] = (p / ".mcp.json").exists()
    except OSError:
        pass
    return out


def user_level_setup(home):
    c = home / ".claude"
    out = {"claude_md": (c / "CLAUDE.md").exists(), "skills": 0, "agents": 0, "hooks": False}
    try:
        if (c / "skills").is_dir():
            out["skills"] = len([d for d in (c / "skills").iterdir()
                                 if d.is_dir() and d.name != "agentic-coach"])
        if (c / "agents").is_dir():
            out["agents"] = len(list((c / "agents").glob("*.md")))
        sf = c / "settings.json"
        if sf.exists():
            out["hooks"] = bool(json.loads(sf.read_text(encoding="utf-8")).get("hooks"))
    except (OSError, ValueError):
        pass
    return out


def band(value, cuts):
    return sum(1 for c in cuts if value >= c)


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def load_history(path):
    rows = []
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--no-text", action="store_true")
    ap.add_argument("--projects-dir", default=None)
    ap.add_argument("--history", default=None)
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--replay", default=None)
    a = ap.parse_args()

    if a.replay:
        replay(a.replay, a.no_text)
        return
    if not a.out:
        ap.error("--out is required")

    home = Path.home()
    root = Path(a.projects_dir) if a.projects_dir else home / ".claude" / "projects"
    if not root.is_dir():
        print("No transcripts found at %s" % root, file=sys.stderr)
        sys.exit(2)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=a.days)

    sessions = []
    for f in root.rglob("*.jsonl"):
        if "subagents" in f.parts:
            continue
        try:
            if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) < since:
                continue
        except OSError:
            continue
        s = analyse_file(f)
        if s and s["user_turns"] > 0 and (s["start"] is None or s["start"] >= since):
            sessions.append(s)

    n = len(sessions)
    if n == 0:
        json.dump({"version": VERSION, "sessions": 0, "days": a.days}, open(a.out, "w"), indent=2)
        print("No sessions with prompts in that window.")
        return

    tools, models, commands = Counter(), Counter(), Counter()
    for s in sessions:
        tools.update(s["tool_calls"])
        models.update(s["models"])
        commands.update(s["commands"])

    def stalled(s):
        return s["last_event"] == "interrupt" or s["max_error_streak"] >= 3

    def looped(s):
        return s["corrections"] >= 3

    edit_s = [s for s in sessions if s["edited_files"]]
    big_s = [s for s in sessions if len(s["edited_files"]) >= 3]
    base = big_s or edit_s
    explore_first = [s for s in edit_s if s["explore_before_edit"]]
    verified = [s for s in edit_s if s["verify_after_edit"]]
    ran_product = [s for s in edit_s if s["ran_product"]]
    designed = [s for s in base if s["spec"] or s["goal"] or s["interview"]]
    reviewed = [s for s in base if s["review"]]
    briefed = [s for s in edit_s if s["brief_has_check"]]
    delegate_calls = sum(s["tool_calls"][t] for s in sessions for t in DELEGATE_TOOLS)
    delegating = [s for s in sessions if any(t in s["tool_calls"] for t in DELEGATE_TOOLS)]
    worktree = [s for s in sessions if s["worktree"]]
    teach_events = sum(s["teach_edits"] for s in sessions)
    teach_sessions = [s for s in sessions if s["teach_edits"]]
    auto_sessions = [s for s in sessions if any(m in AUTO_MODES for m in s["modes"])]
    loop_uses = sum(commands.get(c, 0) for c in LOOP_COMMANDS) + sum(1 for s in sessions if s["goal"] and not s["commands"].get("goal"))
    long_runs = [s for s in sessions if s["turn_tool_counts"] and max(s["turn_tool_counts"]) >= 25]

    spans = sorted([(s["start"], s["end"]) for s in sessions if s["start"] and s["end"]])
    overlapping = 0
    for i, (st, en) in enumerate(spans):
        if any(o_st < en and st < o_en for j, (o_st, o_en) in enumerate(spans) if j != i):
            overlapping += 1

    interrupted = [s for s in sessions if s["interrupts"]]
    recovered = [s for s in interrupted if s["last_event"] != "interrupt"]
    bad = [s for s in sessions if stalled(s) or looped(s)]
    one_shot = [s for s in sessions if s["user_turns"] == 1 and not s["edited_files"]]

    turn_calls = [c for s in sessions for c in s["turn_tool_counts"]]
    med_calls = statistics.median(turn_calls) if turn_calls else 0
    prompt_lens = [l for s in sessions for l in s["prompt_lengths"]]
    first_lens = [len((s["first_prompt"] or "").split()) for s in sessions]

    projects = defaultdict(list)
    for s in sessions:
        projects[s["cwd"] or "unknown"].append(s)
    proj_setup = {c: check_setup(c if c != "unknown" else None) for c in projects}
    user_setup = user_level_setup(home)
    proj_with_md = sum(1 for v in proj_setup.values() if v["claude_md"])
    has_ext = (user_setup["skills"] or user_setup["hooks"] or user_setup["agents"]
               or any(v["skills"] or v["hooks"] or v["agents"] for v in proj_setup.values())
               or tools.get("Skill", 0))

    r_explore = pct(len(explore_first), len(edit_s)) or 0
    r_verify = pct(len(verified), len(edit_s)) or 0
    r_design = pct(len(designed), len(base)) or 0
    r_review = pct(len(reviewed), len(base)) or 0
    r_parallel = pct(overlapping, n) or 0
    r_bad = pct(len(bad), n) or 0
    r_auto = pct(len(auto_sessions), n) or 0
    r_teach = pct(len(teach_sessions), n) or 0
    per10 = 10.0 * delegate_calls / n

    scores = {
        "design": min(4, band(r_design, [10, 25, 45, 65]) + (1 if any(s["diagram"] for s in sessions) else 0)),
        "explore": band(r_explore, [20, 40, 60, 80]),
        "verify": band(r_verify, [15, 30, 50, 70]),
        "review": band(r_review, [5, 15, 30, 50]),
        "delegate": min(4, (1 if delegate_calls else 0) + (1 if per10 >= 1 else 0)
                        + (1 if per10 >= 3 else 0) + (1 if r_parallel >= 15 or worktree else 0)),
        "steer": 4 - band(r_bad, [6, 12, 20, 30]),
        "compound": min(4, (1 if proj_with_md >= max(1, len(proj_setup) // 2) else 0)
                        + (1 if has_ext else 0) + (1 if teach_events else 0)
                        + (1 if teach_events >= 3 or r_teach >= 10 else 0)),
        "loops": min(4, (1 if med_calls >= 3 else 0) + (1 if med_calls >= 6 or long_runs else 0)
                     + (1 if loop_uses else 0) + (1 if r_auto >= 30 else 0)),
    }
    avg = sum(scores.values()) / len(scores)
    level = 1 if avg < 1.5 else (2 if avg < 2.75 else 3)

    # ---- attribute sheet: ~50 specific habits, each with a strength from 0 to 100 ----
    def cnt(group, key):
        return sum(1 for s in group if (key(s) if callable(key) else s[key]))

    attributes = []

    def attr(aid, dim, name, what, num, den, target, unit):
        """strength = how close the share is to the target share that counts as fully trained."""
        if den < MIN_SAMPLE:
            strength, raw = None, "not enough sessions to tell (%d %s)" % (den, unit)
        else:
            strength = int(min(100, round(100.0 * (100.0 * num / den) / target)))
            raw = "%d of %d %s" % (num, den, unit)
        attributes.append({"id": aid, "dim": dim, "name": name, "what": what, "strength": strength,
                           "raw": raw, "full_at_pct": target})

    def inv(aid, dim, name, what, bad_n, den, limit, unit):
        """for things to avoid: full strength at zero, no strength once the share reaches the limit."""
        if den < MIN_SAMPLE:
            strength, raw = None, "not enough sessions to tell (%d %s)" % (den, unit.split(" ")[-1])
        else:
            strength = int(max(0, round(100 - 100.0 * (100.0 * bad_n / den) / limit)))
            raw = "%d of %d %s" % (bad_n, den, unit)
        attributes.append({"id": aid, "dim": dim, "name": name, "what": what, "strength": strength,
                           "raw": raw, "full_at_pct": None, "zero_at_pct": limit})

    def flat(aid, dim, name, what, strength, raw):
        attributes.append({"id": aid, "dim": dim, "name": name, "what": what,
                           "strength": int(max(0, min(100, round(strength)))), "raw": raw, "full_at_pct": None})

    E, B, N = len(edit_s), len(base), n
    ue, ub = "editing sessions", ("multi-file sessions" if big_s else "editing sessions")
    goal_s = [s for s in sessions if s["goal"]]
    deep_s = [s for s in sessions if sum(s["tool_calls"].values()) >= 10]
    all_prompts = sum(s["user_turns"] for s in sessions)
    all_corr = sum(s["corrections"] for s in sessions)

    # design
    attr("brief_check", "design", "Names the check", "Your opening prompt says how the result will be checked", cnt(edit_s, "brief_has_check"), E, 70, ue)
    attr("brief_done", "design", "States the finish line", "Your opening prompt says what done looks like", cnt(edit_s, "op_done"), E, 60, ue)
    attr("brief_scope", "design", "Fences the scope", "Your opening prompt says what is out of scope or must not change", cnt(edit_s, "op_scope"), E, 50, ue)
    attr("brief_paths", "design", "Points at the code", "Your opening prompt names files, folders or paths", cnt(edit_s, "op_paths"), E, 60, ue)
    attr("brief_depth", "design", "Writes a full brief", "Your opening prompt is 40 words or more", cnt(edit_s, lambda s: s["op_words"] >= 40), E, 60, ue)
    attr("spec_first", "design", "Starts from a spec", "Bigger changes start from a spec, a goal or an interview", len(designed), B, 65, ub)
    attr("interview", "design", "Lets Claude interview you", "Claude asked you structured questions before building", cnt(base, "interview"), B, 30, ub)
    attr("diagram", "design", "Draws the system", "A diagram was asked for or written", cnt(base, "diagram"), B, 20, ub)
    # explore
    attr("read_first", "explore", "Reads before editing", "Files were read or searched before the first edit", len(explore_first), E, 80, ue)
    attr("search_first", "explore", "Searches the codebase", "Grep or Glob ran before the first edit", cnt(edit_s, "search_before_edit"), E, 60, ue)
    attr("ask_first", "explore", "Asks before building", "You asked how something works before any edit", cnt(edit_s, "understand_before_edit"), E, 40, ue)
    attr("baseline_tests", "explore", "Runs the tests first", "Tests or a build ran before the first edit", cnt(edit_s, "verify_before_edit"), E, 30, ue)
    attr("scout_agent", "explore", "Sends a scout", "A subagent investigated before the first edit", cnt(edit_s, "delegate_before_edit"), E, 20, ue)
    attr("docs_lookup", "explore", "Checks the docs", "Claude searched the web or documentation", cnt(edit_s, "docs_lookup"), E, 20, ue)
    # verify
    attr("verify_any", "verify", "Checks after editing", "Tests, a build, lint or the product ran after edits", len(verified), E, 70, ue)
    attr("verify_tests", "verify", "Runs the tests", "A test command ran after edits", cnt(edit_s, "tests_after_edit"), E, 60, ue)
    attr("verify_build", "verify", "Builds and lints", "A build, lint or type check ran after edits", cnt(edit_s, "build_after_edit"), E, 50, ue)
    attr("verify_product", "verify", "Runs the product", "Claude drove a browser or app after edits", len(ran_product), E, 25, ue)
    attr("verify_tdd", "verify", "Asks for test-first", "You asked for a failing test before the code", cnt(edit_s, "tdd"), E, 25, ue)
    attr("verify_evidence", "verify", "Asks for evidence", "You asked Claude to show output, not only say it works", cnt(edit_s, "evidence_ask"), E, 30, ue)
    attr("verify_last", "verify", "Ends on a green check", "The last check ran after the last edit", cnt(edit_s, "verified_last"), E, 60, ue)
    # review
    attr("review_any", "review", "Gets a second opinion", "Bigger changes got some review step", len(reviewed), B, 50, ub)
    attr("review_agent", "review", "Uses a reviewer agent", "A subagent reviewed the change in a fresh context", cnt(base, "review_subagent"), B, 30, ub)
    attr("review_cmd", "review", "Runs a review command", "/code-review, /simplify, /security-review or similar", cnt(base, "review_cmd"), B, 30, ub)
    attr("review_security", "review", "Looks at security", "A security review was asked for", cnt(base, "security"), B, 15, ub)
    attr("review_diff", "review", "Reads the diff", "git diff, status or show ran after edits", cnt(edit_s, "diff_after_edit"), E, 50, ue)
    # delegate
    attr("sub_any", "delegate", "Uses subagents", "Sessions that handed work to a subagent", len(delegating), N, 40, "sessions")
    attr("sub_parallel", "delegate", "Fans out in parallel", "Two or more subagents started in one step", cnt(sessions, "parallel_subagents"), N, 15, "sessions")
    attr("sub_custom", "delegate", "Uses specialist agents", "A named subagent type, not the general one", cnt(sessions, "custom_subagent"), N, 20, "sessions")
    attr("par_sessions", "delegate", "Runs sessions side by side", "Sessions that overlapped in time with another", overlapping, N, 30, "sessions")
    attr("worktrees", "delegate", "Works in worktrees", "git worktree was used", len(worktree), N, 20, "sessions")
    attr("tasklist", "delegate", "Keeps a task list", "Longer sessions where Claude tracked tasks", cnt(deep_s, "tasklist"), len(deep_s), 50, "sessions with 10+ tool calls")
    # steer
    inv("steer_clean", "steer", "Finishes cleanly", "Few sessions stall or loop on corrections", len(bad), N, 30, "sessions stalled or looped")
    attr("steer_recover", "steer", "Recovers after interrupting", "Interrupted sessions that carried on afterwards", len(recovered), len(interrupted), 90, "interrupted sessions")
    attr("steer_redirect", "steer", "Redirects early", "Sessions where you interrupted and kept going", len(recovered), N, 20, "sessions")
    inv("steer_first_time", "steer", "Rarely has to correct", "Few of your prompts are corrections", all_corr, all_prompts, 25, "prompts were corrections")
    inv("steer_no_loop", "steer", "Avoids correction loops", "Few sessions needed three or more corrections", cnt(sessions, looped), N, 25, "sessions had 3+ corrections")
    inv("steer_errors", "steer", "Stops error spirals", "Few sessions hit three tool errors in a row", cnt(sessions, lambda s: s["max_error_streak"] >= 3), N, 25, "sessions had an error streak")
    inv("steer_context", "steer", "Keeps context lean", "Few sessions ran long enough to be compacted", cnt(sessions, lambda s: s["compactions"] > 0), N, 40, "sessions were compacted")
    # compound
    attr("md_projects", "compound", "CLAUDE.md in projects", "Projects you worked in that have a CLAUDE.md", proj_with_md, len(proj_setup), 90, "projects")
    attr("teach_sessions", "compound", "Teaches Claude as you go", "Sessions that edited CLAUDE.md, a rule or a skill", len(teach_sessions), N, 10, "sessions")
    n_skills = user_setup["skills"] + sum(v["skills"] for v in proj_setup.values())
    flat("skills_owned", "compound", "Owns skills", "Skills in your user folder or projects (four counts as full)", 25 * n_skills, "%d skills found" % n_skills)
    attr("skills_used", "compound", "Uses skills", "A skill or plugin command ran", cnt(sessions, "skill_used"), N, 30, "sessions")
    any_hooks = user_setup["hooks"] or any(v["hooks"] for v in proj_setup.values())
    flat("hooks", "compound", "Enforces with hooks", "Hooks are configured for you or a project", 100 if any_hooks else 0, "hooks found" if any_hooks else "no hooks found")
    n_agents = user_setup["agents"] + sum(v["agents"] for v in proj_setup.values())
    flat("agents_owned", "compound", "Defines custom agents", "Agent files in your user folder or projects (two counts as full)", 50 * n_agents, "%d agent files found" % n_agents)
    attr("mcp_used", "compound", "Connects tools", "An MCP tool was used", cnt(sessions, "mcp_used"), N, 30, "sessions")
    flat("md_user", "compound", "Has personal rules", "A CLAUDE.md in your user folder",
         100 if user_setup["claude_md"] else 0, "found" if user_setup["claude_md"] else "not found")
    # loops
    flat("loop_depth", "loops", "Hands over bigger steps", "Median tool calls per prompt (eight counts as full)", 100.0 * med_calls / 8, "median %s tool calls per prompt" % med_calls)
    attr("loop_long", "loops", "Lets Claude run long", "Sessions with 25 or more tool calls on one prompt", len(long_runs), N, 25, "sessions")
    attr("loop_goal", "loops", "Sets goals", "Sessions that used /goal", len(goal_s), N, 15, "sessions")
    attr("loop_recurring", "loops", "Automates recurring work", "Sessions that used /loop, /schedule or /batch", cnt(sessions, "loop_cmd"), N, 10, "sessions")
    attr("loop_auto", "loops", "Works with automatic approval", "Sessions with automatic approval on", len(auto_sessions), N, 50, "sessions")

    # ---- two sessions worth a second look ----
    def label(s):
        return Path(s["cwd"]).name if s["cwd"] else "unknown"

    def card(s, why):
        d = {
            "why": why, "project": label(s),
            "date": s["start"].astimezone().strftime("%d %b %Y") if s["start"] else "",
            "prompts": s["user_turns"], "files_edited": len(s["edited_files"]),
            "tool_calls": sum(s["tool_calls"].values()), "corrections": s["corrections"],
            "interrupts": s["interrupts"], "file": s["file"],
            "flags": [k for k in ("spec", "goal", "interview", "diagram", "review", "tdd") if s[k]]
                     + (["verified"] if s["verify_after_edit"] else []),
        }
        if not a.no_text and s["first_prompt"]:
            d["opener"] = redact(s["first_prompt"], 220)
        return d

    def strength(s):
        return (2 * s["verify_after_edit"] + 2 * bool(s["spec"] or s["goal"] or s["interview"])
                + s["review"] + bool(any(t in s["tool_calls"] for t in DELEGATE_TOOLS))
                + min(2, (max(s["turn_tool_counts"]) if s["turn_tool_counts"] else 0) / 15.0)
                - 2 * (stalled(s) or looped(s)))

    examples = {}
    if edit_s:
        best = max(edit_s, key=strength)
        if strength(best) >= 3:
            examples["strong"] = card(best, "Your most expert-looking session in this window")
    if bad:
        worst = max(bad, key=lambda s: (s["corrections"], s["interrupts"], s["user_turns"]))
        examples["stuck"] = card(worst, "The session that fought back the most")

    repeated, openers = [], []
    if not a.no_text:
        norm, example = Counter(), {}
        for s in sessions:
            for p in s["prompts"]:
                for sent in re.split(r"(?<=[.!?\n])\s+", p):
                    k = re.sub(r"[\d\W_]+", " ", sent.lower()).strip()
                    if 4 <= len(k.split()) <= 25:
                        norm[k] += 1
                        example.setdefault(k, sent)
        repeated = [{"text": redact(example[k]), "count": c} for k, c in norm.most_common(40) if c >= 3][:12]
        for s in sorted(sessions, key=lambda x: x["start"] or since, reverse=True)[:8]:
            if s["first_prompt"]:
                openers.append({"text": redact(s["first_prompt"], 220), "prompts": s["user_turns"],
                                "files_edited": len(s["edited_files"]),
                                "tool_calls": sum(s["tool_calls"].values()),
                                "has_check": s["brief_has_check"]})

    # ---- history: what changed since last run ----
    previous = None
    if not a.no_history:
        hpath = Path(a.history) if a.history else home / ".claude" / "agentic-coach" / "history.jsonl"
        today = now.astimezone().strftime("%Y-%m-%d")
        rows = [r for r in load_history(hpath) if r.get("date") != today]
        if rows:
            previous = rows[-1]
        rows.append({"date": today, "days": a.days, "sessions": n, "level": level, "scores": scores,
                     "attributes": {x["id"]: x["strength"] for x in attributes}})
        try:
            hpath.parent.mkdir(parents=True, exist_ok=True)
            with open(hpath, "w", encoding="utf-8") as fh:
                for r in rows[-50:]:
                    fh.write(json.dumps(r) + "\n")
        except OSError:
            pass

    out = {
        "version": VERSION,
        "generated": now.isoformat(timespec="seconds"),
        "days": a.days, "sessions": n, "projects": len(projects),
        "level": level, "scores": scores, "attributes": attributes, "previous": previous,
        "signals": {
            "edit_sessions": len(edit_s),
            "multi_file_sessions": len(big_s),
            "started_from_spec_goal_or_interview_pct": r_design,
            "sessions_with_spec": len([s for s in sessions if s["spec"]]),
            "sessions_with_goal": len([s for s in sessions if s["goal"]]),
            "sessions_with_interview": len([s for s in sessions if s["interview"]]),
            "sessions_with_diagram": len([s for s in sessions if s["diagram"]]),
            "opening_prompt_names_a_check_pct": pct(len(briefed), len(edit_s)),
            "explore_before_edit_pct": r_explore,
            "verify_after_edit_pct": r_verify,
            "ran_the_product_sessions": len(ran_product),
            "test_first_sessions": len([s for s in sessions if s["tdd"]]),
            "second_opinion_review_pct": r_review,
            "delegate_calls": delegate_calls,
            "delegate_calls_per_10_sessions": round(per10, 1),
            "sessions_using_subagents": len(delegating),
            "parallel_sessions_pct": r_parallel,
            "worktree_sessions": len(worktree),
            "interrupted_sessions": len(interrupted),
            "recovered_after_interrupt": len(recovered),
            "sessions_with_3plus_corrections": len([s for s in sessions if looped(s)]),
            "stalled_or_correction_loop_pct": r_bad,
            "one_shot_question_sessions": len(one_shot),
            "compactions": sum(s["compactions"] for s in sessions),
            "tool_errors": sum(s["tool_errors"] for s in sessions),
            "claude_md_or_skill_edits": teach_events,
            "sessions_that_taught_claude_pct": r_teach,
            "median_tool_calls_per_prompt": med_calls,
            "long_unattended_runs": len(long_runs),
            "goal_loop_schedule_batch_uses": loop_uses,
            "auto_approval_sessions_pct": r_auto,
            "median_prompt_words": statistics.median(prompt_lens) if prompt_lens else 0,
            "median_opening_prompt_words": statistics.median(first_lens) if first_lens else 0,
            "median_prompts_per_session": statistics.median([s["user_turns"] for s in sessions]),
            "skill_calls": tools.get("Skill", 0),
            "mcp_calls": sum(v for k, v in tools.items() if k.startswith("mcp__")),
        },
        "tool_mix": dict(tools.most_common(15)),
        "commands": dict(commands.most_common(15)),
        "models": dict(models.most_common(5)),
        "setup": {
            "user": user_setup,
            "projects": [{"name": Path(c).name if c != "unknown" else "unknown", "sessions": len(v), **proj_setup[c]}
                         for c, v in sorted(projects.items(), key=lambda kv: -len(kv[1]))][:12],
        },
        "examples": examples,
        "repeated_instructions": repeated,
        "recent_openers": openers,
        "text_included": not a.no_text,
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print("Analysed %d sessions across %d projects (last %d days)." % (n, len(projects), a.days))
    print("Rule-based level: %d. Scores: %s" % (level, ", ".join("%s=%s" % kv for kv in scores.items())))
    rated = [x for x in attributes if x["strength"] is not None]
    print("Attributes: %d, of which %d have enough data." % (len(attributes), len(rated)))
    if previous:
        print("Previous run: %s (level %s)." % (previous.get("date"), previous.get("level")))
    for k, v in examples.items():
        print("Example (%s): %s" % (k, v["file"]))
    print("Metrics written to %s" % a.out)


if __name__ == "__main__":
    main()
