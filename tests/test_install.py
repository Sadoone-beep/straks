import os
import tempfile
import unittest
import winreg

from straks import i18n, install

TEST_BASE = r"Software\StraksTest"


def setUpModule():
    i18n.set_language("nl", persist=False)
CLASSES = TEST_BASE + r"\Classes"
RUN = TEST_BASE + r"\Run"


class InstallTests(unittest.TestCase):
    def setUp(self):
        install._delete_tree(winreg.HKEY_CURRENT_USER, TEST_BASE)
        self.tmp = tempfile.TemporaryDirectory()
        self.lnk = os.path.join(self.tmp.name, "Straks.lnk")

    def tearDown(self):
        install._delete_tree(winreg.HKEY_CURRENT_USER, TEST_BASE)
        self.tmp.cleanup()

    def test_install_status_uninstall(self):
        r = install.install(classes=CLASSES, run_key=RUN, shortcut=self.lnk)
        self.assertTrue(r["context_menu"])
        self.assertTrue(r["autostart"])
        self.assertTrue(r["shortcut"], "shortcut not created")
        self.assertTrue(os.path.exists(self.lnk))

        s = install.status(classes=CLASSES, run_key=RUN)
        self.assertEqual(s["files"]["text"], "Straks: herinner me hieraan")
        self.assertEqual(s["dirs"]["text"], install.menu_text())
        self.assertIn('"%1"', s["files"]["command"])
        self.assertIn("straks_add.pyw", s["files"]["command"])
        self.assertIn("pythonw", s["files"]["command"].lower())
        self.assertIn("straks_watch.pyw", s["autostart"])
        for part in s["files"]["command"].split('" "')[:2]:
            p = part.strip('"')
            self.assertTrue(os.path.exists(p), p)

        install.uninstall(classes=CLASSES, run_key=RUN, shortcut=self.lnk)
        s2 = install.status(classes=CLASSES, run_key=RUN)
        self.assertIsNone(s2["files"])
        self.assertIsNone(s2["dirs"])
        self.assertIsNone(s2["autostart"])
        self.assertFalse(os.path.exists(self.lnk))

    def test_uninstall_when_nothing_installed(self):
        install.uninstall(classes=CLASSES, run_key=RUN, shortcut=self.lnk)  # must not crash

    def test_exe_flavour(self):
        exe = os.path.join(self.tmp.name, "Straks.exe")
        with open(exe, "wb") as f:
            f.write(b"MZ")
        install.install(classes=CLASSES, run_key=RUN, shortcut=self.lnk, exe=exe)
        s = install.status(classes=CLASSES, run_key=RUN)
        self.assertEqual(s["files"]["command"], f'"{exe}" "add" "%1"')
        self.assertEqual(s["autostart"], f'"{exe}" "watch"')
        self.assertEqual(install.icon_value(exe), exe + ",0")
        self.assertTrue(os.path.exists(self.lnk))
        self.assertEqual(install.launcher("overview", exe), [exe, "overview"])
        install.uninstall(classes=CLASSES, run_key=RUN, shortcut=self.lnk)

    def test_source_flavour_commands(self):
        self.assertEqual(install.launcher("add", None)[1], install.LAUNCHERS["add"])
        self.assertTrue(install.icon_value(None).endswith("straks.ico"))

    def test_no_autostart_option(self):
        install.install(classes=CLASSES, run_key=RUN, shortcut="", autostart=False)
        s = install.status(classes=CLASSES, run_key=RUN)
        self.assertIsNone(s["autostart"])
        self.assertIsNotNone(s["files"])


if __name__ == "__main__":
    unittest.main()
