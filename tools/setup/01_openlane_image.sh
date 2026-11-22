#!/usr/bin/env bash
# Pull the OpenLane 1 image matching ~/OpenLane (v1.0.2 = upstream ff5509f) and the installed PDK.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
docker image inspect "$OPENLANE_IMAGE" >/dev/null 2>&1 || docker pull "$OPENLANE_IMAGE" </dev/null
docker image inspect "$OPENLANE_IMAGE" --format 'image: {{index .RepoTags 0}}{{"\n"}}digest: {{index .RepoDigests 0}}{{"\n"}}size_bytes: {{.Size}}'
