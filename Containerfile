# Digest-pinned Nix build image. Update the digest intentionally and validate
# the complete ISO build afterwards.
FROM docker.io/nixos/nix@sha256:898e3874bc80a8fbd7df6001b6c83d6e0c904a942e3a4cdf8a89881458333cac

RUN printf '%s\n' \
  'experimental-features = nix-command flakes' \
  'sandbox = false' \
  'max-jobs = auto' \
  'cores = 0' \
  > /etc/nix/nix.conf

WORKDIR /workspace

ENTRYPOINT ["bash", "/workspace/scripts/container-build.sh"]
