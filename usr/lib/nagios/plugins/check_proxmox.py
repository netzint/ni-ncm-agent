#!/usr/bin/env python3

###################################################
#
# Name: check_proxmox.py
# Version: 1.0
# Date: 03.05.2021
# Author: lukas.spitznagel@netzint.de
#
###################################################

import argparse
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

def getValueFromProxmox(url, append=""):
    url = url.replace("$hostname$", socket.gethostname())
    return __execute(["sudo", "pvesh", "get", url, append, "--output-format json"])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--info', help='Info category to choose', required = True, choices=["host-version", "cluster-status", "ceph-status", "storage-status", "disk-status", "vms-status", "backup-status", "osd-status"], dest='info')
    parser.add_argument('-w', '--warning', help='Warning in percent', dest='warning')
    parser.add_argument('-c', '--critical', help='Critical in percent', dest='critical')
    args = parser.parse_args()

    if args.info == "host-version":
        __exit_ok(socket.gethostname() + " - Proxmox Version: " + getValueFromProxmox("/version")["version"])

    elif args.info == "cluster-status":
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

    elif args.info == "ceph-status":
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

    elif args.info == "storage-status":
        if args.warning == None or args.critical == None:
            __exit_unknown("Commandline incomplete!")
        json = getValueFromProxmox("/nodes/$hostname$/storage")
        message = ""
        prefdata = ""
        error = False
        warning = False
        for entry in json:
            if entry["active"] == 1:
                usage = round((entry["used"] / entry["total"]) * 100)
                line = "Name: " + entry["storage"] + ", Usage: " + str(usage) + "% (" + str(round(entry["used"] / 1024 / 1024 / 1024)) + " GB / " + str(round(entry["total"] / 1024 / 1024 / 1024)) + " GB) \n"
                
                prefdata += " " + entry["storage"] + "="
                prefdata += str(round(entry["used"] / 1024 / 1024 / 1024, 2)) + ";"
                prefdata += str(round(entry["total"] * (int(args.warning) / 100) / 1024 / 1024 / 1024, 2)) + ";"
                prefdata += str(round(entry["total"] * (int(args.critical) / 100) / 1024 / 1024 / 1024, 2)) + ";0;"
                prefdata += str(round(entry["total"] / 1024 / 1024 / 1024, 2))

                if usage >= int(args.warning) and usage < int(args.critical):
                    warning = True
                    message += "[WARNING] " + line
                elif usage >= int(args.critical):
                    critical = True
                    message += "[CRITICAL] " + line
                else:
                    message += "[OK] " + line

        if error:
            __exit_critical("Storage critical. Please check: \n\n" + message + " |" + prefdata)
        elif warning:
            __exit_warning("Storage warning. Please check: \n\n" + message + " |" + prefdata)
        else:
            __exit_ok("Storage OK! \n\n" + message + " |" + prefdata)

    elif args.info == "disk-status":
        json = getValueFromProxmox("/nodes/$hostname$/disks/list")
        message = ""
        error = False
        for entry in json:
            line = "Name: " + entry["vendor"].replace(" ", "") + " " + entry["model"] + ", Size: " + str(round(entry["size"] / 1024 / 1024 / 1024)) + " GB, Path: " + entry["devpath"] 
            if entry["health"] == "OK" or entry["health"] == "PASSED":
                message += "[OK] " + line + "\n"
            elif entry["health"] == "UNKNOWN":
                message += "[OK] " + line + " (RAID Controller, no SMART values!)\n" 
            else:
                message += "[CRITICAL] " + line + "\n"
                error = True

        if error:
            __exit_critical("One or more disk are in error state. Please check: \n\n" + message)
        else:
            __exit_ok("All disks are ok! \n\n" + message)

    elif args.info == "vms-status":
        if args.warning == None or args.critical == None:
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
                        if snapshot_age.days > int(args.warning):
                            if snapshot_age.days > int(args.critical):
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

    elif args.info == "backup-status":
        if args.warning == None or args.critical == None:
            __exit_unknown("Commandline incomplete!")
        backupPlans = {}
        for backup in getValueFromProxmox("/cluster/backup"):
            backupInfos = getValueFromProxmox("/cluster/backup/" + backup["id"])
            if "starttime" in backupInfos:
                backupPlans[backupInfos["starttime"]] = backupInfos
            elif "schedule" in backupInfos:
                backupPlans[backupInfos["schedule"]] = backupInfos

        json = getValueFromProxmox("/nodes/$hostname$/tasks", "--typefilter vzdump --limit 10")
        message = ""
        error = False
        warning = False
        critical = False

        for entry in json:
            if "starttime" in entry:
                starttime = dt.fromtimestamp(entry["starttime"])
            elif "schedule" in entry:
                starttime = dt.fromtimestamp(entry["schedule"])
            if starttime.strftime('%H:%M') in backupPlans:
                if "dow" in backupPlans[starttime.strftime('%H:%M')]:
                    dayschedule = backupPlans[starttime.strftime('%H:%M')]["dow"]
                else:
                    dayschedule = "daily"
                message += "Infos for backup '" + dayschedule + "' at '" + starttime.strftime('%H:%M') + "':\n"
                now = dt.now()
                timespanLastBackup = (now - starttime)
                timespanLastBackup = (timespanLastBackup.seconds / 60 / 60) + (timespanLastBackup.days * 24)

                json2 = getValueFromProxmox("/nodes/$hostname$/tasks/" + entry["upid"] + "/log", "--limit 9999999")
                backupTasks = {}
                lastBackupTask = None
                for line in json2:
                    if "INFO: Starting Backup of VM" in line["t"]:
                        pvid = line["t"].replace("INFO: Starting Backup of VM ", "").strip().split(" ")[0]
                        backupTasks[pvid] = {"name": "n/a", "size": "n/a", "time": "n/a", "rate": "n/a", "reuse": "n/a", "status": "success", "message": ""}
                        newBackupTask = True
                        lastBackupTask = pvid

                    if lastBackupTask is not None:
                        if "INFO: VM Name:" in line["t"]:
                            backupTasks[lastBackupTask]["name"] = line["t"].replace("INFO: VM Name:", "").strip()
                        if "INFO: transferred" in line["t"]:
                            backupTasks[lastBackupTask]["size"] = line["t"].split(" ")[2]
                            backupTasks[lastBackupTask]["time"] = line["t"].split(" ")[5]
                            backupTasks[lastBackupTask]["rate"] = line["t"].split(" ")[7].replace("(", "").replace(")", "")
                        if "INFO: backup was done" in line["t"]:
                            backupTasks[lastBackupTask]["reuse"] = line["t"].split(" ")[8].replace("(", "").replace(")", "")
                        if "ERROR: Backup of VM " + lastBackupTask + " failed" in line["t"]:
                            backupTasks[lastBackupTask]["status"] = "failed"
                            backupTasks[lastBackupTask]["message"] = line["t"]

                for backup in backupTasks:
                    if backupTasks[backup]["status"] == "success":
                        message += "  [OK] " + backupTasks[backup]["name"] + " (" + backup + ") - Transfer " + backupTasks[backup]["size"] + " GiB in " + backupTasks[backup]["time"] + " seconds with " + backupTasks[backup]["rate"] + " MiB/s\n"
                    else:
                        message += "  [CRITICAL] " + backupTasks[backup]["name"] + " (" + backup + ") - Message: " + backupTasks[backup]["message"] + "\n"
                        error = True

                message += "\n\n"

                if timespanLastBackup > int(args.warning):
                    warning = True
                elif timespanLastBackup > int(args.critical):
                    critical = True

                break

        if error:
            __exit_critical("One or more backup(s) failed! Please check the log for more details!\n\n" + message)

        if warning:
            __exit_warning("Last backup was " + str(round(timespanLastBackup, 2)) + " ago and is older than " + args.warning + " hour(s)!\n\n" + message)
        elif critical:
            __exit_critical("Last backup was " + str(round(timespanLastBackup, 2)) + " ago and is older than " + args.critical  + " hour(s)!\n\n" + message)
        else:
            __exit_ok("Backups ok! Last backup was " + str(round(timespanLastBackup, 2)) + " hour(s) ago.\n\n" + message)

    elif args.info == "osd-status":
        if args.warning == None or args.critical == None:
            __exit_unknown("Commandline incomplete!")

        osdList = __execute(["sudo", "ceph", "osd", "df", "tree", "-f", "json"])

        message = ""
        error = False
        warning = False

        for osd in osdList["nodes"]:
            if osd["id"] > 0:

                total = osd["kb"]
                used = osd["kb_used"]
                percent = (used / total) * 100

                if osd["status"] == "up":
                    if percent >= int(args.warning) and percent < int(args.critical):
                        message += "[CRITICAL] "
                    elif percent >= int(args.critical):
                        message += "[WARNING] "
                    else:
                        message += "[OK] "
                else:
                    message += "[CRITICAL] "

                message +=  osd["name"] + " (" + osd["device_class"].upper() + ") - " + str(round(used / 1024 / 1024 / 1024, 2)) + " / " + str(round(total / 1024 / 1024 / 1024, 2)) + " TB = " + str(round(percent, 2)) + "% ussage\n"

        if error:
            __exit_critical("Some of the OSDs have a problem!\n\n" + message)
        elif warning:
            __exit_warning("Some OSDs soon will have a problem!\n\n" + message)
        else:
            __exit_ok("All OSDs are up!\n\n" + message)

    else:
        __exit_unknown("Commandline incomplete!")


if __name__=="__main__":
    main()
