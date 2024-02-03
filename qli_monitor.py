#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import socket
import json
import time
import psutil

import requests
import subprocess

import argparse
import os
from datetime import datetime

DOWNLOAD_DIR = "/data/app/qli-app/"

CLIENTS = ['qli', 'bitnet', 'xcb', 'hac']


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
    while try_times < 30:
        try:
            response = requests.post(url, data, timeout=10)
            log(response.text)
            return response.text
        except:
            time.sleep(10)
        try_times += 1


def get(url):
    try_times = 0
    while try_times < 30:
        try:
            response = requests.get(url, timeout=10)
            text = response.text
            log(text)
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


def cpu_info():
    cpu_count = psutil.cpu_count()
    percent = psutil.cpu_percent()
    freq = psutil.cpu_freq()
    return cpu_count, percent, freq.max, freq.current


def memory_info():
    info = psutil.virtual_memory()
    return info.total, info.used


def end(secret, host_name, state, command):
    memory_total, memory_used = memory_info()
    cpu_count, cpu_percent, cpu_freq_max, cpu_freq_current = cpu_info()
    data = json.dumps({
        "secret": secret,
        "host_name": host_name,
        "state": state,
        "cpu_percent": cpu_percent,
        "cpu_count": cpu_count,
        "cpu_freq_max": cpu_freq_max,
        "cpu_freq_current": cpu_freq_current,
        "memory_total": memory_total,
        "memory_used": memory_used,
        "ip": get_local_ip(),
        "finish": True if command else False
    })
    post("https://api.mingyan.com/api/qli/monitor", data)


def rmfile(name):
    log(f"rm file {name}")
    os.system(f"rm -f {name}")


def rmdir(name):
    log(f"rm dir {name}")
    os.system(f"rm -rf {name}")


def gitpull():
    log("chdir /data/shell/chia-kit")
    os.chdir('/data/shell/chia-kit')
    log("git pull")
    os.system('git pull')


def upgrade(url):
    execute({
        'cmd': 'stop',
        'param': {}
    })

    if not os.path.exists(DOWNLOAD_DIR):
        log(f"create dir {DOWNLOAD_DIR}")
        os.makedirs(DOWNLOAD_DIR)

    log(f"rm -f {DOWNLOAD_DIR}*")
    os.system(f"rm -f {DOWNLOAD_DIR}*")
    log(f"download {url} to {DOWNLOAD_DIR}qli.tar.gz")
    os.system(f"wget -O {DOWNLOAD_DIR}qli.tar.gz {url}")
    log(f"unzip file {DOWNLOAD_DIR}qli.tar.gz")
    os.system(f"tar zxvf {DOWNLOAD_DIR}qli.tar.gz -C {DOWNLOAD_DIR}")
    rmfile("/data/app/qli/qli-Client")
    rmfile("/data/app/qli/qli-runner")
    rmfile("/data/app/qli/qli-runner.lock")
    rmdir("/data/app/qli/tmp")
    rmdir("/data/app/qli/log")
    log(f"cp {DOWNLOAD_DIR}/qli-Client to /data/app/qli/")
    os.system(f"cp {DOWNLOAD_DIR}/qli-Client /data/app/qli/")

    execute({
        'cmd': 'start',
        'param': {}
    })


def run_supervisor_cmd(cmd, client):
    """run supervisor cmd"""
    log(f"start to run supervisorctl {cmd} {client}")
    subprocess.call(['supervisorctl', cmd, client])


def run_script(script):
    """run script"""
    log(f"start to run script {script} ")
    os.system(script)


def execute(command):
    cmd = command['cmd']
    param = command['param']
    log(f'start to run cmd {cmd}')
    if cmd in ['stop', 'start', 'restart']:
        client = param['client']
        current_state = get_state(client)
        if cmd == 'stop':
            if current_state == 'STOPPED':
                return
        elif cmd == 'start':
            if current_state == 'RUNNING':
                return
        elif cmd == 'restart':
            if current_state == 'STOPPED':
                cmd = 'start'
        run_supervisor_cmd(cmd, client)
    elif cmd == 'upgrade':
        url = param['url']
        upgrade(url)
    elif cmd == 'script':
        script = param['script']
        run_script(script)
    elif cmd == 'gitpull':
        gitpull()


def get_state(client):
    """get state"""
    result = subprocess.run(['supervisorctl', 'status', client], capture_output=True, shell=False, encoding='UTF-8')
    text = result.stdout
    state = "None"
    if result:
        data = split_line(text)
        state = data[1]
        log(f"{client}, state:{state}")
    return state


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    command = start(secret, host_name)

    if command:
        execute(command)

    state = {}
    for client in CLIENTS:
        state[client] = get_state(client)

    end(secret, host_name, state, command)

    if command and command['cmd'] == 'gitpull':
        sys.exit(0)


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
        except SystemExit as e:
            log("exit")
            break
        except:
            pass
        time.sleep(interval)

