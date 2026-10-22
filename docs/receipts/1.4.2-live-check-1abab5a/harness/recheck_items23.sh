#!/usr/bin/env bash
# xrpl-camp re-check of the 1.4.1 run's items 2 and 3 (plus the flow they need), on the clone's current HEAD.
# Usage: recheck_items23.sh <sha> <tag>
set -u
SHA="$1"; TAG="$2"
WT=<worktree>   # the test clone, pinned to <sha>
export CAMP=$WT/.venv/Scripts/xrpl-camp.exe PY=$WT/.venv/Scripts/python.exe
PADROOT=<scratch>/camp   # session scratch: wallet homes live here and never leave it
IC=$(cygpath -w <scratch>/_harness/interrupt_cli.py)
case "$(git -C $WT rev-parse HEAD)" in $SHA*) ;; *) echo "ABORT: clone not at $SHA"; exit 2;; esac
TS=$(date -u +%Y%m%dT%H%MZ); BASE=<scratch>/recheck-$TAG-$TS; mkdir -p $BASE; echo $BASE > $PADROOT/recheck_$TAG
echo "code: $(git -C $WT rev-parse HEAD) | $($CAMP --version)" > $BASE/code.txt

# --- flow home (XRPL_CAMP_HOME absolute) + every command
export RUN=$BASE/flow HOME_DIR=$PADROOT/recheck-$TAG-$TS/flow/home CWD=$PADROOT/recheck-$TAG-$TS/flow/cwd
mkdir -p $RUN $HOME_DIR $CWD
source <scratch>/_harness/camp_run.sh
preflight || { echo "ABORT preflight"; cat $RUN/preflight.txt; exit 3; }
c 01-start --yes start --memo "book keeper $TAG live check"
H=$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['txids']['lesson_4'])" "$(cygpath -w $HOME_DIR/session.json)")
A=$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1]))['wallet_address'])" "$(cygpath -w $HOME_DIR/session.json)")
echo "lesson_4=$H address=$A" > $RUN/ids.txt
mkdir -p $CWD/start-out && cp $CWD/xrpl_camp_*.json $CWD/start-out/
c 02-certificate --yes certificate
c 03-proof-verify-online --yes proof verify xrpl_camp_proof_pack.json --online
c 10-status --yes status
c 11-status-detail --yes status --detail
c 12-wallet-show --yes wallet show
c 13-fund --yes fund
c 14-send --yes send --memo "book keeper $TAG send check"
sleep 5
c 15-read --yes read
c 16-read-address --yes read $A
c 17-read-hash --yes read $H
c 18-verify-tx --yes verify --tx $H
c 19-try --yes try
c 20-self-check --yes self-check
c 21-support-bundle --yes support-bundle --out bundle.zip
c 22-proof-verify-folder --yes proof verify .
c 23-try-replay-verbose --yes --verbose try replay
c 30-start-again --yes start --memo "should not be sent"

# --- resume / Ctrl-C, default ./.xrpl-camp homes
R=$BASE/resume; mkdir -p $R; export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 COLUMNS=140; unset XRPL_CAMP_HOME
d(){ local W="$1" label="$2"; shift 2; echo "cmd: xrpl-camp $*" > $R/$label.cmd; ( cd $W && env -u XRPL_CAMP_HOME timeout 900 $CAMP "$@" < /dev/null > $R/$label.out 2> $R/$label.err ); echo "exit: $?" >> $R/$label.cmd; echo "$label -> $(tail -1 $R/$label.cmd)"; }
ic(){ local W="$1" label="$2" trig="$3" dl="$4"; shift 4; echo "cmd: [Ctrl-C ${dl}s after $trig] xrpl-camp $*" > $R/$label.cmd; ( cd $W && env -u XRPL_CAMP_HOME timeout 900 $PY -I "$IC" "$(cygpath -w $R/$label.out)" "$trig" "$dl" -- "$@" < /dev/null > $R/$label.out 2> $R/$label.err ); echo "exit: $?" >> $R/$label.cmd; echo "$label -> $(tail -1 $R/$label.cmd)"; }
for k in f s i j; do
  sleep 60
  W=$PADROOT/recheck-$TAG-$TS/resume-$k; mkdir -p $W
  M="recheck $TAG $k"
  case $k in
    f) ic $W f1-start-interrupted "Requesting funds from the Testnet faucet" 1 --yes start --memo "$M";;
    s) ic $W s1-start-interrupted "Submitting transaction" 0.3 --yes start --memo "$M";;
    i) ic $W i1-start-interrupted "Submitting transaction" 2.5 --yes start --memo "$M";;
    j) ic $W j1-start-interrupted @submit 0.5 --yes start --memo "$M";;
  esac
  d $W ${k}2-status --yes status
  [ $k = j ] && { sleep 15; d $W j3-read-before-resume --yes read; }
  d $W ${k}4-start-resume --yes start --memo "$M"   # the same command again
  sleep 5
  d $W ${k}5-read-after --yes read
done
echo "DONE $BASE"
