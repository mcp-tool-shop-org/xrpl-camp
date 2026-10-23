#!/usr/bin/env bash
# Install the official Node.js Linux x64 tarball into ~/opt/node-<ver> (no sudo), after
# checking its SHA256 against nodejs.org's SHASUMS256.txt. Usage: bash -l wsl_node.sh v22.22.3
set -eu
ver=$1; name="node-${ver}-linux-x64"; dir=$(mktemp -d)
cd "$dir"
curl -fsSLO "https://nodejs.org/dist/${ver}/${name}.tar.xz"
curl -fsSLO "https://nodejs.org/dist/${ver}/SHASUMS256.txt"
grep " ${name}.tar.xz\$" SHASUMS256.txt | sha256sum -c -
mkdir -p ~/opt && tar -xJf "${name}.tar.xz" -C ~/opt
rm -rf "$dir"
~/opt/${name}/bin/node --version
