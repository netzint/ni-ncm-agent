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
import docker

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

# def getAllDockerContainer():
#     resultString = __execute(["docker", "ps", "-a", "--format", "'{\"id\":\"{{ .ID }}\", \"name\":\"{{ .Names }}\", \"status\":\"{{ .Status }}\"}'"])
#     try:
#         result = json.loads(resultString)
#     except:
#         result = []
#         try:
#             for line in resultString.splitLines():
#                 result.append(line)
#         except:
#             return False
                
#     tmp = {}
#     for entry in result:
#         tmp[entry["name"]] = entry
#     return tmp

# def getDockerDetails(name):
#     result = json.loads(__execute(["docker", "inspect", name]))
#     return result[0]

# def countRunningContainers():
#     result = __execute(["docker", "ps", "|", "wc", "-l"])
#     return (int(result) - 1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required = False, help = "Name of docker container to be monitored (separated by ',')", default = "") 
    args = parser.parse_args()

    dockerClient = docker.from_env()
    containerList = dockerClient.containers.list()

    if len(containerList) == 0:
        if not args.name:
            __exit_ok("No containers currently running on this system!")
        # else:
        #     __exit_critical("All monitored containers are offline!")

    runningContainer = {}
    for container in containerList:
        runningContainer[container.name] = {
            "name": container.name,
            "image": container.image.tags[0],
            "status": container.status,
            "attrs": container.attrs
        }

    dockertocheck = []
    dockernottocheck = []

    if "," in args.name:
        for entry in args.name.split(","):
            if entry in runningContainer: # container should be monitored and is running, add container to dockertocheck array
                dockertocheck.append(runningContainer[entry])
                runningContainer.pop(entry)
            else: # container should be monitored but is not running, add dummy entry to dockertocheck array
                dockertocheck.append({"name": entry, "image": "n/a", "status": "off", "attrs": {}})
    else:
        if args.name != "":
            if args.name in runningContainer: # container should be monitored and is running, add container to dockertocheck array
                    dockertocheck.append(runningContainer[args.name])
                    runningContainer.pop(args.name)
            else: # container should be monitored but is not running, add dummy entry to dockertocheck array
                dockertocheck.append({"name": args.name, "image": "n/a", "status": "off", "attrs": {}})

    for entry in runningContainer:
        if "running" in runningContainer[entry]["status"]:
            dockernottocheck.append(runningContainer[entry])

    infoline = ""
    error = False

    for entry in dockertocheck:
        attrs = entry["attrs"]
        if "State" in attrs and attrs["State"]["Running"]:
            uptime = datetime.datetime.utcnow() - datetime.datetime.strptime(attrs["State"]["StartedAt"][:-4], '%Y-%m-%dT%H:%M:%S.%f')
            infoline += "[OK] " + entry["name"].replace("/", "") + " with image " + entry["image"] + ", Uptime: " + str(uptime).split(".")[0] + "\n"
        else:
            infoline += "[CRITICAL] " + entry["name"].replace("/", "") + " with image " + entry["image"] + " is not running!\n"
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
