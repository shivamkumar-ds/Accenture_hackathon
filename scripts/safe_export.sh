#!/usr/bin/env bash
#
# Safe hand-off export.
#
# RC-2 audit finding C-1: a previous hand-off zipped the working directory
# directly, which swept up the real backend/.env file (gitignored, never
# committed to git, but still a real file sitting on disk) along with the
# source code -- exposing a live credential to whoever received the archive.
#
# This script cannot make that mistake. `git archive` exports exactly what
# git itself is tracking at the given ref -- nothing gitignored (.env,
# venv/, node_modules/, local build output, __pycache__) can ever end up in
# the output, because none of it is tracked in the first place. That's a
# structural guarantee, not a checklist someone has to remember to follow.
#
# Usage:
#   ./scripts/safe_export.sh [output-path.zip]
#
# Defaults to a timestamped zip one directory above the repo root.

set -euo pipefail
cd "$(dirname "$0")/.."

OUT="${1:-../BidOps_handoff_$(date +%Y%m%d_%H%M%S).zip}"

git archive --format=zip -o "$OUT" HEAD

tracked_count=$(git ls-files | wc -l | tr -d ' ')
echo "Wrote $OUT ($tracked_count tracked files -- exactly HEAD's committed content, nothing else)."
echo
echo "Sanity check (should print nothing):"
if unzip -l "$OUT" | grep -iE '(^|/)\.env$'; then
  echo "!! .env made it into the archive somehow -- do not send this file. !!"
  exit 1
else
  echo "  (clean -- no .env in the archive)"
fi
