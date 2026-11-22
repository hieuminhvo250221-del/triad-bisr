#!/usr/bin/env bash
# Git Bash (Windows) helper: sync the repo into WSL, then run a script there with the project
# environment loaded.  The script is read from stdin so nothing is parsed twice:
#   tools/wsl.sh <<'EOS'
#   make -C tb test
#   EOS
# Commands that read stdin (docker run -i, openroad, sta, tclsh, ssh) must be given </dev/null.
set -euo pipefail
REPO_WIN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_WSL="/mnt/$(printf '%s' "${REPO_WIN:1:1}" | tr 'A-Z' 'a-z')${REPO_WIN:2}"
{
  printf 'set -euo pipefail\n'
  printf 'bash "%s/tools/sync_to_wsl.sh" >/dev/null\n' "$REPO_WSL"
  printf 'cd "$HOME/work/triad_bisr"\nsource tools/env.sh\n'
  cat
} | wsl -- bash -l -s
