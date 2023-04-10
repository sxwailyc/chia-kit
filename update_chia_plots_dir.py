#!/usr/bin/python
# -*- coding: utf-8 -*-

from subprocess import getoutput

import argparse
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def batch_get_chia_dirs(base_dirs):
    chia_dirs = []
    for base_dir in base_dirs:
        chia_dirs.extend(get_chia_dirs(base_dir))
    return sorted(chia_dirs)


def get_chia_dirs(base_dir):
    chia_dirs = []
    if not dir or not os.path.isdir(base_dir):
        return []
    names = os.listdir(base_dir)
    for name in names:
        name = os.path.join(base_dir, name)
        if not os.path.isdir(name):
            continue
        files = os.listdir(name)
        for file in files:
            file = os.path.join(name, file)
            if os.path.isfile(file):
                if file.endswith(".plot"):
                    chia_dirs.append(name)
                    break
            else:
                sub_files = os.listdir(file)
                for sub_file in sub_files:
                    sub_file = os.path.join(file, sub_file)
                    if os.path.isfile(sub_file) and sub_file.endswith(".plot"):
                        chia_dirs.append(file)
                        break

    return sorted(chia_dirs)


class ChiaPlotsDirUpdator:

    def __init__(self, bin, folers, grep, grepv, execute, remove):
        self.bin = bin
        self.folers = folers
        self.grep = grep
        self.grepv = grepv
        self.execute = execute
        self.remove = remove

    def main(self):
        if self.remove:
            self.remove_dir()
        self.add_dir()

    def remove_dir(self):
        cmd = "%s plots show" % self.bin
        out = getoutput(cmd)
        lines = out.split("\n")
        start = False
        for line in lines:
            if line.find('chia plots check') > 0:
                start = True
                continue
            if not start:
                continue
            if not line:
                continue
            cmd = '%s plots remove -d %s' % (self.bin, line)
            print(cmd)
            if self.remove and self.execute:
                os.system(cmd)

    def add_dir(self):
        chia_dirs = batch_get_chia_dirs(self.folers)
        for chia_dir in chia_dirs:
            if self.grep:
                if chia_dir.find(self.grep) == -1:
                    continue
            if self.grepv:
                if chia_dir.find(self.grepv) != -1:
                    continue

            cmd = "%s plots add -d %s" % (self.bin, chia_dir)
            print(cmd)
            if self.execute:
                os.system(cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
           This script is auto update chia plots directory.
        """)
    parser.add_argument("-b", "--bin", help="chia bin path, default is chia", default="chia")
    parser.add_argument("-d", "--dir", nargs='+', action='append', help="mount dir, defautl is [/mnt/]")
    parser.add_argument("-g️", "--grep", help="equal grep ", default="")
    parser.add_argument("-v", "--grepv", help="equal grep -v ", default="")
    parser.add_argument("-e", "--execute", action="store_true", help="whether perform operation, default is False",
                        default=False)
    parser.add_argument("-r", "--remove", action="store_true",
                        help="whether remove all the dir in chia config first, default is False", default=False)

    args = parser.parse_args()

    bin = args.bin
    folders = args.dir
    if folders:
        folders = [x[0] for x in folders]
    else:
        if not folders:
            folders = ['/mnt/']
    grep = args.grep
    grepv = args.grepv
    execute = args.execute
    remove = args.remove
    updator = ChiaPlotsDirUpdator(bin, folders, grep, grepv, execute, remove)
    updator.main()
