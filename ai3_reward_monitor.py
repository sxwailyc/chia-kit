import os
import sys
import time
import json
import socket
import argparse
import requests
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

FARM_ID_KEY = "subspace_farmer::commands::farm:   ID:"
FARM_SIZE_KEY = "subspace_farmer::commands::farm:   Allocated space:"
FARM_DIRECTORY_KEY = "subspace_farmer::commands::farm:   Directory:"
SUCCESS_REWARD_KEY = "Successfully signed reward hash"

GB = 1024 * 1024 * 1024
TB = GB * 1024


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)
    sys.stdout.flush()


def get_last_modified_time(path):
    return os.stat(path).st_mtime


def get_reward_hash(s):
    start = s.find(SUCCESS_REWARD_KEY)
    if start > 0:
        reward_hash = s[start + len(SUCCESS_REWARD_KEY):]
        farm_index = get_farm_index(s)
        return farm_index, reward_hash.strip()
    return 0, None


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


def get_farm_id(s):
    start = s.find(FARM_ID_KEY)
    if start > 0:
        farm_id = s[start + len(FARM_ID_KEY):]
        farm_index = get_farm_index(s)
        return farm_index, farm_id.strip()
    return 0, None


def get_farm_size(s):
    start = s.find(FARM_SIZE_KEY)
    end = s.rfind("(")
    if start > 0:
        farm_size = s[start + len(FARM_SIZE_KEY):end]
        return format_size(farm_size)
    return 0


def get_farm_directory(s):
    start = s.find(FARM_DIRECTORY_KEY)
    if start > 0:
        directory = s[start + len(FARM_DIRECTORY_KEY):]
        return directory.strip()
    return None


class Ai3RewardHandler(FileSystemEventHandler):

    def __init__(self, secret, path):
        FileSystemEventHandler.__init__(self)
        self.secret = secret
        self.hostname = socket.gethostname()
        self.path = path
        self.last_modified_time = get_last_modified_time(path)
        self.current_farm_id = None
        self.current_farm_index = 0
        self.current_allocated = 0

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

    def report_reward(self, farm_index, reward_hash):
        data = json.dumps({
            "secret": self.secret,
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
        if line.find(FARM_ID_KEY) > 0:
            self.current_farm_index, self.current_farm_id = get_farm_id(line)
        elif line.find(FARM_SIZE_KEY) > 0:
            self.current_allocated = get_farm_size(line)
        elif line.find(FARM_DIRECTORY_KEY) > 0:
            directory = get_farm_directory(line)
            self.report_farm(directory)
        elif line.find(SUCCESS_REWARD_KEY) > 0:
            farm_index, reward_hash = get_reward_hash(line)
            self.report_reward(farm_index, reward_hash)

    def on_modified(self, event):
        if event.src_path == self.path:
            new_modified_time = get_last_modified_time(self.path)
            if new_modified_time > self.last_modified_time:
                with open(self.path, 'r') as f:
                    f.seek(0, 2)  # 移动到文件末尾
                    while True:
                        line = f.readline()
                        if not line:
                            time.sleep(0.1)  # 等待文件更新
                            continue
                        line = line.strip()
                        print(line)  # 打印新的日志行
                        self.handle_line(line)
                        self.last_modified_time = new_modified_time


if __name__ == "__main__":
    #print(get_reward_hash(
    #    '2025-01-02T08:48:38.964539Z  INFO {farm_index=4}: subspace_farmer::single_disk_farm::reward_signing: Successfully signed reward hash 0xf02fc014d9abbd24ad50bc6cd9ffa6951acda51bfd5465ecad4de7e7fbf72b79'))
    #sys.exit(0)
    # print(get_farm_size(
    #     '2025-01-03T03:29:04.400235Z  INFO {farm_index=0}: subspace_farmer::commands::farm:   Allocated space: 5.7 TiB (6.3 TB)'))
    # print(get_farm_directory(
    #     '2025-01-03T03:29:04.400237Z  INFO {farm_index=0}: subspace_farmer::commands::farm:   Directory: /mnt/spm01'))
    parser = argparse.ArgumentParser(description="""
           This script is for monitor the ai3 farm.
        """)
    parser.add_argument("--secret", metavar="", help="secret, use to post to server ")
    parser.add_argument("--log-path", metavar="", help="log path, use to watch farm event ")

    args = parser.parse_args()
    secret = args.secret
    log_path = args.log_path
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)

    if not log_path:
        print("please input log_path with --log-path")
        sys.exit(0)

    log(f'log path {secret}')

    event_handler = Ai3RewardHandler(secret, log_path)
    observer = Observer()
    observer.schedule(event_handler, log_path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
