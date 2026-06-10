#!/bin/sh
# samsung_rpc_token.sh
#
# Shell/curl token helper.
# Token JSON is saved next to this script:
#   samsung_ipctl_token_<host>_<port>.json
#
# Examples:
#   ./samsung_rpc_token.sh 192.168.1.161
#   ./samsung_rpc_token.sh 192.168.4.123 1516 seclevel1

set -eu

TV="${1:-}"
PORT="${2:-1516}"
SECLEVEL="${3:-}"

if [ -z "$TV" ]; then
  echo "Usage: $0 <tv_ip> [port] [seclevel1]"
  echo "Example: $0 192.168.4.123 1516 seclevel1"
  exit 1
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
OUT="$SCRIPT_DIR/samsung_ipctl_token_${TV}_${PORT}.json"
TMP="$SCRIPT_DIR/samsung_create_token_${TV}_${PORT}.raw"

CIPHER_ARGS=""
if [ "$SECLEVEL" = "seclevel1" ] || [ "$SECLEVEL" = "--openssl-seclevel1" ]; then
  CIPHER_ARGS="--ciphers DEFAULT:@SECLEVEL=1"
fi

echo "Calling createAccessToken on https://${TV}:${PORT}/"
echo "If the TV shows an authorization prompt, accept it."
echo "Token file will be written next to this script:"
echo "  $OUT"
echo

# shellcheck disable=SC2086
curl -k -m 20 -sS -i "https://${TV}:${PORT}/" \
  --json '{"jsonrpc":"2.0","id":1,"method":"createAccessToken"}' \
  $CIPHER_ARGS \
  > "$TMP" || {
    echo "ERROR: curl failed. Raw output, if any:"
    cat "$TMP" 2>/dev/null || true
    exit 2
  }

echo "Raw response saved to:"
echo "  $TMP"
echo

BODY="$(sed '1,/^\r\{0,1\}$/d' "$TMP" | tr -d '\r')"

TOKEN=""
if command -v python3 >/dev/null 2>&1; then
  TOKEN="$(printf '%s' "$BODY" | python3 -c '
import json, sys
text=sys.stdin.read().strip()
try:
    obj=json.loads(text)
except Exception:
    print("")
    raise SystemExit
def walk(x):
    if isinstance(x, dict):
        for k,v in x.items():
            if k.lower() in ("accesstoken","access_token","token") and isinstance(v, str):
                print(v)
                return True
            if walk(v):
                return True
    elif isinstance(x, list):
        for v in x:
            if walk(v):
                return True
    return False
walk(obj)
' 2>/dev/null | head -n 1)"
fi

if [ -z "$TOKEN" ]; then
  TOKEN="$(printf '%s' "$BODY" | sed -n 's/.*"AccessToken"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
fi

if [ -z "$TOKEN" ]; then
  echo "No AccessToken extracted."
  echo "Response body was:"
  printf '%s\n' "$BODY"
  echo
  echo "If the TV displayed a prompt, accept it and rerun."
  exit 3
fi

cat > "$OUT" <<EOF
{
  "host": "$TV",
  "port": $PORT,
  "token": "$TOKEN"
}
EOF

chmod 600 "$OUT" 2>/dev/null || true

echo "AccessToken saved to:"
echo "  $OUT"
