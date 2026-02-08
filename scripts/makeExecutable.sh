#!/usr/bin/env bash
set -euo pipefail

# Usage: ./make_sh_executable.sh [directory]
DIR="${1:-.}"

# Ensure directory exists
if [ ! -d "$DIR" ]; then
  echo "Error: '$DIR' is not a directory" >&2
  exit 1
fi

# Make all .sh files executable (filesystem permissions)
find "$DIR" -type f -name "*.sh" -exec chmod u+x {} \;

# Tell Git to record them as executable as well
# (run this from inside a Git repo)
git ls-files "$DIR"/*.sh 2>/dev/null | while read -r f; do
  git update-index --chmod=+x "$f"
done
