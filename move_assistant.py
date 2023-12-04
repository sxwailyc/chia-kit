#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import argparse
import multiprocessing
import shutil
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def size_to_gb(size):
    return round(size / 1024 / 1024 / 1024, 2)


def size_to_mb(size):
    return round(size / 1024 / 1024, 2)


def print_success(msg):
    return "\033[32m%s\033[0m" % msg


def print_error(msg):
    return "\033[31m%s\033[0m" % msg


def remove_one_plot(_dir, grep):
    """remove one plot file """
    if not _dir or not os.path.isdir(_dir):
        return False
    names = os.listdir(_dir)
    for name in names:
        name = os.path.join(_dir, name)
        if os.path.isfile(name):
            if name.find(grep) >= 0:
                log("start to remove old plot file: %s" % name)
                os.remove(name)
                return True
        else:
            if not os.path.exists(name):
                continue
            files = os.listdir(name)
            for file in files:
                file = os.path.join(name, file)
                if os.path.isfile(file):
                    if file.find(grep) >= 0:
                        log("start to remove old plot file: %s" % file)
                        os.remove(file)
                        return True

    return False


def move(source, target, sub_dir_name, current_dirs, current_files, suffix):
    try:
        dist = os.path.join(target, sub_dir_name)
        if not os.path.exists(dist):
            os.makedirs(dist)
        dist_name = os.path.join(dist, source.split(os.path.sep)[-1])
        dist_temp = dist_name.replace('.%s' % suffix, '.tmp')
        if os.path.exists(dist_temp):
            log("dist temp file exist:%s" % dist_temp)
            os.remove(dist_temp)
        filesize = os.path.getsize(source)
        log("start move %s[%.2fGB] to %s" % (source, size_to_gb(filesize), dist))
        start = time.time()
        shutil.move(source, dist_temp)
        if os.path.exists(dist_name):
            log("dist file exist:%s" % dist_name)
            os.remove(dist_name)
        log('rename [%s] to [%s]' % (dist_temp, dist_name))
        os.renames(dist_temp, dist_name)
        cost_time = time.time() - start
        speed = filesize / cost_time
        log("move %s [file: %s, size: %.2fGB, cost time: %.2fs, speed: %.2fMB/s]" % (
            print_success('success'), source, size_to_gb(filesize), cost_time, size_to_mb(speed)))

    except Exception as e:
        log('move %s:%s' % (print_error('error'), e))
    finally:
        current_dirs.remove(target)
        current_files.remove(source)


def get_free(disk):
    _, _, free = shutil.disk_usage(disk)
    return size_to_gb(free)


def convert_n_bytes(n, b):
    bits = b * 8
    return (n + 2 ** (bits - 1)) % 2 ** bits - 2 ** (bits - 1)


def convert_4_bytes(n):
    return convert_n_bytes(n, 4)


def get_hash_code(s):
    h = 0
    n = len(s)
    for i, c in enumerate(s):
        h = h + ord(c) * 31 ** (n - 1 - i)
    return convert_4_bytes(h)


def match_bucket(name, bucket):
    hash_code = get_hash_code(name)
    b = hash_code % 10
    return b in bucket


def get_files(_dir, suffix='plot', bucket=[]):
    """get all the plot files"""
    if not _dir or not os.path.isdir(_dir):
        return []
    names = os.listdir(_dir)
    files = []
    for name in names:
        name = os.path.join(_dir, name)
        if bucket and not match_bucket(name, bucket):
            continue
        if os.path.isfile(name) and name.endswith(".%s" % suffix):
            files.append(name)
    return files


def timestamp_to_time(timestamp):
    time_struct = time.localtime(timestamp)
    return time.strftime('%Y-%m-%d %H:%M:%S', time_struct)


def get_file_size(file_path):
    size = os.path.getsize(file_path)
    return size_to_gb(size)


def is_need_move(time_diff):
    if time_diff >= 20:
        return True
    return False


def is_mountpoint(path):
    if path[-1] == '/':
        path = path[:-1]
    parent_device = os.stat(os.path.dirname(path)).st_dev
    own_device = os.stat(path).st_dev
    return own_device != parent_device


