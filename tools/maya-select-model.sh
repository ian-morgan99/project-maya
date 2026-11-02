#!/bin/sh
# The desktop launcher's model picker: list the models this Maya has installed,
# pick one, start it.  The installed models are the run configs maya.py's setup
# wrote beside it (maya-<model>.json); what each one is comes from serve/models.py
# - the same listing the dashboard's Models page shows - so a model added later
# with ./maya.sh --setup appears here without this script changing.
#
# Usage:  maya-select-model.sh            (a menu, the most recently used first)
#         maya-select-model.sh <name>     (start it directly: the config's file,
#                                          its stem without maya-/json, or its
#                                          family - glm, deepseek, minimax, qwen)
#         maya-select-model.sh --list     (print what is installed, one per line)
#
# MAYA_PORT starts the chosen model on that port instead of its config's own.
# Maya and Strata share 8080 and are never run at once: a port already held is
# reported with what holds it, and nothing starts.
set -u

# the Maya folder: this script's own directory when it lives in the repo's tools/,
# the installed copy names it through MAYA_DIR, and the one this PC's setup uses
# as the last resort.
HERE=$(cd "$(dirname "$0")" && pwd)
if [ -f "$HERE/../maya.py" ]; then
  ROOT=$(cd "$HERE/.." && pwd)
elif [ -n "${MAYA_DIR:-}" ] && [ -f "$MAYA_DIR/maya.py" ]; then
  ROOT="$MAYA_DIR"
elif [ -f "/home/ian/Documents/VSCodeProjects/Maya/project-maya/maya.py" ]; then
  ROOT="/home/ian/Documents/VSCodeProjects/Maya/project-maya"
else
  echo "Project Maya not found: set MAYA_DIR to its folder."
  exit 1
fi
cd "$ROOT" || exit 1

PY=""
for c in .venv/bin/python python3; do
  if command -v $c >/dev/null 2>&1 && $c -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY=$c; break
  fi
done
[ -n "$PY" ] || { echo "Python 3.10+ not found (.venv/bin/python or python3)."; exit 1; }

# one line per installed config: file|family|quant|port|context|ok|missing
list_models() {
  MAYA_ROOT="$ROOT" $PY - <<'EOF'
import os
import sys
from pathlib import Path
root = Path(os.environ["MAYA_ROOT"])
sys.path.insert(0, str(root / "serve"))
import models as M
for p in sorted((q for q in root.glob("maya-*.json")
                 if not q.name.endswith(".shared-settings.json")),
                key=lambda q: q.stat().st_mtime, reverse=True):
    d = M.describe(p, None)
    ctx = (d.get("settings") or {}).get("context") or ""
    print("|".join(str(x) for x in (d["file"], d["family"], d["quant"],
                                    d.get("port"), ctx,
                                    "ok" if d["ok"] else "broken",
                                    d.get("missing") or "")))
EOF
}

if [ "${1:-}" = "--list" ]; then list_models; exit $?; fi

ROWS=$(list_models) || { echo "could not read the installed models."; exit 1; }
[ -n "$ROWS" ] || { echo "no models installed yet: run ./maya.sh --setup"; exit 1; }

# the chosen row: by menu number, config file, its stem, or its family
pick_row() {
  q="$1"
  case "$q" in
    *[!0-9]*) ;;                                   # not a number: match by name
    *) echo "$ROWS" | awk -F'|' -v n="$q" 'NR == n { print; exit }'; return ;;
  esac
  echo "$ROWS" | awk -F'|' -v q="$q" '
    $2 == q || $1 == q || $1 == "maya-" q ".json" || $1 == q ".json" { print; exit }'
}

if [ $# -gt 0 ]; then
  ROW=$(pick_row "$1")
  [ -n "$ROW" ] || { echo "no installed model matches '$1'.  Installed:"; echo "$ROWS" | cut -d'|' -f1; exit 1; }
else
  ARGS=""
  i=0
  while IFS='|' read -r file fam quant port ctx ok missing; do
    i=$((i + 1))
    desc="$fam · $quant"
    [ -n "$port" ] && desc="$desc  (port $port)"
    [ -n "$ctx" ] && desc="$desc, $ctx context"
    [ "$ok" != "ok" ] && desc="$desc  [missing: $missing]"
    ARGS="$ARGS $i $desc"
  done <<EOF
$ROWS
EOF
  if command -v whiptail >/dev/null 2>&1; then
    N=$(echo "$ROWS" | wc -l)
    CHOICE=$(whiptail --title "Project Maya - which model?" \
      --menu "The models installed here (the most recently used first):" \
      $(( N > 8 ? 10 + N : 18 )) 78 8 $ARGS 3>&1 1>&2 2>&3) || exit 0
  else
    echo "Installed models:"
    echo "$ROWS" | cut -d'|' -f1-5 | nl
    printf "Which one? [1] "; read -r CHOICE
    CHOICE=${CHOICE:-1}
  fi
  ROW=$(echo "$ROWS" | awk -F'|' -v n="$CHOICE" 'NR == n { print; exit }')
  [ -n "$ROW" ] || { echo "'$CHOICE' is not one of them."; exit 1; }
fi

FILE=$(echo "$ROW" | cut -d'|' -f1)
PORT=$(echo "$ROW" | cut -d'|' -f4)
[ -n "${MAYA_PORT:-}" ] && PORT="$MAYA_PORT"

if [ -n "$PORT" ] && ss -tln 2>/dev/null | grep -q ":$PORT "; then
  echo "Port $PORT is already in use:"
  ss -ltnp 2>/dev/null | grep ":$PORT " | sed 's/^/  /'
  echo
  if pgrep -f 'Strata/Strata/serve/[s]erver.py' >/dev/null 2>&1; then
    echo "That is Strata.  Maya and Strata share the port and are never both running:"
    echo "stop Strata first, then start Maya again."
  elif pgrep -f 'project-maya/serve/[s]erver.py' >/dev/null 2>&1; then
    echo "That is Maya, already running: http://127.0.0.1:$PORT/"
  else
    echo "Something else holds the port.  Stop it, or pick another:"
    echo "  MAYA_PORT=8081 $0 $*"
  fi
  echo
  read -r -p "Press Enter to close. " _
  exit 1
fi

echo "Starting $FILE ..."
if [ -n "$PORT" ]; then
  exec ./maya.sh --config "$ROOT/$FILE" --port "$PORT" "$@"
fi
exec ./maya.sh --config "$ROOT/$FILE" "$@"
