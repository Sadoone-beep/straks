"""PyInstaller entry point for Straks.exe (see straks/app.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from straks.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
