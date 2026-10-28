"""Plain-language time -> datetime. Dutch and English, extensible via LANGS.

Understands, among others:
  nl: "over 10 min", "over 2 uur", "morgen", "morgen 14:00", "morgenavond",
      "vanavond", "vrijdag 16:00", "vr", "volgende week", "eind van de dag",
      "31-10", "3 nov 14:00", "22:00", "om 9"
  en: "in 10 min", "in 2 hours", "tomorrow", "tomorrow 2pm", "tomorrow evening",
      "tonight", "friday 4pm", "fri", "next week", "end of day", "eod",
      "nov 3", "11/3", "10pm", "at 9"

The active language is tried first, then the others, so "tomorrow" also
works in Dutch mode and "morgen" also works in English mode.
Everything is local time, no time zone. No external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import i18n

DEFAULT_TIME = (9, 0)
MINUTES = {"min": 1, "hour": 60, "day": 1440, "week": 10080}


@dataclass
class Vocab:
    code: str
    weekdays: dict[str, int]            # "ma"/"monday" -> 0..6
    weekday_names: list[str]            # full names, mon..sun
    weekday_short: list[str]
    months: dict[str, int]              # "jan"/"maart" -> 1..12
    month_short: list[str]
    dayparts: dict[str, tuple[int, int]]  # "ochtend"/"morning" -> (hour, minute)
    units: dict[str, str]               # "min"/"hours" -> "min"/"hour"/"day"/"week"
    numbers: dict[str, float]           # "een"/"two"/"half" -> number
    duration_prefix: list[str]          # "over" / "in"
    time_prefix: list[str]              # "om" / "at"
    next_word: list[str]                # "volgende" / "next"
    today: list[str]
    tomorrow: list[str]
    day_after: list[str]
    today_parts: dict[str, str]         # "vanavond" -> "avond", "tonight" -> "evening"
    now: list[str]
    soon: list[str]
    next_week: list[str]
    next_month: list[str]
    end_of_day: list[str]
    end_of_week: list[str]
    weekend: list[str]
    glue: list[str] = field(default_factory=list)  # words that may be dropped: "de", "the"
    ampm: bool = False
    u_notation: bool = False            # "14u30"
    day_first: bool = True              # 31-10 = day-month
    # descriptions
    w_today: str = "today"
    w_tomorrow: str = "tomorrow"
    w_day_after: str = "day after tomorrow"
    w_in: str = "in"
    w_ago: str = "ago"
    w_now: str = "now"
    w_min: str = "min"
    w_hour: str = "h"
    w_day: str = "d"
    w_days: str = "days"
    labels: dict[str, str] = field(default_factory=dict)


NL = Vocab(
    code="nl",
    weekdays={"ma": 0, "maandag": 0, "di": 1, "dinsdag": 1, "wo": 2, "woensdag": 2, "do": 3,
              "donderdag": 3, "vr": 4, "vrijdag": 4, "za": 5, "zaterdag": 5, "zo": 6, "zondag": 6},
    weekday_names=["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
    weekday_short=["ma", "di", "wo", "do", "vr", "za", "zo"],
    months={"jan": 1, "januari": 1, "feb": 2, "februari": 2, "mrt": 3, "maart": 3, "apr": 4, "april": 4,
            "mei": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7, "aug": 8, "augustus": 8, "sep": 9,
            "sept": 9, "september": 9, "okt": 10, "oktober": 10, "nov": 11, "november": 11,
            "dec": 12, "december": 12},
    month_short=["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    dayparts={"ochtend": (9, 0), "middag": (14, 0), "avond": (20, 0), "nacht": (23, 30)},
    units={"min": "min", "minuut": "min", "minuten": "min", "m": "min", "u": "hour", "uur": "hour",
           "uren": "hour", "d": "day", "dag": "day", "dagen": "day", "w": "week", "week": "week",
           "weken": "week"},
    numbers={"een": 1, "één": 1, "twee": 2, "drie": 3, "vier": 4, "vijf": 5, "zes": 6, "zeven": 7,
             "acht": 8, "negen": 9, "tien": 10, "half": 0.5, "anderhalf": 1.5, "kwartier": 0.25},
    duration_prefix=["over"], time_prefix=["om"], next_word=["volgende", "komende", "aanstaande"],
    today=["vandaag"], tomorrow=["morgen"], day_after=["overmorgen"],
    today_parts={"vanochtend": "ochtend", "vanmorgen": "ochtend", "vanmiddag": "middag",
                 "vanavond": "avond", "vannacht": "nacht"},
    now=["nu", "direct", "meteen"], soon=["straks", "zometeen"],
    next_week=["volgende week"], next_month=["volgende maand"],
    end_of_day=["eind van de dag", "einde van de dag", "einde dag", "eind dag"],
    end_of_week=["eind van de week", "einde van de week", "einde week", "eind week"],
    weekend=["weekend", "dit weekend", "in het weekend"],
    glue=["de", "het", "om", "op"],
    ampm=False, u_notation=True, day_first=True,
    w_today="vandaag", w_tomorrow="morgen", w_day_after="overmorgen", w_in="over", w_ago="geleden",
    w_now="nu", w_min="min", w_hour="u", w_day="d", w_days="dagen",
    labels={"in_1h": "Over 1 uur", "tonight": "Vanavond 20:00", "tomorrow_evening": "Morgenavond 20:00",
            "tomorrow": "Morgen 09:00", "day_after": "Overmorgen 09:00", "monday": "Maandag 09:00",
            "in_week": "Over een week", "10min": "10 min", "1h": "1 uur", "3h": "3 uur",
            "tomorrow_short": "morgen 09:00", "tonight_short": "vanavond 20:00"},
)

EN = Vocab(
    code="en",
    weekdays={"mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
              "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5,
              "saturday": 5, "sun": 6, "sunday": 6},
    weekday_names=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
    weekday_short=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    months={"jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4,
            "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8,
            "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10, "nov": 11,
            "november": 11, "dec": 12, "december": 12},
    month_short=["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
    dayparts={"morning": (9, 0), "noon": (12, 0), "afternoon": (14, 0), "evening": (20, 0),
              "night": (23, 30)},
    units={"min": "min", "mins": "min", "minute": "min", "minutes": "min", "m": "min", "h": "hour",
           "hr": "hour", "hrs": "hour", "hour": "hour", "hours": "hour", "d": "day", "day": "day",
           "days": "day", "w": "week", "wk": "week", "wks": "week", "week": "week", "weeks": "week"},
    numbers={"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "half": 0.5, "quarter": 0.25},
    duration_prefix=["in"], time_prefix=["at"], next_word=["next", "coming", "this"],
    today=["today"], tomorrow=["tomorrow", "tmrw", "tmr"],
    day_after=["day after tomorrow", "the day after tomorrow"],
    today_parts={"tonight": "evening", "this morning": "morning", "this afternoon": "afternoon",
                 "this evening": "evening", "noon": "noon", "midday": "noon"},
    now=["now", "right now", "immediately"], soon=["soon", "later", "in a bit"],
    next_week=["next week"], next_month=["next month"],
    end_of_day=["end of day", "end of the day", "eod"],
    end_of_week=["end of week", "end of the week", "eow"],
    weekend=["weekend", "this weekend", "the weekend", "on the weekend"],
    glue=["the", "at", "on"],
    ampm=True, u_notation=False, day_first=False,
    w_today="today", w_tomorrow="tomorrow", w_day_after="day after tomorrow", w_in="in", w_ago="ago",
    w_now="now", w_min="min", w_hour="h", w_day="d", w_days="days",
    labels={"in_1h": "In 1 hour", "tonight": "Tonight 20:00", "tomorrow_evening": "Tomorrow evening 20:00",
            "tomorrow": "Tomorrow 09:00", "day_after": "Day after tomorrow 09:00", "monday": "Monday 09:00",
            "in_week": "In a week", "10min": "10 min", "1h": "1 hour", "3h": "3 hours",
            "tomorrow_short": "tomorrow 09:00", "tonight_short": "tonight 20:00"},
)

LANGS: dict[str, Vocab] = {"nl": NL, "en": EN}


def vocab(lang: str | None = None) -> Vocab:
    return LANGS.get(lang or i18n.get_language(), LANGS[i18n.DEFAULT])


def _order(lang: str | None) -> list[Vocab]:
    first = vocab(lang)
    return [first] + [v for v in LANGS.values() if v is not first]


# -- helpers -----------------------------------------------------------------------
def _at(day: datetime, hm: tuple[int, int]) -> datetime:
    return day.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)


def _normalize(text: str, v: Vocab) -> str:
    s = text.strip().lower().replace("’", "'").replace("'s ", " ").replace(",", " ")
    s = re.sub(r"\s+", " ", s)
    for w in ("een half", "a half"):
        s = s.replace(w + " ", "half ")
    s = s.replace("half an hour", "half hour").replace("an hour and a half", "1.5 hour")
    # "morgenavond" -> "morgen avond"; "fridayevening" does not occur but is harmless
    words = []
    for w in s.split(" "):
        split = None
        for part in v.dayparts:
            if w.endswith(part) and len(w) > len(part):
                head = w[: -len(part)]
                if head in v.tomorrow or head in v.day_after or head in v.today or head in v.weekdays:
                    split = (head, part)
                    break
        words.extend(split if split else (w,))
    return " ".join(w for w in words if w)


def _duration(s: str, now: datetime, v: Vocab) -> datetime | None:
    prefix = "|".join(re.escape(p) for p in v.duration_prefix)
    units = "|".join(sorted((re.escape(u) for u in v.units), key=len, reverse=True))
    m = re.fullmatch(rf"(?:(?:{prefix})\s+)?(?:(\d+(?:[.,]\d+)?|[a-zé]+)(\s*))?({units})", s)
    if not m:
        return None
    amount, gap, unit = m.group(1), m.group(2), m.group(3)
    kind = v.units[unit]
    if unit == "u" and amount and amount[0].isdigit() and gap == "":
        return None  # "9u" is a time of day (09:00), not a duration; "9 u" is
    if amount is None:
        n = 1.0
    elif amount[0].isdigit():
        n = float(amount.replace(",", "."))
    elif amount in v.numbers:
        n = v.numbers[amount]
    else:
        return None
    minutes = int(round(n * MINUTES[kind]))
    if minutes <= 0:
        return None
    return (now + timedelta(minutes=minutes)).replace(second=0, microsecond=0)


def _split_time(s: str, v: Vocab) -> tuple[str, tuple[int, int] | None, bool]:
    """Take a time off the end: 'friday 4pm' -> ('friday', (16,0), True)."""
    prefix = "|".join(re.escape(p) for p in v.time_prefix)
    unit_u = r"(?:[:.u](\d{2})|u)?" if v.u_notation else r"(?:[:.](\d{2}))?"
    ampm = r"\s*(am|pm|a\.m\.|p\.m\.)?" if v.ampm else r"()?"
    hour_word = r"(?:\s*uur)?" if v.code == "nl" else r"(?:\s*o'?clock)?"
    m = re.search(rf"(?:^|\s)(?:(?:{prefix})\s+)?(\d{{1,2}}){unit_u}{ampm}{hour_word}$", s)
    if not m:
        return s, None, False
    h = int(m.group(1))
    mi = int(m.group(2) or 0)
    suffix = (m.group(3) or "").replace(".", "")
    if h > 23 or mi > 59:
        return s, None, False
    head = s[: m.start()].strip().split(" ")
    if m.group(2) is None and not suffix and head and head[-1] in v.months:
        return s, None, False  # "nov 3": that is a day, not a time
    if suffix == "pm" and h < 12:
        h += 12
    elif suffix == "am" and h == 12:
        h = 0
    elif not suffix and m.group(2) is None and 0 < h < 7:
        h += 12  # "om 3" / "at 3" means afternoon; whoever wants 03:00 types it in full
    return s[: m.start()].strip(), (h, mi), True


def _date_only(s: str, now: datetime, v: Vocab) -> datetime | None:
    """'31-10', '31/10/2026', '3 nov', 'nov 3', '3 november 2027'."""
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})(?:[-/.](\d{2,4}))?", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if a > 12 and b <= 12:
            d, mo = a, b
        elif b > 12 and a <= 12:
            d, mo = b, a
        else:
            d, mo = (a, b) if v.day_first else (b, a)
        year = now.year if y is None else (int(y) + 2000 if len(y) == 2 else int(y))
        return _ymd(year, mo, d, now, y is None)
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?", s)
    if m and m.group(2) in v.months:
        y = m.group(3)
        return _ymd(now.year if y is None else int(y), v.months[m.group(2)], int(m.group(1)), now, y is None)
    m = re.fullmatch(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?", s)
    if m and m.group(1) in v.months:
        y = m.group(3)
        return _ymd(now.year if y is None else int(y), v.months[m.group(1)], int(m.group(2)), now, y is None)
    return None


def _ymd(year: int, mo: int, d: int, now: datetime, roll: bool) -> datetime | None:
    try:
        dt = datetime(year, mo, d)
    except ValueError:
        return None
    if roll and dt.date() < now.date():
        try:
            dt = datetime(year + 1, mo, d)
        except ValueError:
            return None
    return dt


def _parse_in(text: str, now: datetime, v: Vocab) -> datetime | None:
    s = _normalize(text, v)
    if not s:
        return None

    d = _duration(s, now, v)
    if d:
        return d

    if s in v.now:
        return now
    if s in v.soon:
        return now + timedelta(hours=1)
    if s in v.next_week:
        return _at(now + timedelta(days=(7 - now.weekday()) % 7 or 7), DEFAULT_TIME)
    if s in v.next_month:
        y, m = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
        return datetime(y, m, 1, *DEFAULT_TIME)
    if s in v.end_of_day:
        dt = _at(now, (17, 0))
        return dt if dt > now else _at(now + timedelta(days=1), (17, 0))
    if s in v.end_of_week:
        dt = _at(now + timedelta(days=(4 - now.weekday()) % 7), (16, 0))
        return dt if dt > now else dt + timedelta(days=7)
    if s in v.weekend:
        return _at(now + timedelta(days=(5 - now.weekday()) % 7 or 7), (10, 0))

    daypart = None
    for key, part in sorted(v.today_parts.items(), key=lambda kv: -len(kv[0])):
        if s == key or s.startswith(key + " "):
            daypart = part
            s = (v.today[0] + " " + s[len(key):]).strip()
            break

    rest, hm, has_time = _split_time(s, v)
    words = rest.split(" ")
    if len(words) > 1 and words[-1] in v.dayparts:
        daypart = daypart or words[-1]
        rest = " ".join(words[:-1])
    words = [w for w in rest.split(" ") if w and w not in v.glue]
    rest = " ".join(words)
    if not has_time and daypart:
        hm = v.dayparts[daypart]
    time_given = has_time or daypart is not None
    hm = hm or DEFAULT_TIME

    if rest == "" and has_time:
        dt = _at(now, hm)
        return dt if dt > now else dt + timedelta(days=1)
    if rest in v.today or rest == "":
        dt = _at(now, hm)
        if dt <= now and not has_time:
            dt += timedelta(days=1)  # "tonight" when the evening has already passed
        return dt
    if rest in v.tomorrow:
        return _at(now + timedelta(days=1), hm)
    if rest in v.day_after:
        return _at(now + timedelta(days=2), hm)

    nxt = False
    for nw in v.next_word:
        if rest.startswith(nw + " "):
            rest = rest[len(nw) + 1:]
            nxt = nw not in ("this",)
            break
    if rest in v.weekdays:
        wd = v.weekdays[rest]
        days = (wd - now.weekday()) % 7
        if nxt and days == 0:
            days = 7
        dt = _at(now + timedelta(days=days), hm)
        if days == 0 and not (time_given and dt > now):
            dt += timedelta(days=7)
        return dt

    base = _date_only(rest, now, v)
    if base is not None:
        return _at(base, hm)
    return None


def parse_when(text: str, now: datetime | None = None, lang: str | None = None) -> datetime | None:
    """Return the moment the text means, or None if it cannot be understood."""
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    for v in _order(lang):
        dt = _parse_in(text, now, v)
        if dt is not None:
            return dt
    return None


# -- buttons and descriptions -----------------------------------------------------------
def quick_options(now: datetime | None = None, lang: str | None = None) -> list[tuple[str, datetime]]:
    """The six quick buttons in the dialog."""
    v = vocab(lang)
    L = v.labels
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    opts = [(L["in_1h"], now + timedelta(hours=1))]
    evening = _at(now, (20, 0))
    if evening - now >= timedelta(minutes=30):
        opts.append((L["tonight"], evening))
    else:
        opts.append((L["tomorrow_evening"], evening + timedelta(days=1)))
    opts.append((L["tomorrow"], _at(now + timedelta(days=1), DEFAULT_TIME)))
    opts.append((L["day_after"], _at(now + timedelta(days=2), DEFAULT_TIME)))
    opts.append((L["monday"], _at(now + timedelta(days=(0 - now.weekday()) % 7 or 7), DEFAULT_TIME)))
    opts.append((L["in_week"], now + timedelta(days=7)))
    return opts


def snooze_options(now: datetime | None = None, lang: str | None = None) -> list[tuple[str, datetime]]:
    v = vocab(lang)
    L = v.labels
    now = (now or datetime.now()).replace(second=0, microsecond=0)
    out = [(L["10min"], now + timedelta(minutes=10)),
           (L["1h"], now + timedelta(hours=1)),
           (L["3h"], now + timedelta(hours=3))]
    evening = _at(now, (20, 0))
    if evening - now >= timedelta(minutes=30):
        out.append((L["tonight_short"], evening))
    out.append((L["tomorrow_short"], _at(now + timedelta(days=1), DEFAULT_TIME)))
    return out


def describe(dt: datetime, now: datetime | None = None, lang: str | None = None) -> str:
    """'morgen 09:00 (over 11 u 30 min)' / 'tomorrow 09:00 (in 11 h 30 min)'."""
    v = vocab(lang)
    now = now or datetime.now()
    day_diff = (dt.date() - now.date()).days
    if day_diff == 0:
        head = v.w_today
    elif day_diff == 1:
        head = v.w_tomorrow
    elif day_diff == 2:
        head = v.w_day_after
    elif 0 < day_diff < 7:
        head = v.weekday_names[dt.weekday()]
    else:
        head = f"{v.weekday_short[dt.weekday()]} {dt.day} {v.month_short[dt.month - 1]}"
        if dt.year != now.year:
            head += f" {dt.year}"
    return f"{head} {dt:%H:%M} ({relative(dt, now, lang)})"


def relative(dt: datetime, now: datetime | None = None, lang: str | None = None) -> str:
    v = vocab(lang)
    now = now or datetime.now()
    secs = int((dt - now).total_seconds())
    if secs < -60:
        past = -secs
        if past < 3600:
            return f"{past // 60} {v.w_min} {v.w_ago}"
        if past < 86400:
            return f"{past // 3600} {v.w_hour} {v.w_ago}"
        return f"{past // 86400} {v.w_days} {v.w_ago}"
    if secs <= 60:
        return v.w_now
    mins = secs // 60
    if mins < 60:
        return f"{v.w_in} {mins} {v.w_min}"
    if mins < 24 * 60:
        h, m = divmod(mins, 60)
        return f"{v.w_in} {h} {v.w_hour} {m} {v.w_min}" if m else f"{v.w_in} {h} {v.w_hour}"
    days, rem = divmod(mins, 24 * 60)
    h = rem // 60
    if days < 7:
        return f"{v.w_in} {days} {v.w_day} {h} {v.w_hour}" if h else f"{v.w_in} {days} {v.w_days}"
    return f"{v.w_in} {days} {v.w_days}"
