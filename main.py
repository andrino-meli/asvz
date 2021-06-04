#!/usr/bin/env python3

# TODO: licence
# TODO: disclamer

import sys,os
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from fuzzywuzzy.fuzz import ratio
from time import sleep

debug = False
headless = False
options = Options()
#config_dir = os.path.expanduser("user-data-dir=~/.config//")
options.add_argument('--user-data-dir=' + os.path.expanduser('~/.config/chromium')) #cookie storage
options.add_argument("--app=")
if headless: options.add_argument("--headless");
driver = webdriver.Chrome(options=options)
driver.implicitly_wait(5)


class Lesson:
    url = None; lesson_id = None
    weekday = None; day = None ; month = None
    start = None; end = None
    sport = None; niveau = None; facility = None; trainer = None

    def __repr__(self):
        return '{self.lesson_id}\t{self.weekday} {self.day}{self.month} {self.start}-{self.end}\t {self.sport}\t{self.trainer}\t{self.facility}\t{self.niveau}'.format(self=self)


sports = {
    "cycling": "sport:45645",
    "kondi": "sport:45675",
    "yoga": "sport:45750",
    "rowing": "sport:45699",
    "tbow": "sport:45730",
    "mpump": "sport:45686",
    "crossfit": "sport:45643",
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
    "hoengg": "facility:45598",
    "fluntern": "facility:45575",
}

keywords = dict()
keywords.update(sports)
keywords.update(weekdays)
keywords.update(facilities)


# query offers and parse
## this might seem very cryptic and it is because we reverse engineere the parsing
## from the data structure presented in the html. Which is quite arbitrary.
def query_trainings(url):
    global driver
    driver.get(url)
    sleep(0.3) # required for website elements to not go stale (loading time)
    trainings = []
    # find all days where we have offers
    for daytable in driver.find_elements_by_class_name(
        "teaser-list-calendar__container"
    ):
        try:
            weekday = daytable.find_element_by_class_name("day").text
            day = daytable.find_element_by_class_name("date").text
            month = daytable.find_element_by_class_name("month").text
            # find all offers coresponding to this day - each offer has a link
            for offer in daytable.find_elements_by_tag_name("a"):
                # check that link we found indeed corresponds to an offer
                try:
                    # do magic parsing - again reverse engineered from the given
                    # output string in the html
                    offer.find_element_by_class_name("offer__time")
                    l = Lesson()
                    (l.weekday, l.day, l.month) = (weekday, day, month)
                    l.url = offer.get_attribute("href")
                    l.lesson_id = l.url[-6:]
                    split = offer.text.split("\n")
                    if debug: print(split);
                    l.start = split[0]
                    l.end = split[1][-5:]
                    l.sport = split[2]
                    l.niveau = split[3]
                    l.facility = split[4]
                    l.trainer = split[5]
                    # TODO: use enrollment option
                    # enrollment = split[6] # number or 'keine freien' or 'Einschreiben möglich'
                    trainings.append(l)
                except (NoSuchElementException):
                    # in case this is not a valid offer just skip as we found some
                    # random link while parsing
                    pass
        except (NoSuchElementException):
            # TODO: open browser interactively to let user fix himself
            pass
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
    global driver
    url = "https://schalter.asvz.ch/tn/my-lessons"
    driver.get(url)
    trainings = driver.find_elements_by_xpath('//table//tr')
    for t in trainings[1:]:
        try:
            lesson_id = t.find_element_by_tag_name('a').get_attribute('href')[-6:]
            print(lesson_id,'\t',t.text.replace('\n','\t'))
        except:
            pass;
        else:
            print(t.text.replace('\n','\t'))

def create_listener():
    pass

