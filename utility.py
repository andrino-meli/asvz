# make ansi escape sequence work in windows
import os

os.system("")
# yeah i know -> really some magic happening here

# This file includes all constants and things included by every other file
QUERY_DEBUG = False
PROPERTIES_DEBUG = True
SPLIT_DEBUG = True
DEBUG = True
HEADLESS = False

POLL_INTERVALL = 30  # sneak polling intervall in s
# date format in asvz app
DATE_FMT = "%d.%m.%Y %H:%M"
# more readable and short format for printings to user
A_DATE_FMT = "%a %d.%b %H:%M"
TIME_FMT = "%H:%M"
LOGIN_URL = 'https://auth.asvz.ch/account/login'

class LoginRequiredException(Exception):
    pass

# ansi escape sequence
def esc(code):
    return f"\033[{code}"

# ansi colour
def ansi(code):
    return f"\033[{code}m"

CLEAR = ansi("0")
RESET = ansi("0")
BOLD = ansi("1")
RED = ansi("38;2;255;0;0")
YELLOW = ansi("38;2;255;255;0")
GREY = ansi("38;2;150;150;150")

# HELP STRING
# TODO: check interactive ussage potential or delete if from the help string
HELP_STRING = f'\
{RESET}This asvz helper can be run interactively or not.\n\
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
If you can not enroll in a lesson because there is no place left or the\n\
enrollment window is yet closed consider letting the tool\n\
check in later automatically for you.\n\
\n\
available commands:\n\
===================\n\
{BOLD}q{RESET} | {BOLD}q{RESET} | ^D | ^C         quits interaction\n\
{BOLD}help{RESET}                    prints this help message\n\
{BOLD}login{RESET}                   manually login to ASVZ -> chaches cookies for later\n\
{BOLD}list{RESET}                    shows all enrolled trainings\n\
{BOLD}query{RESET} KEYWORDS          searches for trainings according to keywords\n\
{BOLD}dict{RESET}                    prints a dictionary of available KEYWORDS allowd in queries.\n\
\n\
{BOLD}props{RESET}  LESSON           print properties of a Lesson\n\
{BOLD}copy{RESET}   Lesson           copies lesson to clipboard\n\
{BOLD}enroll{RESET} LESSON           tries to enrolls for a lesson given its lesson id\n\
{BOLD}deroll{RESET} LESSON           removes subscription from lesson\n\
{BOLD}sneak{RESET}  LESSON PREPTIME  tries to sneak a place in a booked leaving at least PREPTIME minutes before the lesson end enrollment \n\
\t\t\twindow. This allows the user to prepare for the lesson.\n\
\n\
{BOLD}task{RESET}                    shows all running background task\n\
{BOLD}cancel{RESET} LESSON | {BOLD}all{RESET}     cancel all tasks related to LESSON\n'


# prints while moving the prompt '> ' down
# TODO: maybee generalize this for arbitrary prompt strings
def prompt_print(*args):
    print(esc("2D"), RESET, end="")
    print(*args, end="")
    print("\n> ", end="")


def debug_print(*args):
    print(esc("2D"), RESET, end="")
    print(f"{GREY}Debug: ", *args, end="")
    print(f"{RESET}\n> ", end="")


def warn_print(*args):
    print(esc("2D"), RESET, end="")
    print(f"{YELLOW}Warn: ", *args, end="")
    print(f"{RESET}\n> ", end="")
