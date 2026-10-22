"""Run xrpl-camp in-process and press Ctrl-C (raise KeyboardInterrupt in the main thread) at a chosen moment.

Usage: python -I interrupt_cli.py <watch-file> <trigger> <delay-s> -- <xrpl-camp args...> > <watch-file>

- <trigger> is a string to wait for in the CLI's output; the caller redirects stdout to <watch-file> and a watcher
  thread polls that file. The CLI's own stdout is left alone, so everything it prints (including its "Paused" panel)
  lands in the file as a learner would see it.
- <trigger> "@submit" instead waits for xrpl-py's `submit` RPC (inside `submit_and_wait`) to return: the signed
  payment has reached the server and the CLI is waiting for validation. The wrapper only observes; it does not
  change what is sent.

The Ctrl-C comes <delay-s> later. `_thread.interrupt_main()` is what a console Ctrl-C does at the Python level:
KeyboardInterrupt in the main thread at its next bytecode. Harness notes go to stderr.
"""
import _thread
import sys
import threading
import time

watch, trigger, delay = sys.argv[1], sys.argv[2], float(sys.argv[3])
assert sys.argv[4] == "--", "missing --"
args = sys.argv[5:]
fired = threading.Event()
submitted = threading.Event()


def press(why):
    time.sleep(delay)
    print(f"[interrupt_cli] Ctrl-C {delay}s after {why}", file=sys.stderr, flush=True)
    fired.set()
    _thread.interrupt_main()


def watcher():
    while True:
        if trigger == "@submit":
            if submitted.wait(0.05):
                return press("the submit RPC returned")
            continue
        try:
            with open(watch, encoding="utf-8", errors="replace") as f:
                if trigger in f.read():
                    return press(f"'{trigger}' appeared")
        except FileNotFoundError:
            pass
        time.sleep(0.05)


if trigger == "@submit":
    import xrpl.asyncio.transaction.reliable_submission as rs

    _real_submit = rs.submit

    async def _observed_submit(*a, **kw):
        response = await _real_submit(*a, **kw)
        print(f"[interrupt_cli] submit returned: {response.result.get('engine_result')} "
              f"hash={response.result.get('tx_json', {}).get('hash')}", file=sys.stderr, flush=True)
        submitted.set()
        return response

    rs.submit = _observed_submit

threading.Thread(target=watcher, daemon=True).start()
sys.argv = ["xrpl-camp"] + args
from xrpl_camp.cli import run  # noqa: E402

code = 0
try:
    run()
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
finally:
    sys.stdout.flush()
print(f"[interrupt_cli] fired={fired.is_set()} exit={code}", file=sys.stderr, flush=True)
sys.exit(code)
