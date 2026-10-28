import unittest
from datetime import datetime, timedelta

from straks import i18n
from straks import timeparse as tp

# Wednesday 28 October 2026, 21:30
NOW = datetime(2026, 10, 28, 21, 30)


def setUpModule():
    i18n.set_language("nl", persist=False)


def P(text, now=NOW, lang="nl"):
    return tp.parse_when(text, now, lang)


def E(text, now=NOW):
    return tp.parse_when(text, now, "en")


class Durations(unittest.TestCase):
    def test_minutes(self):
        self.assertEqual(P("over 10 min"), NOW + timedelta(minutes=10))
        self.assertEqual(P("10 minuten"), NOW + timedelta(minutes=10))
        self.assertEqual(P("over 5 m"), NOW + timedelta(minutes=5))

    def test_hours(self):
        self.assertEqual(P("over 2 uur"), NOW + timedelta(hours=2))
        self.assertEqual(P("1 uur"), NOW + timedelta(hours=1))
        self.assertEqual(P("over een uur"), NOW + timedelta(hours=1))
        self.assertEqual(P("over half uur"), NOW + timedelta(minutes=30))
        self.assertEqual(P("over een half uur"), NOW + timedelta(minutes=30))
        self.assertEqual(P("anderhalf uur"), NOW + timedelta(minutes=90))
        self.assertEqual(P("over twee uur"), NOW + timedelta(hours=2))

    def test_days_weeks(self):
        self.assertEqual(P("over 3 dagen"), NOW + timedelta(days=3))
        self.assertEqual(P("over een week"), NOW + timedelta(days=7))
        self.assertEqual(P("2 weken"), NOW + timedelta(days=14))

    def test_zero_is_nothing(self):
        self.assertIsNone(P("over 0 min"))


