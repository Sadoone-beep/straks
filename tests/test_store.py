import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta

from straks import store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "reminders.json")
        self.s = store.Store(self.path)
        self.now = datetime(2026, 10, 28, 21, 30)
        self.file = os.path.join(self.tmp.name, "form.pdf")
        with open(self.file, "w") as f:
            f.write("x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty(self):
        self.assertEqual(self.s.load(), [])
        self.assertEqual(self.s.mtime(), 0.0)

    def test_add_and_load(self):
        r = store.new_reminder(self.file, self.now + timedelta(hours=1), " fill it in ", now=self.now)
        self.s.add(r)
        items = self.s.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].kind, "file")
        self.assertEqual(items[0].note, "fill it in")
        self.assertEqual(items[0].name, "form.pdf")
        self.assertEqual(items[0].folder, os.path.normpath(self.tmp.name))
        self.assertTrue(items[0].exists())
        self.assertEqual(items[0].original_due, items[0].due)

    def test_kinds(self):
        self.assertEqual(store.detect_kind(self.tmp.name), "dir")
        self.assertEqual(store.detect_kind(self.file), "file")
        self.assertEqual(store.detect_kind("https://example.com/x"), "text")
        self.assertEqual(store.detect_kind("call the dentist"), "text")
        self.assertEqual(store.detect_kind(r"D:\gone\file.txt"), "file")  # path that does not exist (right now)
        r = store.new_reminder("https://example.com/x", self.now)
        self.assertTrue(r.is_url)
        self.assertEqual(store.new_reminder("call the dentist", self.now).name, "call the dentist")

    def test_due_and_done(self):
        a = self.s.add(store.new_reminder(self.file, self.now - timedelta(minutes=1), now=self.now))
        b = self.s.add(store.new_reminder("text", self.now + timedelta(hours=2), now=self.now))
        self.assertEqual([r.id for r in self.s.due_items(self.now)], [a.id])
        self.assertEqual([r.id for r in self.s.open_items()], [a.id, b.id])
        self.s.mark_done(a.id, self.now)
        self.assertEqual(self.s.due_items(self.now), [])
        self.assertEqual([r.id for r in self.s.done_items()], [a.id])
        self.assertEqual(self.s.get(a.id).done_at, "2026-10-28T21:30")

    def test_snooze(self):
        a = self.s.add(store.new_reminder(self.file, self.now, now=self.now))
        self.s.snooze(a.id, self.now + timedelta(minutes=10))
        r = self.s.get(a.id)
        self.assertEqual(r.due, "2026-10-28T21:40")
        self.assertEqual(r.snoozes, 1)
        self.assertEqual(r.original_due, "2026-10-28T21:30")
        self.assertIsNone(self.s.snooze("nonexistent", self.now))

    def test_delete_and_prune(self):
        a = self.s.add(store.new_reminder(self.file, self.now, now=self.now))
        b = self.s.add(store.new_reminder(self.file, self.now, now=self.now))
        self.assertTrue(self.s.delete(a.id))
        self.assertFalse(self.s.delete(a.id))
        self.s.mark_done(b.id, self.now - timedelta(days=40))
        self.assertEqual(self.s.prune_done(self.now), 1)
        self.assertEqual(self.s.load(), [])

    def test_corrupt_file_is_set_aside(self):
        with open(self.path, "w") as f:
            f.write("{ broken")
        self.assertEqual(self.s.load(), [])
        self.assertFalse(os.path.exists(self.path))
        self.assertTrue(any(n.startswith("reminders.json.broken-") for n in os.listdir(self.tmp.name)))

    def test_unknown_fields_are_ignored(self):
        data = {"version": 1, "reminders": [{
            "id": "abc", "kind": "text", "target": "hi", "due": "2026-10-28T22:00", "future": 1}]}
        with open(self.path, "w") as f:
            json.dump(data, f)
        items = self.s.load()
        self.assertEqual(items[0].id, "abc")
        self.assertEqual(items[0].status, "open")

    def test_atomic_write_leaves_no_tmp(self):
        self.s.add(store.new_reminder("x", self.now, now=self.now))
        self.assertEqual([n for n in os.listdir(self.tmp.name) if n.endswith(".tmp")], [])


if __name__ == "__main__":
    unittest.main()
