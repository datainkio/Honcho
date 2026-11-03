#!/usr/bin/env python3
"""Read UI/UX Jobs Board (uiuxjobsboard.com) list and job pages over plain HTTP; stage job descriptions verbatim.

`search` walks a list page newest first and stops at the first card that is Expired or older than
max_age_days (Featured cards are kept and never stop the walk). `stage` fetches job pages, converts
div.job-description mechanically to text (nothing added, reordered or reworded) and writes
logs/inbox/<id>.md. `check` runs the parser on saved pages with no network.
Settings come from the `uiux:` block of the profile's criteria file. Spec: pipeline/specs/integrated-datasources-spec.md.

Usage:
    python3 pipeline/scripts/sources/uiux_board.py search uiux-remote-us [--write]          # dry run: print the kept cards
    python3 pipeline/scripts/sources/uiux_board.py stage --search uiux-remote-us [--write] /job/<id>-<slug> ...
    python3 pipeline/scripts/sources/uiux_board.py stage [--write] uiux-remote-us=/job/<id>-<slug> uiux-remote-anywhere=/job/<id>-<slug> ...
    python3 pipeline/scripts/sources/uiux_board.py check logs/fixtures/uiux-board/*.html # offline

Stops the run (exit 1) on a list page other than 200, any 403/429/5xx, or a Cloudflare page. No retries.
"""
import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from sources import common  # noqa: E402
from sources.common import Fail, Stop, q, safe_write  # noqa: E402

ROOT = naming.ROOT
INBOX = naming.INBOX
SEARCHES = naming.SEARCHES

BASE = "https://uiuxjobsboard.com"
USER_AGENT = "uiux_board.py (personal job search; manual runs)"
TIMEOUT = 30
CHALLENGE_HEAD = ("Just a moment", "Attention Required")  # <title> or the first 3,000 characters only: a description could say either
CHALLENGE_BODY = ("cf-chl", "_cf_chl_opt", "Verify you are human")
FILLED = "This role has been successfully filled!"
JOB_PATH = re.compile(r"^(?:https://uiuxjobsboard\.com)?(/job/(\d{6,})-([a-z0-9]+(?:-[a-z0-9]+)*))$")
CARD_HREF = re.compile(r'href="(/job/(\d+)-[^"/?#]+)"')  # looser than JOB_PATH: an odd slug fails loudly at stage, never vanishes here


# ---------- config ----------

def load_uiux():
    """The `sources: uiux:` block, once its `enabled` is checked (opt-in, D17). `check` never reads the config."""
    return common.source_cfg("uiux")


def find_search(cfg, name):
    return common.find_search(cfg, name, "uiux")


# ---------- network (one place; the harness replaces fetch) ----------

_last_end = time.monotonic()  # when the previous request finished; starting at load paces the first request too, across back-to-back runs


