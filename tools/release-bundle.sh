#!/bin/bash
# Package a sim release for cloud launches and publish it to R2.
#
#   tools/release-bundle.sh v0.23.1            # build and upload sim/v0.23.1/
#   tools/release-bundle.sh v0.23.1 --stable   # ...and point new launches at it
#   REF=<branch> R2_REMOTE=r2:dexi-os-releases/test tools/release-bundle.sh v0.23.1-test --stable
#                                              # a test bundle from a branch, outside sim/
#
# The bundle is what a cloud VM needs to run the stack: the compose files, the
# bringup source the stack mounts, the Node-RED flows, the MAVSDK course folders and
# the scripts, taken from a clean recursive checkout of the release tag. Images come
# from Docker Hub; the Unity build files are left out because only their images are used.
# The provisioner reads sim/stable.txt, downloads that version's bundle, and checks its
# SHA-256. Rolling back is pointing stable.txt at an earlier version.
set -euo pipefail
VERSION=${1:?usage: release-bundle.sh <version> [--stable]}
STABLE=${2:-}
REF=${REF:-$VERSION}
REMOTE=${R2_REMOTE:-r2:dexi-os-releases}/sim
NAME=dexi-sim-$VERSION.tar.gz
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT

git clone -q --recursive --depth 1 --shallow-submodules --branch "$REF" \
  https://github.com/DroneBlocks/dexi-sim-ftw.git "$WORK/dexi-sim-ftw"
COPYFILE_DISABLE=1 tar czf "$WORK/$NAME" -C "$WORK/dexi-sim-ftw" \
  --exclude='.git' --exclude='*/.git' --exclude='./unity' .
(cd "$WORK" && shasum -a 256 "$NAME" > "$NAME.sha256")
echo "$NAME: $(du -h "$WORK/$NAME" | cut -f1), $(tar tzf "$WORK/$NAME" | wc -l | tr -d ' ') files"

rclone copyto "$WORK/$NAME" "$REMOTE/$VERSION/$NAME"
rclone copyto "$WORK/$NAME.sha256" "$REMOTE/$VERSION/$NAME.sha256"
if [ "$STABLE" = "--stable" ]; then
  echo "$VERSION" > "$WORK/stable.txt"
  rclone copyto "$WORK/stable.txt" "$REMOTE/stable.txt"
  echo "new launches now use $VERSION"
fi
