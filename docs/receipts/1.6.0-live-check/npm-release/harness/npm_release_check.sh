#!/usr/bin/env bash
# The xrpl-camp npm release check on Linux: npx through fresh npm cache, npm prefix and launcher
# cache (XDG_CACHE_HOME), then the cached binary run directly as the argv[0] control.
# Usage (inside WSL): bash -l npm_release_check.sh <node-bin-dir> <out-dir> <version>
set -u
nodebin=$1; out=$2; ver=$3
export PATH="$nodebin:$PATH"
mkdir -p "$out"/{npm-cache,npm-prefix,xdg-cache,cwd}
cd "$out/cwd"
{ echo "node $(node --version), npm $(npm --version)"; echo "npx: $(command -v npx)"; uname -sm; } > "$out/node-version.txt"
export npm_config_cache="$out/npm-cache" npm_config_prefix="$out/npm-prefix" XDG_CACHE_HOME="$out/xdg-cache"
run() {
  local n=$1; shift
  echo "npx --yes @mcptoolshop/xrpl-camp@${ver} $*   (fresh npm_config_cache, npm_config_prefix, XDG_CACHE_HOME)" > "$out/$n.cmd"
  npx --yes "@mcptoolshop/xrpl-camp@${ver}" "$@" > "$out/$n.out" 2> "$out/$n.err"
  echo $? > "$out/$n.exit"
}
run 01-version --version
run 02-help --help
run 03-reserve-help reserve --help
run 04-certificate-help certificate --help
run 05-proof-verify-help proof verify --help
find "$out/xdg-cache" -type f > "$out/06-cache-files.txt"
bin="$out/xdg-cache/mcptoolshop/xrpl-camp/${ver}/xrpl-camp-${ver}-linux-x64"
(cd "$(dirname "$bin")" && sha256sum "$(basename "$bin")") > "$out/06-cached-sha256.txt"
echo "control: run the cached binary directly, without the launcher's argv0" > "$out/07-direct-help.cmd"
"$bin" --help > "$out/07-direct-help.out" 2> "$out/07-direct-help.err"; echo $? > "$out/07-direct-help.exit"
