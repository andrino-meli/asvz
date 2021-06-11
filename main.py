#!/usr/bin/env python3

# TODO: licence
# TODO: disclamer
import sys, os
import selenium
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from fuzzywuzzy.fuzz import ratio
from time import sleep
import threading

# definitions and settings
debug = False
if debug:
    import timeit
headless = False  # TODO = not debug # in the release
QUERYSIZE = 20
options = Options()
# config_dir = os.path.expanduser("user-data-dir=~/.config//")
options.add_argument(
    "--user-data-dir=" + os.path.expanduser("~/.config/chromium")
)  # cookie storage
options.add_argument("--app=")
options.add_argument("--blink-settings=imagesEnabled=false")

# setup browser driver (namely chromiumdriver)
if headless:
    options.add_argument("--headless")
try:
    global driver
    driver = webdriver.Chrome(options=options)  # uses chromedriver per default
    driver.implicitly_wait(0)
except selenium.common.exceptions.InvalidArgumentException as ex:
    if "--user-data-dir" in ex.msg:
        # driver.close() #TODO: make this work somehow
        print("Error: Only one instance of asvz can run. Allready running.")
        quit(117)  # TODO: make exit values less random? / actually return an exit value
        # maybee use sys.exit() or os.exit()?


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
        if facility[:13] == 'Sport Center ':
            facility = facility[13:]
        if facility == "Polyterasse":
            facility = 'poly'
        elif facility == "Hönggerberg":
            facility = 'höngg'
        elif facility == "Winterthur":
            faclility = 'winti'
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
    "cycling":  "sport:45645",
    "kondi":    "sport:45675",
    "yoga":     "sport:45750",
    "rowing":   "sport:45699",
    "tbow":     "sport:45730",
    "mpump":    "sport:45686",
    "crossfit": "sport:45643",
    "relax":    "sport:245229",
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
    "irchel":   "facility:45577",
    "poly":     "facility:45594",
    "move":     "facility:45614",
    "cab":      "facility:45614",
    "hoengg":   "facility:45598",
    "fluntern": "facility:45575",
}
nofitness = "without_fitness=1"

keywords = dict()
keywords.update(sports)
keywords.update(weekdays)
keywords.update(facilities)

# helper function to make code more readable
def wait_for_element(attribute, string, multiple=False, timeout=15):
    if debug:
        print(
            "waiting for element:",
            attribute,
            string,
            ". Timeout =",
            timeout,
            " seconds.",
        )
    if multiple:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((attribute, string))
        )
    else:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((attribute, string))
        )
    return element


def wait_for_elements(attribute, string, timeout=15):
    return wait_for_element(attribute, string, multiple=True, timeout=timeout)


def wait_for_clickable(attribute, string, timeout=15):
    button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((attribute, string))
    )
    return button


# query offers and parse
## this might seem very cryptic and it is because we reverse engineere the parsing
## from the data structure presented in the html. Which is quite arbitrary.
def query_trainings(url):
    global driver
    driver.get(url)
    sleep(0.3)  # required for website elements to not go stale (loading time)
    trainings = []
    # find all days where we have offers
    try:
        for daytable in wait_for_elements(
            By.CLASS_NAME, "teaser-list-calendar__container"
        ):
            try:
                weekday = daytable.find_element_by_class_name("day").text
                day = daytable.find_element_by_class_name("date").text
                month = daytable.find_element_by_class_name("month").text
                # find all offers coresponding to this day - each offer has a
                # link
                for offer in daytable.find_elements_by_tag_name(
                    "a"
                ):  # TODO: check that no further check on links is necessary
                    # offer.find_element_by_class_name("offer__time")
                    # do magic parsing - again reverse engineered from
                    # the given output string in the html
                    l = Lesson()
                    (l.weekday, l.day, l.month) = (weekday, day, month)
                    l.url = offer.get_attribute("href")
                    l.lesson_id = l.url[-6:]
                    split = offer.text.split("\n")
                    if debug:
                        print(len(split),split)
                    l.start = split[0]
                    l.end = split[1][-5:]
                    l.sport = split[2]
                    l.niveau = split[3]
                    l.facility = split[4]
                    index_shift = 1
                    if split[5].isnumeric():
                        index_shift = 0
                        #unleaded training
                    else:
                        l.trainer = split[5]
                    opt = split[5 + index_shift]
                    enrollmnt_option = ""
                    if opt == "Keine freien":
                        enrollmnt_option = "fully booked"
                    elif opt == "Einschreiben möglich":
                        enrollmnt_option = "window not open"
                    elif opt.isnumeric() and split[6+index_shift] == "freie Plätze":
                        enrollmnt_option = opt + " slots"
                    l.enrollment_string = enrollmnt_option
                    trainings.append(l)
                    if len(trainings) >= QUERYSIZE:
                        raise IndexError("query limit")
                    print(l)
            except (NoSuchElementException):
                # TODO: open browser interactively to let user fix himself
                pass
    except IndexError as er:
        if str(er) != "query limit":
            raise er
        else:
            return trainings

