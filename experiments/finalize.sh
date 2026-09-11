#!/bin/bash
# After all passes: aggregate results, fill the spec's 實測 blocks, rebuild the three pages, validate, deploy.
# Usage: experiments/finalize.sh [--no-deploy]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(dirname "$HERE")"; cd "$ROOT"
PY=./venv/bin/python
echo "== aggregate + fill spec"; $PY experiments/fill_results.py
echo "== build pages"; $PY site/build_results.py; $PY site/build_index.py; $PY site/build_specs.py; $PY site/build_howto.py
echo "== openspec validate"; OPENSPEC_TELEMETRY=0 openspec validate --all --strict --no-interactive < /dev/null 2>&1 | cat | tail -3
[ "${1:-}" = "--no-deploy" ] && exit 0
echo "== deploy"; ./deploy/deploy.sh 2>&1 | grep -E 'Service URL|ERROR' | tail -2
for p in "" specs.html results.html; do curl -s -o /dev/null -w "  /$p %{http_code}\n" "https://doris-ha-demo-195642473078.asia-east1.run.app/$p"; done
