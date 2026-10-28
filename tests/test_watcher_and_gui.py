"""Watcher logic and the windows, without anything appearing on screen
(STRAKS_HEADLESS=1 keeps every window withdrawn)."""

import os
import tempfile
import time
import tkinter as tk
import unittest
from datetime import datetime, timedelta
from unittest import mock

os.environ["STRAKS_HEADLESS"] = "1"
_TMP = tempfile.TemporaryDirectory()
os.environ["STRAKS_DATA_DIR"] = _TMP.name

from straks import add_gui, i18n, paths, store, watcher, winutil  # noqa: E402
from straks.overview_gui import EditDialog, OverviewWindow  # noqa: E402
from straks.popup_gui import ReminderPopup  # noqa: E402


def setUpModule():
    i18n.set_language("nl", persist=False)


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.now = datetime(2026, 10, 28, 21, 30)
        self.s = store.Store(os.path.join(_TMP.name, f"store-{self._testMethodName}.json"))
        self.file = os.path.join(_TMP.name, "letter.txt")
        with open(self.file, "w") as f:
            f.write("x")


class WatcherLogic(_Base):
    def make(self):
        w = watcher.Watcher(self.root, self.s)
        return w

    def test_nothing_due(self):
        w = self.make()
        self.s.add(store.new_reminder(self.file, self.now + timedelta(hours=1), now=self.now))
        self.assertEqual(w.check_due(self.now), watcher.POLL_MS)
        self.assertEqual(w.popups, {})

    def test_due_shows_popup_once(self):
        w = self.make()
        r = self.s.add(store.new_reminder(self.file, self.now - timedelta(minutes=5), "read", now=self.now))
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=False):
            w.check_due(self.now)
            self.assertIn(r.id, w.popups)
            popup = w.popups[r.id]
            self.assertIsInstance(popup, ReminderPopup)
            self.assertIn("open", popup.buttons)
            self.assertIn("reveal", popup.buttons)
            w.check_due(self.now)  # not a second time
            self.assertEqual(len(w.popups), 1)
        w._close_popup(r.id)

    def test_fullscreen_defers(self):
        w = self.make()
        self.s.add(store.new_reminder(self.file, self.now - timedelta(minutes=5), now=self.now))
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=True):
            self.assertEqual(w.check_due(self.now), watcher.FAST_POLL_MS)
            self.assertEqual(w.popups, {})
            w.check_due(self.now)
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=False):
            self.assertEqual(w.check_due(self.now), watcher.POLL_MS)
            self.assertEqual(len(w.popups), 1)
        for rid in list(w.popups):
            w._close_popup(rid)

    def test_actions(self):
        w = self.make()
        r = self.s.add(store.new_reminder(self.file, self.now, now=self.now))
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=False):
            w.check_due(self.now)
        # snooze
        w.on_action(r, "snooze", self.now + timedelta(minutes=10))
        self.assertNotIn(r.id, w.popups)
        self.assertEqual(self.s.get(r.id).due, "2026-10-28T21:40")
        self.assertEqual(self.s.get(r.id).status, "open")
        # done
        w.on_action(r, "done")
        self.assertEqual(self.s.get(r.id).status, "done")
        # open marks done and calls startfile
        r2 = self.s.add(store.new_reminder(self.file, self.now, now=self.now))
        with mock.patch.object(winutil, "open_target", return_value=True) as op:
            w.on_action(r2, "open")
            op.assert_called_once_with(self.file)
        self.assertEqual(self.s.get(r2.id).status, "done")
        # X = 10 minutes later
        r3 = self.s.add(store.new_reminder(self.file, self.now, now=self.now))
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=False):
            w.check_due(self.now)
        popup = w.popups[r3.id]
        popup._do("close")
        self.assertEqual(self.s.get(r3.id).snoozes, 1)
        self.assertGreater(self.s.get(r3.id).due_dt, datetime.now() + timedelta(minutes=8))

    def test_missing_target_popup(self):
        w = self.make()
        r = self.s.add(store.new_reminder(r"Q:\nowhere\gone.txt", self.now, now=self.now))
        self.assertEqual(r.kind, "file")
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=False):
            w.check_due(self.now)
        popup = w.popups[r.id]
        self.assertTrue(popup.missing)
        self.assertIn("search", popup.buttons)
        self.assertNotIn("open", popup.buttons)
        w._close_popup(r.id)

    def test_text_and_url_popup(self):
        w = self.make()
        t = self.s.add(store.new_reminder("call the dentist", self.now, now=self.now))
        u = self.s.add(store.new_reminder("https://example.com/a", self.now, now=self.now))
        with mock.patch.object(winutil, "is_fullscreen_foreground", return_value=False):
            w.check_due(self.now)
        self.assertIn("copy", w.popups[t.id].buttons)
        self.assertNotIn("open", w.popups[t.id].buttons)
        self.assertIn("open", w.popups[u.id].buttons)
        w.on_action(t, "copy")
        self.assertEqual(self.root.clipboard_get(), "call the dentist")
        self.assertEqual(self.s.get(t.id).status, "done")
        w._close_popup(u.id)

    def test_flags(self):
        w = self.make()
        watcher.request_overview()
        with mock.patch.object(w, "open_overview") as ov:
            w.tick()
            ov.assert_called_once()
        self.assertFalse(os.path.exists(paths.flag_path("overview")))
        watcher.request_stop()
        w.tick()
        self.assertTrue(w._stopping)
        self.assertFalse(os.path.exists(paths.flag_path("stop")))


