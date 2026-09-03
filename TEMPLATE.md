# Registry metadata reference

Template for a single entity record (one JSON object; add one per line in
`registry.jsonl`, or use `registry.py upsert '{...}'` so merging is handled).

## Minimal (slug required)

```json
{
  "slug": "graphify",
  "name": "Graphify",
  "aliases": ["calesthio/Graphify"],
  "category": "tool",
  "url": "https://github.com/calesthio/Graphify",
  "repo_url": "https://github.com/calesthio/Graphify",
  "first_seen": "2026-08-03",
  "last_seen": "2026-08-03",
  "sources": ["weekly-ai-projects"],
  "status": "concluded",
  "verdict": "reject",
  "rationale": "Graph-based local knowledge graph; strong stars but our LlamaIndex path already covers local KG — no gap.",
  "route": "→ discarded vs LlamaIndex (no smoke test)",
  "route_link": ""
}
```

## Conventions

- **slug**: lowercase, no spaces — the canonical key. Use project name if
  sensible; aliases catch the rest.
- **category**: `project` | `agent-skill` | `mcp` | `tool` | `paper` | `other`.
- **status**: `seen` → `researching` → `concluded`.
- **verdict**: `adopt` | `trial` | `watch` | `reject` | `pending` | `duplicate`.
- **rationale**: short 1–2 line *why*. Written as if to a busy future you.
  Example reject: *"no gap — covered by X"*; trial: *"promising for Y, needs key"*;
  adopt: *"fits our Karpathy v1 wiki pattern, adopting."*
- **route**: passive pointer only. Keep the registry out of driving downstream
  tools; just record where it went (`→ flora-queue`, `→ wiki page`, `→ installed`).

## Full example (watched → later concluded)

```json
{
  "slug": "openmontage",
  "name": "OpenMontage",
  "aliases": ["calesthio/OpenMontage", "OpenMontage agentic video"],
  "category": "project",
  "url": "https://github.com/calesthio/OpenMontage",
  "repo_url": "https://github.com/calesthio/OpenMontage",
  "first_seen": "2026-07-07",
  "last_seen": "2026-09-02",
  "sources": ["weekly-ai-projects", "manual"],
  "status": "concluded",
  "verdict": "watch",
  "rationale": "Agentic video production framework (52 tools, HyperFrames-native). Rich but heavy; watch until a concrete TNE-marketing need lands.",
  "route": "→ wiki-agentic-stack deep-dive page (evaluating, not installed)",
  "route_link": "../wiki-agentic-stack/wiki/tools/openmontage.md",
  "notes": []
}
```
