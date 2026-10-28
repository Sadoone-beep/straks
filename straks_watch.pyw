"""The background watcher (starts with Windows)."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from straks.watcher import main
    sys.exit(main(sys.argv[1:]))
except SystemExit:
    raise
except Exception:
    from straks import paths
    paths.log("watch crashed:\n" + traceback.format_exc())
    sys.exit(1)