class AddDialogTests(_Base):
    def test_save_creates_reminders(self):
        with mock.patch.object(store, "Store", return_value=self.s):
            d = add_gui.AddDialog(self.root, [self.file, "call the dentist"])
            self.assertEqual(len(d.targets), 2)
            self.assertEqual(d.listbox.size(), 2)
            d.picker.var.set("morgen 10:00")
            d.note_var.set("don't forget")
            self.assertTrue(d.save())
        items = self.s.open_items()
        self.assertEqual(len(items), 2)
        self.assertEqual({r.kind for r in items}, {"file", "text"})
        self.assertTrue(all(r.note == "don't forget" for r in items))
        tomorrow = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0)
        self.assertTrue(all(r.due == store.fmt(tomorrow) for r in items))

    def test_save_refuses_without_when(self):
        with mock.patch.object(store, "Store", return_value=self.s):
            d = add_gui.AddDialog(self.root, [self.file])
            self.assertFalse(d.save())
            self.assertIn("wanneer", d.status.cget("text").lower())
            d.picker.var.set("blabla")
            self.assertFalse(d.save())
            d.destroy()
        self.assertEqual(self.s.open_items(), [])

    def test_text_entry_adds_target(self):
        with mock.patch.object(store, "Store", return_value=self.s):
            d = add_gui.AddDialog(self.root, [])
            self.assertFalse(d.save())  # nothing chosen
            d.text_var.set("https://example.com")
            d.picker.var.set("over 1 uur")
            self.assertTrue(d.save())
        self.assertEqual(self.s.open_items()[0].kind, "text")

    def test_queue_coalescing(self):
        add_gui.enqueue([self.file, self.file, _TMP.name])
        got = add_gui.drain_queue()
        self.assertEqual(got, [self.file, _TMP.name])
        self.assertEqual(add_gui.drain_queue(), [])
        add_gui.enqueue(["old"])
        time.sleep(0.05)
        self.assertEqual(add_gui.drain_queue(max_age=0.01), [])  # too old = ignored and cleaned up
        self.assertEqual(os.listdir(paths.queue_dir()), [])


