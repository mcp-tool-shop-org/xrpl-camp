#!/usr/bin/env bash
# The xrpl-camp npm release check on Windows (Git Bash): npx through a fresh npm cache, npm prefix and launcher cache
# (LOCALAPPDATA), then the cached binary run directly as the argv[0] control.
# Usage: bash npm_release_check_win.sh <out-dir> <version>
set -u
out=$1; ver=$2
mkdir -p "$out"/{npm-cache,npm-prefix,localappdata,cwd}
cd "$out/cwd"
{ node --version; npm --version; } > "$out/node-version.txt"
export npm_config_cache="$(cygpath -w "$out/npm-cache")" npm_config_prefix="$(cygpath -w "$out/npm-prefix")" LOCALAPPDATA="$(cygpath -w "$out/localappdata")"
run() {
  local n=$1; shift
  echo "npx --yes @mcptoolshop/xrpl-camp@${ver} $*   (fresh npm_config_cache, npm_config_prefix, LOCALAPPDATA)" > "$out/$n.cmd"
  npx --yes "@mcptoolshop/xrpl-camp@${ver}" "$@" > "$out/$n.out" 2> "$out/$n.err"
  echo $? > "$out/$n.exit"
}
run 01-version --version
run 02-help --help
run 03-reserve-help reserve --help
run 04-certificate-help certificate --help
run 05-proof-verify-help proof verify --help
(cd "$out/localappdata" && find . -type f) > "$out/06-cache-files.txt"
bin="$out/localappdata/mcptoolshop/xrpl-camp/${ver}/xrpl-camp-${ver}-win-x64.exe"
(cd "$(dirname "$bin")" && sha256sum "$(basename "$bin")") > "$out/06-cached-sha256.txt"
echo "control: run the cached binary directly, without the launcher's argv0" > "$out/07-direct-help.cmd"
"$bin" --help > "$out/07-direct-help.out" 2> "$out/07-direct-help.err"; echo $? > "$out/07-direct-help.exit"
