#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def format_number(i):
    if i <= 9:
        return '0%s' % i
    return i


def size_to_gb(size):
    return round(size / 1024 / 1024 / 1024, 2)


def get_free(disk):
    _, _, free = shutil.disk_usage(disk)
    return size_to_gb(free)


def remove_one_plot(_dir, suffix="plot"):
    """get all the plot files"""
    if not _dir or not os.path.isdir(_dir):
        return
    names = os.listdir(_dir)
    for name in names:
        name = os.path.join(_dir, name)
        if os.path.isfile(name) and name.endswith(".%s" % suffix):
            log("start to remove: %s" % name)
            os.remove(name)
            return


def main():
    for i in range(1, 25):
        disk = "/mnt/chia%s/" % format_number(i)
        if not os.path.exists(disk):
            continue
        dir = "%schia_plot_k32_new" % disk
        free = get_free(disk)
        log("disk: %s, free size: %sGB" % (disk, free))
        if free <= 73:
            remove_one_plot(dir)


if __name__ == '__main__':
    main()