def parse_hdd_dir(hdd_dir_list):
    hdd_dir_infos = []
    for s in hdd_dir_list:
        max_file_count = 0
        hdd_dir = None
        if s.find("=") > 0:
            max_file_count = int(s.split("=")[1])
            hdd_dir = s.split("=")[0]
        else:
            hdd_dir = s
        hdd_dirs = parse_express(hdd_dir)
        for hdd_dir in hdd_dirs:
            log("target dir:%s" % hdd_dir)
            hdd_dir_infos.append({
                'hdd_dir': hdd_dir,
                'max_file_count': max_file_count
            })
    return hdd_dir_infos


def parse_express(dir_name):
    ndir_list = []
    if dir_name.find("[") > 0 and dir_name.find("]") > 0:
        start = dir_name.find("[")
        end = dir_name.find("]")
        prefix = dir_name[:start]
        suffix = dir_name[end + 1:]
        express = dir_name[start + 1:end]
        datas = express.split("-")
        seq_start = int(datas[0])
        seq_end = int(datas[1])
        for i in range(seq_start, seq_end + 1):
            ndir_list.append("%s%s%s" % (prefix, format_number(i), suffix))
    else:
        ndir_list.append(dir_name)
    return ndir_list


def format_number(i):
    if i <= 9:
        return '0%s' % i
    return i