class Days(unittest.TestCase):
    def test_tomorrow(self):
        self.assertEqual(P("morgen"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(P("Morgen 14:00"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(P("morgen om 14.30"), datetime(2026, 10, 29, 14, 30))
        self.assertEqual(P("morgen 14u30"), datetime(2026, 10, 29, 14, 30))
        self.assertEqual(P("morgen om 2"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(P("morgen 9"), datetime(2026, 10, 29, 9, 0))

    def test_dayparts(self):
        self.assertEqual(P("morgenochtend"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(P("morgenmiddag"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(P("morgenavond"), datetime(2026, 10, 29, 20, 0))
        self.assertEqual(P("morgenavond 21:15"), datetime(2026, 10, 29, 21, 15))
        self.assertEqual(P("vrijdagavond"), datetime(2026, 10, 30, 20, 0))
        self.assertEqual(P("overmorgen"), datetime(2026, 10, 30, 9, 0))

    def test_today_variants(self):
        # 21:30: tonight 20:00 has passed -> tomorrow evening
        self.assertEqual(P("vanavond"), datetime(2026, 10, 29, 20, 0))
        self.assertEqual(P("vanavond", datetime(2026, 10, 28, 17, 0)), datetime(2026, 10, 28, 20, 0))
        self.assertEqual(P("vanmiddag", datetime(2026, 10, 28, 10, 0)), datetime(2026, 10, 28, 14, 0))
        self.assertEqual(P("vanmiddag om 3", datetime(2026, 10, 28, 10, 0)), datetime(2026, 10, 28, 15, 0))
        self.assertEqual(P("vandaag 23:00"), datetime(2026, 10, 28, 23, 0))

    def test_weekdays(self):
        self.assertEqual(P("vrijdag"), datetime(2026, 10, 30, 9, 0))
        self.assertEqual(P("vr 16:00"), datetime(2026, 10, 30, 16, 0))
        self.assertEqual(P("woensdag"), datetime(2026, 11, 4, 9, 0))  # today is Wednesday -> next one
        self.assertEqual(P("woensdag 23:00"), datetime(2026, 10, 28, 23, 0))  # still reachable today
        self.assertEqual(P("ma"), datetime(2026, 11, 2, 9, 0))
        self.assertEqual(P("volgende woensdag"), datetime(2026, 11, 4, 9, 0))

    def test_fixed(self):
        self.assertEqual(P("volgende week"), datetime(2026, 11, 2, 9, 0))
        self.assertEqual(P("volgende maand"), datetime(2026, 11, 1, 9, 0))
        self.assertEqual(P("eind van de dag"), datetime(2026, 10, 29, 17, 0))
        self.assertEqual(P("eind van de dag", datetime(2026, 10, 28, 10, 0)), datetime(2026, 10, 28, 17, 0))
        self.assertEqual(P("eind van de week"), datetime(2026, 10, 30, 16, 0))
        self.assertEqual(P("weekend"), datetime(2026, 10, 31, 10, 0))
        self.assertEqual(P("straks"), NOW + timedelta(hours=1))
        self.assertEqual(P("nu"), NOW)


class Dates(unittest.TestCase):
    def test_numeric(self):
        self.assertEqual(P("31-10"), datetime(2026, 10, 31, 9, 0))
        self.assertEqual(P("31-10 15:00"), datetime(2026, 10, 31, 15, 0))
        self.assertEqual(P("31/10/2026 15:00"), datetime(2026, 10, 31, 15, 0))
        self.assertEqual(P("1-1"), datetime(2027, 1, 1, 9, 0))  # already passed this year -> next year
        self.assertEqual(P("28-10-2026 21:30"), NOW)
        self.assertIsNone(P("31-11"))

    def test_month_names(self):
        self.assertEqual(P("3 nov"), datetime(2026, 11, 3, 9, 0))
        self.assertEqual(P("3 november 14:00"), datetime(2026, 11, 3, 14, 0))
        self.assertEqual(P("3 nov 2027"), datetime(2027, 11, 3, 9, 0))
        self.assertEqual(P("5 mei"), datetime(2027, 5, 5, 9, 0))


class Times(unittest.TestCase):
    def test_bare_time(self):
        self.assertEqual(P("22:00"), datetime(2026, 10, 28, 22, 0))
        self.assertEqual(P("14:00"), datetime(2026, 10, 29, 14, 0))  # passed -> tomorrow
        self.assertEqual(P("9u"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(P("om 22"), datetime(2026, 10, 28, 22, 0))
        self.assertEqual(P("om 1 uur"), datetime(2026, 10, 29, 13, 0))
        self.assertEqual(P("23.15"), datetime(2026, 10, 28, 23, 15))

    def test_garbage(self):
        for s in ("", "   ", "blabla", "25:00", "morgen 99:99", "over", "nooit"):
            self.assertIsNone(P(s), s)

    def test_zo_is_sunday(self):
        self.assertEqual(P("zo"), datetime(2026, 11, 1, 9, 0))
        self.assertEqual(P("zometeen"), NOW + timedelta(hours=1))


class English(unittest.TestCase):
    def test_durations(self):
        self.assertEqual(E("in 10 min"), NOW + timedelta(minutes=10))
        self.assertEqual(E("in 2 hours"), NOW + timedelta(hours=2))
        self.assertEqual(E("in an hour"), NOW + timedelta(hours=1))
        self.assertEqual(E("in half an hour"), NOW + timedelta(minutes=30))
        self.assertEqual(E("in 1.5 hours"), NOW + timedelta(minutes=90))
        self.assertEqual(E("3 days"), NOW + timedelta(days=3))
        self.assertEqual(E("in a week"), NOW + timedelta(days=7))
        self.assertEqual(E("2 wks"), NOW + timedelta(days=14))

    def test_days(self):
        self.assertEqual(E("tomorrow"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(E("Tomorrow 2pm"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(E("tomorrow at 2:30pm"), datetime(2026, 10, 29, 14, 30))
        self.assertEqual(E("tomorrow at 9"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(E("tomorrow at 3"), datetime(2026, 10, 29, 15, 0))
        self.assertEqual(E("tomorrow morning"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(E("tomorrow evening"), datetime(2026, 10, 29, 20, 0))
        self.assertEqual(E("tomorrow at noon"), datetime(2026, 10, 29, 12, 0))
        self.assertEqual(E("day after tomorrow"), datetime(2026, 10, 30, 9, 0))
        self.assertEqual(E("the day after tomorrow 10am"), datetime(2026, 10, 30, 10, 0))
        self.assertEqual(E("tonight", datetime(2026, 10, 28, 17, 0)), datetime(2026, 10, 28, 20, 0))
        self.assertEqual(E("this afternoon", datetime(2026, 10, 28, 10, 0)), datetime(2026, 10, 28, 14, 0))
        self.assertEqual(E("today 11pm"), datetime(2026, 10, 28, 23, 0))

    def test_weekdays_and_fixed(self):
        self.assertEqual(E("friday"), datetime(2026, 10, 30, 9, 0))
        self.assertEqual(E("fri 4pm"), datetime(2026, 10, 30, 16, 0))
        self.assertEqual(E("on friday at 4pm"), datetime(2026, 10, 30, 16, 0))
        self.assertEqual(E("friday evening"), datetime(2026, 10, 30, 20, 0))
        self.assertEqual(E("wednesday"), datetime(2026, 11, 4, 9, 0))
        self.assertEqual(E("next wednesday"), datetime(2026, 11, 4, 9, 0))
        self.assertEqual(E("next week"), datetime(2026, 11, 2, 9, 0))
        self.assertEqual(E("next month"), datetime(2026, 11, 1, 9, 0))
        self.assertEqual(E("end of day"), datetime(2026, 10, 29, 17, 0))
        self.assertEqual(E("eod", datetime(2026, 10, 28, 10, 0)), datetime(2026, 10, 28, 17, 0))
        self.assertEqual(E("end of the week"), datetime(2026, 10, 30, 16, 0))
        self.assertEqual(E("this weekend"), datetime(2026, 10, 31, 10, 0))
        self.assertEqual(E("now"), NOW)
        self.assertEqual(E("later"), NOW + timedelta(hours=1))

    def test_dates_and_times(self):
        self.assertEqual(E("nov 3"), datetime(2026, 11, 3, 9, 0))
        self.assertEqual(E("3 nov"), datetime(2026, 11, 3, 9, 0))
        self.assertEqual(E("november 3rd 2pm"), datetime(2026, 11, 3, 14, 0))
        self.assertEqual(E("nov 3 2027"), datetime(2027, 11, 3, 9, 0))
        self.assertEqual(E("11/3"), datetime(2026, 11, 3, 9, 0))      # English: month/day
        self.assertEqual(E("31/10"), datetime(2026, 10, 31, 9, 0))    # 31 cannot be a month
        self.assertEqual(E("10pm"), datetime(2026, 10, 28, 22, 0))
        self.assertEqual(E("9am"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(E("12am"), datetime(2026, 10, 29, 0, 0))
        self.assertEqual(E("at 9"), datetime(2026, 10, 29, 9, 0))
        self.assertEqual(E("14:00"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(E("9h"), NOW + timedelta(hours=9))

    def test_cross_language_fallback(self):
        self.assertEqual(E("morgen 14:00"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(P("tomorrow 2pm"), datetime(2026, 10, 29, 14, 0))
        self.assertEqual(P("in 2 hours"), NOW + timedelta(hours=2))

    def test_describe_english(self):
        self.assertEqual(tp.describe(datetime(2026, 10, 29, 9, 0), NOW, "en"), "tomorrow 09:00 (in 11 h 30 min)")
        self.assertEqual(tp.describe(datetime(2026, 11, 2, 9, 0), NOW, "en"), "monday 09:00 (in 4 d 11 h)")
        self.assertEqual(tp.describe(datetime(2026, 11, 20, 9, 0), NOW, "en"), "fri 20 nov 09:00 (in 22 days)")
        self.assertEqual(tp.describe(datetime(2026, 10, 28, 20, 0), NOW, "en"), "today 20:00 (1 h ago)")
        labels = [l for l, _ in tp.quick_options(NOW, "en")]
        self.assertEqual(labels[0], "In 1 hour")
        for label, dt in tp.quick_options(NOW, "en"):
            self.assertEqual(tp.parse_when(label, NOW, "en"), dt, label)
        for label, dt in tp.snooze_options(NOW, "en"):
            self.assertEqual(tp.parse_when(label, NOW, "en"), dt, label)


class Describe(unittest.TestCase):
    def test_describe(self):
        D = lambda dt: tp.describe(dt, NOW, "nl")  # noqa: E731
        self.assertEqual(D(datetime(2026, 10, 28, 22, 0)), "vandaag 22:00 (over 30 min)")
        self.assertEqual(D(datetime(2026, 10, 29, 9, 0)), "morgen 09:00 (over 11 u 30 min)")
        self.assertEqual(D(datetime(2026, 10, 30, 20, 0)), "overmorgen 20:00 (over 1 d 22 u)")
        self.assertEqual(D(datetime(2026, 11, 2, 9, 0)), "maandag 09:00 (over 4 d 11 u)")
        self.assertEqual(D(datetime(2026, 11, 20, 9, 0)), "vr 20 nov 09:00 (over 22 dagen)")
        self.assertEqual(D(datetime(2027, 1, 1, 9, 0)), "vr 1 jan 2027 09:00 (over 64 dagen)")
        self.assertEqual(D(datetime(2026, 10, 28, 20, 0)), "vandaag 20:00 (1 u geleden)")

    def test_quick_options(self):
        opts = dict(tp.quick_options(NOW, "nl"))
        self.assertEqual(opts["Over 1 uur"], NOW + timedelta(hours=1))
        self.assertEqual(opts["Morgenavond 20:00"], datetime(2026, 10, 29, 20, 0))
        self.assertEqual(opts["Maandag 09:00"], datetime(2026, 11, 2, 9, 0))
        early = dict(tp.quick_options(datetime(2026, 10, 28, 10, 0), "nl"))
        self.assertEqual(early["Vanavond 20:00"], datetime(2026, 10, 28, 20, 0))
        self.assertEqual(len(tp.quick_options(NOW, "nl")), 6)

    def test_every_quick_label_parses_too(self):
        for label, dt in tp.quick_options(NOW, "nl") + tp.snooze_options(NOW, "nl"):
            parsed = tp.parse_when(label, NOW, "nl")
            self.assertIsNotNone(parsed, label)
            self.assertEqual(parsed, dt, label)

    def test_active_language_is_used_by_default(self):
        i18n.set_language("en", persist=False)
        try:
            self.assertEqual(tp.describe(datetime(2026, 10, 29, 9, 0), NOW), "tomorrow 09:00 (in 11 h 30 min)")
            self.assertEqual(tp.quick_options(NOW)[0][0], "In 1 hour")
        finally:
            i18n.set_language("nl", persist=False)


if __name__ == "__main__":
    unittest.main()
