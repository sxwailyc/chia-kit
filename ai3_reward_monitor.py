#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import json
import socket
import argparse
import requests
import threading
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

FARM_ID_KEY = "subspace_farmer::commands::farm:   ID:"
FARM_SIZE_KEY = "subspace_farmer::commands::farm:   Allocated space:"
FARM_DIRECTORY_KEY = "subspace_farmer::commands::farm:   Directory:"

CLUSTER_FARM_ID_KEY = "subspace_farmer::commands::cluster::farmer:   ID:"
CLUSTER_FARM_SIZE_KEY = "subspace_farmer::commands::cluster::farmer:   Allocated space:"
CLUSTER_FARM_DIRECTORY_KEY = "subspace_farmer::commands::cluster::farmer:   Directory:"

SUCCESS_REWARD_KEY = "Successfully signed reward hash"
BLOCK_REWARD_KEY = "Hash now"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

GB = 1024 * 1024 * 1024
TB = GB * 1024

EXIT = False


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime(DATE_FORMAT), msg)
    print(s)
    sys.stdout.flush()


def print_localtime(line):
    # noinspection PyBroadException
    try:
        s = line[:19]
        d = datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
        local_time = d + timedelta(hours=8)
        print('%s%s' % (local_time.strftime(DATE_FORMAT), line[19:]))
    except:
        print(line)


def get_reward_hash(s):
    start = s.find(SUCCESS_REWARD_KEY)
    if start > 0:
        reward_hash = s[start + len(SUCCESS_REWARD_KEY):]
        farm_index = get_farm_index(s)
        return farm_index, reward_hash.strip()
    return 0, None


def get_block_hash(s):
    start = s.find(BLOCK_REWARD_KEY)
    if start > 0:
        s = s[start + len(BLOCK_REWARD_KEY):]
        block_hash = s[:s.find(",")]
        return block_hash.strip()
    return None


def format_size(farm_size):
    if farm_size.find('TiB') > 0:
        size = float(farm_size.replace('TiB', '').strip())
        return size * TB
    if farm_size.find('GiB') > 0:
        size = float(farm_size.replace('GiB', '').strip())
        return size * GB
    return 0


def get_farm_index(s):
    start = s.find("{farm_index=")
    s = s[start + len("{farm_index="):]
    end = s.find("}")
    farm_index = int(s[:end])
    return farm_index


def get_farm_id(s, keyword):
    start = s.find(keyword)
    if start > 0:
        farm_id = s[start + len(keyword):]
        farm_index = get_farm_index(s)
        return farm_index, farm_id.strip()
    return 0, None


def get_farm_size(s, keyword):
    start = s.find(keyword)
    end = s.rfind("(")
    if start > 0:
        farm_size = s[start + len(keyword):end]
        return format_size(farm_size)
    return 0


def get_farm_directory(s, keyword):
    start = s.find(keyword)
    if start > 0:
        directory = s[start + len(keyword):]
        return directory.strip()
    return None


def get_line_count(path):
    with open(path, 'r') as file:
        lines = file.readlines()
        line_count = len(lines)
    return line_count


class Ai3RewardHandler(threading.Thread, FileSystemEventHandler):

    def __init__(self, secret, path, cluster):
        threading.Thread.__init__(self, daemon=True)
        FileSystemEventHandler.__init__(self)
        self.secret = secret
        self.hostname = socket.gethostname()
        self.path = path
        self.current_farm_id = None
        self.current_farm_index = 0
        self.current_allocated = 0
        self.farm_id_keyword = CLUSTER_FARM_ID_KEY if cluster else FARM_ID_KEY
        self.farm_size_keyword = CLUSTER_FARM_SIZE_KEY if cluster else FARM_SIZE_KEY
        self.farm_directory_keyword = CLUSTER_FARM_DIRECTORY_KEY if cluster else FARM_DIRECTORY_KEY
        self.exit = False

    def report_farm(self, directory):
        data = json.dumps({
            "secret": self.secret,
            "farm_id": self.current_farm_id,
            "farm_index": self.current_farm_index,
            "size": self.current_allocated,
            "hostname": self.hostname,
            "directory": directory
        })
        try_times = 0
        while try_times < 3:
            try:
                log(f"start to report, try times {try_times}")
                response = requests.post("https://api.mingyan.com/api/subspace/farm", data, timeout=10)
                log(response.text)
                break
            except Exception as e:
                log(f'report error {e}')
                time.sleep(10)
            try_times += 1

        self.current_farm_id = None
        self.current_allocated = 0
        self.current_farm_index = 0

    def report_reward(self, reward_type, farm_index, reward_hash):
        data = json.dumps({
            "secret": self.secret,
            "type": reward_type,
            "farm_index": farm_index,
            "hostname": self.hostname,
            "reward_hash": reward_hash
        })
        try_times = 0
        while try_times < 3:
            try:
                log(f"start to report, try times {try_times}")
                response = requests.post("https://api.mingyan.com/api/subspace/reward", data, timeout=10)
                log(response.text)
                break
            except Exception as e:
                log(f'report error {e}')
                time.sleep(10)
            try_times += 1

    def handle_line(self, line):
        if line.find(self.farm_id_keyword) > 0:
            self.current_farm_index, self.current_farm_id = get_farm_id(line, self.farm_id_keyword)
        elif line.find(self.farm_size_keyword) > 0:
            self.current_allocated = get_farm_size(line, self.farm_size_keyword)
        elif line.find(self.farm_directory_keyword) > 0:
            directory = get_farm_directory(line, self.farm_directory_keyword)
            self.report_farm(directory)
        elif line.find(SUCCESS_REWARD_KEY) > 0:
            farm_index, reward_hash = get_reward_hash(line)
            self.report_reward(1, farm_index, reward_hash)
        elif line.find(BLOCK_REWARD_KEY) > 0:
            reward_hash = get_block_hash(line)
            self.report_reward(2, 0, reward_hash)

    def run(self):
        with open(self.path, 'r') as f:
            if get_line_count(self.path) > 5:
                f.seek(0, 2)  # 移动到文件末尾
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)  # 等待文件更新
                    continue
                line = line.strip()
                print_localtime(line)  # 打印新的日志行
                self.handle_line(line)

    def on_any_event(self, event):
        global EXIT
        if event.event_type == 'closed':
            EXIT = True


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="""
           This script is for monitor the ai3 farm.
        """)
    parser.add_argument("--secret", metavar="", help="secret, use to post to server ")
    parser.add_argument("--log-path", metavar="", help="log path, use to watch farm event ",
                        default="/data/log/subspace_farmer.out.log")
    parser.add_argument("--cluster", action="store_true", help="ai3 whether run on cluster mode, default is True",
                        default=False)

    args = parser.parse_args()
    secret = args.secret
    log_path = args.log_path
    cluster = args.cluster
    print(cluster)
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)

    if not log_path:
        print("please input log_path with --log-path")
        sys.exit(0)

    log(f'log path {log_path}')

    event_handler = Ai3RewardHandler(secret, log_path, cluster)
    event_handler.start()
    observer = Observer()
    observer.schedule(event_handler, log_path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
            if EXIT:
                observer.stop()
                print('exit')
                sys.exit(0)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
