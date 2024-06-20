#!/usr/bin/python
# -*- coding: utf-8 -*-

import signal
import requests
import uuid
import hashlib
import json
import os
import argparse
import sys
import time
from datetime import datetime

from subprocess import Popen, PIPE, check_output

VERSION = "v1.7"


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s, flush=True)


class FastsmhGpu:

    def __init__(self):
        self.bin = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "fastgpu")

    def start(self):
        os.environ['LD_LIBRARY_PATH'] = f"{os.path.join(os.path.dirname(__file__), 'bin')}/"
        p = Popen([self.bin, "-gpuServer", "-license", "yes"], stdout=PIPE)
        while True:
            line = p.stdout.readline()
            if not line:
                break
            line = line.decode('utf-8')
            line = line.replace("\n", "")
            if line.find("Speed") > 0:
                print(line, flush=True)


def get_system_uuid():
    d = check_output('dmidecode -s system-uuid'.split())
    return d.decode("utf-8").replace("\n", "")


def get_baseboard_serial_number():
    d = check_output('dmidecode -s baseboard-serial-number'.split())
    return d.decode("utf-8").replace("\n", "")


def get_machine_id():
    d = check_output('cat /etc/machine-id', shell=True)
    return d.decode("utf-8").replace("\n", "")


def get_mac():
    d = check_output("cat /sys/class/net/$(ip route show default | awk 'NR==1' | awk '/default/ {print $5}')/address", shell=True)
    return d.decode("utf-8").replace("\n", "")

def verify_license():
    mac = get_mac()
    nonestr = str(uuid.uuid4())[:32]
    t = int(time.time())
    raw = f'{mac}-{nonestr}-d3e616f6b5be276111f227c80b4ec516-{t}'
    sign = hashlib.md5(raw.encode(encoding='utf-8')).hexdigest()
    data = {
        "mac": mac,
        "sign": sign,
        "nonestr": nonestr,
        "t": t,
        "version": VERSION,
        "systemUuid": get_system_uuid(),
        "baseboardSerialNumber": get_baseboard_serial_number(),
        "machineId": get_machine_id()
    }
    response = requests.post("https://api.mingyan.com/api/license/smhv2", data, timeout=10)
    rsp = json.loads(response.text)
    if rsp["status"] == 200:
        info = rsp['data']
        if info['approve'] == 1 and info["nonestr"] == nonestr:
            return info['commitmentAtxId']

    mc_code = hashlib.md5(f"{mac}-d3e616f6b5be276111f227c80b4ec516".encode(encoding='utf-8')).hexdigest()
    log(f"机器未授权.code[{mc_code}], 如需授权，请添加微信:lycaisxw")
    sys.exit(0)


def sigterm_handler(_signo, _stack_frame):
    log("程序退出")
    sys.exit(0)


def is_root():
    return os.getuid() == 0


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""
       This script is for fastgpu runner.
    """)

    parser.add_argument("-v", "--version", action="store_true", help="show version", default=False)

    args = parser.parse_args()
    show_version = args.version

    if show_version:
        print(f"version: {VERSION}", flush=True)
        sys.exit(0)

    if not is_root():
        print("请切换到root用户")
        sys.exit(0)

    verify_license()

    log(f"启动GPU程序，版本[{VERSION}]")

    signal.signal(signal.SIGTERM, sigterm_handler)

    run = FastsmhGpu()
    run.start()
