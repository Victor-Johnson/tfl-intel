#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
target_revision="${1:-origin/main}"
cd "$PROJECT_DIR"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Deployment checkout contains local changes; refusing to overwrite them." >&2
  exit 1
fi

previous_revision="$(git rev-parse HEAD)"
git fetch --prune origin main
git checkout main
git merge --ff-only "$target_revision"
deployed_revision="$(git rev-parse HEAD)"

if PROJECT_DIR="$PROJECT_DIR" ./scripts/bootstrap_production.sh; then
  echo "Deployed $deployed_revision (previously $previous_revision)."
  exit 0
fi

if ! git cat-file -e "$previous_revision:scripts/bootstrap_production.sh" 2>/dev/null; then
  echo "Initial deployment failed; no previous bootstrappable revision exists." >&2
  echo "Leaving $deployed_revision checked out for diagnosis." >&2
  exit 1
fi

echo "Deployment failed; restoring $previous_revision." >&2
git reset --hard "$previous_revision"
PROJECT_DIR="$PROJECT_DIR" ./scripts/bootstrap_production.sh
echo "Rollback to $previous_revision completed." >&2
exit 1