def print_help():
    print(
        '\
        This asvz helper can be run interactively or not.\n\
        In interactive mode one can type commands repeatedly and crossreference\n\
        for example querys easily.\n\
        In noninteractive mode one gives the command as a command line argument.\n\
\n\
        Note that this tool heavily relies on browser cahce for password storage.\n\
        Therefor the first time one is required to login in ASVZ manually. Further logins\n\
        are done by this application by itself with coockies. NOTE however from time\n\
        to time these get invalid and one is simply not allowed to enroll anymore\n\
        due to "missing membership". Then simply log out and in again manually.\n\
        This is maybee a bit tedious but does not require saving ETHZ credentials.\n\
\n\
        available commands:\n\
        ===================\n\
        help                    prints this help message\n\
        list                    \n\
        query KEYWORDS          searches for trainings according to keywords\n\
        dict                    prints a dictionary of available KEYWORDS to query for.\n\
        enroll LESSON           enrolls for a lesson given its lesson id\n\
        deroll LESSON           removes subscription from lesson\n\
        q | q | ^D | ^C         quits interaction\
    '
    )


def query_inscribed():
    url = "https://schalter.asvz.ch/tn/my-lessons"
    driver.get(url)
    try:
        table = wait_for_element(By.TAG_NAME, "table")
        trainings = table.find_elements_by_tag_name("tr")[1:]
        if len(trainings) < 1:
            print("no enrollments")
            return
        for t in trainings:
            lesson_id = t.find_element_by_tag_name("a").get_attribute("href")[-6:]
            print(
                lesson_id, "\t", t.text.replace("\n", "\t")
            )  # TODO: print place number
    except TimeoutException:
        print("Error: page not loeaded")


def create_listener(lesson_id, window):
    print(lesson_id, window)

def lesson_enroll(lesson_id, enroll):
    global driver
    url = "https://schalter.asvz.ch/tn/lessons/" + str(lesson_id)
    driver.get(url)
    try:
        if driver.current_url != url:
            driver.get(url)
        try:
            button = wait_for_element(By.ID, "btnRegister")
            if button.text == "FÜR LEKTION EINSCHREIBEN" and enroll:
                # if disabled create a listener that inscribes later
                if "disabled" in button.get_attribute("class").split():
                    prop = driver.find_element_by_class_name(
                        "event-properties"
                    ).text.split("\n")
                    throwaway = iter(prop)
                    # TODO: implement room
                    while next(throwaway) != "Anmeldezeitraum":
                        pass
                    inscribe_window = next(throwaway)
                    create_listener(lesson_id, inscribe_window[:20])
                else:
                    # directly click at button
                    button.click()
            elif button.text == "FÜR LEKTION EINSCHREIBEN" and not enroll:
                print("You are not enrolled. Use `list` command.")
            elif button.text == "EINSCHREIBUNG FÜR LEKTION ENTFERNEN" and enroll:
                print("You are allready enrolled. Use `list` command.")
            elif button.text == "EINSCHREIBUNG FÜR LEKTION ENTFERNEN" and not enroll:
                button.click()
                ok = wait_for_clickable(
                    By.XPATH, "//app-lessons-enrollment-button//button[text()='Ok']"
                )
                ok.click()
        except NoSuchElementException:
            print("acction not possible")
        finally:
            try:
                allert = wait_for_element(By.CLASS_NAME, "alert", timeout=2)
                allert_msg = ''
                for i in allert.text.split("\n"):
                    if i != 'x' and i != 'Close':
                        allert_msg = i 
                print(allert_msg)
            except TimeoutException:
                pass
    except TimeoutException:
        print("credentials not cached - retry enrollment again after login")
        button = wait_for_element(By.XPATH, '//button[@title="Login"]', timeout=2)
        button.click()
        # check if we are redirected to auth.asvz.ch (so no cached credentials)
        sleep(2)
        curl = driver.current_url
        auth_url = "https://auth.asvz.ch/account/login"
        if curl[: len(auth_url)] == auth_url:
            print("LOGIN REQUIRED - opening browser - pls. login manually.")
            options = Options()
            options.add_argument(
                "--user-data-dir=" + os.path.expanduser("~/.config/chromium")
            )  # cookie storage
            options.add_argument("--app=" + auth_url)
            # TODO: check and make login easier
            if headless:
                driver.close()
                driver = webdriver.Chrome(options=options)
                driver.get(auth_url)
            while driver.current_url != "https://auth.asvz.ch/Manage/Index":
                sleep(0.5)
            # strange but we have to relogin to save the cookie
            driver.get(url)
            button = driver.find_element_by_xpath('//button[@title="Login"]')
            button.click()
            print("Manuall Login Successfull!")
            if headless:
                driver.close()
                options = Options().headless = True
                driver = webdriver.Chrome(options=options)
            # This is strange but has to bee done (so click login again).
            lesson_enroll(lesson_id, enroll) #TODO: recursion might be dangerous (!) maybee find a better syntax


