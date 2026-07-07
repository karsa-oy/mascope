#!/usr/bin/env bash
# Build and publish one workspace package to PyPI, skipping when the local
# version is already published. Runs inside the publish-pypi workflow, where
# `uv publish` authenticates via PyPI Trusted Publishing (OIDC).
#
# Usage: publish-package.sh <project-dir> <pypi-name> <module-name>
#   e.g. publish-package.sh libraries/sdk mascope-sdk mascope_sdk
set -euo pipefail

DIR=$1
PYPI_NAME=$2
MODULE=$3

LOCAL=$(uv version --project "$DIR" --short)

# `has` against .releases (not .info.version) so republishing an older version
# by accident is also caught. An empty/failed response (new project) publishes.
ALREADY_PUBLISHED=$(
  curl -fsS "https://pypi.org/pypi/$PYPI_NAME/json" \
    | jq -r --arg v "$LOCAL" '.releases | has($v)' || echo "false"
)
echo "$PYPI_NAME: local version $LOCAL, already on PyPI: $ALREADY_PUBLISHED"

if [ "$ALREADY_PUBLISHED" = "true" ]; then
  echo "Nothing to publish."
  exit 0
fi

rm -rf dist
uv build --package "$MODULE"

# The wheel must install and import cleanly (with its PyPI dependencies)
# before anything is uploaded.
uv run --isolated --no-project --with dist/*.whl python -c "import $MODULE"

uv publish
echo "Published $PYPI_NAME $LOCAL."