def fetch(url):
    """Return (status, body). HTTP errors come back as a status; network errors stop the run."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Stop(f"network error on {url}: {e}")


def get(url, delay, kind):
    """Paced GET. kind is 'list' or 'job'. Returns (status, body, fetched_at); raises Stop per the hard rules."""
    global _last_end
    wait = delay - (time.monotonic() - _last_end)
    if wait > 0:
        time.sleep(wait)
    try:
        status, body = fetch(url)
    finally:
        _last_end = time.monotonic()
    fetched_at = dt.datetime.now()
    if status in (403, 429) or status >= 500:
        raise Stop(f"HTTP {status} on {url}")
    if kind == "list" and status != 200:
        raise Stop(f"list page returned HTTP {status}: {url}")
    if kind == "job" and status not in (200, 404):
        raise Stop(f"job page returned HTTP {status}: {url}")
    t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    head = (t.group(1) if t else "") + body[:3000]
    for m in CHALLENGE_HEAD:
        if m in head:
            raise Stop(f"challenge page ('{m}') on {url}")
    for m in CHALLENGE_BODY:
        if m in body:
            raise Stop(f"challenge page ('{m}') on {url}")
    return status, body, fetched_at


# ---------- body conversion ----------

# Every tag not listed here acts as a block (p, div, h1, li, dd, section…): an unknown tag then costs at most a
# line break, never two words run together.
INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "del", "dfn", "em", "font", "i", "img", "ins", "kbd",
          "label", "mark", "o:p", "q", "s", "samp", "small", "span", "strike", "strong", "sub", "sup", "time", "tt", "u",
          "var", "wbr"}
SKIP = {"script", "style"}
WS = re.compile(r"[ \t\n\r\f]+")


class DescParser(HTMLParser):
    """Feed the HTML after the opening tag of div.job-description; stops at that div's own closing tag."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.buf = []
        self.depth = 0       # nested div depth; the container itself is depth 0
        self.done = False
        self.lists = 0       # open ul/ol count
        self.skip = 0
        self.need_blank = False
        self.prefix = None   # pending '- ' for the next line

    def flush(self):
        text = WS.sub(" ", "".join(self.buf)).strip(" ")
        self.buf = []
        if not text:
            return
        if self.need_blank and self.lines and self.lines[-1] != "":
            self.lines.append("")
        self.need_blank = False
        if self.prefix is not None:
            text, self.prefix = self.prefix + text, None
        self.lines.append(text)

    def block(self):
        self.flush()
        if not self.lists:
            self.need_blank = True

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if tag in SKIP:
            self.skip += 1
        elif tag == "br":
            if "".join(self.buf).strip(" \xa0\t\n\r\f"):
                self.flush()
            else:
                self.buf = []
                self.lines.append("")
        elif tag == "li":
            self.flush()
            self.prefix = "  " * max(self.lists - 1, 0) + "- "
        elif tag in ("td", "th"):
            if self.buf:
                self.buf.append(" ")
        elif tag not in INLINE:
            if tag == "div":
                self.depth += 1
            if tag in ("ul", "ol"):
                self.flush()
                if not self.lists:
                    self.need_blank = True
                self.lists += 1
            else:
                self.block()

    def handle_startendtag(self, tag, attrs):
        if tag in ("br", "hr"):
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self.done:
            return
        if tag in SKIP:
            self.skip = max(self.skip - 1, 0)
        elif tag == "div":
            if self.depth == 0:
                self.flush()
                self.done = True
                return
            self.depth -= 1
            self.block()
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists = max(self.lists - 1, 0)
            if not self.lists:
                self.need_blank = True
        elif tag == "li":
            self.flush()
        elif tag not in INLINE and tag not in ("td", "th", "br"):
            self.block()

    def handle_data(self, data):
        if self.done or self.skip:
            return
        self.buf.append(data.replace("\xa0", " "))

    def text(self):
        self.flush()
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.lines)).strip("\n")


DESC_OPEN = re.compile(r'<div class="job-description[^"]*"[^>]*>')


def convert_body(page):
    m = DESC_OPEN.search(page)
    if not m:
        return None
    p = DescParser()
    p.feed(page[m.end():])
    p.close()
    return p.text()


# ---------- job page ----------

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]*>", "", s))


def job_header(page):
    for m in re.finditer(r"<header\b.*?</header>", page, re.S):
        if "<h1" in m.group(0) and "LOCATION" in m.group(0):
            return m.group(0)
    return None


def json_ld_posting(page):
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            data = json.loads(m.group(1), strict=False)
        except ValueError:
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict) and d.get("@type") == "JobPosting":
                return d
    return None


def header_location(header):
    m = re.search(r"LOCATION</span><span[^>]*>(.*?)</span>", header or "", re.S)
    if not m:
        return None
    parts = [strip_tags(t).strip() for t in re.findall(r"<(?:a|span)\b[^>]*>(.*?)</(?:a|span)>", m.group(1), re.S)]
    parts = [p for p in parts if p] or [strip_tags(m.group(1)).strip()]
    return ", ".join(parts)


