#!/usr/bin/python
# -*- coding: utf-8 -*-
import base64
import binascii
import threading

import signal
import requests
import uuid
import hashlib
import json
import shutil
import os
import argparse
import sys
import time
from datetime import datetime, timedelta

from subprocess import Popen, PIPE, check_output

current_folder = None
current_num_units = 0
current_max_filesize = 0
pre_time = 0

state = {}

GB = 1024 * 1024 * 1024
LOG_INTERVAL = 60


METADAT_JSON_FILE = "postdata_metadata.json"
VERSION = "v0.7"


def size_to_gb(size):
    return round(size / 1024 / 1024 / 1024, 2)


def size_to_mb(size):
    return round(size / 1024 / 1024, 2)


def size_to_tb(size):
    return round(size / 1024 / 1024 / 1024 / 1024, 2)


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s, flush=True)


def get_free(disk):
    _, _, free = shutil.disk_usage(disk)
    return free


def is_interrupt(folder):
    metadata = os.path.join(folder, METADAT_JSON_FILE)
    if not os.path.exists(metadata):
        return False, 0, 0, None
    with open(metadata) as f:
        data = json.load(f)
        NumUnits = data["NumUnits"]
        MaxFileSize = data["MaxFileSize"]
        CommitmentAtxId = binascii.hexlify(base64.b64decode(data["CommitmentAtxId"])).decode('utf-8')
        last_file_idx = int(NumUnits * 64 * GB / MaxFileSize - 1)
        last_file = os.path.join(folder, f"postdata_{last_file_idx}.bin")
        if not os.path.exists(last_file) or os.path.getsize(last_file) < MaxFileSize:
            return True, NumUnits, MaxFileSize, CommitmentAtxId
    return False, 0, 0, None


def is_finish(folder):
    metadata = os.path.join(folder, METADAT_JSON_FILE)
    if not os.path.exists(metadata):
        return False
    with open(metadata) as f:
        data = json.load(f)
        NumUnits = data["NumUnits"]
        MaxFileSize = data["MaxFileSize"]
        last_file_idx = int(NumUnits * 64 * GB / MaxFileSize - 1)
        last_file = os.path.join(folder, f"postdata_{last_file_idx}.bin")
        if os.path.exists(last_file) and os.path.getsize(last_file) >= MaxFileSize:
            return True
    return False


def is_directory_empty(path):
    return not any([os.path.isfile(os.path.join(path, f)) for f in os.listdir(path)])


def rename_plot(folder):
    if not is_finish(folder):
        return
    key_bin = os.path.join(folder, "key.bin")
    if not os.path.exists(key_bin):
        return
    target = None
    with open(key_bin) as f:
        s = f.read()
        key = s[64:]
        target = os.path.join(os.path.dirname(folder), f'post_{key}')

    log("重命名 %s 为 %s" % (folder, target))
    if target != folder:
        cmd = "mv %s %s" % (folder, target)
        os.system(cmd)