def quit_asvz():
    # only quit if no deamons are running, otherwise prompt
    exiting = True
    if len(lessonThreads) != 0:
        ans = input("Error: deamons running trying to enroll, exit anyway [y/N]?")
        if ans != 'Y' and ans != 'Y':
            #TODO: one can forcefully exit alternatively
            signalQuit.update(lessonThreads) # tell all threads to exit
            for i in lessonThreds:
                i.join()
            exiting = False
    if exiting:
        driver.close()
        print("Happy sporting.")

threads = {}
driverLock = threading.Lock()

class enrollThread(threading.Thread):
    def __init__(self, lesson_id, start, stop):
        self.doStop = False
        self.lesson_id = lesson_id
        self.start = start #window start
        self.stop = stop #window stop
        self.setDaemon(True)

    def __str__(self):
        return f'{self.lesson_id} enrollment Thread in window: {self.start}:{self.stop}.'

    def start(self):
        threads.add(self)
        self.run()

    def terminate(self):
        self.dostop = True

    def run(self):
        # check window
        while(not start):
            if self.doStop:
                self.exit()
            sleep(5)
        # acquire driver lock
        driverLock.acquire()
        # lesson_enroll(lesson_id, release lock
        # release and exit
        driverLock.release()
        threads.remove(self)




if __name__ == "__main__":
    interactive = True
    command = None
    # TODO: argument checking for sanity
    if len(sys.argv) > 1:
        interacive = False
        command = sys.argv[1:]
    while True:
        if interactive:
            try:
                command = input("> ").split(" ")
            except EOFError:
                print("^D", end="")
                quit_asvz()
                break
            except KeyboardInterrupt:
                #hard exit TODO: consider soft exit
                break
        if command[0] == "list":
            query_inscribed()
        elif command[0] == "query":
            # calculate url given the arguments and using the keyword dict.
            url = "https://asvz.ch/426-sportfahrplan?"
            i = 0
            corrected = False
            args = command[1:]
            correction = "query "
            # TODO: make correction bold in text
            # TODO: consider changeing in a correct function for abstraction
            url += 'f[0]=type:3997&' # only show lessons (not events, ...) #TODO ? maybee change - parsing is the problem here
            for i in range(1,len(args)+1):
                arg = args[i-1].lower()  # be case insensitive
                # fuzzy match argument and correct to known key
                if arg not in keywords:
                    best = 0
                    key = arg
                    for k in keywords.keys():
                        b = ratio(k, arg)
                        if b > best:
                            key = k
                            best = b
                            corrected = True
                    args[i] = key
                url += "f[" + str(i) + "]=" + keywords[args[i-1]] + "&"
            url += nofitness  # TODO: make an option
            if corrected:
                print("corrected:\tquery", *args)
            if debug:
                print(url)
            trainings = query_trainings(url)
        elif command[0] == "dict":
            print("sports:\t\t", *list(sports.keys()))
            print("facilities:\t", *list(facilities.keys()))
            print("weekdays:\t", *list(weekdays.keys()))
            # TODO add time and date?
        elif command[0] == "enroll" or command[0] == "deroll":
            for l in command[1:]:
                try:
                    if len(l) != 6:
                        raise ValueError("provided lesson has not 6 digits")
                    lesson_enroll(l, command[0] == "enroll")
                except ValueError:
                    print("Error: provided lesson id is not 6 digits")
        elif command[0] == "quit" or command[0] == "q":
            quit_asvz()
            break
        else:
            print_help()
        if not interactive:
            break
