#!/usr/bin/env bash
# xrpl-camp live-check helpers. Source it, then call: c <label> <args...>
# Each call runs from $CWD with XRPL_CAMP_HOME=$HOME_DIR and stdin from /dev/null (or $STDIN_FILE), and writes
# $RUN/<label>.{cmd,out,err,exit}. Seeds never leave the home, which lives in the session scratchpad.
: "${CAMP:?}" "${RUN:?}" "${HOME_DIR:?}" "${CWD:?}"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 COLUMNS=140
unset XRPL_CAMP_RPC_URL XRPL_CAMP_FAUCET_URL XRPL_CAMP_RETRIES XRPL_CAMP_NO_LOCK XRPL_CAMP_ALLOW_ANY_NETWORK XRPL_CAMP_ALLOW_ANY_ENDPOINT XRPL_CAMP_HOME
c(){ local label="$1"; shift
  echo "cmd: xrpl-camp $*" > "$RUN/$label.cmd"
  local t0=$(date +%s)
  ( cd "$CWD" && XRPL_CAMP_HOME="$(cygpath -w "$HOME_DIR")" timeout "${TMO:-900}" "$CAMP" "$@" < "${STDIN_FILE:-/dev/null}" > "$RUN/$label.out" 2> "$RUN/$label.err" ); local rc=$?
  echo "exit: $rc  seconds: $(( $(date +%s) - t0 ))" >> "$RUN/$label.cmd"; echo "$label -> exit $rc"
}
preflight(){ # endpoint is the default testnet URL and the CLI's own guard passes; writes $RUN/preflight.txt
  ( cd "$CWD" && XRPL_CAMP_HOME="$(cygpath -w "$HOME_DIR")" "$PY" -I -c "
import os
from xrpl_camp import transport, lessons
url = transport.get_rpc_url()
print('XRPL_CAMP_* set:', sorted(k for k in os.environ if k.startswith('XRPL_CAMP_') and k != 'XRPL_CAMP_HOME'))
print('rpc:', url, '| faucet override:', transport.get_faucet_url() if hasattr(transport,'get_faucet_url') else 'n/a')
err = lessons.check_endpoint()
print('check_endpoint:', 'PASS' if err is None else err)
raise SystemExit(0 if err is None and url == transport.TESTNET_URL else 9)
" ) > "$RUN/preflight.txt" 2>&1
}
