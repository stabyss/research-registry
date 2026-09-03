#!/usr/bin/env bash
# registry-gate.sh — thin wrapper so cron prompts can dedupe + record in ONE easy step.
#
# Guarantees the local checkout is fresh (git pull) then runs registry.py.
# All discovery crons should use THIS, never call registry.py directly, so the
# remote stays the source of truth (per operating rules) and matching is unified.
#
# Usage:
#   registry-gate.sh pull          # sync local repo to origin (call first)
#   registry-gate.sh check "NAME"  # exit 0=FOUND(already known) 1=ABSENT(new)
#   registry-gate.sh upsert '{json...}'
#   registry-gate.sh show [--category X --status Y --verdict Z]
#   registry-gate.sh summary
#
# The wrapper always pulls before check/upsert so a cron never writes stale
# over a job that ran moments ago in another isolated session.
set -u
REG_DIR="${REGISTRY_DIR:-/home/node/.openclaw/workspace/research-registry}"
REGISTRY_PY="$REG_DIR/registry.py"

# Optional: push after a write (upsert) so remote stays in sync automatically.
AUTO_PUSH="${REGISTRY_AUTO_PUSH:-1}"

cmd="${1:-}"
if [ -z "$cmd" ]; then
  echo "usage: registry-gate.sh pull|check|upsert|show|summary"
  exit 2
fi

# Always try to be fresh against origin before any op.
if [ -d "$REG_DIR/.git" ]; then
  git -C "$REG_DIR" pull --ff-only -q origin main >/dev/null 2>&1 || \
    echo "[registry-gate] warning: git pull failed (network?) — continuing with local state" >&2
fi

case "$cmd" in
  pull)
    # already pulled above; report state
    git -C "$REG_DIR" rev-parse --short HEAD 2>/dev/null || echo "?"
    ;;
  check)
    shift
    python3 "$REGISTRY_PY" check "${1:-}"
    ;;
  upsert)
    shift
    rc=0
    python3 "$REGISTRY_PY" upsert "${1:-}"
    rc=$?
    if [ "$AUTO_PUSH" = "1" ] && [ $rc -eq 0 ]; then
      ( cd "$REG_DIR" && git add registry.jsonl && \
        git commit -q -m "[cron] registry upsert $(date +%Y-%m-%d)" && \
        GIT_TERMINAL_PROMPT=0 git push -q origin main ) 2>/dev/null
    fi
    exit $rc
    ;;
  show) shift; python3 "$REGISTRY_PY" show "$@";;
  summary) python3 "$REGISTRY_PY" summary;;
  *)
    echo "unknown cmd: $cmd"
    exit 2;;
esac
