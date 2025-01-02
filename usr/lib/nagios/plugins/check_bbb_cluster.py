#!/usr/bin/python3

#
# checkbbb.py
# Frank Schiebel frank@linuxmuster.net
# Ported to Icinga by Lukas Spitznagel (lukas.spitznagel@netzint.de)
# GPL v3
#

import os
import sys
import socket
import re
import hashlib
import requests
from collections import defaultdict
from xml.dom.minidom import parse, parseString

def getStatus():
    stream = os.popen('sudo /usr/bin/docker exec  scalelite-api  ./bin/rake status | tail -n +2')
    stream = stream.read()
    allservers = []
    for line in stream.splitlines():
        fields = re.split(r'\s',line)
        fields = list(filter(None, fields))
        numfields = len(fields)

#        if numfields == 7:
#            hrfields = {}
#            fields[0] = re.split(r'\.',fields[0])[0]
#            hrfields["hostname"] = fields[0]
#            hrfields["state"] = fields[1]
#            hrfields["status"] = fields[2]
#            hrfields["meetings"] = fields[3]
#            hrfields["users"] = fields[4]
#            hrfields["largestmeeting"] = fields[5]
#            hrfields["videos"] = fields[6]
#            hrfields["load"] = 0
#            allservers.append(hrfields)
#        if numfields == 8:
#            hrfields = {}
#            fields[0] = re.split(r'\.',fields[0])[0]
#            hrfields["hostname"] = fields[0]
#            hrfields["state"] = fields[1]
#            hrfields["status"] = fields[2]
 #           hrfields["meetings"] = fields[3]
 #           hrfields["users"] = fields[4]
 #           hrfields["largestmeeting"] = fields[5]
 #           hrfields["videos"] = fields[6]
 #           hrfields["load"] = fields[7]
 #           allservers.append(hrfields)
        if numfields == 9:
            hrfields = {}
            fields[0] = re.split(r'\.',fields[0])[0]
            hrfields["hostname"] = fields[0]
            hrfields["state"] = fields[1]
            hrfields["status"] = fields[2]
            hrfields["meetings"] = fields[3]
            hrfields["users"] = fields[4]
            hrfields["largestmeeting"] = fields[5]
            hrfields["videos"] = fields[6]
            hrfields["load"] = fields[7]
            hrfields["version"] = fields[8]
            allservers.append(hrfields)


    return allservers

def generateCheckLine(bbb):
    global totalMeetings
    global totalAttendees
    global totalVideousers
    checkstate = 0 
    statusline = ""

    if bbb["state"] == "enabled":
        statusline  = str(checkstate) + " " + "BBB_" + bbb["hostname"] + " "
        statusline += "numMeetings=" + bbb["meetings"] + "|"
        statusline += "numAttendees=" + bbb["users"] + "|"
        statusline += "numWithVideo=" + bbb["videos"] + " "
        statusline += "[" + bbb["hostname"] + " M:" + bbb["meetings"] + " "
        statusline += "Att:" + bbb["users"] + " "
        statusline += "Vid:" + bbb["videos"] + "]"
    
    if bbb["state"] == "disabled" and bbb["status"] == "online":
        statusline  = str(checkstate) + " " + "BBB_" + bbb["hostname"] + " "
        statusline += "numMeetings=" + bbb["meetings"] + "|"
        statusline += "numAttendees=" + bbb["users"] + "|"
        statusline += "numWithVideo=" + bbb["videos"] + " "
        statusline += "****DISABLED IN SCALELITE**** [" + bbb["hostname"] + " M:" + bbb["meetings"] + " "
        statusline += "Att:" + bbb["users"] + " "
        statusline += "Vid:" + bbb["videos"] + "]"
    
    if bbb["state"] == "enabled" and bbb["status"] == "offline":
        checkstate = 2
        statusline  = str(checkstate) + " " + "BBB_" + bbb["hostname"] + " "
        statusline += "numMeetings=0|"
        statusline += "numAttendees=0|"
        statusline += "numWithVideo=0 "
        statusline += "****ENABLED BUT OFFLINE****" 
    
    if bbb["state"] == "disabled" and bbb["status"] == "offline":
        checkstate = 1
        statusline  = str(checkstate) + " " + "BBB_" + bbb["hostname"] + " "
        statusline += "numMeetings=0|"
        statusline += "numAttendees=0|"
        statusline += "numWithVideo=0 "
        statusline += "****DISABLED IN SCALELITE AND OFFLINE****" 

    totalMeetings += int(bbb["meetings"])
    totalAttendees += int(bbb["users"])
    totalVideousers += int(bbb["videos"])

    return statusline



# Global metrics
totalMeetings = 0
totalAttendees = 0
totalVideousers = 0

allservers = getStatus()
allservers_string = "\n"
for server in allservers:
  if server["state"] == "enabled" and server["status"] == "online":
    allservers_string += "[OK] "
  else:
    allservers_string += "[WARNING] "
  allservers_string += server["hostname"] + " "
  allservers_string += "Meetings: " + server["meetings"] + ", "
  allservers_string += "Users: " + server["users"] + ", "
  allservers_string += "Videos: " + server["videos"] + ", "
  allservers_string += "Largest-Meeting: " + server["largestmeeting"] + ", "
  allservers_string += "BBB-Version: " + server["version"]
  allservers_string += "\n"

for bbb in allservers:
    generateCheckLine(bbb)


statusline  = "OK - " + socket.gethostname() + " - "
statusline += "Meetings: " + str(totalMeetings) + ", "
statusline += "User: " + str(totalAttendees) + ", "
statusline += "Video: " + str(totalVideousers) + "\n\n"
statusline += allservers_string + " "
statusline += "| 'total_meetings'=" + str(totalMeetings) + " "
statusline += "'total_user'=" + str(totalAttendees) + " "
statusline += "'total_video'=" + str(totalVideousers)
#statusline += "numMeetings=" + str(totalMeetings) + "|"
#statusline += "numAttendees=" + str(totalAttendees) + "|"
#statusline += "numWithVideo=" + str(totalVideousers) + " "
#statusline += "[scale001 totals "
#statusline += "M:" + str(totalMeetings) + " "
#statusline += "Att:" + str(totalAttendees) + " "
#statusline += "Vid:" + str(totalVideousers) + "]"

print(statusline)
#print(allservers_string)
