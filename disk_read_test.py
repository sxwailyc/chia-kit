#!/usr/bin/python
# -*- coding: utf-8 -*-

from subprocess import getoutput


def split_line(line, separator=" "):
    datas = line.split(separator)
    ndatas = []
    for data in datas:
        if data:
            ndatas.append(data)
    return ndatas


def format_device(device):
    if device.startswith("/dev/sd"):
        if device[-1].isdigit():
            device = device[:-1]
    elif device.startswith("/dev/nvme"):
        if device[-1].isdigit():
            device = device[:-2]

    return device


def main():
    cmd = "df -lmT | grep ^/dev/"
    out = getoutput(cmd)
    lines = out.split("\n")
    usage_infos = {}
    if not lines:
        return usage_infos
    for line in lines:
        if not line:
            continue
        datas = split_line(line)
        device = datas[0]
        mount_point = datas[6]
        if mount_point == '/' or mount_point.startswith("/boot/"):
            continue

        devname = format_device(device)

        test_cmd = "time dd if=/dev/%s of=/dev/sdc1 bs=1M count=1000 iflag=direct" % devname
        print(test_cmd)
        print(getoutput(test_cmd))


if __name__ == '__main__':
    main()


