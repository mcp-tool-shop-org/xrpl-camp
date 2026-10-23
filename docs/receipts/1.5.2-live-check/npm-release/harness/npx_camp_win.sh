#!/usr/bin/env bash
# Runs xrpl-camp through `npx --yes @mcptoolshop/xrpl-camp@$NPX_VER` with the npm and launcher caches of an earlier
# npm_release_check_win.sh run ($NPX_OUT), so it uses the binary that run downloaded and checked.
export npm_config_cache="$(cygpath -w "$NPX_OUT/npm-cache")" npm_config_prefix="$(cygpath -w "$NPX_OUT/npm-prefix")" LOCALAPPDATA="$(cygpath -w "$NPX_OUT/localappdata")"
exec npx --yes "@mcptoolshop/xrpl-camp@${NPX_VER}" "$@"
