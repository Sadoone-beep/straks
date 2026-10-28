"""Strings in several languages. `t("key")` returns the text in the active language.

The language comes from settings.json ("language"), else from the user's
Windows display language, else English. Adding a language = one more dict
below plus a vocabulary in timeparse.LANGS.
"""

from __future__ import annotations

import ctypes
import json
import locale
import os
import sys

from . import paths

DEFAULT = "en"
NAMES = {"nl": "Nederlands", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "nl": {
        "menu.remind": "Straks: herinner me hieraan",
        "shortcut.description": "Straks: herinneringen aan bestanden",
        # add dialog
        "add.title": "Straks – herinner me hieraan",
        "add.header": "Herinner me hieraan",
        "add.file": "Bestand…",
        "add.folder": "Map…",
        "add.remove": "Weghalen",
        "add.or_text": "of tekst / link:",
        "add.add": "Toevoegen",
        "add.when": "Wanneer?",
        "add.note": "Notitie:",
        "add.save": "Opslaan",
        "add.cancel": "Annuleren",
        "add.items": "{n} item(s)",
        "add.need_target": "Kies eerst een bestand, map of tekst.",
        "add.need_when": "Vertel me wanneer, bijvoorbeeld 'morgen 10:00'.",
        "add.choose_file": "Welk bestand?",
        "add.choose_folder": "Welke map?",
        # when picker
        "picker.or_type": "Of typ wanneer:",
        "picker.hint": "bijv. 'over 2 uur', 'morgen 14:00', 'vrijdagavond', '3 nov', 'eind van de week'",
        "picker.not_understood": "Dat begrijp ik niet. Probeer bijv. 'morgen 10:00'.",
        # card
        "popup.header": "Herinnering",
        "popup.snoozed": "{n}x uitgesteld",
        "popup.missing": "Niet gevonden op de oude plek (verplaatst of verwijderd?)",
        "popup.open": "Openen",
        "popup.reveal": "Map",
        "popup.copy": "Kopiëren",
        "popup.search": "Zoeken",
        "popup.done": "Klaar ✓",
        "popup.later": "Later:",
        "popup.custom": "zelf…",
        "popup.empty": "(leeg)",
        # overview
        "overview.title": "Straks – overzicht",
        "overview.show_done": "toon afgerond",
        "overview.col_when": "Wanneer",
        "overview.col_what": "Wat",
        "overview.col_where": "Waar",
        "overview.col_note": "Notitie",
        "overview.new": "Nieuw…",
        "overview.open": "Openen",
        "overview.edit": "Bewerken",
        "overview.done": "Klaar ✓",
        "overview.delete": "Verwijderen",
        "overview.hint": "dubbelklik = openen · Enter = bewerken · Delete = weg",
        "overview.n_open": "{n} open",
        "overview.text_kind": "(tekst)",
        "overview.done_prefix": "klaar",
        "overview.confirm_delete": "'{name}' verwijderen?",
        "edit.title": "Straks – bewerken",
        # tray
        "tray.overview": "Overzicht…",
        "tray.new": "Nieuwe herinnering…",
        "tray.language": "Taal",
        "tray.uninstall": "Straks verwijderen…",
        "tray.quit": "Afsluiten",
        "tray.n_open": "Straks – {n} open",
        # install
        "app.install_title": "Straks installeren?",
        "app.install_question": (
            "Straks zet een regel in het rechtsklikmenu van Verkenner\n"
            "(\"Straks: herinner me hieraan\"), start voortaan stil mee met Windows\n"
            "en komt in het Startmenu.\n\n"
            "Alles onder jouw eigen gebruikersaccount, geen beheerdersrechten,\n"
            "geen internet. Verwijderen kan altijd via het klokje in het systeemvak.\n\n"
            "Installeren?"),
        "app.install_done": (
            "Klaar!\n\n"
            "Rechtsklik in Verkenner op een bestand of map en kies\n"
            "\"Straks: herinner me hieraan\".\n\n"
            "Op Windows 11 staat dat onder \"Meer opties weergeven\" (of Shift+F10)."),
        "app.uninstall_title": "Straks verwijderen?",
        "app.uninstall_question": (
            "Rechtsklikmenu, autostart en de Startmenu-snelkoppeling gaan weg.\n"
            "Je herinneringen blijven staan in\n{dir}\n\nDoorgaan?"),
        "app.uninstalled": "Verwijderd.",
        "app.exe_left": "\n\nStraks.exe zelf staat nog in\n{dir}\nen mag je weggooien.",
        "app.error": "Er ging iets mis. Details staan in\n{log}",
        "app.unknown": "Onbekende opdracht: {cmd}",
    },
    "en": {
        "menu.remind": "Straks: remind me about this",
        "shortcut.description": "Straks: reminders for files",
        "add.title": "Straks – remind me about this",
        "add.header": "Remind me about this",
        "add.file": "File…",
        "add.folder": "Folder…",
        "add.remove": "Remove",
        "add.or_text": "or text / link:",
        "add.add": "Add",
        "add.when": "When?",
        "add.note": "Note:",
        "add.save": "Save",
        "add.cancel": "Cancel",
        "add.items": "{n} item(s)",
        "add.need_target": "Pick a file, folder or text first.",
        "add.need_when": "Tell me when, for example 'tomorrow 10:00'.",
        "add.choose_file": "Which file?",
        "add.choose_folder": "Which folder?",
        "picker.or_type": "Or type when:",
        "picker.hint": "e.g. 'in 2 hours', 'tomorrow 2pm', 'friday evening', 'nov 3', 'end of week'",
        "picker.not_understood": "I don't understand that. Try e.g. 'tomorrow 10:00'.",
        "popup.header": "Reminder",
        "popup.snoozed": "snoozed {n}x",
        "popup.missing": "Not found at its old location (moved or deleted?)",
        "popup.open": "Open",
        "popup.reveal": "Folder",
        "popup.copy": "Copy",
        "popup.search": "Search",
        "popup.done": "Done ✓",
        "popup.later": "Later:",
        "popup.custom": "pick…",
        "popup.empty": "(empty)",
        "overview.title": "Straks – overview",
        "overview.show_done": "show done",
        "overview.col_when": "When",
        "overview.col_what": "What",
        "overview.col_where": "Where",
        "overview.col_note": "Note",
        "overview.new": "New…",
        "overview.open": "Open",
        "overview.edit": "Edit",
        "overview.done": "Done ✓",
        "overview.delete": "Delete",
        "overview.hint": "double-click = open · Enter = edit · Delete = remove",
        "overview.n_open": "{n} open",
        "overview.text_kind": "(text)",
        "overview.done_prefix": "done",
        "overview.confirm_delete": "Delete '{name}'?",
        "edit.title": "Straks – edit",
        "tray.overview": "Overview…",
        "tray.new": "New reminder…",
        "tray.language": "Language",
        "tray.uninstall": "Uninstall Straks…",
        "tray.quit": "Quit",
        "tray.n_open": "Straks – {n} open",
        "app.install_title": "Install Straks?",
        "app.install_question": (
            "Straks adds a line to the Explorer right-click menu\n"
            "(\"Straks: remind me about this\"), starts quietly with Windows\n"
            "and gets a Start Menu entry.\n\n"
            "Everything under your own user account: no admin rights,\n"
            "no internet. You can uninstall any time from the tray clock icon.\n\n"
            "Install?"),
        "app.install_done": (
            "Done!\n\n"
            "Right-click a file or folder in Explorer and choose\n"
            "\"Straks: remind me about this\".\n\n"
            "On Windows 11 it's under \"Show more options\" (or Shift+F10)."),
        "app.uninstall_title": "Uninstall Straks?",
        "app.uninstall_question": (
            "The right-click entry, autostart and Start Menu shortcut will be removed.\n"
            "Your reminders stay in\n{dir}\n\nContinue?"),
        "app.uninstalled": "Uninstalled.",
        "app.exe_left": "\n\nStraks.exe itself is still in\n{dir}\nand can be deleted.",
        "app.error": "Something went wrong. Details are in\n{log}",
        "app.unknown": "Unknown command: {cmd}",
    },
}

