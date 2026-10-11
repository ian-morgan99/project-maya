#!/bin/sh
# Waits until the Strata server on 8080 has been dormant (no new lines in its log) for DORMANT seconds,
# then stops Strata and starts Project Maya (GLM-5.3-Flash) on 8080.
# Usage: wait-dormant-then-swap.sh [dormant_seconds]   (default 120)
#
# The desktop shortcuts are the manual version of this: Start Maya / Stop Maya (~/.local/bin/maya-start,
# maya-stop).  This is the unattended version - leave it running before bed and Maya takes over once Strata
# has gone quiet.
LOG="/home/ian/Documents/VSCodeProjects/Strata/Strata/strata-ud-q4_k_xl.log"
MAYA_DIR="/home/ian/Documents/VSCodeProjects/Maya/project-maya"
MAYA_LOG="/tmp/maya-start-after-dormant.log"

# The installed model's run script, taken from the most recently used config rather than named: a hardcoded
# run-maya-<model>.sh goes stale the moment the model is re-set-up under a new name (it pointed at the
# disabled zai-org GGUF config for a while).  Same rule as maya.py's configs(): newest maya-*.json wins, and
# configs moved to configs-disabled/ are not installed.
CFG=$(ls -t "$MAYA_DIR"/maya-*.json 2>/dev/null | head -1)
[ -n "$CFG" ] || { echo "$(date -Is) no maya-*.json in $MAYA_DIR - run ./maya.sh --setup first"; exit 1; }
RUN_SCRIPT="$MAYA_DIR/run-$(basename "$CFG" .json).sh"
[ -x "$RUN_SCRIPT" ] || { echo "$(date -Is) $RUN_SCRIPT is missing or not executable"; exit 1; }
echo "$(date -Is) swapping to $(basename "$RUN_SCRIPT") (config $(basename "$CFG"))"
DORMANT="${1:-120}"
POLL=5

echo "$(date -Is) watcher started: waiting for $LOG to be idle for ${DORMANT}s"
while :; do
  [ -f "$LOG" ] || { echo "$(date -Is) strata log missing - assuming strata already stopped"; break; }
  now=$(date +%s); m=$(stat -c %Y "$LOG"); idle=$((now - m))
  if [ "$idle" -ge "$DORMANT" ]; then
    echo "$(date -Is) strata dormant for ${idle}s >= ${DORMANT}s - swapping"
    break
  fi
  sleep "$POLL"
done

# stop Strata and wait for 8080 to be released
pkill -f 'Strata/Strata/serve/server.py' && echo "$(date -Is) strata stopped" || echo "$(date -Is) strata was not running"
i=0
while ss -tln 2>/dev/null | grep -q ':8080 '; do
  i=$((i + 1)); [ "$i" -gt 30 ] && { echo "$(date -Is) 8080 still held after 30s, giving up"; exit 1; }
  sleep 1
done
echo "$(date -Is) port 8080 free"

# start Maya
cd "$MAYA_DIR" || exit 1
nohup "$RUN_SCRIPT" > "$MAYA_LOG" 2>&1 &
echo "$(date -Is) maya started (pid $!), engine log: $MAYA_LOG"
