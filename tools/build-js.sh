#!/bin/sh
# Bundle the page entries into static/js/bundle/.
#
# The source stays as separate ES modules; this produces the
# production artifact, which is committed like static/css/
# tailwind.css because the Docker image carries no Node. Re-run it
# after editing anything under static/js/.
set -eu
cd "$(dirname "$0")/.."
ESBUILD="esbuild@0.25.12"
COMMON="--bundle --format=esm --minify --target=es2022 --legal-comments=none"

# shellcheck disable=SC2086
npx --yes "$ESBUILD" static/js/entry.index.js $COMMON \
    --outfile=static/js/bundle/index.js
# shellcheck disable=SC2086
npx --yes "$ESBUILD" static/js/loans.js $COMMON \
    --outfile=static/js/bundle/loans.js

ls -l static/js/bundle/
