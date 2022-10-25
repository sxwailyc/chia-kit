#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import socket
import json
import requests

from subprocess import Popen, PIPE, getoutput

import argparse
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def call_hdsentinel():
    """cal hdsentinel"""
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "hdsentinel-019c-x64")
    p = Popen(cmd, stdout=PIPE)
    disks = []
    model_id, size, temperature, health, device = "", 0, 0, 0, ""
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = line.decode('utf-8')
        if line.startswith("HDD Device"):
            if device:
                disks.append({
                    "model_id": model_id,
                    "size": size,
                    "temperature": temperature,
                    "health": health,
                    "device": device,
                    "serial_no": serial_no
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


def split_line(line):
    datas = line.split(" ")
    ndatas = []
    for data in datas:
        if data:
            ndatas.append(data)
    return ndatas


def get_usage_infos():
    cmd = "df -lm | grep /dev/sd"
    out = getoutput(cmd)
    lines = out.split("\n")
    usage_infos = {}
    for line in lines:
        datas = split_line(line)
        device = datas[0]
        usage = int(datas[2])
        mount_point = datas[5]
        if mount_point == '/' or mount_point.startswith("/boot/"):
            continue
        usage_infos[format_device(device)] = {
            'usage': usage,
            'mount_point': mount_point
        }

    return usage_infos


def get_chia_count(base_dir):
    count = 0
    if not dir or not os.path.isdir(base_dir):
        return count
    names = os.listdir(base_dir)
    for name in names:
        name = os.path.join(base_dir, name)
        if os.path.isfile(name):
            if name.endswith(".plot"):
                count += 1
        else:
            files = os.listdir(name)
            for file in files:
                file = os.path.join(name, file)
                if os.path.isfile(file):
                    if file.endswith(".plot"):
                        count += 1
                else:
                    sub_files = os.listdir(file)
                    for sub_file in sub_files:
                        sub_file = os.path.join(file, sub_file)
                        if os.path.isfile(sub_file) and sub_file.endswith(".plot"):
                            count += 1

    return count


def format_device(device):
    if device[-1].isdigit():
        device = device[:-1]
    return device


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


def report(secret, machine_info, disk_infos):
    data = json.dumps({
        "secret": secret,
        "machine": machine_info,
        "disks": disk_infos
    })
    requests.post("http://api.mingyan.com/api/chia/monitor", data)


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    disk_infos = call_hdsentinel()
    usage_infos = get_usage_infos()
    disk_count = 0
    all_size = 0
    all_usage = 0
    all_plot_count = 0
    for disk_info in disk_infos:
        device = disk_info['device']
        size = disk_info['size']
        usage_info = usage_infos.get(device, {})
        usage = usage_info.get(device, 0)
        mount_point = usage_info.get(device, "")
        plot_count = get_chia_count(mount_point)
        disk_count += 1
        all_plot_count += plot_count
        all_size += size
        all_usage += usage
        disk_info["usage"] = usage
        disk_info["plot_count"] = plot_count
        disk_info["mount_point"] = mount_point

    machine_info = {
        'host_name': host_name,
        'plot_count': all_plot_count,
        'disk_count': disk_count,
        'all_usage': all_usage,
        'all_size': all_size,
    }

    report(secret, machine_info, disk_infos)


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
