#!/usr/bin/env python3
"""
research-registry — the single shared helper for project/skill/MCP discovery dedupe.

Registry is a JSONL file (registry.jsonl), one entity per line. All discovery
cron jobs call THIS script to check (dedupe) and upsert (record) so matching
logic lives in one place and does not drift across prompts.

Vocabulary (shared with Flora queue + wiki-agentic-stack):
  status : seen | researching | concluded
  verdict: adopt | trial | watch | reject | pending | duplicate
    - duplicate records carry the canonical slug in verdict value or note.
  route  : passive pointer to where the entity went next (flora-queue, wiki
           page, installed). The registry does NOT drive those destinations.

Commands:
  check "<name-or-url>"   Dedupe filter. Prints "FOUND" + record if matched by
                          slug / alias / substring of url, else "ABSENT".
                          Exit 0 if found (match), 1 if absent.
  upsert {json}           Append if new; bump last_seen + merge given fields if
                          an existing record matches.
  show [--category C] [--status S] [--verdict V] [--limit N]
                          Central oversight listing. Filters optional.
  summary                 Counts by status and verdict.
  init                    Create an empty registry.jsonl.
"""
import json
import re
import sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent / "registry.jsonl"

# Fields that a bare check should match against (normalized)
MATCH_FIELDS = ["slug", "aliases", "url", "repo_url"]

# Controlled vocab — validated on upsert but warnings only (registry stays permissive)
STATUSES = {"seen", "researching", "concluded"}
VERDICTS = {"adopt", "trial", "watch", "reject", "pending", "duplicate"}


def _norm(s: str) -> str:
    """Lowercase, strip scheme/www/git suffix + trailing slashes + .git, collapse whitespace."""
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    s = re.sub(r"\.git$", "", s)
    s = s.rstrip("/")
    s = re.sub(r"\s+", "", s)  # aliases often have spaces/casing issues
    return s


def _norm_repo_url(s: str) -> str:
    """repo_url → owner/repo tail form for substring matching."""
    n = _norm(s)
    n = re.sub(r"^github\.com/", "", n)
    n = re.sub(r"^gitee\.com/", "", n)
    n = re.sub(r"^gitlab", "", n)
    return n


def _load() -> list[dict]:
    if not REGISTRY.exists():
        return []
    out = []
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # skip corrupt/partial lines but keep going
                continue
    return out


def _save(records: list[dict]) -> None:
    REGISTRY.write_text(
        "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records),
        encoding="utf-8",
    )


def _match(record: dict, query: str) -> bool:
    q = _norm(query)
    qurl = _norm_repo_url(query)
    # exact slug/alias match
    for key in ("slug", "aliases"):
        vals = record.get(key)
        if isinstance(vals, str):
            vals = [vals]
        if vals:
            for v in vals:
                if q and _norm(str(v)) == q:
                    return True
    # url / repo_url substring match (tolerant of trailing forms)
    for key in ("url", "repo_url"):
        v = record.get(key)
        if v and qurl:
            if qurl in _norm_repo_url(str(v)) or _norm_repo_url(str(v)) in qurl:
                return True
    # fallback: query substring of slug (catches partial naming)
    return bool(q) and q in _norm(record.get("slug", ""))


def cmd_check(query: str) -> int:
    if not query:
        print("usage: registry.py check '<name-or-url>'")
        return 2
    for rec in _load():
        if _match(rec, query):
            print("FOUND")
            print(json.dumps(rec, ensure_ascii=False, sort_keys=True))
            return 0
    print("ABSENT")
    return 1


def cmd_upsert(payload_json: str) -> int:
    try:
        new = json.loads(payload_json)
    except json.JSONDecodeError as e:
        print(f"invalid json: {e}")
        return 2
    if not new.get("slug"):
        print("error: upsert requires a 'slug' field")
        return 2

    records = _load()
    now = new.get("last_seen") or new.get("first_seen")
    # if a match exists, merge (bump last_seen, overwrite provided fields)
    for i, rec in enumerate(records):
        if _match(rec, new["slug"]):
            merged = dict(rec)
            merged.update(new)
            merged["last_seen"] = max(
                str(now or ""), str(rec.get("last_seen") or "")
            ) if now and rec.get("last_seen") else (now or rec.get("last_seen"))
            records[i] = merged
            _save(records)
            print("UPDATED", merged["slug"])
            return 0
    # no match → append
    records.append(new)
    _save(records)
    print("ADDED", new["slug"])
    return 0


def cmd_show(category=None, status=None, verdict=None, limit=0):
    recs = _load()
    if category:
        recs = [r for r in recs if r.get("category") == category]
    if status:
        recs = [r for r in recs if r.get("status") == status]
    if verdict:
        recs = [r for r in recs if r.get("verdict") == verdict]
    recs.sort(key=lambda r: r.get("last_seen", ""), reverse=True)
    if limit:
        recs = recs[: int(limit)]
    if not recs:
        print("(none)")
        return 0
    for r in recs:
        slug = r.get("slug", "?")
        name = r.get("name", slug)
        cat = r.get("category", "-")
        st = r.get("status", "-")
        vd = r.get("verdict", "-")
        ls = r.get("last_seen", r.get("first_seen", "-"))
        print(f"{ls}  [{cat}]  {name}  | status={st} verdict={vd}")
        if r.get("rationale"):
            print(f"      why: {r['rationale']}")
        if r.get("route"):
            print(f"      -> {r['route']}")
    return 0


def cmd_summary():
    recs = _load()
    if not recs:
        print("empty registry")
        return 0
    from collections import Counter
    print(f"total entities: {len(recs)}")
    print("by status:", dict(Counter(r.get("status", "-") for r in recs)))
    print("by verdict:", dict(Counter(r.get("verdict", "-") for r in recs)))
    print("by category:", dict(Counter(r.get("category", "-") for r in recs)))
    return 0


def cmd_init():
    if REGISTRY.exists():
        print("registry.jsonl already exists")
        return 0
    REGISTRY.touch()
    print("created", REGISTRY)
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    cmd = args[0]
    if cmd == "check":
        return cmd_check(args[1] if len(args) > 1 else "")
    if cmd == "upsert":
        return cmd_upsert(args[1] if len(args) > 1 else "")
    if cmd == "show":
        return cmd_show(
            category=_arg(args, "--category"),
            status=_arg(args, "--status"),
            verdict=_arg(args, "--verdict"),
            limit=_arg(args, "--limit"),
        )
    if cmd == "summary":
        return cmd_summary()
    if cmd == "init":
        return cmd_init()
    print(__doc__)
    return 2


def _arg(args, flag):
    try:
        i = args.index(flag)
        return args[i + 1]
    except (ValueError, IndexError):
        return None


if __name__ == "__main__":
    sys.exit(main())
