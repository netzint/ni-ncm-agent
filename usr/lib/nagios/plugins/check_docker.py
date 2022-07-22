#!/usr/bin/env python3

###################################################
#
# Name: check_docker.py
# Version: 1.0
# Date: 11.05.2021
# Author: lukas.spitznagel@netzint.de
#
###################################################

import argparse
import os
import json
import datetime

def __execute(command):
    commandline = "sudo "
    for cmd in command:
        commandline += cmd + " "
    stream = os.popen(commandline)
    return stream.read()

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



def getAllDockerContainer():
    result = json.loads(__execute(["docker", "ps", "-a", "--format", "'{\"id\":\"{{ .ID }}\", \"name\":\"{{ .Names }}\", \"status\":\"{{ .Status }}\"}'", "|", "jq", "--slurp"]))
    tmp = {}
    for entry in result:
        tmp[entry["name"]] = entry
    return tmp

def getDockerDetails(name):
    result = json.loads(__execute(["docker", "inspect", name]))
    return result[0]

def countRunningContainers():
    result = __execute(["docker", "ps", "|", "wc", "-l"])
    return (int(result) - 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required = False, help = "Name of docker container to be monitored (separated by ',')", default = "") 
    args = parser.parse_args()

    if countRunningContainers() == 0:
        if not args.name:
            __exit_ok("No containers currently running on this system!")
        else:
            __exit_critical("All monitored containers are offline!")

    docker = getAllDockerContainer()

    dockertocheck = []
    dockernottocheck = []

    if "," in args.name:
        for entry in args.name.split(","):
            if entry in docker:
                dockertocheck.append(getDockerDetails(entry))
                docker.pop(entry)
            else:
                dockertocheck.append({"Name": entry, "Config": {"Image": "n/a"}, "State": {"Running": False}})
    else:
        if args.name in docker:
            dockertocheck.append(getDockerDetails(args.name))
            docker.pop(args.name)

    for entry in docker:
        if "Up" in docker[entry]["status"]:
            dockernottocheck.append(docker[entry])

    infoline = ""
    error = False

    for entry in dockertocheck:
        if entry["State"]["Running"]:
            uptime = datetime.datetime.now() - datetime.datetime.strptime(entry["State"]["StartedAt"][:-4], '%Y-%m-%dT%H:%M:%S.%f')
            infoline += "[OK] " + entry["Name"].replace("/", "") + " with image " + entry["Config"]["Image"] + ", Uptime: " + str(uptime).split(".")[0] + "\n"
        else:
            infoline += "[CRITICAL] " + entry["Name"].replace("/", "") + " with image " + entry["Config"]["Image"] + " is not running!\n"
            error = True

    if len(dockernottocheck) >= 1:
        infoline += "\nSome online containers are not in monitoring:\n"
        for entry in dockernottocheck:
            infoline += " - " + entry["name"] + "\n"

    if error:
        __exit_critical("Some monitored containers are offline!\n\n" + infoline)
    else:
        __exit_ok("All monitored containers are online!\n\n" + infoline)



if __name__=="__main__":
    main()
