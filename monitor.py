#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import socket

from subprocess import Popen, PIPE

import argparse
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def call_hdsentinel():
    """cal hdsentinel"""
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "hdsentinel-019c-x64")
    last_line, line = None, None
    p = Popen(cmd, stdout=PIPE)
    disks = []
    model_id, size, temperature, health, device = "", 0, 0, 0, ""
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = line.deocde('utf-8')
        if line.startswith("HDD Device"):
            if device:
                disks.append({
                    "model_id": model_id,
                    "size": size,
                    "temperature": temperature,
                    "health": health,
                    "device": device
                })
            device = get_value(line)
        if line.startswith("HDD Model ID"):
            model_id = get_value(line)
        if line.startswith("HDD Serial No"):
            serial_no = get_value(line)
        if line.startswith("HDD Size"):
            size = format_size(get_value(line))
        if line.startswith("Temperature"):
            temperature = format_temperature(get_value(line))
        if line.startswith("Health"):
            health = format_health(get_value(line))

    return disks


def get_value(line):
    datas = line.split(":")
    return datas[1].strip()

def format_size(s):
    return int(s.replace("MB", ""))


def format_temperature(s):
    return int(s.replace("°C", ""))


def format_health(s):
    return int(s.replace("%", ""))


def is_root():
    return os.getuid() == 0


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    call_hdsentinel()


if __name__ == '__main__':
    if not is_root():
        print("must run by root")
        sys.exit(0)

    """parser = argparse.ArgumentParser(description="""
    #   This script is for move plot files from ssd to hdd.
    """)
    #parser.add_argument("--host-name", metavar="", help="sub dir name, default is empty", default='')
    #parser.add_argument("--secret", metavar="", help="scan interval, default is 30 seconds")
    #args = parser.parse_args()
    #secret = args.secret
    #host_name = args.host_name"""
    main(secret='', host_name='')
