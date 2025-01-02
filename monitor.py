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
    sys.stdout.flush()


def to_int(s):
    try:
        s = s.strip()
        return int(s)
    except Exception as e:
        raise e
        return 0


def to_float(s):
    try:
        s = s.strip()
        return float(s)
    except Exception as e:
        raise e
        return 0


def call_hdsentinel(devname, print_info):
    """call hdsentinel"""
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "hdsentinel-019c-x64")
    p = Popen([cmd, "-dev", devname], stdout=PIPE)
    model_id, size, temperature, health, device, serial_no, power_time, total_write = None, 0, 0, 0, None, None, 0, 0
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = line.decode('utf-8')
        line = line.replace("\n", "")
        datas = split_line(line, ": ")
        if len(datas) != 2:
            continue

        if print_info:
            print(line)

        key = datas[0]
        value = datas[1]
        key = key.strip()
        print("[%s], [%s]" % (key, value))
        if key == 'HDD Model ID':
            model_id = value
        elif key == 'HDD Serial No':
            serial_no = value
        elif key == 'Temperature':
            temperature = to_int(value.replace('°C', ''))
        elif key == 'Health':
            health = to_int(value.replace('%', ''))
        elif key == 'Power on time':
            power_time = parse_power_time(value)
        elif key == 'Total written':
            total_write = parse_total_write(value)

    return {
        "model_id": model_id,
        "temperature": temperature,
        "health": health,
        "serial_no": serial_no,
        "power_time": power_time,
        "total_write": total_write,
    }


def parse_power_time(s):
    datas = s.split(",")
    powter_time = 0
    for data in datas:
        if data.endswith("days"):
            powter_time += 24 * to_int(data.replace('days', ''))
        if data.endswith("hours"):
            powter_time += to_int(data.replace('hours', ''))
    return powter_time


def parse_total_write(s):
    if s.endswith("TB"):
        print(s)
        v = to_float(s.replace('TB', '').replace(",", ''))
        return int(v * 1024 * 1024 * 1024)

    if s.endswith("GB"):
        v = to_float(s.replace('GB', '').replace(",", ''))
        return int(v * 1024 * 1024)
    return 0


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"


def split_line(line, separator=" "):
    datas = line.split(separator)
    ndatas = []
    for data in datas:
        if data:
            ndatas.append(data)
    return ndatas


def get_usage_infos():
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
        filesystem = datas[1]
        if filesystem == 'fuseblk':
            filesystem = 'ntfs'
        size = to_int(datas[2])
        usage = to_int(datas[3])
        mount_point = datas[6]
        if mount_point == '/' or mount_point.startswith("/boot/"):
            continue
        usage_infos[format_device(device)] = {
            'size': size,
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
    if device.startswith("/dev/sd"):
        if device[-1].isdigit():
            device = device[:-1]
    elif device.startswith("/dev/nvme"):
        if device[-1].isdigit():
            device = device[:-2]

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
    print(disk_infos)
    try_times = 0
    while try_times < 3:
        try:
            log(f"start to report, try times {try_times}")
            response = requests.post("https://api.mingyan.com/api/chia/monitor", data, timeout=10)
            log(response.text)
            break
        except Exception as e:
            log(f'report error {e}')
            time.sleep(10)
        try_times += 1


def main(secret, host_name, print_info):
    if not host_name:
        host_name = socket.gethostname()
        log(host_name)

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
        size = usage_info.get('size', 0)
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
        disk_info["size"] = size
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
        log(f"Another process is already listening on port {port}. Exiting.")
        exit(1)


def release_port_lock(sock):
    fcntl.flock(sock.fileno(), fcntl.LOCK_UN)
    sock.close()


if __name__ == '__main__':

    log("monitor start")

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

    log(f'secret {secret}')

    host_name = args.host_name
    print_info = args.print

    sock = None
    try:
        log('start to lock')
        sock = acquire_port_lock(port)
        log('lock success')
        main(secret=secret, host_name=host_name, print_info=print_info)
        log("start to exit")
        sys.exit(0)
    finally:
        if sock:
            release_port_lock(sock)
