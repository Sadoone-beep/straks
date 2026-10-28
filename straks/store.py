"""Storage of reminders: one JSON file, written atomically."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta

from . import paths

FMT = "%Y-%m-%dT%H:%M"
KINDS = ("file", "dir", "text")


def fmt(dt: datetime) -> str:
    return dt.strftime(FMT)


def parse(s: str) -> datetime:
    return datetime.strptime(s, FMT)


@dataclass
class Reminder:
    id: str
    kind: str
    target: str
    due: str
    note: str = ""
    created: str = ""
    status: str = "open"  # open | done
    snoozes: int = 0
    done_at: str = ""
    original_due: str = ""

    @property
    def due_dt(self) -> datetime:
        return parse(self.due)

    @property
    def name(self) -> str:
        if self.kind == "text":
            t = self.target.strip().splitlines()[0] if self.target.strip() else ""
            return t if len(t) <= 60 else t[:57] + "..."
        base = os.path.basename(self.target.rstrip("\\/"))
        return base or self.target

    @property
    def folder(self) -> str:
        if self.kind == "text":
            return ""
        return os.path.dirname(self.target.rstrip("\\/"))

    @property
    def is_url(self) -> bool:
        return self.kind == "text" and self.target.strip().lower().startswith(("http://", "https://"))

    def is_due(self, now: datetime) -> bool:
        return self.status == "open" and self.due_dt <= now

    def exists(self) -> bool:
        if self.kind == "text":
            return True
        return os.path.exists(self.target)

    @classmethod
    def from_dict(cls, d: dict) -> "Reminder":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})


def detect_kind(target: str) -> str:
    t = target.strip()
    if os.path.isdir(t):
        return "dir"
    if os.path.isfile(t):
        return "file"
    if t.lower().startswith(("http://", "https://")):
        return "text"
    # Looks like a path (e.g. just deleted, or on a disconnected drive)
    if len(t) > 2 and t[1] == ":" and ("\\" in t or "/" in t):
        return "file"
    return "text"


def new_reminder(target: str, due: datetime, note: str = "", kind: str | None = None,
                 now: datetime | None = None) -> Reminder:
    now = now or datetime.now()
    kind = kind or detect_kind(target)
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    return Reminder(
        id=uuid.uuid4().hex[:10],
        kind=kind,
        target=target if kind == "text" else os.path.normpath(target),
        due=fmt(due),
        note=note.strip(),
        created=fmt(now),
        original_due=fmt(due),
    )


class Store:
    def __init__(self, path: str | None = None):
        self.path = path or paths.store_path()

    # -- read / write ------------------------------------------------------
    def mtime(self) -> float:
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return 0.0

    def load(self) -> list[Reminder]:
        if not os.path.exists(self.path):
            return []
        for attempt in range(5):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                break
            except json.JSONDecodeError:
                # Half-written or corrupt: set it aside, start empty. Never crash on data.
                broken = self.path + f".broken-{int(time.time())}"
                try:
                    os.replace(self.path, broken)
                    paths.log(f"store corrupt, set aside as {broken}")
                except OSError:
                    pass
                return []
            except PermissionError:
                time.sleep(0.05 * (attempt + 1))
        else:
            return []
        items = data.get("reminders", []) if isinstance(data, dict) else []
        out = []
        for d in items:
            try:
                out.append(Reminder.from_dict(d))
            except (TypeError, ValueError):
                continue
        return out

    def save(self, reminders: list[Reminder]) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = {"version": 1, "reminders": [asdict(r) for r in reminders]}
        tmp = f"{self.path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        for attempt in range(8):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                time.sleep(0.05 * (attempt + 1))
        os.replace(tmp, self.path)

    # -- operations ------------------------------------------------------
    def add(self, r: Reminder) -> Reminder:
        items = self.load()
        items.append(r)
        self.save(items)
        return r

    def get(self, rid: str) -> Reminder | None:
        for r in self.load():
            if r.id == rid:
                return r
        return None

    def update(self, rid: str, **changes) -> Reminder | None:
        items = self.load()
        hit = None
        for r in items:
            if r.id == rid:
                for k, v in changes.items():
                    setattr(r, k, v)
                hit = r
        if hit is not None:
            self.save(items)
        return hit

    def mark_done(self, rid: str, now: datetime | None = None) -> Reminder | None:
        now = now or datetime.now()
        return self.update(rid, status="done", done_at=fmt(now))

    def reopen(self, rid: str, due: datetime) -> Reminder | None:
        return self.update(rid, status="open", done_at="", due=fmt(due))

    def snooze(self, rid: str, new_due: datetime) -> Reminder | None:
        r = self.get(rid)
        if r is None:
            return None
        return self.update(rid, due=fmt(new_due), snoozes=r.snoozes + 1)

    def delete(self, rid: str) -> bool:
        items = self.load()
        keep = [r for r in items if r.id != rid]
        if len(keep) != len(items):
            self.save(keep)
            return True
        return False

    def prune_done(self, now: datetime | None = None, days: int = 30) -> int:
        now = now or datetime.now()
        items = self.load()
        cutoff = now - timedelta(days=days)
        keep = []
        for r in items:
            if r.status == "done" and r.done_at:
                try:
                    if parse(r.done_at) < cutoff:
                        continue
                except ValueError:
                    pass
            keep.append(r)
        removed = len(items) - len(keep)
        if removed:
            self.save(keep)
        return removed

    # -- selections ------------------------------------------------------
    def open_items(self) -> list[Reminder]:
        return sorted((r for r in self.load() if r.status == "open"), key=lambda r: r.due)

    def done_items(self) -> list[Reminder]:
        return sorted((r for r in self.load() if r.status == "done"), key=lambda r: r.done_at, reverse=True)

    def due_items(self, now: datetime | None = None) -> list[Reminder]:
        now = now or datetime.now()
        return [r for r in self.open_items() if r.is_due(now)]
