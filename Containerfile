# Digest-gepinntes Nix-Build-Image. Den Digest nur bewusst aktualisieren und
# anschließend den vollständigen ISO-Build validieren.
FROM docker.io/nixos/nix:2.34.8@sha256:c03c1081ba8fb98528dee2a677dee6f42bdddb6b90e1c14c67aba8c1e31ed4bb

# sandbox = false: Der Nix-Build-Sandbox braucht mount + user-namespaces mit
# Privilegien, die im rootless-Podman-Container nicht zuverlässig verfügbar sind
# (#31). Die Isolation liefert stattdessen der Container selbst + die digest-
# gepinnten Inputs (Containerfile-Digest + flake.lock) = reproduzierbar. Wo eine
# echte Sandbox möglich ist (privilegierter CI-Runner / Nix auf dem Host), kann
# sie aktiviert werden; dort ist `sandbox = true` vorzuziehen.
RUN printf '%s\n' \
  'experimental-features = nix-command flakes' \
  'sandbox = false' \
  'max-jobs = auto' \
  'cores = 0' \
  > /etc/nix/nix.conf

WORKDIR /workspace

ENTRYPOINT ["bash", "/workspace/scripts/container-build.sh"]
