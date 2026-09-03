# research-registry

**Central decision log + dedupe registry** for every project / agent-skill / MCP
that our discovery crons surface. One entity per row, with the initial verdict
and *why*, plus a pointer to where it went next.

Solves two recurring problems:
1. **Repetition filter** — crons programmatically `check()` before researching,
   so we stop re-researching the same thing across jobs.
2. **Central oversight** — one queryable place to see what's been looked at and
   what we concluded.

## Stack & role

- This is a **registry (decision log)**, NOT a knowledge base.
- The **wiki-agentic-stack** remains the deep-dive layer; registry rows *point*
  into it via `route`.
- **Flora's smoke-test pipeline** keeps its own queue; the registry only records
  `route: "→ flora-queue"` when we kick something that way. Passive log, not a
  driver (extensible later if we want it to trigger steps).

## Layout

```
research-registry/
├── registry.jsonl    # canonical records (append-only-ish; upsert merges)
├── registry.py       # single shared helper (all crons call this)
├── TEMPLATE.md       # for manual adds / metadata reference
├── README.md
└── archive/          # (future: rename / retire handling)
```

## Record schema (one JSON per line in registry.jsonl)

| field | type | notes |
|-------|------|-------|
| `slug` | str | canonical id, lowercased (e.g. `graphify`) **required** |
| `name` | str | display name (optional, defaults to slug) |
| `aliases` | list[str] | alt names for matching (rebrand, casing) |
| `category` | str | `project` \| `agent-skill` \| `mcp` \| `tool` \| `paper` ... |
| `url` / `repo_url` | str | homepage / github-or-gitee repo |
| `first_seen` | str | YYYY-MM-DD |
| `last_seen` | str | YYYY-MM-DD (bumped on re-report) |
| `sources` | list[str] | which cron/flow surfaced it (e.g. `weekly-ai-projects`) |
| `status` | str | `seen` → `researching` → `concluded` |
| `verdict` | str | `adopt` \| `trial` \| `watch` \| `reject` \| `pending` \| `duplicate` |
| `rationale` | str | **short "why"** — the reasoning for the verdict (1–2 lines) |
| `route` | str | passive pointer: where it went (`→ flora-queue 2026-08-16`, `→ wiki page X`) |
| `route_link` | str | optional URL/path to the deep-dive destination |
| `notes` | list[str] | optional free-form thread (future decisions) |

**`rationale` lives on the row** (scanable in `show`); the *full* analysis lives in
the destination `route_link` points to. Keep registry rows lean — one JSON line.

## Controlled vocabulary (shared with Flora queue + wiki)

- **status**: `seen → researching → concluded`
- **verdict**: `adopt | trial | watch | reject | pending | duplicate`
  - `duplicate` rows: keep the canonical record; set the dup's `verdict=duplicate`
    and point `route`/note at the canonical slug. Prefer *not* adding a dup at all
    if `check()` already finds it.
- `route` may be blank if nothing acted on it yet.

## How crons use this (the payoff)

Each discovery cron prompt shrinks to:
1. Build candidate list (as today).
2. For each candidate → `registry.py check "<name-or-url>"`:
   - **FOUND** → drop / mark duplicate. This is the repetition filter.
   - **ABSENT** → research it.
3. Research survivors.
4. For each → `registry.py upsert '{json}'` with `status`, `verdict`, `rationale`, `route`.
5. `git add registry.jsonl && git commit && git push` (remote is source of truth).

**Never re-implement matching in a cron prompt** — always call `registry.py`.
Matching lives in exactly one place so all jobs dedupe identically.

## CLI reference

```
registry.py init                       # create empty registry.jsonl
registry.py check "graphify"           # FOUND <record> | ABSENT   (exit 0/1)
registry.py upsert '{...json...}'      # ADDED | UPDATED <slug>
registry.py show --category mcp --verdict watch --status concluded
registry.py summary                    # counts by status / verdict / category
```

`check` matches against `slug`, `aliases`, `url`, and `repo_url` (normalized:
case-insensitive, strips scheme/www/.git/trailing slash).

## Updating the registry

- Cron auto-upserts programmatically.
- Manual: edit the repo, `registry.py upsert '{...}'` or directly add a line,
  then commit + push.
- **Remote is the source of truth** — pull before editing cron-touching files;
  rebase if the remote moved (multiple crons may write).
