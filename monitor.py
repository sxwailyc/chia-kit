#!/usr/bin/python
# -*- coding: utf-8 -*-

from subprocess import Popen, PIPE

import socket

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
    s = ""
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = line.replace("\n", "")
        s += line

    return s

def is_root():
    return os.getuid() == 0


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    call_hdsentinel()


if __name__ == '__main__':
    if is_root():
        print("must run by root")
    """parser = argparse.ArgumentParser(description="""
    #   This script is for move plot files from ssd to hdd.
    """)
    #parser.add_argument("--host-name", metavar="", help="sub dir name, default is empty", default='')
    #parser.add_argument("--secret", metavar="", help="scan interval, default is 30 seconds")
    #args = parser.parse_args()
    #secret = args.secret
    #host_name = args.host_name"""
    main(secret='', host_name='')