_current: str | None = None


def settings_path() -> str:
    return os.path.join(paths.data_dir(), "settings.json")


def load_settings() -> dict:
    try:
        with open(settings_path(), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(d: dict) -> None:
    tmp = settings_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, settings_path())


def system_language() -> str:
    """The Windows user's language as 'nl'/'en'/...; unknown -> DEFAULT."""
    code = None
    if sys.platform == "win32":
        try:
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            buf = ctypes.create_unicode_buffer(16)
            if ctypes.windll.kernel32.GetLocaleInfoW(lcid, 0x59, buf, 16):  # LOCALE_SISO639LANGNAME
                code = buf.value
        except Exception:
            code = None
    if not code:
        try:
            loc = locale.getlocale()[0] or ""
            code = loc.split("_")[0].split("-")[0]
        except Exception:
            code = None
    code = (code or "").lower()[:2]
    return code if code in STRINGS else DEFAULT


def get_language() -> str:
    global _current
    if _current is None:
        forced = os.environ.get("STRAKS_LANG")
        chosen = forced or load_settings().get("language") or system_language()
        _current = chosen if chosen in STRINGS else DEFAULT
    return _current


def set_language(code: str, persist: bool = True) -> None:
    global _current
    if code not in STRINGS:
        raise ValueError(code)
    _current = code
    if persist:
        d = load_settings()
        d["language"] = code
        save_settings(d)


def reset() -> None:
    """Forget the chosen language (tests)."""
    global _current
    _current = None


def t(key: str, **kw) -> str:
    lang = get_language()
    s = STRINGS.get(lang, {}).get(key) or STRINGS[DEFAULT].get(key) or key
    return s.format(**kw) if kw else s
