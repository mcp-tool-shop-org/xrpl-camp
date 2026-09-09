"""Allow running as `python -m xrpl_camp` (used by PyInstaller).

Uses `run()` rather than `app()` so the packaged binary gets the same
CampFailure handling as the console script — the PyInstaller build is the
path most likely to meet a corrupt state file on someone else's machine.
"""
from xrpl_camp.cli import run

if __name__ == "__main__":
    run()
