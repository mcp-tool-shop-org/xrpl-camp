#!/usr/bin/env bash
# xrpl-camp: Ctrl-C after submit (j) and before signing (s), each then `start` with the same memo, in fresh
# default-mode homes. Lists the state dir (names only) after the interrupt and after the resume, and runs `fund`
# on the funded wallet at the end. Usage: recheck_ctrlc.sh <sha> <tag>
set -u
SHA="$1"; TAG="$2"
WT=<worktree>; CAMP=$WT/.venv/Scripts/xrpl-camp.exe; PY=$WT/.venv/Scripts/python.exe
PADROOT=<scratch>/camp   # session scratch: wallet homes live here and never leave it
IC=$(cygpath -w <runs>/_harness/interrupt_cli.py)
case "$(git -C $WT rev-parse HEAD)" in $SHA*) ;; *) echo "ABORT: clone not at $SHA"; exit 2;; esac
TS=$(date -u +%Y%m%dT%H%MZ); R=<runs>/ctrlc-$TAG-$TS; mkdir -p $R; echo $R > $PADROOT/ctrlc_$TAG
echo "code: $(git -C $WT rev-parse HEAD) | $($CAMP --version)" > $R/code.txt
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 COLUMNS=140; unset XRPL_CAMP_HOME XRPL_CAMP_RPC_URL XRPL_CAMP_FAUCET_URL
d(){ local W="$1" label="$2"; shift 2; echo "cmd: xrpl-camp $*" > $R/$label.cmd; ( cd $W && timeout 900 $CAMP "$@" < /dev/null > $R/$label.out 2> $R/$label.err ); echo "exit: $?" >> $R/$label.cmd; echo "$label -> $(tail -1 $R/$label.cmd)"; }
ic(){ local W="$1" label="$2" trig="$3" dl="$4"; shift 4; echo "cmd: [Ctrl-C ${dl}s after $trig] xrpl-camp $*" > $R/$label.cmd; ( cd $W && timeout 900 $PY -I "$IC" "$(cygpath -w $R/$label.out)" "$trig" "$dl" -- "$@" < /dev/null > $R/$label.out 2> $R/$label.err ); echo "exit: $?" >> $R/$label.cmd; echo "$label -> $(tail -1 $R/$label.cmd)"; }
state(){ ( cd "$1" && ls -1 .xrpl-camp 2>/dev/null ) > $R/$2; if [ -f "$1/.xrpl-camp/in_flight.json" ]; then "$PY" -I -c "
import json,sys; d=json.load(open(sys.argv[1])); print('in_flight.json keys:', sorted(d)); print('in_flight.json hash:', d.get('hash') or d.get('txid'))" "$(cygpath -w $1/.xrpl-camp/in_flight.json)" >> $R/$2; fi; }
for k in j s; do
  [ $k = s ] && sleep 60
  W=$PADROOT/ctrlc-$TAG-$TS/$k; mkdir -p $W; M="ctrlc $TAG $k"
  if [ $k = j ]; then ic $W j1-start-interrupted @submit 0.5 --yes start --memo "$M"
  else ic $W s1-start-interrupted "Submitting transaction" 0.3 --yes start --memo "$M"; fi
  state $W ${k}1-state-after-interrupt.txt
  d $W ${k}2-status --yes status
  sleep 15
  d $W ${k}3-read-before-resume --yes read
  d $W ${k}4-start-resume --yes start --memo "$M"
  state $W ${k}4-state-after-resume.txt
  sleep 5
  d $W ${k}5-read-after --yes read
  d $W ${k}6-fund-funded --yes fund
done
echo "DONE $R"
