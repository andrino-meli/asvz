#!/usr/bin/env python3
import sys, os
from fuzzywuzzy.fuzz import ratio
from time import sleep, localtime, time , mktime, strptime
import threading

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
)
from selenium.webdriver.common.by import By

from task import *
import task
from lesson import Lesson,keywords

class QueryException(Exception):
    pass

# definitions and settings
debug = True
if debug:
    import timeit
headless = False

# setup browser driver (namely chromiumdriver)
options = webdriver.chrome.options.Options()
options.add_argument(
    "--user-data-dir=" + os.path.expanduser("~/.config/chromium")
)  # cookie storage
if headless:
    options.add_argument("--headless")
try:
    global driver
    driver = webdriver.Chrome(options=options)  # uses chromedriver per default
    driver.implicitly_wait(0)
    task.set_driver(driver) #avoids passing driver to task
except InvalidArgumentException as ex:
    if "--user-data-dir" in ex.msg:
        # driver.close() #TODO: make this work somehow
        print("Error: Only one instance of asvz can run. Allready running.")
        sys.exit(114)
        # maybee use sys.exit() or os.exit()?

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


#FIFO queue for imediate task, but all candidates with an execution window take preference and are executed as soon as possible
# We do not botter with higher complexity data structures as we sometimes need 
# to remove elements from the middle and the overall lenght of tasks rarely 
# exceeds 10
tasks = []
lock = threading.Lock()

# The basic Idea here is we run a frontend accepting and parsing input from the 
# user and a backend sequentially executing tasks like enrolling or querying.
# This is necessary as the webdriver only allows one instance with the 
# --user-dir flag but we wan't to do multiple tasks like enrolling for multiple 
# lessons simultanously
class taskExecuter(threading.Thread):
    def __init__(self,debug=False):
        self.debug=debug
        self.doStop = False
        super().__init__()
        self.daemon = True

    def __str__(self):
        return f'{self.lesson_id} enrollment Thread in window: {self.start}:{self.stop}.'
    def run(self):
        while(not self.doStop):
            # chek for potential task candidate and execute one according to 
            # the principle mentioned where `task` is defined
            if len(tasks) == 0:
                sleep(1)
                continue
            else:
                lock.acquire()
                candidate = None
                it = iter(tasks)
                while(candidate is None):
                    i = next(it)
                    if not i.imediate:
                        # can we execute task within the next 7s?
                        if time() > i.start - 7:
                            candidate = i
                    elif candidate is None:
                        candidate = i
                # mainly the next line is protected by the lock
                # this as the driver allows only one instance
                candidate.exec()
                tasks.remove(candidate)
                lock.release()

def quit_asvz(executer):
    # only quit if no tasks are running
    exiting = True
    if len(tasks) != 0:
        ans = input("Error: task are running, exit anyway [y/N]?")
        if ans != 'Y' and ans != 'Y':
            exiting = False
    if exiting:
        executer.doStop = True # tell the backend to exit
        executer.join()
        driver.close()
        print("Happy sporting.")


if __name__ == "__main__":
    executer = taskExecuter(debug=debug)
    executer.start()
    command = None
    while True:
        try:
            command = input(esc('2D')+'> ').split(" ")
        except EOFError:
            print("^D", end="")
            quit_asvz(executer)
            break
        except KeyboardInterrupt:
            #hard exit TODO: consider soft exit
            break
        if command[0] == "list":
            t = Task(query_inscribed, [], imediate=True)
            lock.acquire()
            tasks.append(t)
            lock.release()
        elif command[0] == "query":
            # calculate url given the arguments and using the keyword dict.
            try:
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
                        key = None
                        for k in keywords.keys():
                            b = ratio(k, arg)
                            if b > best and b > 60:
                                key = k
                                best = b
                                corrected = True
                        if key is None:
                            raise QueryException('query key "' + arg + '" is invalid')
                        args[i-1] = key
                    url += "f[" + str(i) + "]=" + keywords[args[i-1]] + "&"
                url += keywords['nofitness'] # TODO: make an option
                if corrected:
                    print("corrected:\tquery", *args)
                if debug:
                    print(url)
                query_trainings(url)
            except QueryException as er:
                print(er,'Use `dict` to display available keywords. Or consider contributiong to githuburl in case your keyword is not yet available. (It\'s really easy).') #TODO: insert github contribute url
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
            quit_asvz(executer)
            break
        else:
            print_help()