def parse_job(page):
    """Markers, note fields and body for a job page; `problems` empty means stageable."""
    header = job_header(page)
    posting = json_ld_posting(page)
    markers = {
        "POSTED": bool(header and "POSTED" in header),
        "</header>": header is not None,
        "job-description": bool(DESC_OPEN.search(page)),
        "Share this job": "Share this job" in page,
        "JobPosting": posting is not None,
    }
    filled = FILLED in page
    missing = [k for k, v in markers.items() if not v]
    fields, body = {}, None
    if posting is not None:
        org = posting.get("hiringOrganization") or {}
        loc = header_location(header)
        fields = {
            "title": (posting.get("title") or "").strip(),
            "company": ((org.get("name") if isinstance(org, dict) else "") or "").strip(),
            "location": loc or "",
            "work_type": "remote" if (loc or "").startswith("Remote") else "hybrid" if (loc or "").startswith("Hybrid") else "",
            "posted": str(posting.get("datePosted") or "")[:10],
        }
    elif header:  # filled / odd pages: header fallback, for the skip line only
        co = re.search(r"<span>(.*?)<span> is hiring</span>", header, re.S)
        ti = re.search(r'<span class="text-5xl[^>]*>(.*?)</span>', header, re.S)
        fields = {"title": strip_tags(ti.group(1)).strip() if ti else "",
                  "company": strip_tags(co.group(1)).strip() if co else ""}
    if markers["job-description"]:
        body = convert_body(page)
    if filled:
        verdict = "refuse: filled"
    elif missing:
        verdict = "refuse: missing " + ", ".join(missing)
    elif not body:
        verdict = "refuse: empty description"
    elif not all(fields.get(k) for k in ("title", "company", "posted")):
        verdict = "refuse: JobPosting lacks title, company or datePosted"
    else:
        verdict = "ok"
    return {"markers": markers, "filled": filled, "missing": missing, "fields": fields, "body": body, "verdict": verdict}


def word_count(body):
    return len(re.sub(r"(?m)^( *)- ", r"\1", body).split())


def build_note(job_id, url, f, retrieved_at, body, search):
    head = [
        "---",
        "type: uiux-job",
        f"job_id: {q(str(job_id))}",
        f"url: {q(url)}",
        f"title: {q(f['title'])}",
        f"company: {q(f['company'])}",
        f"location: {q(f['location']) if f['location'] else ''}".rstrip(),
        f"work_type: {f['work_type']}".rstrip(),
        f"retrieved_at: {retrieved_at.strftime('%Y-%m-%dT%H:%M:%S')}",
        f"posted: {f['posted']}",
        f"source_search: {q(search)}",
        "---",
    ]
    return "\n".join(head) + f"\n\n# {f['title']} — {f['company']}\n\n{body}\n"


# ---------- list page ----------

CARD_SPLIT = re.compile(r'(?=<div class="[^"]*\bborder shadow-xs rounded-xl\b)')


def parse_cards(page):
    cards = []
    for chunk in CARD_SPLIT.split(page)[1:]:
        href = CARD_HREF.search(chunk)
        if not href:
            continue
        opening = chunk[:chunk.index(">")]
        co = re.search(r'<span class="text-xl[^>]*>(.*?)</span></span>(?=<span class="text-2xl)', chunk, re.S)
        ti = re.search(r'<span class="text-2xl[^>]*>(.*?)</span>', chunk, re.S)
        ty = re.search(r'<span class="text-xs uppercase opacity-80 mr-3">(.*?)</span>', chunk, re.S)
        sal = re.search(r'mr-3">.*?</span><span class="text-xs uppercase opacity-80">(.*?)</span>', chunk, re.S)
        loc = re.search(r'<div class="flex flex-wrap[^>]*>(.*?)</div>', chunk, re.S)
        age = re.search(r'<div class="text-sm">(.*?)</div></div>', chunk, re.S)
        company = strip_tags(co.group(1)).strip() if co else ""
        company = re.sub(r"\s*is hiring$", "", company)
        parts = [strip_tags(t).strip() for t in re.findall(r"<a\b[^>]*>(.*?)</a>", loc.group(1), re.S)] if loc else []
        age_txt = strip_tags(age.group(1)).strip() if age else ""
        feat = "bg-accentColor" in opening or "★ Featured" in age_txt
        cards.append({
            "id": href.group(2), "path": href.group(1), "company": company,
            "title": strip_tags(ti.group(1)).strip() if ti else "",
            "type": strip_tags(ty.group(1)).strip() if ty else "",
            "salary": strip_tags(sal.group(1)).strip() if sal else "",
            "location": ", ".join(p for p in parts if p),
            "featured": bool(feat), "expired": age_txt == "Expired" and not feat,
            "age": "" if feat else age_txt,
        })
    return cards


