#!/usr/bin/env bash
# tools/maya-verify.sh - prove a running Maya answers, and how fast.
#
# Start Maya first (the desktop icon "Start Maya (choose model)", or
# maya-select-model glm / deepseek), then run this.  It waits for the server to
# be ready, sends one real chat request, and prints the answer with its speed.
# Nothing is installed and nothing is stopped: it only talks HTTP to the port.
#
# Usage:  maya-verify.sh                (finds the running Maya itself)
#         maya-verify.sh 8090           (that port)
#         maya-verify.sh 8080 "your prompt"
#         MAYA_WAIT=1200 maya-verify.sh (a cold GLM load takes minutes: longer wait)
set -u

PROMPT="${2:-Reply with exactly two words: hello from Maya}"
WAIT="${MAYA_WAIT:-900}"          # seconds to wait for the model to load

# the server on a port is this Maya's own serve/server.py (Strata answers /health
# and /v1/models too, so an HTTP reply alone does not tell them apart)
port_is_maya() {
  local p=$1 pid
  pid=$(ss -ltnp 2>/dev/null | grep ":$p " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
  [ -n "$pid" ] || return 1
  tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'project-maya/serve/[s]erver.py'
}

port_holder() {   # what the port's process is, for the messages
  local p=$1 pid
  pid=$(ss -ltnp 2>/dev/null | grep ":$p " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
  [ -n "$pid" ] || { echo "nothing"; return; }
  if tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'project-maya/serve/[s]erver.py'; then
    echo "maya"
  elif tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q 'Strata'; then
    echo "strata"
  else
    echo "other"
  fi
}

PORT="${1:-}"
if [ -z "$PORT" ]; then
  for p in 8080 8090; do
    if port_is_maya "$p"; then PORT=$p; break; fi
  done
fi
if [ -z "$PORT" ]; then
  echo "No Maya answering on 8080 or 8090."
  for p in 8080 8090; do
    ss -tln 2>/dev/null | grep -q ":$p " || continue
    case "$(port_holder "$p")" in
      strata) echo "  :$p is Strata - stop it first (Maya and Strata never run at once)." ;;
      other)  echo "  :$p is held by something else:"; ss -ltnp 2>/dev/null | grep ":$p " | sed 's/^/    /' ;;
    esac
  done
  echo "Start Maya with the desktop icon, or:  maya-select-model glm"
  exit 1
fi

echo "== port $PORT: waiting for the model to load (up to ${WAIT}s) =="
MODEL=""
for _ in $(seq 1 "$WAIT"); do
  MODEL=$(curl -fsS -m 5 "http://127.0.0.1:$PORT/v1/models" 2>/dev/null |
          sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  [ -n "$MODEL" ] && break
  sleep 1
done
[ -n "$MODEL" ] || { echo "timed out: the model never came up.  Engine log:"; ls -t /home/ian/Documents/VSCodeProjects/Maya/project-maya/*.log 2>/dev/null | head -1 | xargs -r tail -20; exit 1; }
echo "   loaded: $MODEL"

echo "== one chat request =="
T0=$(date +%s.%N)
RESP=$(curl -fsS -m 900 "http://127.0.0.1:$PORT/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\": \"$MODEL\", \"max_tokens\": 512, \"temperature\": 0.2,
       \"messages\": [{\"role\": \"user\", \"content\": $(printf '%s' "$PROMPT" | .venv/bin/python -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '"hello"')}]}") \
  || { echo "the request failed"; exit 1; }
T1=$(date +%s.%N)

.venv/bin/python - "$RESP" "$T0" "$T1" <<'EOF'
import json, sys
r = json.loads(sys.argv[1])
t0, t1 = float(sys.argv[2]), float(sys.argv[3])
m = r["choices"][0]["message"]
ans = (m.get("content") or "").strip()
think = (m.get("reasoning_content") or m.get("reasoning") or "").strip()
u = r.get("usage") or {}
n = u.get("completion_tokens") or 0
dt = max(t1 - t0, 1e-6)
if think:
    print(f"   thinking: {think[:200]}{'...' if len(think) > 200 else ''}")
print(f"   answer:   {ans[:400] or '(empty)'}")
print(f"   tokens:   {n} completion / {u.get('prompt_tokens', '?')} prompt")
print(f"   wall:     {dt:.1f}s" + (f"  ({n / dt:.1f} tok/s)" if n else ""))
print("\nVERDICT:", "PASS - the model answered" if ans or think else "FAIL - empty answer, check the engine log")
EOF
