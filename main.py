#!/usr/bin/env python3
# main does 4 things:
#
# Fist:     setting every thing up: So creating a browser driver for chromium,
#           creating a task list and a corresponding thread lock
# Second:   Check if main is running as __main__ if so then:
#           create a background thread called taskExecutor
#           this thread is required because the chromium browser is hard to
#           parallelise so we have sort of a server-client model here.
#           All tasks in the task list are (if possible) executed by the
#           taskExecutor. The taskExecutor thread does only communicate with
#           main by raising exceptions to pass to main follup up tasks that
#           should be created.  But mostly it just prints to the screen for the
#           user. Therefor the input/output is asynchronuous.
# Third:    main runs a while loop where it asks for user input. It is parsed
#           and if necessary main creates a new task and appends it to the task
#           list.
# Fourth:   if the interaction is terminated by the user main dups all furhter
# tasks and joins the executor
import sys, os, copy, threading
from time import sleep, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    InvalidArgumentException,
    TimeoutException,
    WebDriverException,
)

import task, lesson
from task import *
from utility import *
from lesson import Lesson, keywords, QueryException

if DEBUG:
    import timeit


# setup browser driver (namely chromiumdriver)
options = webdriver.chrome.options.Options()
options.add_argument(
    "--user-data-dir=" + os.path.expanduser("~/.config/chromium")
)  # cookie storage
driver = None
if headless:
    options.add_argument("--headless")
try:
    driver = webdriver.Chrome(options=options)  # uses chromedriver per default
    driver.implicitly_wait(0)
    task.set_driver(
        driver
    )  # passes driver - hacky but avoids passing driver to all function calls where we need it
except InvalidArgumentException as ex:
    if "--user-data-dir" in ex.msg:
        # driver.close() #TODO: make this work somehow
        print("Error: Only one instance of asvz can run. Allready running.")
        sys.exit(114)
        # maybee use sys.exit() or os.exit()?


# The basic Idea here is we run a frontend accepting and parsing input from the
# user and a backend sequentially executing tasks like enrolling or querying.
# This is necessary as the webdriver only allows one instance with the
# --user-dir flag but we wan't to do multiple tasks like enrolling for multiple
# lessons simultanously
class TaskExecuter(threading.Thread):
    executer = None

    def __init__(self):
        if TaskExecuter.executer is None:
            self.doStop = False
            TaskExecuter.executer = self
            super().__init__()
            self.daemon = True
        else:
            raise Exception("Error: TaskExecuter instatiated more than onece")

    def __str__(self):
        return (
            f"{self.lesson_id} enrollment Thread in window: {self.start}:{self.stop}."
        )

    def run(self):
        try:
            while not self.doStop:
                # chek for potential task candidate and execute one according to
                # the principle mentioned where `task` is defined
                if len(Task.tasks) == 0:
                    sleep(1)
                    continue
                now = time()
                Task.lock.acquire()
                # remove all spoiled tasks
                for k,t in Task.tasks.items():
                    if t.stop is not None and time() > t.stop:
                        Task.tasks.pop(k)
                # check for candidate to execute
                candidate = None
                for k,t in Task.tasks.items():
                    if candidate is not None:
                        break
                    if not t.imediate:
                        # can we execute task within the next 10s?
                        if time() > t.start - 10:
                            candidate = k
                    elif candidate is None:
                        candidate = k
                if candidate is None:
                    Task.lock.release()
                    sleep(1)
                    continue
                #execute candidate
                try:
                    Task.tasks[candidate].execute()
                except WebDriverException as ex:
                    if "net::ERR_INTERNET_DISCONNECTED" in str(ex):
                        warn_print("no internet connection - retry in 1min")
                        Task(t.function,t.args,imediate=False,start=time()+60,stop=t.stop)
                finally:
                    Task.tasks.pop(candidate)
                    Task.lock.release()
        except Exception as ex:
            print(f"{RED} asvz crashed due to {str(ex)}")
            quit_asvz()
            raise ex


