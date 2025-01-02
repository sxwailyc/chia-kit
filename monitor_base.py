#!/usr/bin/python
# -*- coding: utf-8 -*-

import fcntl
import sys
import socket
import json
import time

import requests

from subprocess import Popen, PIPE, getoutput
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


class Base():

    def __init__(self, secret, host_name, print_info, report_url):
        self.secret = secret
        if not host_name:
            host_name = socket.gethostname()
            log(host_name)
        self.host_name = host_name
        self.print_info = print_info
        self.report_url = report_url

    def run(self):
        usage_infos = get_usage_infos()
        disk_count = 0
        all_size = 0
        all_usage = 0
        ndisk_infos = []
        for devname, usage_info in usage_infos.items():
            disk_info = call_hdsentinel(devname, self.print_info)
            if not disk_info:
                continue
            if not self.is_need_handle(disk_info):
                continue

            size = usage_info.get('size', 0)
            usage = usage_info.get('usage', 0)
            mount_point = usage_info.get('mount_point', "")
            filesystem = usage_info.get('filesystem', "")

            disk_count += 1
            all_size += size
            all_usage += usage
            disk_info["usage"] = usage
            disk_info["size"] = size
            disk_info["mount_point"] = mount_point
            disk_info["filesystem"] = filesystem

            self.handle_single_disk(disk_info)

            ndisk_infos.append(disk_info)

        machine_info = {
            'host_name': self.host_name,
            'ip': get_local_ip(),
            'disk_count': disk_count,
            'all_usage': all_usage,
            'all_size': all_size
        }
        self.handle_machine_info(machine_info)

        self.report(machine_info, ndisk_infos)


    def is_need_handle(self, disk):
        pass

    def handle_single_disk(self, disk):
        pass

    def handle_machine_info(self, machine):
        pass

    def report(self, machine_info, disk_infos):
        data = json.dumps({
            "secret": self.secret,
            "machine": machine_info,
            "disks": disk_infos
        })
        try_times = 0
        while try_times < 3:
            try:
                log(f"start to report, try times {try_times}")
                response = requests.post(self.report_url, data, timeout=10)
                log(response.text)
                break
            except Exception as e:
                log(f'report error {e}')
                time.sleep(10)
            try_times += 1


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
