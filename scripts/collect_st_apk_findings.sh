#!/usr/bin/env bash
# Collect decompiled SmartThings APK files relevant to MobileBFF / IP Control / remote
# protocol research, copying matches into a single output directory for review.
#
# Usage: ./collect_st_apk_findings.sh <decompiled_source_dir> <output_dir>

set -euo pipefail

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

PATTERNS=(
  "mobilebff"
  "ms\.channel\.emit"
  "/sec/tv/appdata"
  "appdata/mobilebff"
  "samsung\.remote\.control"
  "ms\.remote\.control"
  "remoteKeyControl"
  "jsonrpc"
  "createAccessToken"
  "artModeControl"
  "powerControl"
  "api/v2/channels"
  ":1516"
  ":8001"
  ":8002"
)

# Build a single extended regex from all patterns (OR'd together).
REGEX=$(IFS='|'; echo "${PATTERNS[*]}")

echo "Searching '$SRC_DIR' for pattern: $REGEX"
echo "Copying matches into: $OUT_DIR"
echo

COUNT=0
while IFS= read -r -d '' file; do
  # Preserve the relative path under OUT_DIR so duplicate filenames don't collide.
  rel_path="${file#"$SRC_DIR"/}"
  dest="$OUT_DIR/$rel_path"
  mkdir -p "$(dirname "$dest")"
  cp -p "$file" "$dest"
  echo "copied: $rel_path"
  COUNT=$((COUNT + 1))
done < <(grep -rlZ -i -E "$REGEX" "$SRC_DIR" --include="*.java" --include="*.kt" --include="*.smali" --include="*.xml" --include="*.json" 2>/dev/null || true)

echo
echo "Done. $COUNT file(s) copied to $OUT_DIR"