class OverviewTests(_Base):
    def test_overview_lists_and_edits(self):
        real_now = datetime.now()
        a = self.s.add(store.new_reminder(self.file, real_now - timedelta(hours=1), "a", now=real_now))
        b = self.s.add(store.new_reminder("text", real_now + timedelta(days=1), now=real_now))
        self.s.mark_done(b.id, self.now)
        with mock.patch.object(store, "Store", return_value=self.s):
            ov = OverviewWindow(self.root)
            self.assertEqual(ov.tree.get_children(), (a.id,))
            self.assertIn("due", ov.tree.item(a.id, "tags"))
            ov.show_done.set(True)
            ov.refresh(force=True)
            self.assertEqual(set(ov.tree.get_children()), {a.id, b.id})
            ov.tree.selection_set(a.id)
            ov.done_selected()
            self.assertEqual(self.s.get(a.id).status, "done")
            ov.tree.selection_set(a.id)
            ov.done_selected()  # reopen
            self.assertEqual(self.s.get(a.id).status, "open")
            ov.tree.selection_set(b.id)
            ov.delete_selected()
            self.assertIsNone(self.s.get(b.id))
            ed = EditDialog(ov, self.s.get(a.id), ov._apply_edit)
            ed.picker.var.set("3 nov 14:00")
            ed.note_var.set("new")
            ed.save()
            r = self.s.get(a.id)
            self.assertEqual(r.due[5:], "11-03T14:00")
            self.assertEqual(r.note, "new")
            ov.close()


class I18nTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("nl", persist=False)

    def test_translate_and_fallback(self):
        self.assertEqual(i18n.t("popup.open"), "Openen")
        i18n.set_language("en", persist=False)
        self.assertEqual(i18n.t("popup.open"), "Open")
        self.assertEqual(i18n.t("add.items", n=3), "3 item(s)")
        self.assertEqual(i18n.t("does.not.exist"), "does.not.exist")

    def test_every_key_exists_in_every_language(self):
        keys = {k for d in i18n.STRINGS.values() for k in d}
        for code, d in i18n.STRINGS.items():
            self.assertEqual(keys - set(d), set(), f"missing in {code}")

    def test_settings_roundtrip(self):
        i18n.set_language("en")
        i18n.reset()
        self.assertEqual(i18n.get_language(), "en")
        self.assertIn(i18n.system_language(), i18n.STRINGS)
        with self.assertRaises(ValueError):
            i18n.set_language("xx")

    def test_english_popup_and_overview(self):
        i18n.set_language("en", persist=False)
        root = tk.Tk()
        root.withdraw()
        s = store.Store(os.path.join(_TMP.name, "store-i18n.json"))
        r = s.add(store.new_reminder("call the dentist", datetime.now()))
        p = ReminderPopup(root, r, 0, lambda *a: None)
        self.assertEqual(p.buttons["copy"].cget("text"), "Copy")
        self.assertEqual(p.buttons["done"].cget("text"), "Done ✓")
        self.assertIn(len(p.snooze_buttons), (4, 5))
        p.destroy()
        with mock.patch.object(store, "Store", return_value=s):
            ov = OverviewWindow(root)
            self.assertEqual(ov.tree.heading("when")["text"], "When")
            self.assertEqual(ov.tree.item(r.id, "values")[2], "(text)")
            ov.close()
        root.destroy()


class WinutilTests(unittest.TestCase):
    def test_work_area_sane(self):
        l, t, r, b = winutil.work_area()
        self.assertGreater(r - l, 200)
        self.assertGreater(b - t, 200)

    def test_mutex_single_instance(self):
        name = "Local\\StraksTestMutex"
        h1 = winutil.acquire_mutex(name)
        self.assertIsNotNone(h1)
        self.assertIsNone(winutil.acquire_mutex(name))
        winutil.release_mutex(h1)
        h2 = winutil.acquire_mutex(name)
        self.assertIsNotNone(h2)
        winutil.release_mutex(h2)

    def test_fullscreen_detection_runs(self):
        self.assertIn(winutil.is_fullscreen_foreground(), (True, False))
        self.assertIsInstance(winutil.foreground_info(), dict)


if __name__ == "__main__":
    unittest.main()
