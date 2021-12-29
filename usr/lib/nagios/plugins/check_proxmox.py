#!/usr/bin/env python3

###################################################
#
# Name: check_proxmox.py
# Version: 1.0
# Date: 03.05.2021
# Author: lukas.spitznagel@netzint.de
#
###################################################

#
# This to check: Cluster health, pve version, disk-health, vm-status / snapshots
#
# cluster-status: pvesh get /cluster/status --output-format json-pretty
# ceph-status: pvesh get /cluster/ceph/status --output-format json-pretty
# storage-status: pvesh get /nodes/$(hostname)/storage --output-format json-pretty
# disk-status: pvesh get /nodes/$(hostname)/disks/list --output-format json-pretty
# host-version: pvesh get /version --output-format json-pretty
# vms-status: pvesh get /nodes/$(hostname)/qemu --output-format json-pretty
# vms-snapshot: pvesh get /nodes/$(hostname)/qemu/701/snapshot --output-format json-pretty | name != current
#

import optparse
import os
import socket
import json
import datetime

from datetime import datetime as dt

def __execute(command):
    commandline = ""
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

def getValueFromProxmox(url):
    url = url.replace("$hostname$", socket.gethostname())
    return json.loads(__execute(["sudo", "pvesh", "get", url, "--output-format json", "2> /dev/null"]))

def main():
    optp = optparse.OptionParser()
    optp.add_option('-i', '--info', help='host-version, cluster-status, ceph-status, storage-status, disk-status, vms-status', dest='info')
    optp.add_option('-w', '--warning', help='Warning in percent', dest='warning')
    optp.add_option('-c', '--critical', help='Critical in percent', dest='critical')
    opts, args = optp.parse_args()

    if opts.info == "host-version":
        __exit_ok(socket.gethostname() + " - Proxmox Version: " + getValueFromProxmox("/version")["version"])

    elif opts.info == "cluster-status":
        json = getValueFromProxmox("/cluster/status")
        output = ""
        error = False
        for entry in json:
            if entry["type"] == "node":
                line = entry["name"] + " with IP " + entry["ip"] + " is "
                if entry["online"] == 1:
                    line += "online \n"
                    output += "[OK] " + line
                else:
                    line += "offline \n"
                    error = True
                    output += "[CRITICAL] " + line
        if error:
            __exit_critical("One or more host(s) are offline! \n\n" + output)
        else:
            __exit_ok("Alle host(s) are ok! \n\n" + output)

    elif opts.info == "ceph-status":
        json = getValueFromProxmox("/cluster/ceph/status")
        if json["health"]["status"] == "HEALTH_OK":
            __exit_ok("Ceph is healthy!")
        elif json["health"]["status"] == "HEALTH_WARN":
            message = ""
            for key in json["health"]["checks"].keys():
                message += "Warning: " + key + " Message: " + json["health"]["checks"][key]["summary"]["message"] + "\n"
            __exit_warning("Ceph is in warn state. Please check: \n\n" + message)
        elif json["health"]["status"] == "HEALTH_ERR":
            message = ""
            for key in json["health"]["checks"].keys():
                message += "Error: " + key + " Message: " + json["health"]["checks"][key]["summary"]["message"] + "\n"
            __exit_warning("Ceph is in error state. Please check: \n\n" + message)
        else:
            __exit_unknown("Unable to get ceph health status!")

    elif opts.info == "storage-status":
        if opts.warning == None or opts.critical == None:
            __exit_unknown("Commandline incomplete!")
        json = getValueFromProxmox("/nodes/$hostname$/storage")
        message = ""
        error = False
        warning = False
        for entry in json:
            if entry["active"] == 1:
                usage = round((entry["used"] / entry["total"]) * 100)
                line = "Name: " + entry["storage"] + ", Usage: " + str(usage) + "% (" + str(round(entry["used"] / 1024 / 1024 / 1024)) + " GB / " + str(round(entry["total"] / 1024 / 1024 / 1024)) + " GB) \n"
                if usage >= int(opts.warning) and usage < int(opts.critical):
                    warning = True
                    message += "[WARNING] " + line
                elif usage >= int(opts.critical):
                    critical = True
                    message += "[CRITICAL] " + line
                else:
                    message += "[OK] " + line

        if error:
            __exit_critical("Storage critical. Please check: \n\n" + message)
        elif warning:
            __exit_warning("Storage warning. Please check: \n\n" + message)
        else:
            __exit_ok("Storage OK! \n\n" + message)

    elif opts.info == "disk-status":
        json = getValueFromProxmox("/nodes/$hostname$/disks/list")
        message = ""
        error = False
        for entry in json:
            if "unknown" in entry["vendor"]:
                line = "Name: " + entry["model"]
            else:
                line = "Name: " + entry["vendor"].replace(" ", "") + " " + entry["model"]
                
            line += ", Size: " + str(round(entry["size"] / 1024 / 1024 / 1024)) + " GB, Path: " + entry["devpath"] + "\n"
            
            if entry["health"] == "OK" or entry["health"] == "PASSED":
                message += "[OK] " + line
            elif entry["health"] == "UNKNOWN":
                message += "[OK] " + line
            else:
                message += "[CRITICAL] " + line
                error = True

        if error:
            __exit_critical("One or more disk are in error state. Please check: \n\n" + message)
        else:
            __exit_ok("All disks are ok! \n\n" + message)

    elif opts.info == "vms-status":
        if opts.warning == None or opts.critical == None:
            __exit_unknown("Commandline incomplete!")
        json = getValueFromProxmox("/nodes/$hostname$/qemu")
        message = ""
        error = False
        warning = False
        for entry in json:
            json2 = getValueFromProxmox("/nodes/$hostname$/qemu/" + str(entry["vmid"]) + "/snapshot")
            line = "Name: " + entry["name"] + "(" + str(entry["vmid"]) + "), Status: " + entry["status"] + ", Uptime: " + str(datetime.timedelta(seconds=int(entry["uptime"])))
            if len(json2) > 1:
                line += ", " + str(len(json2) - 1) + " Snapshot(s): "
                tmp_error = False
                tmp_warning = False
                for snapshot in json2:
                    if snapshot["name"] != "current":
                        snapshot_age = datetime.timedelta(seconds=(dt.timestamp(dt.now()) - snapshot["snaptime"]))
                        line += snapshot["name"] + " (" + str(snapshot_age.days) + " days), "
                        if snapshot_age.days > int(opts.warning):
                            if snapshot_age.days > int(opts.critical):
                                tmp_error = True
                            else:
                                tmp_warning = True
                if tmp_error:
                    message += "[CRITICAL] " + line[:-2] + "\n"
                    error = True
                elif tmp_warning:
                    message += "[WARNING] " + line[:-2] + "\n"
                    warning = True
                else:
                    message += "[OK] " + line[:-2] + "\n"
            else:
                message += "[OK] " + line + "\n"
        if error:
            __exit_critical("One or more vms have old snapshots. Please check: \n\n" + message)
        elif warning:
            __exit_warning("One or more vms have old snapshots. Please check: \n\n" + message)
        else:
            __exit_ok("All VMs are OK! \n\n" + message)



    else:
        __exit_unknown("Commandline incomplete!")


if __name__=="__main__":
    main()
