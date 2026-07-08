#!/usr/bin/env bash
# Collect a runtime behavior trace for ONE Python file, for dynamic analysis.
#
# ############################################################################
# # DO NOT RUN THIS ON YOUR PRIMARY MACHINE, THIS PROJECT'S DEV ENVIRONMENT, #
# # OR ANY MACHINE WITH ACCESS TO CREDENTIALS/DATA YOU CARE ABOUT.          #
# #                                                                          #
# # This script executes a file you are treating as POTENTIALLY MALICIOUS.  #
# # Run it only on a disposable VM / throwaway machine you are prepared to   #
# # wipe afterward, with no sensitive credentials, no mounted secrets, and   #
# # network access you are comfortable fully disabling.                     #
# ############################################################################
#
# What it does: runs the target file inside a Docker container with no
# network, a read-only root filesystem (one throwaway scratch dir excepted),
# dropped capabilities, a process-count limit, and a hard wall-clock timeout
# -- then converts the syscall trace (via `strace`) into the JSON-Lines event
# format `security_classifier/dynamic_features.py` expects.
#
# Usage:
#   ./scripts/sandboxed_trace.sh path/to/suspect.py trace_output.jsonl
#
# Requires: Docker, and a Docker image with Python + strace installed. Adjust
# SANDBOX_IMAGE below or build one, e.g.:
#   FROM python:3.11-slim
#   RUN apt-get update && apt-get install -y strace && rm -rf /var/lib/apt/lists/*

set -euo pipefail

TARGET="${1:?usage: $0 <target.py> <trace_output.jsonl>}"
TRACE_OUT="${2:?usage: $0 <target.py> <trace_output.jsonl>}"
SANDBOX_IMAGE="${SANDBOX_IMAGE:-python-strace-sandbox:latest}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-10}"

RAW_STRACE="$(mktemp)"
trap 'rm -f "$RAW_STRACE"' EXIT

echo "[sandboxed_trace] running '$TARGET' inside an isolated, network-off container (timeout ${TIMEOUT_SECONDS}s)..." >&2

docker run \
  --rm \
  --network none \
  --read-only \
  --tmpfs /scratch:rw,size=32m \
  --cap-drop ALL \
  --pids-limit 64 \
  --memory 256m \
  --cpus 1 \
  --user nobody \
  --volume "$(realpath "$TARGET")":/scratch/target.py:ro \
  "$SANDBOX_IMAGE" \
  timeout --signal=KILL "${TIMEOUT_SECONDS}" \
  strace -f -tt -e trace=network,file,process -o /scratch/trace.strace \
  python3 /scratch/target.py \
  > /dev/null 2> "$RAW_STRACE" || true  # a crash/timeout in the target is expected and fine -- we still want the partial trace

echo "[sandboxed_trace] converting strace output -> JSON-Lines events -> $TRACE_OUT" >&2

python3 - "$RAW_STRACE" "$TRACE_OUT" <<'PYEOF'
import json
import re
import sys

raw_path, out_path = sys.argv[1], sys.argv[2]

# IPv4: connect(3, {sa_family=AF_INET, sin_port=htons(4444), sin_addr=inet_addr("1.2.3.4")}, 16) = 0
CONNECT_RE_V4 = re.compile(r'connect\(.*sin_port=htons\((\d+)\).*sin_addr=inet_addr\("([^"]+)"\)')
# IPv6: connect(3, {sa_family=AF_INET6, sin6_port=htons(4444), ..., sin6_addr=inet_pton(AF_INET6, "::1")}, 28) = 0
CONNECT_RE_V6 = re.compile(r'connect\(.*sin6_port=htons\((\d+)\).*sin6_addr=inet_pton\(AF_INET6,\s*"([^"]+)"\)')
# open(AT_FDCWD, "/path", O_WRONLY|O_CREAT|O_TRUNC, 0644) = 4  -- note the ", "
# between the fd argument and the quoted path; a plain `[^,]*"` can't cross it.
OPEN_RE = re.compile(r'open(?:at)?\((?:AT_FDCWD,\s*)?"([^"]+)",\s*([A-Z_|]+)')
WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC")
EXECVE_RE = re.compile(r'execve\("([^"]+)"')

events = []
try:
    with open(raw_path, "r", errors="replace") as fh:
        for line in fh:
            if m := (CONNECT_RE_V4.search(line) or CONNECT_RE_V6.search(line)):
                port, host = m.group(1), m.group(2)
                events.append({"type": "network_connect", "host": host, "port": int(port)})
            elif m := OPEN_RE.search(line):
                path, flags = m.group(1), m.group(2)
                if any(flag in flags for flag in WRITE_FLAGS):
                    events.append({"type": "file_write", "path": path})
            elif m := EXECVE_RE.search(line):
                events.append({"type": "subprocess", "cmd": m.group(1)})
except FileNotFoundError:
    pass

with open(out_path, "w") as fh:
    for event in events:
        fh.write(json.dumps(event) + "\n")

print(f"wrote {len(events)} event(s) to {out_path}", file=sys.stderr)
PYEOF

echo "[sandboxed_trace] done. Score it with:" >&2
echo "  python -m security_classifier.classify $TARGET --trace $TRACE_OUT" >&2
