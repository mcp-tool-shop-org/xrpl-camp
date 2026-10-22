"""Run xrpl-camp in-process and log, through Python audit hooks, every network lookup / connect and every filesystem
change it makes: opens for writing, mkdir, rename, remove, rmdir, chmod.

Usage: python -I trace_camp.py <trace-file> <xrpl-camp args...>

Read-only opens are not logged. Writes of the interpreter's own bytecode cache (`__pycache__`) are logged with a
`pycache` tag, since they are Python's, not the tool's. Loopback connects are asyncio's own socketpair on Windows.
"""
import os
import sys

trace_path = sys.argv[1]
args = sys.argv[2:]
fd = os.open(trace_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)


def note(kind, detail):
    tag = " pycache" if "__pycache__" in detail else ""
    os.write(fd, f"{kind}{tag} {detail}\n".encode("utf-8", "replace"))


def hook(event, a):
    if event == "open":
        path, mode, flags = a
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing and not (isinstance(path, int)):
            note("write", str(path))
    elif event in ("os.mkdir", "os.rename", "os.replace", "os.remove", "os.rmdir", "os.chmod", "shutil.rmtree",
                   "os.symlink", "os.link", "os.truncate"):
        note(event, " ".join(str(x) for x in a[:2]))
    elif event == "socket.getaddrinfo":
        note("lookup", str(a[0]))
    elif event == "socket.connect":
        addr = a[1]
        note("connect", str(addr[0] if isinstance(addr, tuple) else addr))


sys.addaudithook(hook)
sys.argv = ["xrpl-camp"] + args
from xrpl_camp.cli import run  # noqa: E402

run()
