"""What the five source scripts share: exit codes, YAML quoting, guarded writes, config lookups and API keys.

Each source script (linkedin_fetch, jobgether_fetch, uiux_board, fantastic_fetch, theirstack_fetch) raises Stop for a
hard rule (the run ends, exit 1, no retry) and Fail for bad input or config (exit 2), reads its `sources: <source>:`
block of the profile's criteria file through source_cfg, which enforces the opt-in (D17, D35), and writes only under logs/ through
safe_write. Pacing, parsing and the hard stops themselves stay in each script. A library, not a command.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/scripts: `naming` and the sibling packages
import naming  # noqa: E402
from naming import q  # noqa: E402,F401  (re-exported: every source quotes YAML scalars with it)

LABELS = {"linkedin": "LinkedIn", "jobgether": "Jobgether", "indeed": "Indeed", "uiux": "UI/UX Jobs Board",
          "fantastic": "Fantastic.jobs", "theirstack": "TheirStack"}


class Stop(Exception):
    """End the whole run: a hard rule, no retry (exit 1)."""


class Fail(Exception):
    """Bad input, config, or an unreadable page or response (exit 2)."""


def criteria():
    import yaml  # only the config readers need it; a script's `check` runs without
    cfg = yaml.safe_load(naming.criteria_text()) or {}
    old = legacy_keys(cfg)
    if old:
        raise Fail(f"{naming.CRITERIA.name} uses the old layout (top-level {', '.join(old)}): move each source's "
                   "settings under `sources: <source>:` (applicant/criteria/README.md, D35)")
    return cfg


def legacy_keys(cfg):
    """Top-level keys of the layout before D35: LinkedIn's blocks and every other source's block sat at the top."""
    sel = cfg.get("selection") or {}
    return [k for k in ("searches", "defaults", "incremental", *LABELS) if k in cfg] + \
        [f"selection.{k}" for k in ("fit_check", "max_fetches_per_run", "fetch_delay_seconds") if k in sel]


def enabled(cfg, source):
    """D17: a source runs only when `sources: <source>: enabled` is true. A missing entry is off, except Jobgether."""
    return block(cfg, source).get("enabled", source == "jobgether")


def block(cfg, source):
    """The source's own block, `sources: <source>:` ({} when absent): enabled, pacing, defaults, searches (D35)."""
    return (cfg.get("sources") or {}).get(source) or {}


def source_cfg(source):
    """The source's block of the criteria file, once `sources: <source>: enabled` is checked."""
    cfg = criteria()
    if not enabled(cfg, source):
        raise Fail(f"{LABELS.get(source, source)} is off: set `sources: {source}: enabled: true` in the profile's "
                   "criteria file (naming.py paths)")
    sub = block(cfg, source)
    if not sub.get("searches"):
        raise Fail(f"no `sources: {source}: searches:` in {naming.CRITERIA.name}")
    return sub


def pacing(sub, key, default):
    """A `pacing:` value of a source block: `fetch_delay_seconds` or `max_fetches_per_run`."""
    return (sub.get("pacing") or {}).get(key, default)


def find_search(cfg, name, source="a"):
    """The named search, merged over the block's `defaults:`."""
    for s in cfg.get("searches", []):
        if s["name"] == name:
            return {**cfg.get("defaults", {}), **s}
    names = ", ".join(s["name"] for s in cfg.get("searches", []))
    raise Fail(f"unknown {source} search '{name}' (have: {names})")


def api_key(var):
    """A key from the environment, else from .env, which is gitignored. Never from the repo."""
    key = os.environ.get(var)
    if not key and naming.ENV_FILE.exists():
        for line in naming.ENV_FILE.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.partition("=")
            if sep and k.strip() == var:
                key = v.strip().strip("'\"")
    if not key:
        raise Fail(f"no {var} in the environment or .env")
    return key


def safe_write(path, text, allowed):
    """Write only directly into one of the `allowed` folders (the inbox, the search records)."""
    p = Path(path).resolve()
    if not any(p.parent == Path(a).resolve() for a in allowed):
        raise Fail(f"refusing to write outside the data folders: {p}")
    p.write_text(text, encoding="utf-8")


def run(handlers, args):
    """Run the subcommand `args.cmd` and map its exceptions to exit codes: Stop prints RUN STOPPED and returns 1,
    Fail prints the error and returns 2. The source scripts end with `sys.exit(main())`."""
    try:
        return handlers[args.cmd](args)
    except Stop as e:
        print(f"RUN STOPPED: {e}", file=sys.stderr)
        return 1
    except Fail as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
