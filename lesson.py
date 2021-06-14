from fuzzywuzzy.fuzz import ratio
from debug import *


class QueryException(Exception):
    pass


sports = {
    "cycling": "sport:45645",
    "kondi": "sport:45675",
    "yoga": "sport:45750",
    "rowing": "sport:45699",
    "tbow": "sport:45730",
    "mpump": "sport:45686",
    "crossfit": "sport:45643",
    "relax": "sport:245229",
    "jazz": "sport:45664"
}
weekdays = {
    "mon": "weekday:3999",
    "tue": "weekday:4006",
    "wed": "weekday:4007",
    "thu": "weekday:4002",
    "fri": "weekday:4008",
    "sat": "weekday:4003",
    "son": "weekday:4000",
    "mo": "weekday:3999",
    "di": "weekday:4006",
    "mi": "weekday:4007",
    "do": "weekday:4002",
    "fr": "weekday:4008",
    "sa": "weekday:4003",
    "so": "weekday:4000",
}
facilities = {
    "irchel": "facility:45577",
    "poly": "facility:45594",
    "move": "facility:45614",
    "cab": "facility:45614",
    "hoengg": "facility:45598",
    "fluntern": "facility:45575",
}

# keywords not in the f[i]=keyword notation
nolist = {"nofitness": "without_fitness=1"}
keywords = dict()
keywords.update(sports)
keywords.update(weekdays)
keywords.update(facilities)
keywords.update(nolist)


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
        return "{:6} | {} {}{} {}-{}\t{:<13}\t{:<16}\t{:<12}\t{:<35}\t{:>15}".format(
            self.lesson_id,
            self.weekday[:2],
            self.day,
            self.month,
            self.start,
            self.end,
            self.sport[:13],
            trainer[:16],
            facility[:12],
            self.niveau[:35],
            self.enrollment_string[:15],
        )


# TODO add time and date?
def keyword_show():
    print("sports:\t\t", *list(sports.keys()))
    print("facilities:\t", *list(facilities.keys()))
    print("weekdays:\t", *list(weekdays.keys()))
    others = set(keywords.keys())
    others.difference_update(set(sports.keys()))
    others.difference_update(set(facilities.keys()))
    others.difference_update(set(weekdays.keys()))
    print("others:\t\t", *list(others))


# given a list of keywords (args) match them to the keyword dictionary and
# build a query url from it and return the url.
# To alloow easier ussage we allow fuzzy matching
def match_keywords(args):
    url = "https://asvz.ch/426-sportfahrplan?"
    url += "f[0]=type:3997"  # only show lessons (not events, ...) #TODO ? maybee change - parsing is the problem here
    corrected = False
    correction = "keywords corrected:"
    # TODO: make correction bold in text
    i = 1
    for arg in args:
        # be case insensitive
        arg = arg.lower()
        if arg == '':
            continue
        # fuzzy match argument and correct to known key
        if arg not in keywords:
            best = 0
            key = None
            for k in keywords.keys():
                b = ratio(k, arg)
                if b > best and b > 60:
                    key = k
                    best = b
                    corrected = True
            if key is None:
                raise QueryException('query key "' + arg + '" is invalid')
            else:
                correction += " " + arg + " -> " + key
            arg = key
        if arg not in nolist:
            url += "&f[" + str(i) + "]=" + keywords[arg]
            i += 1
        else:
            url += "&" + nolist[arg]
    return (
        url,
        corrected,
        correction + "\t If this is not desired consider calling `dict`.",
    )


# given a lesson l with date und url allready given
# add the rest of the information of split to l
# Basially this is a helper function mangeling the website content
# in its strage format to a lesson object with trainer, date, ...
# Most of this is reverse engineering - if you are required to understand this
# run a query with DEBUG=True to show the split list for each lesson.
def from_split(l, split):
    l.start = split[0]
    l.end = split[1][-5:]
    l.sport = split[2]
    l.niveau = split[3]
    l.facility = split[4]
    enrollmnt_option = ""
    num = None
    if "Abgesagt" in split:
        enrollmnt_option = "canceled"
    else:
        if split[5].isnumeric():
            # unleaded training
            num = split[5]
            opt = split[6]
        elif split[5] == "Keine freien":
            opt = split[5]
        else:
            l.trainer = split[5]
            if split[6].isnumeric():
                num = split[6]
                opt = split[7]
            else:
                opt = split[6]
        if opt == "Keine freien":
            enrollmnt_option = "fully booked"
        elif opt == "Einschreiben möglich":
            enrollmnt_option = "window not open"
        elif opt == "freie Plätze" or opt == "freier Platz":
            enrollmnt_option = num + " slots"
    l.enrollment_string = enrollmnt_option
    return l
