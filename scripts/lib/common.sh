#!/usr/bin/env bash
# Shared host setup. Internal scripts also work when invoked by a container benchmark.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"
export ATOM_UID="$(id -u)"
export ATOM_GID="$(id -g)"
mkdir -p .docker-runtime/jazzy_ws/{build,install,log}
