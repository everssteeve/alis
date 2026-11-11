#!/bin/bash
# Build and ad-hoc sign ALIS.app (native launcher used by the launchd agents).
# Re-signing changes the code identity: macOS will ask again for Google Drive access.
set -euo pipefail
cd "$(dirname "$0")"
cc -O2 -Wall -Wextra -o ALIS.app/Contents/MacOS/alis-launcher src/alis-launcher.c
codesign --force -s - ALIS.app
codesign -dv ALIS.app 2>&1 | grep -E "Identifier|Format"
