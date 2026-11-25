#!/usr/bin/env python3
"""
Build the interactive coaching report (one self-contained HTML file).

Usage:
  python3 build_report.py --metrics metrics.json --coaching coaching.json \
                          --out report.html [--path-url URL]

coaching.json is written by Claude after reading metrics.json and the rubric.
See SKILL.md for its shape. Every field is optional; missing parts are skipped.
"""
import argparse
import html
import json

PATH_URL = "https://claude.ai/artifact/QEQb3VQKwMiBipPVx5hCYs"
LEVEL_SLUGS = {1: "getting-started", 2: "building-habits", 3: "extending"}
LEVEL_NAMES = {1: "Getting started", 2: "Building habits", 3: "Extending and scaling"}

# key, title, what it measures, practice to borrow, who it comes from
DIMENSIONS = [
    ("design", "Design before building", "Graphs, specs and goals before code",
     "Have Claude interview you, write a self-contained spec, then build it in a fresh session.",
     "Anthropic, Best practices for Claude Code"),
    ("explore", "Ground it first", "Reading and searching before the first edit",
     "Open with a question or with the test suite, so Claude learns the project before it changes it.",
     "Simon Willison, Agentic Engineering Patterns"),
    ("verify", "Make Claude prove it", "Tests, builds or a running product after edits",
     "Verification means the agent can run the thing, not only that unit tests pass.",
     "Boris Cherny, as summarised by The Neuron, June 2026"),
    ("review", "Maker and checker", "A second agent or review step on bigger changes",
     "A separate agent reviews the change in a fresh context before the pull request. Stop after three rounds and rethink.",
     "The Claude Code team's review process"),
    ("delegate", "Delegate and parallelise", "Subagents, parallel sessions, worktrees",
     "Run three to five sessions at once, each in its own git worktree.",
     "Anthropic, Claude Code power user tips"),
    ("steer", "Steer and recover", "Sessions that stall or loop on corrections",
     "After two failed corrections, clear the session and restart with a better prompt.",
     "Anthropic, Best practices for Claude Code"),
    ("compound", "Teach Claude once", "CLAUDE.md, skills and hooks that grow over time",
     "Whenever Claude makes a mistake, add a rule so it never repeats it.",
     "Anthropic, Claude Code power user tips"),
    ("loops", "Build loops", "Long runs, /goal, /loop and unattended work",
     "Design the loop that prompts the agent, with a stop condition it can check.",
     "Addy Osmani, Loop Engineering"),
]

