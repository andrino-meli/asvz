from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from time import sleep, localtime, time, mktime, strptime, strftime,struct_time,asctime

import lesson
from debug import *

# sometimes its inherently impossible to to execute a task modularyly: in this
# case a task can raise a subtask exception informing the task handler to 
# schedule a followup task
class FollowUpTaskException(Exception):
    def __init__(self,task):
        self.task = task

# TODO: check how to do this cleaner?
driver = None
def set_driver(dr):
    global driver
    driver = dr

# helper function to make code more readable
def wait_for_element(attribute, string, multiple=False, timeout=15):
    if DEBUG:
        prompt_debug_print(
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

# ansi escape sequence color/style
def text_style(r=255,g=255,b=255,clear=False,foreground=True):
    if clear:
        return f"\033[0m"
    elif foreground:
        return f"\033[38;2;{r};{g};{b}m"
    return ''

# prints while moving the prompt '> ' down
# TODO: maybee generalize this for arbitrary prompt strings
def prompt_print(*args):
    print(esc("2D"), end="")
    print(*args, end="")
    print("\n> ", end="")

def prompt_debug_print(*args):
    r,g,b = (150,150,150)
    print(esc("2D"),text_style(r=r,g=g,b=b),end="")
    print(*args, end="")
    print(text_style(clear=True), "\n> ",end="")

def safe_page_load(url):
    if DEBUG:
        prompt_debug_print("soft load", url)
    if driver.current_url == url:
        tmp = driver.find_element_by_xpath("/html")
        driver.get(url)
        WebDriverWait(driver, 2).until(EC.staleness_of(tmp))
    else:
        driver.get(url)
        # TODO: does not work with redirects
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
                        prompt_debug_print(len(split), split)
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


def lesson_properties(lesson_id,show=False):
    url = "https://schalter.asvz.ch/tn/lessons/" + lesson_id
    safe_page_load(url)
    evpr = wait_for_element(By.CLASS_NAME, "event-properties")
    properties = {}
    it = iter(evpr.text.split("\n"))
    try:
        while(True):
            name = next(it)
            value = next(it)
            if name == 'Anmeldezeitraum':
                (winopen,winclose) = value.split(' - ')
                properties['winopen'] = strptime(winopen[4:],DATE_FMT)
                properties['winclose'] = strptime(winclose[4:],DATE_FMT)
            elif name == 'Abmeldefrist':
                properties['derolldue'] = strptime(value,DATE_FMT)
            else:
                properties[name] = value
    except StopIteration: pass;
    if PROPERTIES_DEBUG:
        prompt_debug_print(properties)
    if show:
        for k,v in properties.items():
            if isinstance(v,struct_time):
                prompt_print('{:<20}:\t {}'.format(k,strftime(A_DATE_FMT,v)))
            else:
                prompt_print('{:<20}:\t {}'.format(k,v))
    else:
        return properties


def check_for_free_seat(lesson_id,stop):
    if DEBUG:
        prompt_debug_print(f"Debug: check for free seat in {lesson_id} stop at {asctime(stop)}.")
    seats = lesson_properties(lesson_id)['Freie Plätze']
    if seats.isdecimal():
        if localtime() > stop:
            return
        elif int(seats) > 0:
            t = Task(lesson_enroll, [lesson_id, True], imediate=True)
            raise FollowUpTaskException(t)
        else:
            start = time()+POLL_INTERVALL
            t = Task(check_for_free_seat, [lesson_id, stop], start=start,stop=mktime(stop))
            raise FollowUpTaskException(t)

    else:
        raise Exception('Error, "Freie Plätze" is not a number.')


def check_window(lesson_id,enroll):
    properties = lesson_properties(lesson_id)
    # check weather the task can be executed immediately
    if enroll:
        (winopen,winclose) = (properties['winopen'],properties['winclose'])
        #TODO: add padding for time checking?
        if localtime() < winopen:
            if DEBUG:
                prompt_debug_print(f'Note: enrollment window not open, create background task for {lesson_id}. Consider calling `task` or `cancel`.')
            # request creation of a task but with a window instead of imediate
            t = Task(lesson_enroll,[lesson_id,'enroll=True'],start=winopen,stop=winclose)
            FollowUpTaskException(t)
        elif  winclose < localtime():
            prompt_print('Eror: enrollment window for {lesson_id} allready closed.')
        else:
            lesson_enroll(lesson_id,enroll)
    else:
        if properties['derolldue'] < localtime():
            prompt_print(f"Eror: to late to deroll from {lesson_id}. Risk \
            evaluation: currently {properties['Freie Plätze']} seats are free \
            and {properties['Trainingsleitende']} is your trainer.")
        else:
            lesson_enroll(lesson_id,enroll)


def lesson_enroll(lesson_id, enroll):
    # TODO: make properties not required multiple times
    # maybee create a lesson object instead of the lesson id
    url = "https://schalter.asvz.ch/tn/lessons/" + str(lesson_id)
    properties = lesson_properties(lesson_id)
    if enroll and properties['Freie Plätze'] == '0':
        prompt_print(f'Error: {lesson_id} fully booked. Consider calling `sneak.')
        return
    try:
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
                    if i != "x" and i != "Close": # x and Close are button texts in the allert
                        allert_msg = i
                prompt_print(allert_msg)
            except TimeoutException:
                pass
    except TimeoutException:
        global driver
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
            # TODO: recursion might be dangerous (!) maybee find a better 
            # syntax
            lesson_enroll( lesson_id, enroll)  


class Task:
    def __init__(
        self, function, args, imediate=False, start=None, stop=None
    ):
        if not imediate and start is None:
            raise ValueError("A task must be imediate or have a start time.")
        self.function = function
        self.args = args
        self.imediate = imediate
        self.start = start  # if start/stop is None we later simply ignore it
        self.stop = stop

    def exec(self):
        # a task shall not have a return value, rather prefere raising an # exception
        # a task is expected to print to stdout
        self.function(*self.args)