def quit_asvz():
    # only quit if no tasks are running
    exiting = True
    if len(Task.tasks) != 0:
        ans = input(f"{YELLOW}Warn:\ttask are running, exit anyway [y/N]?{RESET}")
        if ans != "Y" and ans != "y":
            exiting = False
    if exiting:
        TaskExecuter.executer.doStop = True  # tell the backend to exit
        TaskExecuter.executer.join()
        driver.close()
        print(f"{BOLD}Happy sporting.{RESET}")


if __name__ == "__main__":
    executer = TaskExecuter()
    executer.start()
    command = None
    while True:
        try:
            command = [x.strip() for x in input(esc("2D") + "> ").split(" ")]
            for i in command:
                i.strip()
        except EOFError:
            print("^D", end="")
            quit_asvz()
            break
        except KeyboardInterrupt:
            # hard exit
            print("Keybord Interrupt.")
            if len(Task.tasks) > 0:
                warn_print("interrupting tasks:\n")
                for t in Task.tasks.values():
                    print(t)
            break
        if command[0] in ["prop", "props", "properties",'copy']:
            l = command[1]
            if l is None or l == '':
                pass
            elif len(l) != 6 or not l.isdecimal():
                warn_print(f"provided lesson {l} is not  a 6 digit number")
            elif command[0] == 'copy':
                Task(lesson_properties, [l, 'show=False','copy=True'], imediate=True)
            else:
                Task(lesson_properties, [l, "show=True"], imediate=True)
        elif command[0] == "list":
            Task(query_inscribed, [], imediate=True)
        elif command[0] == "dict":
            lesson.keyword_show()
            print(
                "\nOr consider contributing to https://github.com/andrino-meli/asvz in case your keyword is not yet available. (It's really easy)."
            )
            # TODO: insert github contribute url
        elif command[0] == "query":
            # calculate url given the arguments and using the keyword dict.
            try:
                args = command[1:]
                (url, corrected, correction) = lesson.match_keywords(args)
                if corrected:
                    print(correction)
                Task(query_trainings, [url], imediate=True)
            except QueryException as er:
                warn_print(
                    er,
                    "Use `dict` to display available keywords.",
                )
        elif command[0] in ["tasks", "task"]:
            Task.lock.acquire()
            for i in Task.tasks.values():
                prompt_print(i)
            Task.lock.release()
        elif command[0] == "cancel":
            if len(command) < 2:
                warn_print(f"provide task index.")
            elif command[1] == "all":
                Task.lock.acquire()
                Task.tasks.clear()
                Task.lock.release()
            elif not command[1].isdecimal() or int(command[1]) not in Task.tasks:
                warn_print(f"{command[1]} is not a task id corresponding to a task.")
            else:
                l = int(command[1])
                Task.lock.acquire()
                Task.tasks.pop(l)
                Task.lock.release()
        elif command[0] == "enroll" or command[0] == "deroll":
            for l in command[1:]:
                if len(l) != 6 or not l.isdecimal():
                    warn_print(f"provided lesson {l} is not  a 6 digit number")
                    continue
                Task(check_window, [l, command[0] == "enroll"], imediate=True)
        elif command[0] == "sneak":
            l = command[1]
            if len(l) != 6 or not l.isdecimal():
                prompt_print(f"Error: provided lesson {l} is not  a 6 digit number")
                continue
            # calculate window
            start = time()
            preptime = command[2]
            if not preptime.isdecimal():
                prompt_print(f"Error: provided time horizon is not readable")
                continue
            preptime = int(preptime) * 60  # preptime from minutes to seconds
            props = lesson_properties(l)
            stop = props["winclose"] - preptime
            Task(check_for_free_seat, [l, stop], start=start, stop=stop)

        elif command[0] == "quit" or command[0] == "q":
            quit_asvz()
            break
        else:
            print(HELP_STRING)
