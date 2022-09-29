#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
import time
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def is_root():
    return os.getuid() == 0


def get_file_systems():
    fss = []
    command = 'blkid | grep " UUID"'
    r = os.popen(command)
    lines = r.readlines()
    for line in lines:
        print(line)
    return fss


class DiskUtil:
    MOUNT = "mount"
    MKFS = "mkfs"

    def __init__(self, action, folder, prefix, execute=False):
        self.action = action
        self.folder = folder
        self.prefix = prefix
        self.execute = execute

    def start(self):
        if self.action == DiskUtil.MOUNT:
            self.mount()
        elif self.action == DiskUtil.MKFS:
            self.mkfs()
        else:
            log("unknow action:%s" % self.action)

    def mount(self):
        if not is_root():
            log("must run by root")

        fss = get_file_systems()
        for fs in fss:
            print(fs)

    def mkfs(self):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
           This script is mount disk or make file system.
        """)
    parser.add_argument("action", help="mount: mount disk; mkfs: make file system ",
                        choices=['mount', 'mkfs'])
    parser.add_argument("-d", "--dir", help="mount dir, defautl is /mnt", default="/mnt")
    parser.add_argument("-p", "--prefix", help="mount sub foler preifx, default is empty", default="")
    parser.add_argument("-e", "--execute", action="store_true",
                        help="whether perform operation, default is Flase",
                        default=False)

    args = parser.parse_args()

    action = args.action
    folder = args.dir
    prefix = args.prefix
    execute = args.execute
    util = DiskUtil(action, folder, prefix, execute)
    util.start()
