#!/usr/bin/env bash
set -euo pipefail

workspace="${WORKSPACE:-/workspace}"
output_dir="${OUTPUT_DIR:-$workspace/artifacts/output}"
meta_dir="${META_DIR:-$workspace/artifacts/meta}"
mode="${BUILD_MODE:-build}"

cd "$workspace"

bash -n build.sh scripts/container-build.sh
nix flake metadata --no-write-lock-file >/dev/null

if [[ "$mode" == check ]]; then
  nix flake check --no-build --show-trace
  printf 'Source and flake evaluation checks passed.\n'
  exit 0
fi

if [[ "$mode" != build ]]; then
  printf 'Unsupported BUILD_MODE: %s\n' "$mode" >&2
  exit 2
fi

mkdir -p "$output_dir" "$meta_dir"
out_link="$(mktemp -d)/installer-iso"
nix build .#installerIso --out-link "$out_link" --print-build-logs --show-trace

mapfile -d '' -t built_isos < <(find -L "$out_link" -type f -name '*.iso' -print0)
if (( ${#built_isos[@]} != 1 )); then
  printf 'Expected exactly one built ISO, found %d.\n' "${#built_isos[@]}" >&2
  exit 1
fi

find "$output_dir" -maxdepth 1 -type f \( -name '*.iso' -o -name '*.iso.sha256' \) -delete
out_name="$(basename "${built_isos[0]}")"
install -m 0644 "${built_isos[0]}" "$output_dir/$out_name"

(
  cd "$output_dir"
  sha256sum "$out_name" > "$out_name.sha256"
)

sha256="$(sha256sum "$output_dir/$out_name" | cut -d' ' -f1)"
bytes="$(stat -c %s "$output_dir/$out_name")"
revision="$(nix flake metadata --json | jq -r '.locks.nodes.nixpkgs.locked.rev // "unknown"')"
generated_at="$(date --utc +%Y-%m-%dT%H:%M:%SZ)"

jq -n \
  --arg path "artifacts/output/$out_name" \
  --argjson bytes "$bytes" \
  --arg sha256 "$sha256" \
  --arg nixpkgs_revision "$revision" \
  --arg generated_at "$generated_at" \
  '{path: $path, bytes: $bytes, sha256: $sha256, nixpkgs_revision: $nixpkgs_revision, generated_at: $generated_at}' \
  > "$meta_dir/output-iso.json"

printf 'ISO: %s\nSHA256: %s\n' "$output_dir/$out_name" "$sha256"
