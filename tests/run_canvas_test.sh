#!/usr/bin/env bash
# End-to-end test of the Canvas sync against a fake Canvas (tests/mock_canvas.py). No school account needed.
# Usage: bash tests/run_canvas_test.sh        Prints PASS at the end, or stops at the first failure.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"; T="$(mktemp -d)"; V="$T/vault"; PORT=8765
export CANVAS_SYNC_CONFIG="$T/config.json"
S="$V/13 Calendar/System/canvas-sync"
serve() { pkill -f "mock_canvas.py --port $PORT" 2>/dev/null || true; python3 "$REPO/tests/mock_canvas.py" --port $PORT --files "$REPO/tests/fixtures" --stage "$1" & sleep 1; }
trap 'pkill -f "mock_canvas.py --port $PORT" 2>/dev/null || true' EXIT
python3 "$REPO/scripts/build_vault.py" --answers "$REPO/blueprint/answers.example.json" --dest "$V" >/dev/null
serve 1
echo "test-token" | python3 "$S/canvas_api.py" login --host 127.0.0.1:$PORT --token-stdin
python3 "$S/sync.py" setup
python3 "$S/sync.py" plan >/dev/null
python3 "$S/sync.py" apply --keep-placeholders >/dev/null
python3 "$S/sync.py" finish --by test
D="$V/12 School/Fall 2026/ECON 325 - Entrepreneurship"
test -f "$D/02 Lecture Slides/Lecture 1 - Finding Opportunities.pptx"
test -f "$D/02 Lecture Slides/ECON 325 - Lecture 1 - Finding Opportunities.md"
test -f "$D/03 Readings & Cases/Case - Lemonade Stand.pdf"
test ! -f "$D/08 Other/banner.png"
grep -q "Business Model Canvas.*due::" "$V/04 Maps/ECON 325 MOC.md"
! grep -q "Attendance" "$V/04 Maps/ECON 325 MOC.md"
grep -q "Lemonade Stand" "$V/13 Calendar/Prep/ECON 325 Prep.md"
echo "ok: first sync imported files, deadlines, a lecture note and a prep task"
git -C "$V" add -A; git -C "$V" -c user.name=t -c user.email=t@t commit -qm "after first sync"
python3 "$S/sync.py" plan >/dev/null; python3 "$S/sync.py" apply >/dev/null; python3 "$S/sync.py" finish --by test >/dev/null
test "$(git -C "$V" status --short | sed 's/^...//')" = '"13 Calendar/System/canvas-sync/state.json"'
echo "ok: a sync with no Canvas changes edits only state.json"
B="$(grep "Business Model Canvas" "$V/04 Maps/ECON 325 MOC.md")"
serve 2
python3 "$S/sync.py" plan >/dev/null; python3 "$S/sync.py" apply --keep-placeholders >/dev/null; python3 "$S/sync.py" finish --by test >/dev/null
test "$B" != "$(grep "Business Model Canvas" "$V/04 Maps/ECON 325 MOC.md")"
grep -q "Canvas moved it" "$V/04 Maps/ECON 325 MOC.md"
test -f "$D/02 Lecture Slides/Lecture 2 - Customer Discovery.pptx"
echo "ok: a moved due date and a new deck came through"
python3 "$REPO/scripts/verify_vault.py" "$V" | tail -1 | grep -q PASS
! grep -rq "test-token" "$V"
echo "ok: vault still verifies and holds no token"
echo PASS
