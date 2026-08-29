#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Das NIX_IMAGE-Tag ist nur ein Podman-Label; tatsächlich pinnen flake.lock und der Containerfile-Digest.
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

# Optionaler minisign-Secret-Key für die ISO-Signatur; NICHT im Repo.
sign_args=()
if [[ -n "${MINISIGN_SECRET_KEY_FILE:-}" ]]; then
  sign_args=(--volume "$MINISIGN_SECRET_KEY_FILE:/minisign.key:ro" --env MINISIGN_SECRET_KEY_FILE=/minisign.key)
fi

# CAP_SYS_ADMIN + unmask=ALL: Nix braucht sie für die rootless Sandbox-Mounts.
# Breiter als eine reine Mount-Capability, aber beschraenkt auf den trusted,
# ephemeren (--rm) lokalen Build.
podman run --rm --pull=never \
  --cap-add SYS_ADMIN \
  --security-opt unmask=ALL \
  --volume "$repo_dir:/workspace:Z" \
  --workdir /workspace \
  --env BUILD_MODE="$mode" \
  --env OUTPUT_DIR=/workspace/artifacts/output \
  --env META_DIR=/workspace/artifacts/meta \
  "${sign_args[@]}" \
  "$image"
