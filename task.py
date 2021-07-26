import threading, pyperclip, sys, pickle, errno
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import (
    sleep,
    time,
    mktime,
    strptime,
    localtime,
    strftime,
    struct_time,
    asctime,
)

import lesson
from localstorage import LocalStorage
from utility import *


def create_driver(headless=HEADLESS, app=not HEADLESS):
    global driver
    options = webdriver.chrome.options.Options()
    options.add_argument("--user-data-dir=" + os.path.expanduser("~/.config/chromium"))
    options.add_argument("--disable-extensions")
    if headless:
        options.add_argument("--headless")
    if app:
        options.add_argument("--app")
    try:
        debug_print(f"starting chrome with {options}")
        driver = webdriver.Chrome(options=options)  # uses chromedriver per default
        driver.implicitly_wait(0)
        # set login token
        driver.get(RANDOM_URL)
        storage = LocalStorage(driver)
        sleep(1)
        if os.path.exists(os.path.expanduser("~/.cache/asvz/tk")):
            cfile = open(os.path.expanduser("~/.cache/asvz/tk"), "rb")
            token = pickle.load(cfile)
            (k, v) = token
            storage.set(k, v)
            debug_print(f"set login token {k}")
            cfile.close()
        else:
            warn_print("no login token found: run `login` first")
        return driver
    except InvalidArgumentException as ex:
        if "--user-data-dir" in ex.msg:
            # driver.close() #TODO: make this work somehow
            print("Error: Only one instance of asvz can run. Allready running.")
            sys.exit(114)
        else:
            raise ex


def close_driver():
    driver.close()


# setup browser driver (namely chromiumdriver)
driver = create_driver()