class MoveAssistant:
    ORDER = 1
    AVG = 2

    def __init__(self, temp_dir_list, hdd_dir_list, sub_dir_name='', scan_interval=30, max_concurrency=5,
                 move_strategy=1, suffix='plot', skip_mount_point_check=False, auto_remove_grep='', bucket=[]):
        self.max_concurrency = max_concurrency
        self.temp_dir_list = temp_dir_list
        self.hdd_dir_info_list = parse_hdd_dir(hdd_dir_list)
        self.sub_dir_name = sub_dir_name
        self.scan_interval = scan_interval
        self.move_strategy = move_strategy
        self.suffix = suffix
        self.skip_mount_point_check = skip_mount_point_check
        self.auto_remove_grep = auto_remove_grep
        self.bucket = bucket
        self.pool = multiprocessing.Pool(max_concurrency)  # processing pool
        self.current_dirs = multiprocessing.Manager().list()
        self.current_files = multiprocessing.Manager().list()

    def add_move_task(self, plot_name, target):
        self.current_dirs.append(target)
        self.current_files.append(plot_name)
        self.pool.apply_async(move, (
            plot_name, target, self.sub_dir_name, self.current_dirs, self.current_files, self.suffix))
        log("add move task success:%s" % plot_name)
        return True

    def is_hdd_dir_enable(self, hdd_dir, max_file_count, file_size):
        if max_file_count == 0:
            free = get_free(hdd_dir)
            enable = free >= file_size
        else:
            files = get_files(os.path.join(hdd_dir, self.sub_dir_name), self.suffix)
            free = (max_file_count - len(files)) * 102
            enable = free > 0
        return enable, free

    def auto_remove_old(self, file_size, grep, max_remove=3):
        empty_count = 0
        for hdd_dir_info in self.hdd_dir_info_list:
            hdd_dir = hdd_dir_info['hdd_dir']
            if not os.path.exists(hdd_dir):
                continue

            if hdd_dir in self.current_dirs:
                continue

            free = get_free(hdd_dir)
            if free > file_size:
                empty_count += 1
                if empty_count >= max_remove:
                    break

        if empty_count >= max_remove:
            return

        for hdd_dir_info in self.hdd_dir_info_list:
            hdd_dir = hdd_dir_info['hdd_dir']
            if not os.path.exists(hdd_dir):
                continue

            if hdd_dir in self.current_dirs:
                continue

            free = get_free(hdd_dir)
            if free <= file_size:
                if remove_one_plot(hdd_dir, grep):
                    empty_count += 1

            if empty_count >= max_remove:
                return

    def select_one_hdd(self, file_size):
        disks = []
        for hdd_dir_info in self.hdd_dir_info_list:
            hdd_dir = hdd_dir_info['hdd_dir']
            if not os.path.exists(hdd_dir):
                continue
            if os.name != 'nt' and not self.skip_mount_point_check and not is_mountpoint(hdd_dir):
                log("hdd dir is not mount point:%s" % hdd_dir)
                continue
            max_file_count = hdd_dir_info['max_file_count']
            if hdd_dir in self.current_dirs:
                continue
            enable, free = self.is_hdd_dir_enable(hdd_dir, max_file_count, file_size)
            if not enable:
                continue
            disks.append({
                'hdd_dir': hdd_dir,
                'free': free
            })
        if not disks:
            return None

        if self.move_strategy == MoveAssistant.ORDER:
            disks = sorted(disks, key=lambda x: x['hdd_dir'], reverse=False)
        else:
            disks = sorted(disks, key=lambda x: x['free'], reverse=True)

        return disks[0]['hdd_dir']

    def check_auto_remove(self, file_size):
        if file_size <= 0:
            return
        if self.auto_remove_grep:
            self.auto_remove_old(file_size, self.auto_remove_grep)

    def main(self):
        single_file_size = 0
        for temp_dir in self.temp_dir_list:
            files = get_files(temp_dir, self.suffix, self.bucket)
            if not files:
                log("get 0 files from temp dir:[%s]" % temp_dir)
            now = time.time()
            for file in files:
                if file in self.current_files:
                    continue
                modify_time = os.path.getmtime(file)
                time_diff = now - modify_time
                if is_need_move(time_diff):
                    file_size = get_file_size(file)
                    if single_file_size == 0:
                        single_file_size = file_size
                    target = self.select_one_hdd(file_size)
                    if not target:
                        self.check_auto_remove(single_file_size)
                        return
                    else:
                        dist = os.path.join(target, self.sub_dir_name)
                        log("move to:%s" % dist)
                        self.add_move_task(file, target)

        self.check_auto_remove(single_file_size)

    def start(self):
        log('start')
        while True:
            try:
                while len(self.current_files) >= self.max_concurrency:
                    time.sleep(1)
                self.main()
            except Exception as e:
                print(e)
            time.sleep(self.scan_interval)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
       This script is for move plot files from ssd to hdd.
    """)
    parser.add_argument("temp_dir_list", help="chia plot temp dir list, , split by comma")
    parser.add_argument("hdd_dir_list", help="chia hdd dir list, split by comma")
    parser.add_argument("--max-concurrency", metavar="", type=int, help="max concurrency, default is 10", default=10)
    parser.add_argument("--sub-dir-name", metavar="", help="sub dir name, default is empty", default='')
    parser.add_argument("--scan-interval", metavar="", type=int, help="scan interval, default is 30 seconds",
                        default=30)
    parser.add_argument("--move-strategy", metavar="", type=int, help="move strategy 1. by order 2. avg, default is 2",
                        default=2)
    parser.add_argument("--suffix", metavar="", help="file suffix default is plot",
                        default='plot')
    parser.add_argument("--skip-mount-point-check", action="store_true",
                        help="skip check the target dir is a mount point, default is False",
                        default=True)

    parser.add_argument("--auto-remove-grep", metavar="", help="auto remove old file grep string", default="")

    parser.add_argument("--bucket", metavar="",
                        help="split file to 10 bucket, if specify, then only move the specify bucket", default='')

    args = parser.parse_args()

    temp_dir_list = args.temp_dir_list.split(",")
    hdd_dir_list = args.hdd_dir_list.split(",")
    max_concurrency = args.max_concurrency
    sub_dir_name = args.sub_dir_name
    scan_interval = args.scan_interval
    move_strategy = args.move_strategy
    suffix = args.suffix
    skip_mount_point_check = args.skip_mount_point_check
    auto_remove_grep = args.auto_remove_grep
    bucket_val = args.bucket
    bucket = []
    if bucket_val:
        bucket = [int(v) for v in bucket_val.split(',')]

    assistant = MoveAssistant(temp_dir_list, hdd_dir_list, sub_dir_name, scan_interval, max_concurrency,
                              move_strategy, suffix, skip_mount_point_check, auto_remove_grep, bucket)
    assistant.start()
