# Releasing the sim

Cloud launches do not clone this repo. They download a release bundle from R2, so a
change reaches students only when it is released.

1. Merge to main. Images that changed are built for `linux/amd64` and `linux/arm64`,
   pushed with the release tag, and pinned in `docker-compose.yml`.
2. Run the release check against a stack on those images:
   `HOST=<ip> DOCKER_HOST=ssh://root@<ip> tools/release-check/check.sh`
3. Tag main (`vX.Y` for releases shared with dexi-os, `vX.Y.Z` for sim-only patches)
   and publish the GitHub release.
4. Publish the bundle and point new launches at it:
   `tools/release-bundle.sh vX.Y.Z --stable`
5. Launch one demo from my.droneblocks.io and run the release check against it.

Rollback: `echo vX.Y.Z > stable.txt && rclone copyto stable.txt r2:dexi-os-releases/sim/stable.txt`
with an earlier version. Bundles are kept per version under `sim/`.

`tools/release-bundle.sh` needs `rclone` with an `r2` remote for the DroneBlocks
Cloudflare account.
