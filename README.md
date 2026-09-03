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

## Glossary — exact usage rules (pin this down when tagging)

**Mental model:** `category` = the noun · `status` = the tense · `verdict` = the verdict · `rationale` = the reason · `route` = where to read more.

### category — what kind of thing is it? (the physical type, NEVER the report's section letter)
- **`tool`** — a library/utility you embed as a building block (Docling, MinerU, Whisper, Crawl4AI, LightRAG)
- **`project`** — a standalone open-source app/framework you'd clone and run (DeepTutor, OpenMontage, TradingAgents, Sequoia-X)
- **`agent-skill`** — a reusable agent skill (reverse-skill, feishu-bitable, finance-markets-research)
- **`mcp`** — an MCP server (alphavantage-mcp-server, dbhub, email-mcp)
- **`concept`** — an idea/framework/architecture, not code (tencentdb-agent-memory)

**tool vs project:** `tool` = building block you embed in your own stack; `project` = a thing you'd stand up and run on its own. When genuinely unsure, use `project` (safer default for software you found).
**Hard rule:** do NOT use the report's internal category letter (a=investment, b=education, c=productivity, d=infra, e=fun) as the registry `category`. Those letters organize a report body; they are not physical types.

### status — where is it in the lifecycle?
- **`seen`** — surfaced by a cron, logged to avoid re-discovery, NOT yet triaged. (The "inbox" state.)
- **`researching`** — actively being evaluated (by us or Flora).
- **`concluded`** — decision made; must have a real `verdict` + `rationale`.

**seen → concluded:** promote only when there's a genuine verdict + rationale. `seen`/`pending` means "logged, judge later."

### verdict — what did we conclude? (decision vocabulary, shared with Flora's queue)
- **`adopt`** — yes, using it
- **`trial`** — worth a real test-drive
- **`watch`** — interesting; keep an eye on, no action now
- **`reject`** — looked, decided no
- **`pending`** — not yet decided (pairs with `status: seen`)
- **`done`** — evaluated and complete (no further state)
- **`duplicate`** — same entity re-surfaced; set this and point `route`/note at the canonical slug (prefer NOT adding a dup row if `check` already finds it)

**adopt/trial/watch/reject/done** are terminal conclusions → must carry a `rationale`. **pending** = logged but judge later.

### route + route_link — where did it go next? (passive pointer, not a driver)
- `route` — human pointer, e.g. `→ adopted (smoke-pipeline)`, `→ wiki-agentic-stack deep-dive page`, `→ weekly digest`, `pending triage`
- `route_link` — actual URL/path to the wiki page, Flora report, or Drive link

### rationale — the short "why"
1–2 lines, always present on `concluded` rows. The full analysis lives one hop away via `route_link`.

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
