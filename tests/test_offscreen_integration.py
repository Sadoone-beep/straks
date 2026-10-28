"""Real windows, but off-screen: proves a card becomes visible without
taking focus. Windows only."""

import ctypes
import os
import sys
import tkinter as tk
import unittest
from datetime import datetime
from unittest import mock

from straks import store, winutil
from straks.popup_gui import ReminderPopup

OFFSCREEN = (-20000, -20000, -19000, -19200)  # far outside any screen


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class OffscreenPopup(unittest.TestCase):
    def test_popup_is_visible_but_does_not_take_focus(self):
        root = tk.Tk()
        root.withdraw()
        root.update()  # Tk itself activates the (hidden) root on creation; that is the baseline
        user32 = ctypes.windll.user32
        before = user32.GetForegroundWindow()
        r = store.new_reminder("have a look", datetime.now())
        with mock.patch.dict(os.environ, {"STRAKS_HEADLESS": ""}), \
                mock.patch.object(winutil, "work_area", return_value=OFFSCREEN), \
                mock.patch.object(winutil, "beep"):
            popup = ReminderPopup(root, r, 0, lambda *a: None)
            root.update()
            hwnd = winutil.toplevel_hwnd(popup)
            self.assertTrue(user32.IsWindowVisible(hwnd), "card was not made visible")
            after = user32.GetForegroundWindow()
            self.assertEqual(before, after, "the card stole focus")
            self.assertNotEqual(hwnd, after)
            GWL_EXSTYLE, WS_EX_NOACTIVATE = -20, 0x08000000
            self.assertTrue(user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_NOACTIVATE)
            self.assertIn(len(popup.snooze_buttons), (4, 5))
            popup.destroy()
        root.destroy()


if __name__ == "__main__":
    unittest.main()
