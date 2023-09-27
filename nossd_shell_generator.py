#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import argparse
import shutil
import sys
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def batch_get_nossd_dirs(base_dirs):
    nossd_dirs = []
    for base_dir in base_dirs:
        nossd_dirs.extend(get_nossd_dirs(base_dir))
    return sorted(nossd_dirs)


def get_nossd_dirs(base_dir):
    nossd_dirs = []
    if not dir or not os.path.isdir(base_dir):
        return []
    names = os.listdir(base_dir)
    for name in names:
        name = os.path.join(base_dir, name)
        if not os.path.isdir(name):
            continue
        files = os.listdir(name)
        for file in files:
            file = os.path.join(name, file)
            if os.path.isfile(file):
                if file.endswith(".fpt"):
                    nossd_dirs.append(name)
                    break
            else:
                sub_files = os.listdir(file)
                for sub_file in sub_files:
                    sub_file = os.path.join(file, sub_file)
                    if os.path.isfile(sub_file) and sub_file.endswith(".fpt"):
                        nossd_dirs.append(file)
                        break

    return sorted(nossd_dirs)


class NossdShellGenerator:

    def __init__(self, bin, address, output, work_name, folders, no_plotting):
        self.bin = bin
        self.address = address
        self.output = output
        self.work_name = work_name
        self.folders = folders
        self.no_plotting = no_plotting

    def main(self):
        nossd_dirs = batch_get_nossd_dirs(self.folders)
        print(nossd_dirs)
        no_plotting_s = ' --no-plotting ' if self.no_plotting else ''
        work_name_s = f' -w {self.work_name} ' if self.work_name else ''
        dir_s = " \\\n".join([f'    {nossd_dir}' for nossd_dir in nossd_dirs]);

        s = f"""#!/bin/sh
        
{self.bin} -a {self.address}{no_plotting_s}{work_name_s}\\
{dir_s}
"""

        print(s)
        if self.output:
            target = os.path.join(self.output, "start_nossd.sh")
            with open(target, "w") as of:
                of.write(s)
                log("success write start_nossd.sh to %s" % self.output)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""
       This script is for generate nossd shell.
    """)

    parser.add_argument("-b", "--bin", help="nossd bin path, default is client", default="client")
    parser.add_argument("-o", "--output-dir", metavar="", help="output dir", default='')
    parser.add_argument("-a", "--address", metavar="", help="reward xch adress", type=str)
    parser.add_argument("-w", "--work-name", metavar="", help="worker name", default='')
    parser.add_argument("--no-plotting", action='store_true', help="no plotting", default=True)
    parser.add_argument("-d", "--dir", nargs='+', action='append', help="fpt file dirs, defautl is [/mnt/]")

    args = parser.parse_args()
    bin = args.bin
    address = args.address
    output_dir = args.output_dir
    work_name = args.work_name
    no_plotting = args.no_plotting

    path = shutil.which(bin)

    if path is None:
        pass
        #print(f"{bin} Command not found, please specify the path to Nossd.")
        #sys.exit(0)

    if address is None:
        print(f"{bin} please specify -a param.")
        sys.exit(0)

    folders = args.dir
    if folders:
        folders = [x[0] for x in folders]
    else:
        if not folders:
            folders = ['/mnt/']

    run = NossdShellGenerator(bin, address, output_dir, work_name, folders, no_plotting)
    run.main()