def print_speed():
    global current_folder, state, current_num_units, pre_time, current_max_filesize
    while True:
        try:
            info = {}
            if not current_folder:
                time.sleep(1)
                continue
            if current_num_units > 0 and current_max_filesize > 0:
                total_file = int(current_num_units * 64 * GB / current_max_filesize)
                total_size = current_num_units * 64 * GB
                total_finish = 0
                all_gpu_finish = 0
                now = time.time()
                if pre_time > 0:
                    time_diff = now - pre_time
                else:
                    time_diff = LOG_INTERVAL
                pre_time = now
                for i in range(total_file):
                    bin_file_name = f"postdata_{i}.bin"
                    bin_file_path = os.path.join(current_folder, bin_file_name)
                    if not os.path.exists(bin_file_path):
                        continue
                    file_size = os.path.getsize(bin_file_path)
                    total_finish += file_size
                    if file_size >= current_max_filesize:
                        continue
                    pre_file_size = state.get(bin_file_name, 0)
                    if pre_file_size > 0:
                        rate = file_size / current_max_filesize * 100
                        all_gpu_finish += (file_size - pre_file_size)
                        speed = (file_size - pre_file_size) / time_diff
                        log("文件:%s: %.2fGB/%.2fGB %.2f%% %.2fMB/s" % (
                            bin_file_name, size_to_gb(file_size), size_to_gb(current_max_filesize), rate, size_to_mb(speed)))

                        info[bin_file_name] = {
                            "speed": size_to_mb(speed),
                            "size": size_to_gb(file_size),
                            "pre_size": size_to_gb(pre_file_size)
                        }

                    state[bin_file_name] = file_size

                total_rate = total_finish / total_size * 100
                total_speed = all_gpu_finish / time_diff
                if total_speed > 0:
                    remain_size = total_size - total_finish
                    remain_time = remain_size / total_speed
                    finish_time = datetime.now() + timedelta(seconds=remain_time)

                    log("汇总:%s: %.2fTB/%.2fTB %.2f%% %.2fMB/s 预计完成时间: %s" % (
                        current_folder, size_to_tb(total_finish), size_to_tb(total_size), total_rate,
                        size_to_mb(total_speed), finish_time.strftime("%Y-%m-%d %H:%M:%S")))

                    info["total"] = {
                        "speed": size_to_mb(total_speed),
                        "size": size_to_gb(total_finish),
                        "finish_time": finish_time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    report(info)

        except KeyboardInterrupt:
            break
        time.sleep(LOG_INTERVAL)


class FastsmhRunner:

    def __init__(self, folders, numUnits=32, reservedSize=0, commitmentAtxId=None, maxFileSize=34359738368):
        self.folders = sorted(folders)
        self.numUnits = numUnits
        self.reservedSize = reservedSize
        self.commitmentAtxId = commitmentAtxId
        self.maxFileSize = maxFileSize
        self.bin = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "postcli")
        self.current_folder = None

    def restart_interrupt_plot(self):
        for folder in self.folders:
            sub_folders = os.listdir(folder)
            for sub_folder in sub_folders:
                sub_folder = os.path.join(folder, sub_folder)
                interrupt, num_units, max_filesize, commitmentAtxId = is_interrupt(sub_folder)
                if interrupt:
                    log(f"继续运行中断的P盘任务, 目录:{sub_folder}, 图容量: {size_to_tb(num_units * 64 * GB)}TB")
                    self.plot(sub_folder, num_units, max_filesize, commitmentAtxId)

    def plot(self, folder, num_units, max_filesize, commitmentAtxId):
        global current_folder, state, current_num_units, current_max_filesize
        current_folder = folder
        current_num_units = num_units
        current_max_filesize = max_filesize
        state.clear()

        cmd = f"{self.bin} -datadir {folder} -numUnits {num_units} -maxFileSize {max_filesize}"
        log(cmd)
        os.environ['LD_LIBRARY_PATH'] = f"{os.path.join(os.path.dirname(__file__), 'bin')}/"
        p = Popen([self.bin, "-datadir", folder, "-numUnits", f"{num_units}", "-maxFileSize", f"{max_filesize}", "-commitmentAtxId", f"{commitmentAtxId}", "-provider", "0"], stdout=PIPE, stderr=PIPE)
        ret_code = p.wait()
        if ret_code != 0:
            log(f"P图执行失败[{cmd}]")
            error = ""
            while True:
                line = p.stderr.readline()
                if not line:
                    break
                line = line.decode('utf-8')
                error += line

            report_error(error)

            sys.exit(0)

        rename_plot(folder)

    def is_continue(self, folder):
        free = get_free(folder)
        if free < 4 * 64 * GB:
            return False, 0

        if free < self.numUnits * 64 * GB:
            if self.reservedSize >= 0:
                use_space = free - self.reservedSize * GB
                num_units = int(use_space / (64 * GB))
                if num_units >= 4:
                    return True, num_units
                else:
                    return False, 0
            else:
                return False, 0
        else:
            return True, self.numUnits

    def start_new_plot(self):
        for folder in self.folders:

            go, num_units = self.is_continue(folder)
            if not go:
                continue

            for i in range(10):
                sub_dir = os.path.join(folder, f"post_{i + 1}")
                if os.path.exists(sub_dir) and is_directory_empty(sub_dir):
                    continue

                if not os.path.exists(sub_dir):
                    log(f"创建目录: {sub_dir}")
                    os.makedirs(sub_dir)

                self.plot(sub_dir, num_units, self.maxFileSize, self.commitmentAtxId)

                go, num_units = self.is_continue(folder)
                if not go:
                    break

    def start(self):

        t = threading.Thread(target=print_speed)
        t.daemon = True
        t.start()

        self.restart_interrupt_plot()

        self.start_new_plot()


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


def report_error(error):
    mac = get_mac()
    data = {
        "mac": mac,
        "error": error
    }
    requests.post("https://api.mingyan.com/api/license/error", data, timeout=10)


def report(info):
    try:
        mac = get_mac()
        info["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "mac": mac,
            "content": json.dumps(info)
        }
        requests.post("https://api.mingyan.com/api/license/report", data, timeout=10)
    except:
        pass


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
       This script is for fastsmh runner.
    """)

    parser.add_argument("--num-units", metavar="", type=int, help="numUnits, default is 32", default=32)
    parser.add_argument("--max-filesize", metavar="", type=int, help="maxFileSize, default is 34359738368", default=34359738368)
    parser.add_argument("--reserved-size", metavar="", type=int, help="reserved size, default is 0", default=0)
    parser.add_argument("-d", "--dir", nargs='+', action='append', help="plot dirs")

    parser.add_argument("-v", "--version", action="store_true", help="show version", default=False)

    args = parser.parse_args()
    show_version = args.version

    if show_version:
        print(f"version: {VERSION}", flush=True)
        sys.exit(0)

    if not is_root():
        print("请切换到root用户")
        sys.exit(0)

    log(f"启动P图程序，版本[{VERSION}]")

    numUnits = args.num_units
    maxFileSize = args.max_filesize
    reservedSize = args.reserved_size

    commitmentAtxId = verify_license()

    folders = args.dir
    if folders:
        folders = [x[0] for x in folders]
    else:
        print(f"请用 -d 参数指定P盘目录，可以重复使用添加多个目录.", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    run = FastsmhRunner(folders, numUnits, reservedSize, commitmentAtxId, maxFileSize)
    run.start()
