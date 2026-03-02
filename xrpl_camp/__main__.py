"""Allow running as `python -m xrpl_camp` (used by PyInstaller)."""
from xrpl_camp.cli import app

if __name__ == "__main__":
    app()