def has_next(page):
    return bool(re.search(r'<nav aria-label="Pagination".*?rel="next"', page, re.S))


def is_list(page):
    return 'aria-label="Pagination"' in page or bool(re.search(r"<h1[^>]*>Explore ", page))


AGE = re.compile(r"^(\d+)\s*(mo|min|h|m|d|w|y)$")
UNIT_DAYS = {"h": 0, "m": 0, "min": 0, "d": 1, "w": 7, "mo": 30, "y": 365}


def age_days(txt):
    m = AGE.match(txt)
    if not m:
        raise Fail(f"cannot read card age '{txt}'")
    return int(m.group(1)) * UNIT_DAYS[m.group(2)]


# ---------- commands ----------

def cmd_search(args):
    cfg = load_uiux()
    s = find_search(cfg, args.name)
    delay = common.pacing(cfg, "fetch_delay_seconds", 5)
    max_age, max_pages, slug = s["max_age_days"], s["max_pages"], s["slug"]
    base_url = f"{BASE}/design-jobs/{slug}"
    kept, stopped, more = [], False, False
    for n in range(1, max_pages + 1):
        url = base_url if n == 1 else f"{base_url}?page={n}"
        _, page, _ = get(url, delay, "list")
        cards = parse_cards(page)
        if n == 1 and not cards:
            raise Fail(f"zero cards on page 1 of {url}: unknown slug or layout change, not 'nothing new'")
        blank = [c["id"] for c in cards if not (c["title"] and c["company"])]
        if blank:
            raise Fail(f"cards without a title or company on {url} ({', '.join(blank[:5])}): layout may have changed")
        for c in cards:
            if not c["featured"]:
                if c["expired"] or age_days(c["age"]) > max_age:
                    stopped = True
                    break
            kept.append(c)
        if stopped:
            break
        more = has_next(page)
        if not more:
            break
    if not stopped and more:
        print(f"warning: stopped at max_pages={max_pages}; more postings within {max_age} days may be on the next page", file=sys.stderr)
    for c in kept:
        print(" | ".join([c["id"], c["company"], c["title"], c["type"], c["location"], c["age"], "yes" if c["featured"] else "", c["path"]]))
    print(f"{len(kept)} kept")
    if not args.write:
        return 0
    now = dt.datetime.now()
    out = SEARCHES / f"{now.strftime('%Y-%m-%d')}--{args.name}.md"
    if out.exists():
        raise Fail(f"{out} exists; not overwriting")
    esc = lambda v: str(v).replace("|", "\\|")
    rows = [f"| {c['id']} | " + " | ".join(esc(c[k]) for k in ("title", "company", "location", "type", "age")) +
            f" | {'yes' if c['featured'] else ''} | {c['path']} |" for c in kept]
    text = "\n".join([
        "---", "type: uiux-search-run", f"search_name: {q(args.name)}", f"run_at: {now.strftime('%Y-%m-%dT%H:%M:%S')}",
        "criteria:", f"  slug: {q(slug)}", f"  url: {q(base_url)}", f"  max_age_days: {max_age}", f"  max_pages: {max_pages}",
        f"result_count: {len(kept)}", "fetched: []", "---", "",
        f"# {args.name} — {now.strftime('%Y-%m-%d')}", "",
        "| job_id | title | company | location | type | age | featured | path |", "| --- | --- | --- | --- | --- | --- | --- | --- |",
        *rows, ""])
    safe_write(out, text, [SEARCHES])
    print(f"wrote {out}")
    return 0


