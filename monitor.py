#!/usr/bin/python
# -*- coding: utf-8 -*-

import fcntl
import sys
import socket
import json
import time

import requests

from subprocess import Popen, PIPE, getoutput

import argparse
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def to_int(s):
    try:
        return int(s)
    except:
        return 0


def call_hdsentinel(devname, print_info):
    """call hdsentinel"""
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "hdsentinel-019c-x64")
    p = Popen([cmd, "-dev", devname, "-solid"], stdout=PIPE)
    disks = []
    # device, temperature, health, power_time, model_id, serial_no, size
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = line.decode('utf-8')
        line = line.replace("\n", "")
        datas = split_line(line)
        if len(datas) < 7:
            continue

        if print_info:
            print(line)

        return {
            "model_id": datas[4],
            "size": to_int(datas[6]),
            "temperature": to_int(datas[1]),
            "health": to_int(datas[2]),
            "device": datas[0],
            "serial_no": datas[5],
            "power_time": to_int(datas[3])
        }


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"


def split_line(line):
    datas = line.split(" ")
    ndatas = []
    for data in datas:
        if data:
            ndatas.append(data)
    return ndatas


def get_usage_infos():
    cmd = "df -lmT | grep /dev/sd"
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
        filesystem = datas[1]
        if filesystem == 'fuseblk':
            filesystem = 'ntfs'
        usage = to_int(datas[3])
        mount_point = datas[6]
        if mount_point == '/' or mount_point.startswith("/boot/"):
            continue
        usage_infos[format_device(device)] = {
            'usage': usage,
            'mount_point': mount_point,
            'filesystem': filesystem
        }

    return usage_infos


def get_chia_count(base_dir):
    count = 0
    nossd_count = 0
    if not dir or not os.path.isdir(base_dir):
        return count, nossd_count
    names = os.listdir(base_dir)
    for name in names:
        name = os.path.join(base_dir, name)
        if os.path.isfile(name):
            if name.endswith(".plot"):
                count += 1
            elif name.endswith(".fpt"):
                nossd_count += 1
        else:
            if not os.path.exists(name):
                continue
            files = os.listdir(name)
            for file in files:
                file = os.path.join(name, file)
                if os.path.isfile(file):
                    if file.endswith(".plot"):
                        count += 1
                    elif file.endswith(".fpt"):
                        nossd_count += 1
                else:
                    sub_files = os.listdir(file)
                    for sub_file in sub_files:
                        sub_file = os.path.join(file, sub_file)
                        if os.path.isfile(sub_file) and sub_file.endswith(".plot"):
                            count += 1
                        elif os.path.isfile(sub_file) and sub_file.endswith(".fpt"):
                            nossd_count += 1

    return count, nossd_count


def format_device(device):
    if device[-1].isdigit():
        device = device[:-1]
    return device


def is_root():
    return os.getuid() == 0


def is_harvester_alive():
    cmd = "ps -eo pid,args | grep chia_harvester | grep -v grep"
    out = getoutput(cmd)
    lines = out.split("\n")
    for line in lines:
        if line.find("chia_harvester") != -1:
            return 1
    return 0


def report(secret, machine_info, disk_infos):
    data = json.dumps({
        "secret": secret,
        "machine": machine_info,
        "disks": disk_infos
    })
    try_times = 0
    while try_times < 3:
        try:
            response = requests.post("https://api.mingyan.com/api/chia/monitor", data)
            print(response.text)
            break
        except Exception as e:
            print(f'report error {e}')
            time.sleep(10)
        try_times += 1


def main(secret, host_name, print_info):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    usage_infos = get_usage_infos()
    disk_count = 0
    all_size = 0
    all_usage = 0
    all_plot_count = 0
    all_nossd_count = 0
    ndisk_infos = []
    for devname, usage_info in usage_infos.items():
        disk_info = call_hdsentinel(devname, print_info)
        if not disk_info:
            continue
        size = disk_info['size']
        usage = usage_info.get('usage', 0)
        mount_point = usage_info.get('mount_point', "")
        filesystem = usage_info.get('filesystem', "")
        plot_count, nossd_count = get_chia_count(mount_point)
        disk_count += 1
        all_plot_count += plot_count
        all_nossd_count += nossd_count
        all_size += size
        all_usage += usage
        disk_info["usage"] = usage
        disk_info["plot_count"] = plot_count
        disk_info["nossd_count"] = nossd_count
        disk_info["mount_point"] = mount_point
        disk_info["filesystem"] = filesystem
        ndisk_infos.append(disk_info)

    machine_info = {
        'host_name': host_name,
        'ip': get_local_ip(),
        'plot_count': all_plot_count,
        'nossd_count': all_nossd_count,
        'disk_count': disk_count,
        'all_usage': all_usage,
        'all_size': all_size,
        'harvester': is_harvester_alive()
    }

    report(secret, machine_info, ndisk_infos)


def acquire_port_lock(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', port))
        sock.listen(1)
        fcntl.flock(sock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return sock
    except IOError:
        print(f"Another process is already listening on port {port}. Exiting.")
        exit(1)


def release_port_lock(sock):
    fcntl.flock(sock.fileno(), fcntl.LOCK_UN)
    sock.close()


if __name__ == '__main__':
    if not is_root():
        print("must run by root")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="""
       This script is for monitor the harvester server and report to the server.
    """)
    parser.add_argument("--host-name", metavar="", help="the host name, default is current host name", default='')
    parser.add_argument("--secret", metavar="", help="secret, use to post to server ")
    parser.add_argument("-p", "--print", action="store_true",
                        help="whether print the info, default is False",
                        default=False)
    parser.add_argument("--lock-port", metavar="", type=int, help="lock port, default is 8000",
                        default=8000)

    args = parser.parse_args()
    secret = args.secret
    port = args.lock_port
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)
    host_name = args.host_name
    print_info = args.print

    sock = None
    try:
        sock = acquire_port_lock(port)
        print('lock success')
        main(secret=secret, host_name=host_name, print_info=print_info)
    finally:
        if sock:
            release_port_lock(sock)