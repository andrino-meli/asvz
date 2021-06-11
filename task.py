from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from time import sleep, localtime, time, mktime, strptime
from lesson import Lesson


# TODO: check how to do this cleaner?
driver = None


def set_driver(dr):
    global driver
    driver = dr


# helper function to make code more readable
def wait_for_element(attribute, string, multiple=False, timeout=15, debug=False):
    if debug:
        prompt_print(
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


# ansi escape sequence
def esc(code):
    return f"\033[{code}"


# prints while moving the prompt '> ' down
# TODO: maybee generalize this for arbitrary promt strings
def prompt_print(*args):
    print(esc("2D"), end="")
    print(*args, end="")
    print("\n> ", end="")


def safe_page_load(url):
    if driver.current_url == url:
        tmp = driver.find_element_by_xpath("/html")
        driver.get(url)
        WebDriverWait(driver, 2).until(EC.staleness_of(tmp))
    else:
        driver.get(url)
        while (driver.current_url) != url:
            sleep(0.3)
    sleep(0.3)


####### Task Function Definitions #############
# these functions are ment to be put in the task list

# query offers, parse and print
## this might seem very cryptic and it is because we reverse engineere the parsing
## from the data structure in the website. Which is quite arbitrary and also
## depends quite a bit on scripting.
QUERYSIZE = 20


def query_trainings(url, debug=False):
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
                    l = Lesson()
                    (l.weekday, l.day, l.month) = (weekday, day, month)
                    l.url = offer.get_attribute("href")
                    l.lesson_id = l.url[-6:]
                    split = offer.text.split("\n")
                    if debug:
                        prompt_print(len(split), split)
                    l.start = split[0]
                    l.end = split[1][-5:]
                    l.sport = split[2]
                    l.niveau = split[3]
                    l.facility = split[4]
                    index_shift = 1
                    if split[5].isnumeric():
                        index_shift = 0
                        # unleaded training
                    else:
                        l.trainer = split[5]
                    opt = split[5 + index_shift]
                    enrollmnt_option = ""
                    if opt == "Keine freien":
                        enrollmnt_option = "fully booked"
                    elif opt == "Einschreiben möglich":
                        enrollmnt_option = "window not open"
                    elif opt.isnumeric() and split[6 + index_shift] == "freie Plätze":
                        enrollmnt_option = opt + " slots"
                    l.enrollment_string = enrollmnt_option
                    trainings.append(l)  # TODO:
                    if len(trainings) >= QUERYSIZE:
                        raise IndexError("query limit")
                    prompt_print(l)
            except (NoSuchElementException):
                # TODO: open browser interactively to let user fix himself
                pass
    except IndexError as er:
        if str(er) != "query limit":
            raise er


def query_inscribed(debug=False):
    url = "https://schalter.asvz.ch/tn/my-lessons"
    driver.get(url)
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


def lesson_enroll(lesson_id, enroll, debug=False):
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
                    prompt_print("window closed", lesson_id, inscribe_window[:20])
                    # TODO: raise error
                else:
                    # directly click at button
                    button.click()
            elif button.text == "FÜR LEKTION EINSCHREIBEN" and not enroll:
                prompt_print("You are not enrolled. Use `list` command.")
            elif button.text == "EINSCHREIBUNG FÜR LEKTION ENTFERNEN" and enroll:
                prompt_print("You are allready enrolled. Use `list` command.")
            elif button.text == "EINSCHREIBUNG FÜR LEKTION ENTFERNEN" and not enroll:
                button.click()
                ok = wait_for_clickable(
                    By.XPATH, "//app-lessons-enrollment-button//button[text()='Ok']"
                )
                ok.click()
        except NoSuchElementException:
            prompt_print("acction not possible")
        finally:
            try:
                allert = wait_for_element(By.CLASS_NAME, "alert", timeout=2)
                allert_msg = ""
                for i in allert.text.split("\n"):
                    if i != "x" and i != "Close":
                        allert_msg = i
                prompt_print(allert_msg)
            except TimeoutException:
                pass
    except TimeoutException:
        prompt_print("credentials not cached - retry enrollment again after login")
        button = wait_for_element(By.XPATH, '//button[@title="Login"]', timeout=2)
        button.click()
        # check if we are redirected to auth.asvz.ch (so no cached credentials)
        sleep(2)
        curl = driver.current_url
        auth_url = "https://auth.asvz.ch/account/login"
        if curl[: len(auth_url)] == auth_url:
            prompt_print("LOGIN REQUIRED - opening browser - pls. login manually.")
            options = webdriver.chrome.options.Options()
            options.add_argument(
                "--user-data-dir=" + os.path.expanduser("~/.config/chromium")
            )  # cookie storage
            options.add_argument("--app=" + auth_url)
            # TODO: check and make login easier
            headless = False  # TODO: remove hardecoded fix
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
            prompt_print("Manuall Login Successfull!")
            if headless:
                driver.close()
                options = Options().headless = True
                driver = webdriver.Chrome(options=options)
            # This is strange but has to bee done (so click login again).
            lesson_enroll(
                lesson_id, enroll
            )  # TODO: recursion might be dangerous (!) maybee find a better syntax


class Task:
    def __init__(
        self, function, args, imediate=False, start=None, stop=None, debug=False
    ):
        if not imediate and start is None:
            raise ValueError("A task must be imediate or have a start time.")
        self.function = function
        self.args = args
        self.imediate = imediate
        self.start = start  # if start/stop is None we later simply ignore it
        self.stop = stop
        self.debug = debug

    def exec(self):
        # a task shall not have a return value, rather prefere raising an # exception
        # a task is expected to print to stdout
        self.function(*self.args, debug=self.debug)