def lesson_enroll(lesson_id,enroll):
    global driver
    url = 'https://schalter.asvz.ch/tn/lessons/' + str(lesson_id)
    if debug: print(url)
    driver.get(url)
    sleep(0.3)
    try:
        button = driver.find_element_by_xpath('//button[@title="Login"]')
        button.click()
        # check if we are redirected to auth.asvz.ch (so no cached credentials)
        sleep(1)
        curl = driver.current_url
        auth_url = 'https://auth.asvz.ch/account/login'
        if curl[:len(auth_url)] == auth_url:
            print("LOGIN REQUIRED - opening browser - pls. login manually.")
            options = Options()
            options.add_argument('--user-data-dir=' + os.path.expanduser('~/.config/chromium')) #cookie storage
            options.add_argument("--app="+auth_url)
            if headless:
                driver.close()
                driver = webdriver.Chrome(options=options)
                #driver.implicitly_wait(1)
                driver.get(auth_url)
            while (driver.current_url != 'https://auth.asvz.ch/Manage/Index'):
                sleep(0.5)
            # strange but we have to relogin to save the cookie
            driver.get(url)
            sleep(0.5)
            button = driver.find_element_by_xpath('//button[@title="Login"]')
            button.click()
            sleep(0.5)
            print("Manuall Login Successfull!")
            if headless:
                driver.close()
                options = Options().headless = True
                driver = webdriver.Chrome(options=options)
            # This is strange but has to bee done (so click login again).
    except NoSuchElementException:
        if debug: print('user logged in');
    finally:
        if driver.current_url != url:
            driver.get(url)
        try:
            button = driver.find_element_by_xpath('//button[@id="btnRegister"]')
            sleep(1)
            if button.text == 'FÜR LEKTION EINSCHREIBEN' and enroll:
                button.click()
            elif button.text == 'FÜR LEKTION EINSCHREIBEN' and not enroll:
                print('You are not enrolled. Use `list` command.')
            elif button.text == 'EINSCHREIBUNG FÜR LEKTION ENTFERNEN' and enroll:
                print('You are allready enrolled. Use `list` command.')
            elif button.text == 'EINSCHREIBUNG FÜR LEKTION ENTFERNEN' and not enroll:
                button.click()
                sleep(6)
                buttons = driver.find_elements_by_xpath('//div[@class="modal-content"]//button')
                for b in buttons:
                    if b.text == "Ok":
                        b.click()
        except NoSuchElementException:
            print('acction not possible')

if __name__ == "__main__":
    interactive = True
    command = None
    if len(sys.argv) > 1:
        interacive = False
        command = sys.argv[1:]
    while True:
        if interactive:
            try:
                command = input("> ").split(' ')
            except EOFError:
                print("^D", end="")
                break
            except KeyboardInterrupt:
                break

        if command[0] == "list":
            query_inscribed()
        elif command[0] == "query":
            # calculate url given the arguments and using the keyword dict.
            url = "https://asvz.ch/426-sportfahrplan?"
            i = 0; corrected = False; args = command[1:]; correction = 'query '
            #TODO: make correction bold in text
            #TODO: consider changeing in a correct function for abstraction
            for i in range(len(args)):
                arg = args[i].lower() #be case insensitive
                # fuzzy match argument and correct to known key
                if arg not in keywords:
                    best = 0; key = arg;
                    for k in keywords.keys():
                        b = ratio(k, arg)
                        if b > best:
                            key = k; best = b; corrected = True; 
                    args[i]=key;
                url += "f[" + str(i) + "]=" + keywords[args[i]] + "&"
                i += 1
            if corrected: print("corrected:\tquery", *args);
            if debug: print(url);
            trainings = query_trainings(url)
            # TODO pretty print query
            for training in trainings[:20]:
                print(str(training))
        elif command[0] == "dict":
            print("sports:\t\t", *list(sports.keys()))
            print("facilities:\t", *list(facilities.keys()))
            print("weekdays:\t", *list(weekdays.keys()))
            # TODO add time and date?
        elif command[0] == "enroll":
            for l in command[1:]:
                lesson_enroll(l,True)
        elif command[0] == "deroll":
            for l in command[1:]:
                lesson_enroll(l,False)
        elif command[0] == "quit" or command[0] == "q":
            break
        else:
            print_help()
        if not interactive:
            break

# username_box = driver.find_element_by_id('email')
# username_box.send_keys("usr")
# username_box = driver.find_element_by_id('email')
# password_box = driver.find_element_by_id('pass')
# password_box.send_keys("pwd")
# login_box = driver.find_element_by_id('loginbutton')
# login_box.click()
# print ("Done")