# helper function to make code more readable
def wait_for_element(attribute, string, multiple=False, timeout=15):
    if DEBUG:
        debug_print(
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


def safe_page_load(url):
    if DEBUG:
        debug_print("safe load", url)
    if driver.current_url == url:
        tmp = driver.find_element_by_xpath("/html")
        driver.get(url)
        WebDriverWait(driver, 2).until(EC.staleness_of(tmp))
    else:
        driver.get(url)
        while driver.current_url != url and LOGIN_URL not in driver.current_url:
            sleep(0.3)
    if LOGIN_URL in driver.current_url:
        if DEBUG:
            warn_print("redirected to login during opening of: ", url)
        raise LoginRequiredException("Redirected to the login page")
    sleep(0.3)


####### Task Function Definitions #############
# these functions are ment to be put in the task list

# query offers, parse and print
## this might seem very cryptic and it is because we reverse engineere the parsing
## from the data structure in the website. Which is quite arbitrary and also
## depends quite a bit on scripting.
QUERYSIZE = 20


def query_trainings(url):
    safe_page_load(url)
    trainings = []
    try:
        # find all days where we have offers
        for daytable in wait_for_elements(
            By.CLASS_NAME, "teaser-list-calendar__container"
        ):
            try:
                weekday = daytable.find_element_by_class_name("day").text
                day = daytable.find_element_by_class_name("date").text
                month = daytable.find_element_by_class_name("month").text
                # find all offers coresponding to this day and parse them into
                # a lesson object
                for offer in daytable.find_elements_by_tag_name(
                    "a"
                ):  # TODO: check that no further check on links is necessary
                    # offer.find_element_by_class_name("offer__time")
                    # do magic parsing - again reverse engineered from
                    # the given output string in the html
                    l = lesson.Lesson()
                    (l.weekday, l.day, l.month) = (weekday, day, month)
                    l.url = offer.get_attribute("href")
                    l.lesson_id = l.url[-6:]
                    split = offer.text.split("\n")
                    if QUERY_DEBUG:
                        debug_print(len(split), split)
                    try:
                        l = lesson.from_split(l, split)
                        trainings.append(l)
                        prompt_print(l)
                    except IndexError:
                        # some other format we don't know - as a backup solution just print split
                        trainings.append(l)
                        prompt_print(
                            "{:6} | {} {}{}\t".format(
                                self.lesson_id, self.weekday[:2], self.day, self.month
                            ),
                            *split,
                        )
                    if len(trainings) >= QUERYSIZE:
                        raise IndexError("query limit")
            except (NoSuchElementException):
                # TODO: open browser interactively to let user fix himself
                pass
    except IndexError as er:
        if str(er) != "query limit":
            raise er


def query_inscribed():
    url = "https://schalter.asvz.ch/tn/my-lessons"
    safe_page_load(url)
    try:
        table = wait_for_element(By.TAG_NAME, "table")
        trainings = table.find_elements_by_tag_name("tr")[1:]
        if len(trainings) < 1:
            prompt_print("no enrollments")
            return
        for t in trainings:
            lesson_id = t.find_element_by_tag_name("a").get_attribute("href")[-6:]
            prompt_print(
                lesson_id, "\t", t.text.replace("\n", "\t")
            )  # TODO: print place number
    except TimeoutException:
        prompt_print("Error: page not loaded")


def lesson_properties(lesson_id, show=False, copy=False):
    url = "https://schalter.asvz.ch/tn/lessons/" + lesson_id
    safe_page_load(url)
    # parse EVentPRoperties
    evpr = wait_for_element(By.TAG_NAME, "app-lesson-properties-display")
    evpr = evpr.find_elements_by_tag_name("dl")
    properties = {}
    for p in evpr:
        name = p.find_element_by_tag_name("dt").text
        value = [x.text for x in p.find_elements_by_tag_name("dd")]
        if len(value) == 1:  # if only one element move out of list
            value = value[0]
        if name == "Anmeldezeitraum":
            (winopen, winclose) = value.split(" - ")
            properties["winopen"] = mktime(strptime(winopen[4:], DATE_FMT))
            properties["winclose"] = mktime(strptime(winclose[4:], DATE_FMT))
        elif name == "Abmeldefrist":
            properties["derolldue"] = mktime(strptime(value, DATE_FMT))
        else:
            properties[name] = value

    # debug print
    if PROPERTIES_DEBUG:
        debug_print(properties)

    # generate a string representation of the properties for printing
    # or for copy to clipboard
    if show or copy:
        string = url + "\n"
        for k, v in properties.items():
            if k in [
                "Versicherung",
                "Unterrichtssprache",
                "Nummer",
            ]:
                pass
            elif k in ["winopen", "winclose", "derolldue"]:
                v = strftime(A_DATE_FMT, localtime(v))
                string += "{:<20}:    {}\n".format(k, v)
            else:
                string += "{:<20}:    {}\n".format(k, v)
        if copy:
            pyperclip.copy(string)
            prompt_print("copied propertie of lesson to clipboard")
        if show:
            prompt_print(string)

    # return dictionary
    if not show and not copy:
        return properties


def check_for_free_seat(lesson_id, stop):
    if DEBUG:
        debug_print(f"check for free seat in {lesson_id} stop at {localtime(stop)}.")
    seats = lesson_properties(lesson_id)["Freie Plätze"]
    if seats.isdecimal():
        if time() > stop:
            return
        elif int(seats) > 0:
            t = Task(lesson_enroll, [lesson_id, True], imediate=True)
            if DEBUG:
                debug_print(f"adding follow up: {t.function}")
        else:
            start = time() + POLL_INTERVALL
            t = Task(check_for_free_seat, [lesson_id, stop], start=start, stop=stop)
            if DEBUG:
                debug_print(f"adding follow up: {t.function}")

    else:
        raise Exception('Error, "Freie Plätze" is not a number.')


def check_window(lesson_id, enroll):
    properties = lesson_properties(lesson_id)
    # check weather the task can be executed immediately
    if enroll:
        (winopen, winclose) = (properties["winopen"], properties["winclose"])
        # TODO: add padding for time checking?
        if time() < winopen:
            # request creation of a task but with a window instead of imediate
            Task(
                lesson_enroll, [lesson_id, "enroll=True"], start=winopen, stop=winclose
            )
            warn_print(
                f"enrollment window not open, created background task for {RESET}{BOLD}{lesson_id}{RESET}{YELLOW}. Consider calling `task` or `cancel`.{RESET}"
            )
        elif winclose < time():
            prompt_print("Eror: enrollment window for {lesson_id} allready closed.")
        else:
            lesson_enroll(lesson_id, enroll)
    else:
        if properties["derolldue"] < time():
            prompt_print(
                f"Eror: to late to deroll from {lesson_id}. Risk \
            evaluation: currently {properties['Freie Plätze']} seats are free \
            and {properties['Trainingsleitende']} is your trainer."
            )
        else:
            lesson_enroll(lesson_id, enroll)


def manuall_login(executer):
    """
    Okay this is webtechnology so try to stick with me.
    First we note that a token (similar to a cookie) is saved to identify the user. This token is
    saved in three places: the browser local storage in headless and headfull
    mode and in a token file in ~/.cache/asvz/tk.

    Whever we login in manually in the headfull browser the token gets writen
    to file and from there loaded in headless mode. In priciple the chromium user-data-dir
    should fix this issue but somehow does not.
    """
    global driver
    manuall_logout()
    warn_print("LOGIN REQUIRED, opening browser. Do standby.")
    # stop the executer
    executer.doStop = True
    close_driver()
    create_driver(headless=False)
    driver.get(RANDOM_URL)
    try:
        button = wait_for_element(By.XPATH, '//button[@title="Login"]', timeout=5)
        button.click()
        warn_print("Login manually in the opened browser window and wait for redirect.")
        while "https://auth.asvz.ch/account/login?" not in driver.current_url:
            sleep(0.5)  # wait until we are surely redirected
        # wait for manuall action by the user
        while driver.current_url != random_url:
            sleep(0.5)
    except TimeoutException:
        debug_print(
            f"Can not find a 'Login' button. Maybee we are allready loged in. Contine trying to save token."
        )
    # save login tokens from the Web Storage API local storage
    storage = LocalStorage(driver)
    token = None
    debug_print(type(storage.items()), storage)
    for k in storage.keys():  # items() does somehow not work!
        v = storage.get(k)
        debug_print(f"localstorage {k}: {v}")
        if "oidc.user:https://auth.asvz.ch:" in k:
            token = (k, v)
    if token is None:
        prompt_print("{RED}Manuall Login Failed - no token generated!")
        return
    cpath = os.path.expanduser("~/.cache/asvz/tk")
    if not os.path.exists(os.path.dirname(cpath)):  # check parent-dir exist
        try:
            os.makedirs(os.path.dirname(cpath))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    cfile = open(cpath, "wb")
    pickle.dump(token, cfile)
    cfile.close()
    # finish
    prompt_print("Manuall Login Successfull!")
    close_driver()  # close the headfull driver
    create_driver()
    # TODO: wow this is hacky: how about a true server client model - also for
    # synchronized in and output?
    debug_print("deleting the executer")  # let main restart the taskExecuter
    del executer


def manuall_logout():
    """Logs out manually from asvz webapp.
    Clears the token file on disk as well as all local storage
    for the headless browser session.
    Does not clear the local storage for the headfull browser session (for
    unknown reason).
    """
    global driver
    storage = LocalStorage(driver)
    driver.get("https://schalter.asvz.ch")
    sleep(2)
    storage.clear()
    debug_print("Cleared local storage.")
    cpath = os.path.expanduser("~/.cache/asvz/tk")
    if os.path.exists(cpath):  # check parent-dir exist
        os.remove(cpath)
        debug_print("Removed file.")


def lesson_enroll(lesson_id, enroll):
    url = "https://schalter.asvz.ch/tn/lessons/" + str(lesson_id)
    properties = lesson_properties(lesson_id)  # loads url for us
    if enroll and properties["Freie Plätze"] == "0":
        prompt_print(f"Error: {lesson_id} fully booked. Consider calling `sneak.")
        return
    try:
        button = wait_for_element(By.XPATH, '//button[@title="Login"]', timeout=10)
        button.click()
        sleep(5)  # wait for possible redirect
        if LOGIN_URL in driver.current_url:
            warn_print("Cached credentials are not valid anymore. relogin MANUALLY")
            Task(lesson_enroll, [lesson_id, enroll], imediate=True)  # recreate task
            raise LoginRequiredException()
    except TimeoutException:
        debug_print("credentials cached")
    try:
        button = wait_for_clickable(By.ID, "btnRegister")
        if button.text == "FÜR LEKTION EINSCHREIBEN" and enroll:
            button.click()
        elif button.text == "FÜR LEKTION EINSCHREIBEN" and not enroll:
            prompt_print("Error: You are not enrolled. Use `list` command.")
        elif button.text == "EINSCHREIBUNG FÜR LEKTION ENTFERNEN" and enroll:
            prompt_print("Error: You are allready enrolled. Use `list` command.")
        elif button.text == "EINSCHREIBUNG FÜR LEKTION ENTFERNEN" and not enroll:
            button.click()
            ok = wait_for_clickable(
                By.XPATH, "//app-lessons-enrollment-button//button[text()='Ok']"
            )
            ok.click()
    except NoSuchElementException:
        prompt_print("Error, acction not possible")
    finally:
        try:
            # TODO: find allert with xpath!
            allert = wait_for_element(By.CLASS_NAME, "alert", timeout=2)
            allert_msg = ""
            for i in allert.text.split("\n"):
                if (
                    i != "x" and i != "Close"
                ):  # x and Close are button texts in the allert
                    allert_msg = i
            prompt_print(allert_msg)
        except TimeoutException:
            pass


class Task:
    tasks = {}
    lock = threading.Lock()
    taskid = 0

    # Note one must lock the thread before entering init
    def __init__(
        self, function, args, kwargs=None, imediate=False, start=None, stop=None
    ):
        if not imediate and start is None:
            raise ValueError("A task must be imediate or have a start time.")
        if not type(args) is list:
            raise ValueError("Arguments must be a list.")
        if kwargs is not None and not type(kwargs) is dict:
            raise ValueError("Keyword arguments must be a dict.")
        # set others
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.imediate = imediate
        self.start = start  # if start/stop is None we later simply ignore it
        self.stop = stop
        self.task_id = Task.taskid
        Task.taskid += 1
        Task.tasks[self.task_id] = self

    def execute(self):
        # a task shall not have a return value, rather prefere raising an # exception
        # a task is expected to print to stdout
        if DEBUG:
            debug_print(
                f"executing task {self.task_id}: {self.function} with arguments {self.args}"
            )
        if self.kwargs is None:
            self.function(*self.args)
        else:
            self.function(*self.args, **self.kwargs)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        s = f"{BOLD}{self.task_id}{RESET}\tworking on {self.function.__name__}({str(self.args)[1:-1]})"
        if self.imediate:
            return s + " imediatly"
        else:
            winstart = strftime(A_DATE_FMT, localtime(self.start))
            if self.stop is not None:
                winclose = strftime(A_DATE_FMT, localtime(self.stop))
                return s + f" in window {winstart} - {winclose}"
            return s + f" starting at {winstart}"
