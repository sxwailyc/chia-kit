#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def is_root():
    return os.getuid() == 0


def get_mounteds():
    disks = []
    command = "mount | grep ^/dev | awk '{print $1}'"
    r = os.popen(command)
    lines = r.readlines()
    for line in lines:
        line = line.replace("\n", "")
        disks.append(line)

    return disks


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
            if os.path.isfile(file) and name.endswith(".plot"):
                chia_dirs.append(name)
                break

    return chia_dirs


def get_file_systems():
    fss = []
    command = 'blkid | grep " UUID"'
    r = os.popen(command)
    lines = r.readlines()
    for line in lines:
        line = line.replace('\n', '')
        datas = line.split(" ")
        disk, uuid, ftype = "", "", ""
        for data in datas:
            if data.startswith("/dev"):
                disk = data.replace(":", "").replace("：", "")
            if data.startswith("UUID="):
                uuid = data.replace("UUID=", "").replace('"', "")
            if data.startswith("TYPE="):
                ftype = data.replace("TYPE=", "").replace('"', "")

        if ftype in ('vfat', 'swap'):
            continue

        fss.append({
            "disk": disk,
            "uuid": uuid,
            "type": ftype
        })
    return fss


def format_number(i):
    if i <= 9:
        return '0%s' % i
    return i


def get_mount_type(ftype):
    if ftype == 'ntfs':
        return 'ntfs-3g'
    elif ftype in ('xfs', 'f2fs', 'ext4'):
        return ftype


class DiskUtil:
    MOUNT = "mount"
    MKFS = "mkfs"
    ADD_DIR = "add_dir"

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
        elif self.action == DiskUtil.MKFS:
            self.add_dir()
        else:
            log("unknow action:%s" % self.action)

    def mount(self):
        if not is_root():
            log("must run by root")

        fss = get_file_systems()
        mounted_disks = get_mounteds()
        seq = 1
        for fs in fss:
            disk = fs["disk"]
            ftype = fs["type"]
            uuid = fs["uuid"]
            if disk in mounted_disks:
                continue
            mounted_point = os.path.join(self.folder, "%s%s" % (self.prefix, format_number(seq)))
            if not os.path.exists(mounted_point):
                os.makedirs(mounted_point)

            mount_cmd = "mount -t %s /dev/disk/by-uuid/%s %s%s%s" % (
                get_mount_type(ftype), uuid, self.folder, self.prefix, format_number(seq))
            seq += 1
            print(mount_cmd)
            if self.execute:
                os.system(mount_cmd)

    def add_dir(self):
        chia_dirs = get_chia_dirs(self.folder)
        seq = 1
        for chia_dir in chia_dirs:
            cmd = "chia plots add -d %s" % chia_dir
            print(cmd)
            if self.execute:
                os.system(cmd)

    def mkfs(self):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
           This script is mount disk or make file system.
        """)
    parser.add_argument("action", help="mount: mount disk; mkfs: make file system; add_dir: add chia dir ",
                        choices=['mount', 'mkfs'])
    parser.add_argument("-d", "--dir", help="mount dir, defautl is /mnt/", default="/mnt/")
    parser.add_argument("-p", "--prefix", help="mount sub foler preifx, default is empty", default="")
    parser.add_argument("-e", "--execute", action="store_true",
                        help="whether perform operation, default is Flase",
                        default=False)

    args = parser.parse_args()

    action = args.action
    folder = args.dir
    if not folder.endswith("/"):
        foler = folder + "/"
    prefix = args.prefix
    execute = args.execute
    util = DiskUtil(action, folder, prefix, execute)
    util.start()
