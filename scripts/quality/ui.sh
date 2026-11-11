#!/usr/bin/env bash
# The setup pages' toolchain (5c.3a), run only in pinned images: Node and npm
# never run on the machine itself. `build` installs the locked packages (the
# one step with network, no install scripts) and audits them against npm's
# advisories (any advisory fails, and so does an audit that cannot be read),
# then type-checks and builds ui/dist with no network. `test` runs the
# render tests in the Playwright
# image, whose browsers are inside it, with no network. The control plane
# embeds ui/dist (control-plane/crates/rikuri-control/build.rs).
#
# It starts containers, so it runs only in CI unless RIKURI_UI_LOCAL=1 says
# that this machine's Docker is not the live node's (AGENTS.md > The live node).
# Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

NODE_IMAGE="docker.io/library/node:22.23.4-trixie-slim@sha256:be1e2a3dc2c4fd68cdfadad2a696a280e0d2749098bee509230174d72fb768c6"
TEST_IMAGE="mcr.microsoft.com/playwright:v1.64.1-noble@sha256:2f05f8a734509a7b3f26a912639488ee08f58a7b292d14d62271bcff9038768f"
UI="$PWD/ui"

fail() { echo "ui.sh: $1" >&2; exit 1; }

if [ "${GITHUB_ACTIONS:-}" != "true" ] && [ "${RIKURI_UI_LOCAL:-}" != "1" ]; then
    fail "starts containers; it runs in CI. On a machine whose Docker is not the live node's, set RIKURI_UI_LOCAL=1"
fi
command -v docker >/dev/null || fail "docker is missing"

case "${1:-}" in
build)
    rm -rf "$UI/dist"
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$UI:/ui" -w /ui \
        "$NODE_IMAGE" sh -c 'npm ci --ignore-scripts --engine-strict --no-audit --no-fund && npm audit --audit-level=low'
    docker run --rm --user "$(id -u):$(id -g)" --network none -e HOME=/tmp -v "$UI:/ui" -w /ui \
        "$NODE_IMAGE" npm run check
    docker run --rm --user "$(id -u):$(id -g)" --network none -e HOME=/tmp -v "$UI:/ui" -w /ui \
        "$NODE_IMAGE" npm run build
    for page in index.html cert.html favicon.svg licenses.txt; do
        [ -s "$UI/dist/$page" ] || fail "the build made no dist/$page"
    done
    ;;
test)
    [ -d "$UI/node_modules" ] && [ -s "$UI/dist/index.html" ] || fail "build first: scripts/quality/ui.sh build"
    docker run --rm --user "$(id -u):$(id -g)" --network none --shm-size=1g -e HOME=/tmp -e CI=1 -v "$UI:/ui" -w /ui \
        "$TEST_IMAGE" npm run test:render
    ;;
*)
    fail "usage: scripts/quality/ui.sh build|test"
    ;;
esac