CSS = """
:root{--bg:#F3F4F8;--soft:#FFFFFF;--ink:#14171C;--muted:#6B7280;--subtle:#8B919C;--border:#D9DCE3;
--brand:#4F2FE8;--brand-strong:#3F25BA;--accent:#4F2FE8;--stage:#14171C;--stage-ink:#FFFFFF;--stage-muted:#BAC0CA;
--tint:#9D8CF5;--magma:#EE7A4A;--good:#1DA838;--bad:#C2410C;color-scheme:light;
--sans:"Inter Tight","Helvetica Neue",Helvetica,Arial,system-ui,sans-serif;--mono:"JetBrains Mono","SFMono-Regular",Consolas,"Liberation Mono",monospace}
@media (prefers-color-scheme:dark){:root{--bg:#14171C;--soft:#1C2028;--ink:#FFFFFF;--muted:#BAC0CA;--subtle:#8B919C;--border:#323844;
--accent:#9D8CF5;--stage:#0E1014;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none;border-bottom:1px solid currentColor}a:hover{color:var(--accent)}
.w{max-width:1040px;margin:0 auto;padding:0 24px}
.stage{background:var(--stage);color:var(--stage-ink);padding:56px 0 64px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.26em;text-transform:uppercase;color:var(--tint);margin:0 0 20px}
.dot{color:var(--magma)}
h1{font-weight:600;font-size:clamp(34px,5.5vw,64px);line-height:1;letter-spacing:-.03em;margin:0;max-width:20ch;text-wrap:balance}
.lede{color:var(--stage-muted);font-size:18px;max-width:60ch;margin:24px 0 0}
.lvl{display:flex;gap:16px 32px;align-items:baseline;flex-wrap:wrap;margin-top:40px;padding-top:24px;border-top:1px solid rgba(255,255,255,.18)}
.lvl .k{font-family:var(--mono);font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--subtle)}
.lvl b{font-weight:500;font-size:24px}
.btn{display:inline-block;background:#fff;color:#14171C;border:0;border-radius:9999px;padding:12px 24px;font:500 15px/1 inherit;cursor:pointer}
.btn:hover{opacity:.9;color:#14171C}
section{padding:72px 0;border-bottom:1px solid var(--border)}
section.soft{background:var(--soft)}
.head{display:grid;grid-template-columns:1.1fr 1fr;gap:24px 64px;align-items:end;margin-bottom:40px}
h2{font-weight:600;font-size:clamp(28px,3.6vw,44px);line-height:1.05;letter-spacing:-.025em;margin:0;text-wrap:balance}
.head p{margin:0;color:var(--muted);max-width:52ch}
.dim{border-top:1px solid var(--border)}.dim:last-child{border-bottom:1px solid var(--border)}
.dim button.row{all:unset;box-sizing:border-box;display:grid;grid-template-columns:44px 1fr auto auto;gap:16px;align-items:center;width:100%;padding:20px 0;cursor:pointer}
.dim button.row:focus-visible,.copy:focus-visible,.btn:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.n{color:var(--magma);font-family:var(--mono);font-size:20px}
.dim .t{font-weight:500;font-size:20px;display:block}.dim .s{color:var(--muted);font-size:14px}
.pips{display:flex;gap:4px}.pips i{width:22px;height:8px;background:var(--border)}.pips i.on{background:var(--magma)}
.delta{font-size:13px;font-variant-numeric:tabular-nums;min-width:3.2em;text-align:right;color:var(--muted)}
.delta.up{color:var(--good)}.delta.down{color:var(--bad)}
.body{display:none;padding:0 0 28px 60px}.dim.open .body{display:block}
.body p{margin:0 0 12px;max-width:68ch}.lab{font-weight:500}
.borrow{border-left:2px solid var(--magma);padding:2px 0 2px 16px;margin:16px 0;max-width:68ch}
.borrow .who{display:block;color:var(--muted);font-size:14px;margin-top:4px}
pre{white-space:pre-wrap;word-break:break-word;background:var(--soft);border-radius:12px;padding:18px 20px;margin:8px 0;font:13.5px/1.6 var(--mono)}
section.soft pre{background:var(--bg)}
.copy{all:unset;cursor:pointer;font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
.copy:hover{color:var(--accent)}
.exp{display:grid;grid-template-columns:44px 1fr;gap:16px;padding:24px 0;border-top:1px solid var(--border)}
.exp h3,.card h3{margin:0 0 6px;font-weight:500;font-size:22px}
.exp p{margin:0 0 8px;max-width:68ch;color:var(--muted)}
.exp label{display:inline-flex;gap:8px;align-items:center;font-size:14px;margin-top:8px;cursor:pointer}
.exp input{width:16px;height:16px;accent-color:var(--brand)}
.exp.done h3{color:var(--muted);text-decoration:line-through}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}
.card{background:var(--soft);border:1px solid var(--border);border-radius:12px;padding:28px}
.card .k{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--subtle);font-weight:500;margin-bottom:12px;display:block}
.card p{margin:0 0 10px;color:var(--muted)}.card .q{color:var(--ink)}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0}
.pill{border:1px solid var(--border);border-radius:9999px;padding:4px 12px;font-size:13px}
ul.plain{margin:8px 0;padding:0;list-style:none}ul.plain li{padding:10px 0;border-top:1px solid var(--border);max-width:68ch}
table{border-collapse:collapse;width:100%;font-size:14px}td{border-top:1px solid var(--border);padding:8px 0}td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.bar{display:grid;grid-template-columns:10rem 1fr 3rem;gap:12px;align-items:center;font-size:14px;margin:6px 0}
.bar span.b{height:8px;background:var(--magma)}.bar span:last-child{text-align:right;font-variant-numeric:tabular-nums}
details summary{cursor:pointer;font-weight:500;margin:24px 0 8px}
.note{color:var(--muted);font-size:14px;max-width:72ch;margin-top:24px}
footer{padding:32px 0 48px;color:var(--muted);font-size:13px}
@media (max-width:700px){.head{grid-template-columns:1fr}.dim button.row{grid-template-columns:28px 1fr auto}.delta{display:none}.body{padding-left:0}.exp{grid-template-columns:28px 1fr}.bar{grid-template-columns:6.5rem 1fr 2.5rem}section{padding:48px 0}}
"""

