#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import shutil
import os
import argparse
import sys
from datetime import datetime

GB = 1024 * 1024 * 1024


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def get_free(disk):
    _, _, free = shutil.disk_usage(disk)
    return free


def format_number(i):
    if i <= 9:
        return '0%s' % i
    return i


class FastsmhRunner:

    def __init__(self, folders, numUnits=32, nonces=288):
        self.folders = sorted(folders)
        self.numUnits = numUnits
        self.nonces = nonces
        self.bin = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "fastsmh")

    def is_interrupt(self, folder):
        metadata = os.path.join(folder, "postdata_metadata.json")
        if os.path.exists(metadata):
            return False, 0
        with open(metadata) as f:
            data = json.load(f)
            NumUnits = data["NumUnits"]
            MaxFileSize = data["MaxFileSize"]
            last_file_idx = (NumUnits * 64 * GB / MaxFileSize - 1)
            last_file = f"postdata_{last_file_idx}.bin"
            if not os.path.exists(last_file) or os.path.getsize(last_file) < MaxFileSize:
                return True
        return False

    def restart_interrupt_plot(self):
        for folder in self.folders:
            sub_folders = os.listdir(folder)
            for sub_folder in sub_folders:
                is_interrupt, num_units = self.is_interrupt(sub_folder)
                if is_interrupt:
                    self.numUnits = num_units
                    log(f"continue interrupt plot: {sub_folder}")
                    self.plot(sub_folder)

    def plot(self, folder):
        export = f"export LD_LIBRARY_PATH={os.path.join(os.path.dirname(__file__), 'bin')}/:$LD_LIBRARY_PATH"
        log(export)
        os.system(export)
        cmd = f"{self.bin} -datadir {folder} -nonces {self.nonces} -numUnits {self.numUnits}"
        log(cmd)
        os.system(cmd)

    def start_new_plot(self):
        for folder in self.folders:
            free = get_free(folder)
            if free < self.numUnits * 64 * GB:
                continue

            for i in range(10):
                sub_dir = os.path.join(folder, f"post_{format_number(i + 1)}")
                if os.path.exists(sub_dir):
                    continue
                else:
                    log(f"create dir{sub_dir}")
                    os.makedirs(sub_dir)
                    self.plot(sub_dir)

    def start(self):

        self.restart_interrupt_plot()

        self.start_new_plot()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""
       This script is for fastsmh runner.
    """)

    parser.add_argument("--num-units", metavar="", type=int, help="numUnits, default is 32", default=32)
    parser.add_argument("--num-units", metavar="", type=int, help="numUnits, default is 32", default=32)
    parser.add_argument("-d", "--dir", nargs='+', action='append', help="plot dirs")

    args = parser.parse_args()
    numUnits = args.num_units

    folders = args.dir
    if folders:
        folders = [x[0] for x in folders]
    else:
        print(f"{bin} please specify -d param.")
        sys.exit(0)

    run = FastsmhRunner(folders, numUnits)
    run.start()
