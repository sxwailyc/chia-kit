#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading

import json
import shutil
import os
import argparse
import sys
import time
from datetime import datetime

from subprocess import Popen, PIPE

current_folder = None
state = {}

GB = 1024 * 1024 * 1024


def size_to_gb(size):
    return round(size / 1024 / 1024 / 1024, 2)


def size_to_mb(size):
    return round(size / 1024 / 1024, 2)


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def get_free(disk):
    _, _, free = shutil.disk_usage(disk)
    return free


def is_interrupt(folder):
    metadata = os.path.join(folder, "postdata_metadata.json")
    if not os.path.exists(metadata):
        return False, 0
    with open(metadata) as f:
        data = json.load(f)
        NumUnits = data["NumUnits"]
        MaxFileSize = data["MaxFileSize"]
        last_file_idx = (NumUnits * 64 * GB / MaxFileSize - 1)
        last_file = os.path.join(folder, f"postdata_{last_file_idx}.bin")
        if not os.path.exists(last_file) or os.path.getsize(last_file) < MaxFileSize:
            return True, NumUnits
    return False, 0


def rename_plot(folder):
    key_bin = os.path.join(folder, "key.bin")
    with open(key_bin) as f:
        s = f.read()
        key = s[64:]
        target = os.path.join(os.path.dirname(folder), f'post_{key}')
        shutil.move(folder, target)


def print_speed():
    global current_folder, state
    while True:
        try:
            if not current_folder:
                time.sleep(1)
                continue
            metadata = os.path.join(current_folder, "postdata_metadata.json")
            if os.path.exists(metadata):
                with open(metadata) as f:
                    data = json.load(f)
                    NumUnits = data["NumUnits"]
                    MaxFileSize = data["MaxFileSize"]
                    total_file = int(NumUnits * 64 * GB / MaxFileSize)
                    for i in range(total_file):
                        bin_file_name = f"postdata_{i}.bin"
                        bin_file_path = os.path.join(current_folder, bin_file_name)
                        if not os.path.exists(bin_file_path):
                            continue
                        file_size = os.path.getsize(bin_file_path)
                        if file_size >= MaxFileSize:
                            continue
                        pre_file_size = state.get(bin_file_name, 0)
                        if pre_file_size > 0:
                            rate = file_size / MaxFileSize * 100
                            speed = (file_size - pre_file_size) / 20
                            print("%s: %.2fGB/%.2fGB %.2f%% %.2fMB/s" % (
                            bin_file_name, size_to_gb(file_size), size_to_gb(MaxFileSize), rate, size_to_mb(speed)))
                        state[bin_file_name] = file_size
        except Exception as e:
            print(e)
            raise e
            pass
        time.sleep(20)


class FastsmhRunner:

    def __init__(self, folders, numUnits=32, nonces=288):
        self.folders = sorted(folders)
        self.numUnits = numUnits
        self.nonces = nonces
        self.bin = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "fastsmh")
        self.current_folder = None

    def restart_interrupt_plot(self):
        for folder in self.folders:
            sub_folders = os.listdir(folder)
            for sub_folder in sub_folders:
                sub_folder = os.path.join(folder, sub_folder)
                interrupt, num_units = is_interrupt(sub_folder)
                if interrupt:
                    log(f"continue interrupt plot: {sub_folder}, num_units: {num_units}")
                    self.plot(sub_folder, num_units)

    def plot(self, folder, num_units):
        global current_folder, state
        current_folder = folder
        state.clear()

        cmd = f"{self.bin} -datadir {folder} -nonces {self.nonces} -numUnits {num_units}"
        log(cmd)
        os.environ['LD_LIBRARY_PATH'] = f"{os.path.join(os.path.dirname(__file__), 'bin')}/"
        p = Popen([self.bin, "-datadir", folder, "-nonces", f"{self.nonces}", "-numUnits", f"{num_units}"], stdout=PIPE)
        while True:
            line = p.stdout.readline()
            if not line:
                break
            print(line.decode("utf8").replace("\n", ""))

    def start_new_plot(self):
        for folder in self.folders:
            free = get_free(folder)
            if free < self.numUnits * 64 * GB:
                continue

            for i in range(10):
                sub_dir = os.path.join(folder, f"post_{i + 1}")
                if os.path.exists(sub_dir):
                    continue
                else:
                    log(f"create dir{sub_dir}")
                    os.makedirs(sub_dir)
                    self.plot(sub_dir, self.numUnits)
                    rename_plot(sub_dir)

                    free = get_free(folder)
                    if free < self.numUnits * 64 * GB:
                        break

    def start(self):

        t = threading.Thread(target=print_speed)
        t.daemon = True
        t.start()

        self.restart_interrupt_plot()
        self.start_new_plot()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""
       This script is for fastsmh runner.
    """)

    parser.add_argument("--num-units", metavar="", type=int, help="numUnits, default is 32", default=32)
    parser.add_argument("--nonces", metavar="", type=int, help="nonces, default is 288", default=288)
    parser.add_argument("-d", "--dir", nargs='+', action='append', help="plot dirs")

    args = parser.parse_args()
    numUnits = args.num_units
    nonces = args.nonces

    folders = args.dir
    if folders:
        folders = [x[0] for x in folders]
    else:
        print(f"please specify -d param.")
        sys.exit(0)

    run = FastsmhRunner(folders, numUnits, nonces)
    run.start()
