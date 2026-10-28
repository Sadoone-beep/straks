# Straks

**Right-click a file or folder → "Straks: remind me about this" → say when.**
At that moment a small card appears bottom-right with *Open*, *Folder*, *Later* and *Done*.

That's all. No account, no cloud, no app you have to open. The file itself is
the reminder.

## Download

Grab **Straks.exe** from the [Releases page](../../releases), double-click it, answer *Yes*.
Done. No admin rights; everything lives under your own user account.

> Windows SmartScreen may warn because the exe is not signed:
> *More info → Run anyway*. If you'd rather not, run from source (below).

## Why

Everyone has files that are "for later": the form you have to send on Monday,
the quote you want to read again in a week, the folder of photos you want to
sort on Sunday. Windows can't remind you of them. You make a calendar entry, a
todo or a sticky note, and in it you have to describe which file you meant and
where it was. Straks skips that step.

## Usage

| What | How |
|---|---|
| Reminder for a file or folder | Right-click in Explorer → **Straks: remind me about this** (on Windows 11 under *Show more options*, or Shift+F10) |
| Several files at once | Select them all and right-click; they land in one dialog |
| Reminder for a text or link | Tray icon → *New reminder…* → type it in the text box |
| Overview of everything | Start Menu → **Straks**, or double-click the tray icon |
| Snooze | On the card: *Later:* 10 min / 1 hour / 3 hours / tonight / tomorrow / pick. The X = 10 minutes later |
| Language | Tray icon → *Language* → English / Nederlands (default: your Windows language) |
| Uninstall | Tray icon → *Uninstall Straks…* |

### When? Just type it

`in 10 min` · `in 2 hours` · `tomorrow` · `tomorrow 2pm` · `tomorrow evening` · `tonight` ·
`friday 4pm` · `fri` · `next week` · `end of day` · `eod` · `weekend` ·
`nov 3` · `11/3` · `10pm` · `at 9`

Dutch works too, in either language mode: `morgen 14:00` · `over 2 uur` · `vrijdagavond` ·
`volgende week` · `eind van de dag` · `3 nov`.

Without a time it's 09:00. A bare number below 7 (`at 3`) means afternoon.
The dialog shows live what it understood.

### House rules of the watcher

- **Full-screen game or film?** The card waits until you're out of it. Nothing interrupts you.
- **A card never takes focus.** Keep typing; the card sits bottom-right on top.
- **File moved or deleted?** The card says so honestly and offers *Search* by name.
- Done reminders stay visible for 30 days under *show done*, then get cleaned up.

## From source

Needs Python 3.12+ with tkinter (standard), plus `pystray` and `Pillow` for the tray icon.

```
pip install -r requirements.txt
install.bat          context menu + autostart + Start Menu, and starts the watcher
uninstall.bat        removes all of that (your reminders stay)
python straks.py status | list | lang en | test
build.bat            builds dist\Straks.exe (PyInstaller)
```

Data: `%LOCALAPPDATA%\Straks\reminders.json` (plain JSON), `settings.json` and `straks.log`.
As an exe, Straks.exe lives there too, so the registry never points into your Downloads folder.

## Layout

```
straks/
  timeparse.py    time text → datetime, one vocabulary per language (LANGS), plus quick buttons and descriptions
  i18n.py         strings per language, language choice (settings.json → Windows language → English)
  store.py        JSON storage, written atomically
  winutil.py      ctypes: full-screen detection, show without focus, mutex, open
  add_gui.py      the "remind me about this" dialog (coalesces multiple selections)
  popup_gui.py    the card that appears
  overview_gui.py overview + edit
  watcher.py      background loop + tray
  install.py      registry (right-click, autostart) + shortcut, source and exe flavour
  app.py          entry point of Straks.exe (first run = install question)
straks_add.pyw / straks_watch.pyw / straks_overview.pyw   console-less launchers (source)
straks_app.py    PyInstaller entry point
straks.py        command line
tests/           python straks.py test
```

Standard library plus pystray/Pillow, on purpose. No framework, no background
service with privileges. Adding a language is one dict in `i18n.py` plus a
`Vocab` in `timeparse.py`.

## Tests

```
python straks.py test
```

Covers the time parser (en + nl), storage, registration (in its own test branch of
the registry), the watcher logic, the translations and all windows (withdrawn, so
invisible), plus one real off-screen test proving a card appears without stealing focus.

## Name

"Straks" is Dutch for "later" or "in a bit".
