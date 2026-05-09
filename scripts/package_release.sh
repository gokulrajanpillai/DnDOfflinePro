#!/usr/bin/env bash
# Package the compiled binary into a versioned ZIP for itch.io upload.
#
# Usage:
#   bash scripts/package_release.sh 0.2.0
#
# Output:
#   release/DnDOfflinePro-v0.2.0-linux.zip

set -euo pipefail

VERSION="${1:-0.2.0}"
DIST_DIR="dnd_offline.dist"
OUT_DIR="release"
ZIP_NAME="DnDOfflinePro-v${VERSION}-linux.zip"

if [ ! -d "$DIST_DIR" ]; then
  echo "Error: $DIST_DIR not found. Run the Nuitka build first."
  exit 1
fi

mkdir -p "$OUT_DIR"

# Write a short launch README into the zip root
cat > /tmp/DnD-README.txt <<EOF
DnD Offline Pro v${VERSION}
===========================

REQUIREMENTS: Linux x86-64 (Ubuntu 20.04+ or equivalent)

HOW TO RUN
----------
1. Extract this ZIP anywhere on your machine
2. Open a terminal and cd into the extracted folder
3. Run: ./DnDOfflinePro.bin

On first run you may need to mark the binary as executable:
  chmod +x DnDOfflinePro.bin

MODELS
------
The binary does NOT include the AI model (too large for download).
On first launch it will download Qwen2.5-0.5B-Instruct (~1 GB) automatically
to a 'models/' folder next to the binary.

Requires an internet connection for that one-time download only.
All subsequent runs are fully offline.

SOURCE & ISSUES
---------------
https://github.com/gokulrajanpillai/DnDOfflinePro

LICENSE
-------
Apache 2.0 — see LICENSE file or the GitHub repo above.
EOF

# Build the zip
zip -r "$OUT_DIR/$ZIP_NAME" "$DIST_DIR" /tmp/DnD-README.txt
echo ""
echo "Release packaged: $OUT_DIR/$ZIP_NAME"
echo "Upload this file to itch.io as the Linux build."
