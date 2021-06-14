# make ansi escape sequence work in windows
import os
os.system("")
# yeah i know -> really some magic happening here

# This file includes all constants and things included by every other file
QUERY_DEBUG=False
PROPERTIES_DEBUG=False
DEBUG=True
debug=DEBUG #TODO rename and remove
HEADLESS=False
headless=HEADLESS #TODO ren and rev

POLL_INTERVALL=60 # sneak polling intervall
# date format in asvz app
DATE_FMT = '%d.%m.%Y %H:%M'
# more readable and short format for printings to user
A_DATE_FMT = '%a %d.%b %H:%M'

# HELP STRING
#TODO: check interactive ussage potential or delete if from the help string
HELP_STRING= '\
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
If you can not enroll in a lesson because there is no place left or the\n\
enrollment window is yet closed consider letting the tool\n\
check in later automatically for you.\n\
\n\
available commands:\n\
===================\n\
q | q | ^D | ^C         quits interaction\
help                    prints this help message\n\
list                    shows all enrolled trainings\n\
query KEYWORDS          searches for trainings according to keywords\n\
dict                    prints a dictionary of available KEYWORDS allowd in queries.\n\
\n\
props  LESSON           print properties of a Lesson\n\
enroll LESSON           tries to enrolls for a lesson given its lesson id\n\
deroll LESSON           removes subscription from lesson\n\
sneak  LESSON PREPTIME  tries to sneak a place in a booked leaving at least PREPTIME minutes before the lesson end enrollment window. This allows the user to prepare for the lesson.\n\
\n\
task                    shows all running background task\n\
cancel LESSON | all     cancel all tasks related to LESSON\n\
'
