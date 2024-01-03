#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import socket
import json
import time

import requests
import subprocess

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


def is_win():
    return sys.platform.startswith("win32")


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


def post(url, data):
    try_times = 0
    while try_times < 3:
        try:
            response = requests.post(url, data, timeout=10)
            print(response.text)
            return response.text
        except:
            time.sleep(10)
        try_times += 1


def get(url):
    try_times = 0
    while try_times < 3:
        try:
            response = requests.get(url, timeout=10)
            text = response.text
            print(text)
            return text
        except:
            time.sleep(10)
        try_times += 1


def start(secret, host_name):
    text = get(f"https://api.mingyan.com/api/qli/getCommand?secret={secret}&hostname={host_name}")
    data = json.loads(text)
    command = data["data"]["cmd"]
    param = data["data"]["param"]
    if command:
        return {
            'cmd': command,
            'param': param
        }


def end(secret, host_name, state):
    data = json.dumps({
        "secret": secret,
        "host_name": host_name,
        "state": state,
        "ip": get_local_ip()
    })
    text = post("https://api.mingyan.com/api/qli/monitor", data)
    print(text)

def upgrade(url):
    pass


def run_supervisor_cmd(cmd):
    """run supervisor cmd"""
    subprocess.call(['supervisorctl', cmd, 'qli'])


def execute(command):
    cmd = command['cmd']
    param = command['param']
    log(f'start to run cmd {cmd}')
    if cmd in ['stop', 'start', 'restart']:
        current_state = get_state()
        if cmd == 'stop':
            if current_state == 'STOPPED':
                return
        elif cmd == 'start':
            if current_state == 'RUNNING':
                return
        elif cmd == 'restart':
            if current_state == 'STOPPED':
                cmd = 'start'
        run_supervisor_cmd(cmd)
    elif cmd == 'upgrade':
        url = param['url']
        upgrade(url)


def get_state():
    """get state"""
    result = subprocess.call(['supervisorctl', 'status', 'qli'])
    result = result.decode("utf8")
    print(result)
    status = ""
    if result:
        data = split_line(result)
        status = data[1]
    return status


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    command = start(secret, host_name)

    if command:
        execute(command)

    state = get_state()

    end(secret, host_name, state)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""
       This script is for monitor the harvester server and report to the server.
    """)
    parser.add_argument("--host-name", metavar="", help="the host name, default is current host name", default='')
    parser.add_argument("--secret", metavar="", help="secret, use to post to server ")
    parser.add_argument("-i", "--interval", metavar="", type=int, help="interval",
                        default=20)

    args = parser.parse_args()
    secret = args.secret
    interval = args.interval
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)

    while True:
        try:
            host_name = args.host_name
            main(secret=secret, host_name=host_name)
        except:
            raise
            pass
        time.sleep(interval)
