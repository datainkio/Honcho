#!/usr/bin/env python3
"""Measure this project's Claude Code sessions from their transcripts: calls, tokens, weighted cost, time, agents.

The acceptance test for context/package-efficiency-plan.md. Reads ~/.claude/projects/<this repo's key>/*.jsonl and
each session's subagents/*.jsonl. Usage is summed once per unique message id (Claude Code may store a response
several times). 'Weighted' prices each token class against fresh input: cache read 0.1, cache write 1.25,
output 5, input 1. It is a cost proxy that compares across sessions, not dollars.

Usage:
    python3 pipeline/scripts/measure_sessions.py                      # sessions of the last 7 days, one line each
    python3 pipeline/scripts/measure_sessions.py --since 2026-10-13   # from a date (UTC)
    python3 pipeline/scripts/measure_sessions.py --session 8b8fde25   # one session: its agents, one line each
    python3 pipeline/scripts/measure_sessions.py --session 8b8fde25 --match 'match report'   # only agents whose prompt matches
    python3 pipeline/scripts/measure_sessions.py --timeline 125d70db [--gap 5]   # elapsed-time phases: segments, pauses over --gap minutes, agent spans
Standard library only.
"""
import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # the Honcho repo; standard library only, so no naming import
PROJECTS = Path.home() / ".claude" / "projects"
WEIGHTS = {"input_tokens": 1, "cache_creation_input_tokens": 1.25, "cache_read_input_tokens": 0.1, "output_tokens": 5}


def project_dir():
    return PROJECTS / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))


def stats(path):
    """Totals for one transcript: calls, usage, models, tools, agent spawns, first prompt, first and last timestamp."""
    seen, usage, models, tools = set(), collections.Counter(), collections.Counter(), collections.Counter()
    spawns, first, t0, t1 = [], None, None, None
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if ts := d.get("timestamp"):
            t = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            t0, t1 = min(t0 or t, t), max(t1 or t, t)
        m = d.get("message") or {}
        if d.get("type") == "user" and first is None:
            c = m.get("content")
            text = c if isinstance(c, str) else next((b.get("text", "") for b in c or [] if b.get("type") == "text"), "")
            if text and not text.startswith("<"):
                first = " ".join(text.split())[:100]
        if d.get("type") != "assistant":
            continue
        u = m.get("usage")
        if u and m.get("id") and m["id"] not in seen:
            seen.add(m["id"])
            models[m.get("model", "?")] += 1
            for k in WEIGHTS:
                usage[k] += u.get(k) or 0
        for b in m.get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                tools[b.get("name", "")] += 1
                if b.get("name") in ("Agent", "Task"):
                    i = b.get("input") or {}
                    spawns.append((i.get("subagent_type") or "general-purpose", i.get("model") or "inherit"))
    return {"calls": len(seen), "usage": usage, "models": models, "tools": tools, "spawns": spawns,
            "first": first or "", "t0": t0, "t1": t1}


def weighted(u):
    return sum(u[k] * w for k, w in WEIGHTS.items())


def fmt(n):
    return f"{n / 1e6:.2f}M" if n >= 1e6 else f"{n / 1e3:.0f}k"


def minutes(s):
    return (s["t1"] - s["t0"]).total_seconds() / 60 if s["t0"] else 0


MODEL_SHORT = re.compile(r"^claude-|-\d.*$")  # 'claude-opus-4-5-20251101' -> 'opus'


def short_models(models):
    return " ".join(f"{MODEL_SHORT.sub('', k)}:{v}" for k, v in models.most_common() if k != "<synthetic>")


def subagents(sid_path):
    d = sid_path.with_suffix("") / "subagents"
    return [stats(p) for p in sorted(d.glob("*.jsonl"))] if d.is_dir() else []


def list_sessions(since):
    rows = []
    for p in project_dir().glob("*.jsonl"):
        s = stats(p)
        if s["t0"] and s["t0"] >= since and s["calls"]:
            rows.append((p, s))
    rows.sort(key=lambda r: r[1]["t0"])
    print("session   start (UTC)   min  main calls  models                 avg ctx  main wtd  agents  agent wtd  total wtd")
    tot = collections.Counter()
    for p, s in rows:
        subs = subagents(p)
        su = sum((x["usage"] for x in subs), collections.Counter())
        ctx = (s["usage"]["cache_read_input_tokens"] + s["usage"]["cache_creation_input_tokens"] + s["usage"]["input_tokens"]) / s["calls"]
        mw, aw = weighted(s["usage"]), weighted(su)
        tot["main"] += mw
        tot["agents"] += aw
        print(f"{p.stem[:8]}  {s['t0']:%m-%d %H:%M}  {minutes(s):5.0f}  {s['calls']:10}  {short_models(s['models'])[:21]:21}  "
              f"{fmt(ctx):>7}  {fmt(mw):>8}  {len(subs):6}  {fmt(aw):>9}  {fmt(mw + aw):>9}")
    print(f"{len(rows)} sessions; weighted main {fmt(tot['main'])}, agents {fmt(tot['agents'])}, total {fmt(tot['main'] + tot['agents'])}")