JS = """
document.querySelectorAll('.dim button.row').forEach(function(b){b.addEventListener('click',function(){var d=b.parentElement;var o=d.classList.toggle('open');b.setAttribute('aria-expanded',String(o));});});
document.querySelectorAll('.copy').forEach(function(b){var label=b.textContent;b.addEventListener('click',function(){var t=document.getElementById(b.dataset.for).textContent;
 function done(m){b.textContent=m;setTimeout(function(){b.textContent=label},1600)}
 try{navigator.clipboard.writeText(t).then(function(){done('Copied')},function(){done('Select the text to copy')})}catch(e){done('Select the text to copy')}});});
var KEY='agentic-coach-done-'+document.body.dataset.run;function ld(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){return{}}}
var st=ld();document.querySelectorAll('.exp input').forEach(function(c){if(st[c.dataset.id]){c.checked=true;c.closest('.exp').classList.add('done')}
 c.addEventListener('change',function(){st[c.dataset.id]=c.checked;c.closest('.exp').classList.toggle('done',c.checked);try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}});});
"""


def e(x):
    return html.escape(str(x)) if x is not None else ""


def dotted(text):
    """Headline with the Moberg coloured full stop."""
    t = str(text).rstrip()
    if t.endswith(("?", "!")):
        return e(t)
    return e(t.rstrip(".")) + '<span class="dot">.</span>'


def pips(score):
    return '<span class="pips" role="img" aria-label="%d of 4">%s</span>' % (
        score, "".join('<i class="on"></i>' if i < score else "<i></i>" for i in range(4)))


def delta(now, prev):
    if prev is None:
        return '<span class="delta"></span>'
    d = now - prev
    if d > 0:
        return '<span class="delta up">+%d</span>' % d
    if d < 0:
        return '<span class="delta down">%d</span>' % d
    return '<span class="delta">same</span>'


