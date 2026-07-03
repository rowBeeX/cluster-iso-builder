#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# NIX_IMAGE tag is a cosmetic Podman label; real pinning is flake.lock plus the Containerfile digest.
image="${NIX_IMAGE:-local/cluster-iso-builder:26.05}"
rebuild="${REBUILD_IMAGE:-0}"

usage() {
  cat <<'EOF'
Usage: ./build.sh [--check] [--rebuild]

  --check    Evaluate the flake and run source checks without building an ISO.
  --rebuild  Rebuild the digest-pinned container image before running.
EOF
}

mode=build
while (($#)); do
  case "$1" in
    --check) mode=check ;;
    --rebuild) rebuild=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

command -v podman >/dev/null 2>&1 || {
  printf 'podman is required\n' >&2
  exit 1
}

if [[ "$rebuild" == 1 ]] || ! podman image exists "$image"; then
  podman build --pull=missing --tag "$image" --file "$repo_dir/Containerfile" "$repo_dir"
fi

mkdir -p "$repo_dir/artifacts/output" "$repo_dir/artifacts/meta"

podman run --rm --pull=never \
  --volume "$repo_dir:/workspace:Z" \
  --workdir /workspace \
  --env BUILD_MODE="$mode" \
  --env OUTPUT_DIR=/workspace/artifacts/output \
  --env META_DIR=/workspace/artifacts/meta \
  "$image"
