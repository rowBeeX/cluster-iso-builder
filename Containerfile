# Digest nur bewusst aktualisieren und danach den vollstaendigen ISO-Build validieren.
FROM docker.io/nixos/nix:2.35.2@sha256:7a007c766426c1877758ddc5cb87a965ac131fc78c582ce0083d922d51ae945c

# sandbox-fallback = false: ohne funktionierende Sandbox abbrechen statt still
# unsandboxed zu bauen.
RUN printf '%s\n' \
  'experimental-features = nix-command flakes' \
  'sandbox = true' \
  'sandbox-fallback = false' \
  'max-jobs = auto' \
  'cores = 0' \
  > /etc/nix/nix.conf

WORKDIR /workspace

ENTRYPOINT ["bash", "/workspace/scripts/container-build.sh"]