def prompt_block(pid, text, label="Copy prompt"):
    if not text:
        return ""
    return ('<pre id="%s">%s</pre><button class="copy" data-for="%s">%s</button>'
            % (pid, e(text), pid, e(label)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics", required=True)
    ap.add_argument("--coaching", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--path-url", default=PATH_URL)
    a = ap.parse_args()

    m = json.load(open(a.metrics, encoding="utf-8"))
    c = json.load(open(a.coaching, encoding="utf-8")) if a.coaching else {}
    if not m.get("sessions"):
        raise SystemExit("metrics.json has no sessions; nothing to report.")

    level = int(c.get("level") or m.get("level") or 1)
    scores = m.get("scores", {})
    sig = m.get("signals", {})
    dims = c.get("dimensions", {})
    prev = m.get("previous") or {}
    pscores = prev.get("scores") or {}
    path_link = "%s#%s" % (a.path_url, LEVEL_SLUGS.get(level, ""))
    run = e(m.get("generated", "")[:10])

    o = ['<!doctype html><html lang="en"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">'
         '<title>Claude Code coaching report</title><link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"><style>%s</style></head><body data-run="%s">' % (CSS, run)]

    # stage
    o.append('<header class="stage"><div class="w"><p class="eyebrow">Moberg · Your Claude Code coaching report</p>')
    o.append("<h1>%s</h1>" % dotted(c.get("headline") or "How you work with Claude Code"))
    if c.get("summary"):
        o.append('<p class="lede">%s</p>' % e(c["summary"]))
    o.append('<div class="lvl"><span><span class="k">Start from</span><br><b>Level %d · %s</b></span>'
             '<span><span class="k">Based on</span><br><b>%s sessions, last %s days</b></span>'
             % (level, e(LEVEL_NAMES.get(level, "")), e(m.get("sessions")), e(m.get("days"))))
    if prev.get("date"):
        o.append('<span><span class="k">Compared with</span><br><b>your run on %s</b></span>' % e(prev["date"]))
    o.append('<a class="btn" href="%s" target="_blank" rel="noopener">Open your learning path →</a></div></div></header><main>' % e(path_link))

    # experiments first: the thing to act on
    exps = c.get("experiments", [])
    if exps:
        o.append('<section><div class="w"><div class="head"><h2>Three experiments for this week<span class="dot">.</span></h2>'
                 '<p>Try each one on a real ticket. Tick it off when you have, then run the coach again in two or three weeks.</p></div>')
        for i, x in enumerate(exps):
            o.append('<div class="exp"><span class="n">%02d</span><div><h3>%s</h3><p>%s</p>%s'
                     '<br><label><input type="checkbox" data-id="x%d"> I tried this</label></div></div>'
                     % (i + 1, e(x.get("title")), e(x.get("why")), prompt_block("x-%d" % i, x.get("prompt")), i))
        o.append("</div></section>")

    # dimensions
    o.append('<section class="soft"><div class="w"><div class="head"><h2>Eight habits, from your own sessions<span class="dot">.</span></h2>'
             '<p>Each score runs from 0 to 4 and comes from patterns in your transcripts. Open a row for what we saw, what to try, and whose practice it borrows.</p></div>')
    for i, (key, title, sub, borrow, who) in enumerate(DIMENSIONS):
        d = dims.get(key, {})
        sc = int(scores.get(key) or 0)
        first = i == 0
        o.append('<div class="dim%s"><button class="row" aria-expanded="%s"><span class="n">%02d</span>'
                 '<span><span class="t">%s</span><span class="s">%s</span></span>%s%s</button><div class="body">'
                 % (" open" if first else "", "true" if first else "false", i + 1, e(title), e(sub),
                    delta(sc, pscores.get(key)), pips(sc)))
        if d.get("observation"):
            o.append('<p><span class="lab">What we saw. </span>%s</p>' % e(d["observation"]))
        if d.get("next"):
            o.append('<p><span class="lab">Try next. </span>%s</p>' % e(d["next"]))
        o.append('<div class="borrow">%s<span class="who">%s</span></div>' % (e(borrow), e(who)))
        o.append(prompt_block("p-%s" % key, d.get("prompt")))
        o.append("</div></div>")
    o.append("</div></section>")

    # two sessions
    ex = m.get("examples") or {}
    notes = c.get("session_notes") or {}
    if ex:
        o.append('<section><div class="w"><div class="head"><h2>Two sessions worth a second look<span class="dot">.</span></h2>'
                 '<p>One that went the way experts work, and one that fought back. The difference between them is usually the lesson.</p></div><div class="two">')
        for key, lab in (("strong", "Went well"), ("stuck", "Got stuck")):
            x = ex.get(key)
            if not x:
                continue
            o.append('<div class="card"><span class="k">%s · %s · %s</span>' % (e(lab), e(x.get("project")), e(x.get("date"))))
            if x.get("opener"):
                o.append('<p class="q">“%s”</p>' % e(x["opener"]))
            o.append("<p>%s prompts, %s files edited, %s tool calls, %s corrections, %s interrupts.</p>"
                     % (e(x.get("prompts")), e(x.get("files_edited")), e(x.get("tool_calls")),
                        e(x.get("corrections")), e(x.get("interrupts"))))
            if notes.get(key):
                o.append('<p class="q">%s</p>' % e(notes[key]))
            if x.get("flags"):
                o.append('<div class="pills">%s</div>' % "".join('<span class="pill">%s</span>' % e(f) for f in x["flags"]))
            o.append("</div>")
        o.append("</div></div></section>")

    # make permanent
    md, sk = c.get("claude_md", []), c.get("skills_to_build", [])
    if md or sk:
        o.append('<section class="soft"><div class="w"><div class="head"><h2>Teach Claude once<span class="dot">.</span></h2>'
                 '<p>Instructions you keep repeating belong in CLAUDE.md or a skill, so you stop typing them.</p></div>')
        if md:
            o.append('<p class="lab">Lines for CLAUDE.md</p>' + prompt_block("md", "\n".join("- " + x for x in md), "Copy lines"))
        if sk:
            o.append('<p class="lab" style="margin-top:32px">Skills worth building</p><ul class="plain">' +
                     "".join("<li><span class='lab'>%s</span><br>%s</li>" % (e(x.get("name")), e(x.get("why"))) for x in sk) + "</ul>")
        o.append("</div></section>")

    # teach me
    tm = c.get("teach_me", [])
    if tm:
        o.append('<section><div class="w"><div class="head"><h2>Teach yourself with an interactive page<span class="dot">.</span></h2>'
                 '<p>Paste one of these into Claude. It builds an interactive explainer for your weakest areas, the same way this report was built.</p></div>')
        for i, x in enumerate(tm):
            o.append('<p class="lab" style="margin-top:24px">%s</p>%s' % (e(x.get("topic")), prompt_block("t-%d" % i, x.get("prompt"))))
        o.append("</div></section>")

    # numbers
    o.append('<section class="soft"><div class="w"><div class="head"><h2>The numbers behind it<span class="dot">.</span></h2>'
             '<p>Scores are estimates. A low score with few sessions behind it means little.</p></div>')
    tmix = m.get("tool_mix", {})
    if tmix:
        mx = max(tmix.values())
        o.append('<p class="lab">Tools Claude used most</p>')
        for k, v in list(tmix.items())[:10]:
            o.append('<div class="bar"><span>%s</span><span class="b" style="width:%d%%"></span><span>%s</span></div>'
                     % (e(k if len(k) < 22 else k[:20] + "…"), max(2, int(100 * v / mx)), e(v)))
    o.append("<details><summary>All signals</summary><table>")
    for k, v in sig.items():
        o.append("<tr><td>%s</td><td>%s</td></tr>" % (e(k.replace("_", " ")), e("n/a" if v is None else v)))
    o.append("</table></details>")
    share = "Claude Code habits (0-4), last %s days, %s sessions: %s. Level %d." % (
        m.get("days"), m.get("sessions"),
        ", ".join("%s %s" % (t.lower(), int(scores.get(k) or 0)) for k, t, _, _, _ in DIMENSIONS), level)
    o.append('<p class="lab" style="margin-top:32px">Want to share with your team?</p>'
             '<p class="note" style="margin-top:4px">Share this line, not the report. It has scores only and none of your prompts.</p>'
             + prompt_block("share", share, "Copy scores only"))
    o.append('<p class="note">Built only from transcripts on this computer. This file contains short, redacted snippets of your prompts, '
             'so keep it on your machine and don\'t attach it to tickets or chats.</p>')
    o.append("</div></section></main>")
    o.append('<footer><div class="w">Generated by the agentic-coach skill, version 2.1. Scoring rules and sources: references/rubric.md in the skill folder. '
             'Scores are rough estimates for your own learning. They are not a performance measure and should not be used to evaluate anyone.</div></footer>')
    o.append("<script>%s</script></body></html>" % JS)

    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o))
    print("Report written to", a.out)


if __name__ == "__main__":
    main()
