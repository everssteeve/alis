#!/bin/bash
# ALIS launcher dispatcher (child of the native stub in Contents/MacOS).
#
# Runs an ALIS job so that macOS (TCC) attributes Google Drive file access to
# the "ALIS" app (one consent, then persistent) instead of silently denying it
# to a bare launchd job.
#
# Usage: open -W -n -a ALIS.app --args <job> [args...]   → runs bin/alis-<job>
#
# KEEP THIS FILE STABLE: it is sealed by the bundle signature. Editing it
# requires launcher/build.sh, which changes the code identity and makes macOS
# ask again for Google Drive access. Job logic lives in bin/, outside the bundle.
set -u
REPO="/Users/steeve/Dev/repos/alis"
export HOME="/Users/steeve"
export PATH="/Users/steeve/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
mkdir -p "$REPO/logs"
job="${1:-}"
if [[ ! "$job" =~ ^[a-z][a-z-]*$ ]] || [[ ! -x "$REPO/bin/alis-$job" ]]; then
  echo "$(date '+%F %T') unknown job: '$job'" >> "$REPO/logs/launcher.log"
  exit 64
fi
shift
exec "$REPO/bin/alis-$job" "$@"
