#!/usr/bin/env python3

###################################################
#
# Name: check_pbs.py
# Version: 1.0
# Date: 02.03.2022
# Author: lukas.spitznagel@netzint.de
#
###################################################

import argparse
import os
import socket
import json
import datetime

from datetime import datetime as dt
from datetime import timedelta

def __execute(command):
    commandline = ""
    for cmd in command:
        commandline += cmd + " "
    stream = os.popen(commandline)
    return json.loads(stream.read())

def __exit_ok(message):
    print("OK - " + message)
    exit(0)

def __exit_warning(message):
    print("WARNING - " + message)
    exit(1)

def __exit_critical(message):
    print("CRITICAL - " + message)
    exit(2)

def __exit_unknown(message):
    print("UNKNOWN - " + message)
    exit(3)

def getValueFromPBS(url, method="list", append=""):
    return __execute(["sudo", "proxmox-backup-manager", url, method, append, "--output-format json"])

def KBToTB(value, calc=1):
    return str(round((value / 1024 / 1024 / 1024 / 1024) * calc, 2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--info', help='Info category to choose', required = True, choices=["host-version", "disk-status", "datastore-status", "garbage-collection-status"], dest='info')
    parser.add_argument('-w', '--warning', help='Warning in percent/days', dest='warning')
    parser.add_argument('-c', '--critical', help='Critical in percent/days', dest='critical')
    args = parser.parse_args()

    if args.info == "host-version":
        values = getValueFromPBS("versions", "")
        if args.warning:
            if values[0]["Version"] != values[0]["OldVersion"]:
                __exit_warning(socket.gethostname() + " - " + values[0]["Package"] + " " + values[0]["ExtraInfo"] + ", newest is " + values[0]["Version"])
        elif args.critical:
            if values[0]["Version"] != values[0]["OldVersion"]:
                __exit_critical(socket.gethostname() + " - " + values[0]["Package"] + " " + values[0]["ExtraInfo"] + ", newest is " + values[0]["Version"])
        __exit_ok(socket.gethostname() + " - " + values[0]["Package"] + " " + values[0]["ExtraInfo"])

    elif args.info == "disk-status":
        values = getValueFromPBS("disk")
        message = ""
        error = False
        for entry in values:
            line = "Name: " + entry["vendor"].replace(" ", "") + " " + entry["model"] + ", Size: " + KBToTB(entry["size"]) + " GB, Path: " + entry["devpath"] + "\n"
            if entry["status"].upper() == "OK" or entry["status"].upper() == "PASSED" or entry["status"].upper() == "UNKNOWN":
                message += "[OK] " + line
            else:
                message += "[CRITICAL] " + line
                error = True

        if error:
            __exit_critical("One or more disk are in error state. Please check: \n\n" + message)
        else:
            __exit_ok("All disks are ok! \n\n" + message)

    elif args.info == "datastore-status":
        if args.warning == None or args.critical == None:
            __exit_unknown("Commandline incomplete!")
        values = __execute(["sudo", "proxmox-backup-debug", "api", "get", "status/datastore-usage", "--output-format json"])
        message = ""
        prefdata = ""
        error = False
        warning = False
        for entry in values:
            name = entry["store"]
            total = entry["total"]
            used = entry["used"]
            estimatedFullDate = dt.fromtimestamp(entry["estimated-full-date"])
            now = dt.now()
            timespanEstimatedFullDate = (estimatedFullDate - now)
            if timespanEstimatedFullDate.days < int(args.warning):
                warning = True
            if timespanEstimatedFullDate.days < int(args.critical):
                error = True

            message += name + " - Usage: " + KBToTB(used) + " / " + KBToTB(total) + " TB = " + str(round((used / total) * 100, 2)) + "% - Estimated Full: " + estimatedFullDate.strftime('%d.%m.%Y %H:%M:%S') + " (" + str(timespanEstimatedFullDate.days) + " days)"
            prefdata += " " + name + "_usage=" + KBToTB(used) + ";" + KBToTB(total, 0.8) + ";" + KBToTB(total, 0.9) + ";0;" + KBToTB(total)
            prefdata += " " + name + "_full=" + str(timespanEstimatedFullDate.days)

        if error:
            __exit_critical(message + " |" + prefdata)
        elif warning:
            __exit_warning(message + " |" + prefdata)
        else:
            __exit_ok(message + " |" + prefdata)

    elif args.info == "garbage-collection-status":
        values = __execute(["sudo", "proxmox-backup-debug", "api", "get", "nodes/" + socket.gethostname() + "/tasks", "--typefilter garbage_collection", "--limit 2", "--output-format json"])
        for entry in values:
            if "endtime" in entry:
                starttime = dt.fromtimestamp(entry["starttime"])
                endtime = dt.fromtimestamp(entry["endtime"])
                timespan = (endtime - starttime)
                if entry["status"] == "OK":
                    __exit_ok("Last " + entry["worker_type"] + " at " + entry["worker_id"] + " was successful! Runtime was " + str(timespan))
                __exit_warning("Last " + entry["worker_type"] + " at " + entry["worker_id"] + " failed!")

if __name__=="__main__":
    main()