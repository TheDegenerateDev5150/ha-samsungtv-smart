#!/usr/bin/env bash
# Collect decompiled SmartThings APK files relevant to MobileBFF / IP Control /
# remote protocol research, copying matches into a single output directory.
#
# Unlike the first version this:
#   - does NOT filter by file extension (searches every file),
#   - reports a per-pattern hit count so you can spot noisy patterns
#     (e.g. bare "1516" matches random number sequences everywhere),
#   - copies the union of all matches, preserving relative paths.
#
# Usage: ./collect_st_apk_findings.sh <decompiled_source_dir> <output_dir>

set -uo pipefail

SRC_DIR="${1:-}"
OUT_DIR="${2:-}"

if [[ -z "$SRC_DIR" || -z "$OUT_DIR" ]]; then
  echo "Usage: $0 <decompiled_source_dir> <output_dir>" >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory not found: $SRC_DIR" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

# High-signal patterns. Kept specific on purpose: ":1516" not bare "1516",
# "appdata/mobilebff" not bare numbers, to avoid coincidental matches.
PATTERNS=(
  "mobilebff"
  "ms\.channel\.emit"
  "/sec/tv/appdata"
  "appdata/mobilebff"
  "samsung\.remote\.control"
  "ms\.remote\.control"
  "remoteKeyControl"
  "createAccessToken"
  "artModeControl"
  "powerControl"
  "getTVStates"
  "getVideoStates"
  "api/v2/channels"
  ":1516"
  ":8001"
  ":8002"
  "jsonrpc"
)

echo "Source : $SRC_DIR"
echo "Output : $OUT_DIR"
echo
echo "Per-pattern hit counts (number of files matching each):"
printf '%-30s %s\n' "PATTERN" "FILES"
printf '%-30s %s\n' "-------" "-----"
for p in "${PATTERNS[@]}"; do
  n=$(grep -rlI -i -E -- "$p" "$SRC_DIR" 2>/dev/null | wc -l)
  printf '%-30s %s\n' "$p" "$n"
done
echo

# Build a combined regex and copy the union of all matching files.
REGEX=$(IFS='|'; echo "${PATTERNS[*]}")

COUNT=0
while IFS= read -r -d '' file; do
  rel_path="${file#"$SRC_DIR"/}"
  dest="$OUT_DIR/$rel_path"
  mkdir -p "$(dirname "$dest")"
  cp -p "$file" "$dest"
  echo "copied: $rel_path"
  COUNT=$((COUNT + 1))
done < <(grep -rlIZ -i -E -- "$REGEX" "$SRC_DIR" 2>/dev/null)

echo
echo "Done. $COUNT file(s) copied to $OUT_DIR"
echo
echo "Tip: if a pattern above shows a suspiciously high count (e.g. a bare"
echo "number), it is probably noise. Inspect the real hits with, for example:"
echo "  grep -rn -i 'mobilebff' \"$OUT_DIR\""