def show_session(prefix, match):
    hits = [p for p in project_dir().glob(f"{prefix}*.jsonl")]
    if len(hits) != 1:
        sys.exit(f"{len(hits)} sessions match '{prefix}'")
    p = hits[0]
    s = stats(p)
    print(f"{p.stem}  {s['t0']:%Y-%m-%d %H:%M} UTC  {minutes(s):.0f} min")
    print(f"  main: {s['calls']} calls ({short_models(s['models'])}), cache read {fmt(s['usage']['cache_read_input_tokens'])}, "
          f"cache write {fmt(s['usage']['cache_creation_input_tokens'])}, output {fmt(s['usage']['output_tokens'])}, "
          f"weighted {fmt(weighted(s['usage']))}")
    print(f"  spawns: {collections.Counter(f'{t}/{m}' for t, m in s['spawns']).most_common()}")
    subs = [x for x in subagents(p) if not match or re.search(match, x["first"], re.I)]
    print(f"  agents{' matching ' + repr(match) if match else ''}: {len(subs)}")
    print("    calls  models          cache read  cache write  output  weighted   min  prompt")
    for x in sorted(subs, key=lambda x: x["t0"] or dt.datetime.max.replace(tzinfo=dt.timezone.utc)):
        u = x["usage"]
        print(f"    {x['calls']:5}  {short_models(x['models'])[:14]:14}  {fmt(u['cache_read_input_tokens']):>10}  "
              f"{fmt(u['cache_creation_input_tokens']):>11}  {fmt(u['output_tokens']):>6}  {fmt(weighted(u)):>8}  "
              f"{minutes(x):4.0f}  {x['first'][:70]}")
    if subs:
        su = sum((x["usage"] for x in subs), collections.Counter())
        print(f"  agents total: {sum(x['calls'] for x in subs)} calls, weighted {fmt(weighted(su))}, "
              f"mean {fmt(weighted(su) / len(subs))} per agent")


def utc(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def events(path):
    """(time, kind, label) for each main-session tool call and operator turn, in time order. Meta, tool-result and notification turns are not operator turns."""
    out = []
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        ts, m = d.get("timestamp"), d.get("message") or {}
        if not ts or d.get("isSidechain"):
            continue
        if d.get("type") == "assistant":
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    i = b.get("input") or {}
                    label = i.get("command") or i.get("description") or i.get("subagent_type") or i.get("file_path") or ""
                    out.append((utc(ts), "call", f"{b.get('name', '')} {' '.join(str(label).split())[:60]}".strip()))
        elif d.get("type") == "user" and not d.get("isMeta"):
            c = m.get("content")
            text = c if isinstance(c, str) else next((b.get("text", "") for b in c or [] if b.get("type") == "text"), "")
            text = " ".join(text.split())
            if text and not text.startswith("<task-notification"):
                out.append((utc(ts), "turn", text[:70]))
    return sorted(out, key=lambda e: e[0])


def show_timeline(prefix, gap_min):
    hits = list(project_dir().glob(f"{prefix}*.jsonl"))
    if len(hits) != 1:
        sys.exit(f"{len(hits)} sessions match '{prefix}'")
    p = hits[0]
    ev = events(p)
    if not ev:
        sys.exit("no events")
    t0 = ev[0][0]
    subs = [x for x in subagents(p) if x["t0"]]
    off = lambda t: (t - t0).total_seconds() / 60
    print(f"{p.stem}  {t0:%Y-%m-%d %H:%M:%S} UTC  pauses are gaps over {gap_min:g} min with no call or turn; 'agents' = a subagent ran in the gap")
    print("  start    end   min  what")
    segs, cur = [], [ev[0]]
    for e in ev[1:]:
        if (e[0] - cur[-1][0]).total_seconds() / 60 > gap_min:
            segs.append(cur)
            cur = []
        cur.append(e)
    segs.append(cur)
    pause = agents = 0.0
    for n, seg in enumerate(segs):
        if n:
            a, b = segs[n - 1][-1][0], seg[0][0]
            g = (b - a).total_seconds() / 60
            busy = any(x["t0"] < b and x["t1"] > a for x in subs)
            pause, agents = (pause, agents + g) if busy else (pause + g, agents)
            print(f"  {off(a):5.1f}  {off(b):5.1f}  {g:4.1f}  -- {'agents' if busy else 'PAUSE'}")
        calls = [e for e in seg if e[1] == "call"]
        turns = [e for e in seg if e[1] == "turn"]
        first = (turns or calls)[0][2] if seg else ""
        tools = collections.Counter(e[2].split(" ")[0] for e in calls).most_common(3)
        print(f"  {off(seg[0][0]):5.1f}  {off(seg[-1][0]):5.1f}  {off(seg[-1][0]) - off(seg[0][0]):4.1f}  "
              f"{len(calls)} calls, {len(turns)} turns {dict(tools)}  {first[:60]}")
    print(f"  pauses {pause:.1f} min, waits on agents {agents:.1f} min, session {off(ev[-1][0]):.1f} min")
    if subs:
        print("  agents: start   end   min  prompt")
        for x in sorted(subs, key=lambda x: x["t0"]):
            print(f"    {off(x['t0']):6.1f} {off(x['t1']):6.1f} {minutes(x):5.1f}  {x['first'][:70]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since", help="UTC date, YYYY-MM-DD (default: 7 days ago)")
    ap.add_argument("--session", help="session id or its first characters: list its agents")
    ap.add_argument("--timeline", help="session id or its first characters: calls, operator pauses and agent spans against the clock")
    ap.add_argument("--gap", type=float, default=5.0, help="with --timeline: minutes of silence that end a segment (default 5)")
    ap.add_argument("--match", help="with --session: only agents whose first prompt matches this regex")
    args = ap.parse_args()
    if not project_dir().is_dir():
        sys.exit(f"no transcripts at {project_dir()}")
    if args.timeline:
        show_timeline(args.timeline, args.gap)
        return
    if args.session:
        show_session(args.session, args.match)
        return
    since = (dt.datetime.fromisoformat(args.since).replace(tzinfo=dt.timezone.utc) if args.since
             else dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7))
    list_sessions(since)


if __name__ == "__main__":
    main()
