class Lesson:
    url = None
    lesson_id = None
    weekday = None
    day = None
    month = None
    start = None
    end = None
    sport = None
    niveau = None
    facility = None
    trainer = None
    enrollment_string = None

    def __repr__(self):
        trainer = self.trainer
        if trainer is None:
            trainer = ""
        facility = self.facility
        if facility[:13] == "Sport Center ":
            facility = facility[13:]
        if facility == "Polyterasse":
            facility = "poly"
        elif facility == "Hönggerberg":
            facility = "höngg"
        elif facility == "Winterthur":
            faclility = "winti"
        return "{:6} | {} {}{} {}-{}\t{:<13}\t{:<14}\t{:<8}\t{:<35}\t{:>15}".format(
            self.lesson_id,
            self.weekday[:2],
            self.day,
            self.month,
            self.start,
            self.end,
            self.sport[:13],
            trainer[:14],
            facility[:8],
            self.niveau[:35],
            self.enrollment_string[:15],
        )


sports = {
    "cycling": "sport:45645",
    "kondi": "sport:45675",
    "yoga": "sport:45750",
    "rowing": "sport:45699",
    "tbow": "sport:45730",
    "mpump": "sport:45686",
    "crossfit": "sport:45643",
    "relax": "sport:245229",
}
weekdays = {
    "mon": "weekday:3999",
    "tue": "weekday:4006",
    "wed": "weekday:4007",
    "thu": "weekday:4002",
    "fri": "weekday:4008",
    "sat": "weekday:4003",
    "son": "weekday:4000",
}
facilities = {
    "irchel": "facility:45577",
    "poly": "facility:45594",
    "move": "facility:45614",
    "cab": "facility:45614",
    "hoengg": "facility:45598",
    "fluntern": "facility:45575",
}
nofitness = "without_fitness=1"

keywords = dict()
keywords.update(sports)
keywords.update(weekdays)
keywords.update(facilities)
keywords["nofitness"] = nofitness
