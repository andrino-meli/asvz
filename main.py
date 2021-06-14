#!/usr/bin/env python3
import sys, os
#from time import sleep, localtime, time, mktime, strptime
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
)
from time import sleep, localtime, time, mktime, strptime, strftime,struct_time
import task, lesson
from task import *
from lesson import Lesson, keywords, QueryException
from debug import *

# definitions and settings
if DEBUG:
    import timeit

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
    task.set_driver(driver)  # avoids passing driver to task
except InvalidArgumentException as ex:
    if "--user-data-dir" in ex.msg:
        # driver.close() #TODO: make this work somehow
        print("Error: Only one instance of asvz can run. Allready running.")
        sys.exit(114)
        # maybee use sys.exit() or os.exit()?


def print_help():
    print(HELP_STRING)

# FIFO queue for imediate task, but all candidates with an execution window take preference and are executed as soon as possible
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
    def __init__(self):
        self.doStop = False
        super().__init__()
        self.daemon = True

    def __str__(self):
        return (
            f"{self.lesson_id} enrollment Thread in window: {self.start}:{self.stop}."
        )

    def run(self):
        while not self.doStop:
            # chek for potential task candidate and execute one according to
            # the principle mentioned where `task` is defined
            if len(tasks) == 0:
                sleep(1)
                continue
            else:
                now = localtime()
                candidate = None
                lock.acquire()
                for i in tasks:
                    if candidate is not None:
                        break
                    if not i.imediate:
                        # can we execute task within the next 10s?
                        if time() > i.start - 10:
                            candidate = i
                    elif candidate is None:
                        candidate = i
                if candidate is None:
                    lock.release()
                    sleep(1)
                else:
                    try:
                        if DEBUG:
                            prompt_debug_print(f"Debug: executing task: {candidate.function}")
                        candidate.exec()
                    except FollowUpTaskException as ftask:
                        if DEBUG:
                            prompt_debug_print(f"Debug: adding follow up: {ftask.task.function}")
                        tasks.append(ftask.task)
                    finally:
                        tasks.remove(candidate)
                        lock.release()

def quit_asvz(executer):
    # only quit if no tasks are running
    exiting = True
    if len(tasks) != 0:
        ans = input("Error: task are running, exit anyway [y/N]?")
        if ans != "Y" and ans != "Y":
            exiting = False
    if exiting:
        executer.doStop = True  # tell the backend to exit
        executer.join()
        driver.close()
        print("Happy sporting.")


if __name__ == "__main__":
    executer = taskExecuter()
    executer.start()
    command = None
    while True:
        try:
            command = [x.strip() for x in input(esc("2D") + "> ").split(" ")]
            for i in command:
                i.strip()
        except EOFError:
            print("^D", end="")
            quit_asvz(executer)
            break
        except KeyboardInterrupt:
            # hard exit
            print("Keybord Interrupt.")
            if len(tasks) > 0:
                print("interrupting tasks:")
                for t in tasks:
                    print(f"\t{str(tasks)}")
            break
        if command[0] in ["prop","props","properties"]:
            l = command[1]
            if len(l) != 6 or not l.isdecimal():
                prompt_print(f"Error: provided lesson {l} is not  a 6 digit number")
                continue
            if DEBUG:
                print(lesson_properties,[l,'show=True'])
            t = Task(lesson_properties,[l,'show=True'],imediate=True)
            lock.acquire()
            tasks.append(t)
            lock.release()
        elif command[0] == "list":
            t = Task(query_inscribed, [], imediate=True)
            lock.acquire()
            tasks.append(t)
            lock.release()
        elif command[0] == "dict":
            lesson.keyword_show()
            print(
                "Or consider contributing to https://github.com/andrino-meli/asvz in case your keyword is not yet available. (It's really easy)."
            )
            # TODO: insert github contribute url
        elif command[0] == "query":
            # calculate url given the arguments and using the keyword dict.
            try:
                args = command[1:]
                (url, corrected, correction) = lesson.match_keywords(args)
                if corrected:
                    print(correction)
                query_trainings(url)
            except QueryException as er:
                print( er, "Use `dict` to display available keywords.",)
        elif command[0] in ['tasks','task']:
            lock.acquire()
            for i in tasks:
                prompt_print(i)
            lock.release()
        elif command[0] == 'cancel':
            if command[1] == 'all':
                lock.acquire()
                tasks = []
                lock.release()
            for l in command[1:]:
                if len(l) != 6 or not l.isdecimal():
                    prompt_print(f"Error: provided lesson {l} is not  a 6 digit number")
                    continue
                lock.acquire()
                for t in tasks:
                    if l in t.args: #TODO consider making lesson_id part of a task of making a class Lesson and putting it into a Task
                        tasks.remove(t)
                lock.release()
        elif command[0] == "enroll" or command[0] == "deroll":
            for l in command[1:]:
                if len(l) != 6 or not l.isdecimal():
                    prompt_print(f"Error: provided lesson {l} is not  a 6 digit number")
                    continue
                t = Task(lesson_enroll, [l, command[0] == "enroll"], imediate=True)
                lock.acquire()
                tasks.append(t)
                lock.release()
        elif command[0] == 'sneak':
            l = command[1]
            if len(l) != 6 or not l.isdecimal():
                prompt_print(f"Error: provided lesson {l} is not  a 6 digit number")
                continue
            # calculate window
            start = localtime(time())
            preptime = command[2]
            if not preptime.isdecimal():
                prompt_print(f"Error: provided time horizon is not readable")
                continue
            preptime = int(preptime)*60 # preptime from minutes to seconds
            props = lesson_properties(l)
            stop = localtime(mktime(props['winclose']) - preptime)
            t = Task(check_for_free_seat, [l,stop],start=mktime(start),stop=mktime(stop))
            lock.acquire()
            tasks.append(t)
            lock.release()

        elif command[0] == "quit" or command[0] == "q":
            quit_asvz(executer)
            break
        else:
            print_help()
