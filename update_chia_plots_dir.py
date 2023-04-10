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

    def __init__(self, bin, folers, grep, grepv, execute, clean):
        self.bin = bin
        self.folers = folers
        self.grep = grep
        self.grepv = grepv
        self.execute = execute
        self.clean = clean

    def main(self):
        self.add_dir()

    def get_present_dirs(self):
        cmd = "%s plots show" % self.bin
        out = getoutput(cmd)
        lines = out.split("\n")
        start = False
        present_dirs = []
        for line in lines:
            if line.find('chia plots check') > 0:
                start = True
                continue
            if not start:
                continue
            if not line:
                continue
            present_dirs.append(line)

        return present_dirs

    def add_dir(self):
        present_dirs = self.get_present_dirs()
        chia_dirs = batch_get_chia_dirs(self.folers)
        chia_filter_dirs = []
        remove_dirs = []
        for chia_dir in chia_dirs:
            if self.grep:
                if chia_dir.find(self.grep) == -1:
                    continue
            if self.grepv:
                if chia_dir.find(self.grepv) != -1:
                    continue
            chia_filter_dirs.append(chia_dir)

        new, remove = 0, 0
        for present_dir in present_dirs:
            if present_dir not in chia_filter_dirs:
                cmd = '%s plots remove -d %s' % (self.bin, present_dir)
                print(cmd)
                if self.execute:
                    os.system(cmd)
                remove_dirs.append(present_dir)
                remove += 1

        for chia_filter_dir in chia_filter_dirs:
            cmd = "%s plots add -d %s" % (self.bin, chia_filter_dir)
            print(cmd)
            if self.execute:
                os.system(cmd)
            new += 1

        log("add %s dirs, remove %s dirs" % (new, remove))
        log("add dirs:")
        for remove_dir in remove_dirs:
            log("%s-%s" % ("\t" * 4, remove_dir))
        log("remove dirs:")
        for chia_filter_dir in chia_filter_dirs:
            log("%s+%s" % ("\t" * 4, chia_filter_dir))


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
    parser.add_argument("-c", "--clean", action="store_true",
                        help="whether clean all the dir in chia config", default=False)

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
    clean = args.clean
    updator = ChiaPlotsDirUpdator(bin, folders, grep, grepv, execute, clean)
    updator.main()
