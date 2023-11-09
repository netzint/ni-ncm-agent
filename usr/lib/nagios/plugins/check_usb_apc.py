#!/usr/bin/env python3

###################################################
#
# Name: check_usb_apc.py
# Version: 1.0
# Date: 07.03.2022
# Author: lukas.spitznagel@netzint.de
#
###################################################

import argparse
import os
import subprocess

def __execute(command):
    res = subprocess.Popen(command, stdout=subprocess.PIPE)
    res.wait()
    return { "return_code": res.returncode, "output": res.stdout.read().decode("utf-8") }

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--info', help='Info category to choose', required = True, choices=["VERSION", "MODEL", "STATUS", "LINEV", "LOADPCT", "BCHARGE", "TIMELEFT", "BATTDATE"], dest='info')
    parser.add_argument('-w', '--warning', help='Warning value', dest='warning', type=int)
    parser.add_argument('-c', '--critical', help='Critical value', dest='critical', type=int)
    parser.add_argument('-r', '--reverse', help='Reverse the result', dest='reverse', action='store_true')
    parser.add_argument('-p', '--prefdata', help='Store prefdata', dest='prefdata', action='store_true')
    args = parser.parse_args()

    result = __execute(["/usr/sbin/apcaccess", "-p", args.info])

    if result["return_code"] == 0:
        value = result["output"].split(" ")[0]
        message = "Value = " + result["output"].replace("\n", "")
        if args.prefdata:
            message += " | " + args.info.lower() + "=" + str(value)

        if args.warning and args.critical:
            if args.prefdata:
                message += ";" + str(args.warning) + ";" + str(args.critical)
            if args.reverse:
                if float(value) < args.warning:
                    if float(value) < args.critical:
                        __exit_critical(message)
                    else:
                        __exit_warning(message)
                __exit_ok(message)
            else:
                if float(value) > args.warning:
                    if float(value) > args.critical:
                        __exit_critical(message)
                    else:
                        __exit_warning(message)
                __exit_ok(message)
        else:
            __exit_ok(message)
    __exit_unknown("Could not get value. Please check if apcaccess is installed and configured!")


if __name__=="__main__":
    main()