"""Straks - command line.

  python straks.py install       context menu + autostart + Start Menu, and start the watcher
  python straks.py uninstall     remove all of that (reminders are kept)
  python straks.py status        what is registered
  python straks.py start         start the watcher now (if not already running)
  python straks.py stop          stop the watcher
  python straks.py add PATH...   add a reminder via the dialog
  python straks.py list          open reminders in the terminal
  python straks.py overview      the overview window
  python straks.py lang nl|en    pin the language (default: Windows language)
  python straks.py test          test suite
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

def _start_watcher() -> None:
    from straks import install
    print("Watcher started." if install.spawn_watcher() else "Watcher already running.")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "help"
    rest = argv[1:]
    if cmd == "install":
        from straks import install
        return install.main(["install"])
    if cmd == "uninstall":
        from straks import install
        return install.main(["uninstall"])
    if cmd == "status":
        from straks import install
        return install.main(["status"])
    if cmd == "start":
        _start_watcher()
        return 0
    if cmd == "stop":
        from straks.watcher import request_stop
        request_stop()
        print("Stop request sent.")
        return 0
    if cmd == "add":
        from straks.add_gui import main as add_main
        return add_main(rest)
    if cmd == "overview":
        from straks.overview_gui import main as ov_main
        return ov_main(rest)
    if cmd == "lang":
        from straks import i18n
        if rest:
            i18n.set_language(rest[0])
        print("language:", i18n.get_language())
        return 0
    if cmd == "list":
        from datetime import datetime
        from straks import store, timeparse
        items = store.Store().open_items()
        if not items:
            print("No open reminders.")
        now = datetime.now()
        for r in items:
            flag = "!" if r.is_due(now) else " "
            print(f"{flag} {timeparse.describe(r.due_dt, now):34} {r.name}" + (f"  - {r.note}" if r.note else ""))
        return 0
    if cmd == "test":
        import unittest
        suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"), top_level_dir=ROOT)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return 0 if result.wasSuccessful() else 1
    print(__doc__)
    return 0 if cmd in ("help", "-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
