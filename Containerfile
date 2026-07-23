# Digest-gepinntes Nix-Build-Image. Den Digest nur bewusst aktualisieren und
# anschließend den vollständigen ISO-Build validieren.
FROM docker.io/nixos/nix:2.35.1@sha256:377d4887aca98f0dfa12971c1ea6d6a625a435d8b610d4c95a436843da6fbfd1

# Der rootless Podman-Container erhält beim Start nur die für Nix-Mount-
# Namespaces nötige Capability. Ohne funktionierende Sandbox muss der Build
# geschlossen abbrechen.
RUN printf '%s\n' \
  'experimental-features = nix-command flakes' \
  'sandbox = true' \
  'sandbox-fallback = false' \
  'max-jobs = auto' \
  'cores = 0' \
  > /etc/nix/nix.conf

WORKDIR /workspace

ENTRYPOINT ["bash", "/workspace/scripts/container-build.sh"]