def cmd_stage(args):
    cfg = load_uiux()
    names = {s["name"] for s in cfg.get("searches", [])}
    delay = common.pacing(cfg, "fetch_delay_seconds", 5)
    targets = []
    for a in args.paths:
        name, sep, rest = a.partition("=")
        if sep and name in names:
            search, a = name, rest
        elif args.search:
            search = args.search
        else:
            raise Fail(f"no search for '{a}': pass --search <name> or write <search>=<path>")
        m = JOB_PATH.match(a)
        if not m:
            raise Fail(f"not a /job/<id>-<slug> path or board URL: {a}")
        targets.append((search, m.group(2), m.group(1)))
    for search in {s for s, _, _ in targets}:
        find_search(cfg, search)
    missing_in_a_row = 0
    for search, job_id, path in targets:
        dest = INBOX / f"{job_id}.md"
        if dest.exists():
            print(f"{job_id} | - | - | skipped: already staged")
            continue
        url = BASE + path
        status, page, fetched_at = get(url, delay, "job")
        if status == 404:
            missing_in_a_row = 0
            print(f"{job_id} | - | - | skipped: not found")
            continue
        j = parse_job(page)
        f = j["fields"]
        label = f"{job_id} | {f.get('company') or '-'} | {f.get('title') or '-'}"
        if j["filled"]:
            missing_in_a_row = 0
            print(f"{label} | skipped: filled")
            continue
        if j["verdict"] != "ok":
            reason = j["verdict"].removeprefix("refuse: ")
            print(f"{label} | skipped: {reason}")
            missing_in_a_row += 1
            if missing_in_a_row >= 2:
                raise Stop("two job pages in a row lacked markers: layout may have changed")
            continue
        missing_in_a_row = 0
        n = word_count(j["body"])
        if args.write:
            safe_write(dest, build_note(job_id, url, f, fetched_at, j["body"], search), [INBOX])
            print(f"{label} | staged ({n} words)")
        else:
            print(f"{label} | would stage ({n} words)")
    return 0


def snippet(words):
    return " ".join(words[:6]), " ".join(words[-6:])


def cmd_check(args):
    bad = False
    for fp in args.files:
        page = Path(fp).read_text(encoding="utf-8", errors="replace")
        print(f"== {fp}")
        if job_header(page) or DESC_OPEN.search(page) or "Share this job" in page:
            j = parse_job(page)
            for k, v in j["markers"].items():
                print(f"  {k}: {'yes' if v else 'NO'}")
            print(f"  filled notice: {'yes' if j['filled'] else 'no'}")
            for k, v in j["fields"].items():
                print(f"  {k}: {v!r}")
            if j["body"]:
                words = re.sub(r"(?m)^( *)- ", r"\1", j["body"]).split()
                first, last = snippet(words)
                print(f"  body: {len(words)} words, {len(j['body'])} chars")
                print(f"  first six: {first}")
                print(f"  last six: {last}")
            print(f"  verdict: {j['verdict']}")
            bad |= j["verdict"] != "ok"
        elif is_list(page):
            cards = parse_cards(page)
            feat = [i + 1 for i, c in enumerate(cards) if c["featured"]]
            print(f"  list page: {len(cards)} cards, {len(feat)} featured at {feat}, {sum(c['expired'] for c in cards)} expired, next page: {'yes' if has_next(page) else 'no'}")
            for c in cards[:3]:
                print("  " + " | ".join([c["id"], c["company"], c["title"], c["type"], c["location"], c["age"] or "Featured"]))
            bad |= not cards
            print(f"  verdict: {'ok' if cards else 'refuse: zero cards'}")
        else:
            print("  verdict: refuse: neither a job page nor a list page")
            bad = True
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="walk a list page and print/record the kept cards")
    s.add_argument("name")
    s.add_argument("--write", action="store_true", help="save the search record (default: dry run)")
    g = sub.add_parser("stage", help="fetch job pages and stage them in the inbox")
    g.add_argument("--search", help="source_search for bare paths; omit when every path is written <search>=<path>")
    g.add_argument("--write", action="store_true", help="write inbox notes (default: dry run)")
    g.add_argument("paths", nargs="+", metavar="[search=]path-or-url")
    c = sub.add_parser("check", help="offline: run the parser on saved pages")
    c.add_argument("files", nargs="+")
    args = ap.parse_args()
    return common.run({"search": cmd_search, "stage": cmd_stage, "check": cmd_check}, args)


if __name__ == "__main__":
    sys.exit(main())
