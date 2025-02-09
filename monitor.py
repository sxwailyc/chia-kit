#!/usr/bin/python
# -*- coding: utf-8 -*-

import fcntl
import sys
import socket

from subprocess import getoutput

from monitor_base import Base, log

import argparse
import os


def get_chia_count(base_dir):
    count = 0
    nossd_count = 0
    if not dir or not os.path.isdir(base_dir):
        return count, nossd_count
    names = os.listdir(base_dir)
    for name in names:
        name = os.path.join(base_dir, name)
        if os.path.isfile(name):
            if name.endswith(".plot"):
                count += 1
            elif name.endswith(".fpt"):
                nossd_count += 1
        else:
            if not os.path.exists(name):
                continue
            files = os.listdir(name)
            for file in files:
                file = os.path.join(name, file)
                if os.path.isfile(file):
                    if file.endswith(".plot"):
                        count += 1
                    elif file.endswith(".fpt"):
                        nossd_count += 1
                else:
                    sub_files = os.listdir(file)
                    for sub_file in sub_files:
                        sub_file = os.path.join(file, sub_file)
                        if os.path.isfile(sub_file) and sub_file.endswith(".plot"):
                            count += 1
                        elif os.path.isfile(sub_file) and sub_file.endswith(".fpt"):
                            nossd_count += 1

    return count, nossd_count


def is_root():
    return os.getuid() == 0


def is_harvester_alive():
    cmd = "ps -eo pid,args | grep chia_harvester | grep -v grep"
    out = getoutput(cmd)
    lines = out.split("\n")
    for line in lines:
        if line.find("chia_harvester") != -1:
            return 1
    return 0


class ChiaMonitor(Base):

    def __init__(self, secret, host_name, print_info):
        super().__init__(secret, host_name, print_info, "https://api.mingyan.com/api/chia/monitor", "disks")
        self.all_plot_count = 0
        self.all_nossd_count = 0

    def is_need_handle(self, disk):
        total_write = disk['total_write']
        if total_write > 0:
            return False
        return True

    def handle_single_disk(self, disk):
        mount_point = disk['mount_point']
        plot_count, nossd_count = get_chia_count(mount_point)
        disk['plot_count'] = plot_count
        disk['nossd_count'] = nossd_count
        self.all_plot_count += plot_count
        self.all_nossd_count += nossd_count

    def handle_machine_info(self, machine):
        machine['plot_count'] = self.all_plot_count
        machine['nossd_count'] = self.all_nossd_count
        machine['harvester'] = is_harvester_alive()


def acquire_port_lock(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', port))
        sock.listen(1)
        fcntl.flock(sock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return sock
    except IOError:
        log(f"Another process is already listening on port {port}. Exiting.")
        exit(1)


def release_port_lock(sock):
    fcntl.flock(sock.fileno(), fcntl.LOCK_UN)
    sock.close()


if __name__ == '__main__':

    if not is_root():
        print("must run by root")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="""
       This script is for monitor the harvester server and report to the server.
    """)
    parser.add_argument("--host-name", metavar="", help="the host name, default is current host name", default='')
    parser.add_argument("--secret", metavar="", help="secret, use to post to server ")
    parser.add_argument("-p", "--print", action="store_true",
                        help="whether print the info, default is False",
                        default=False)
    parser.add_argument("--lock-port", metavar="", type=int, help="lock port, default is 8000",
                        default=8000)

    args = parser.parse_args()
    secret = args.secret
    port = args.lock_port
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)

    log(f'secret {secret}')

    host_name = args.host_name
    print_info = args.print

    sock = None
    try:
        log('start to lock')
        sock = acquire_port_lock(port)
        log('lock success')
        monitor = ChiaMonitor(secret=secret, host_name=host_name, print_info=print_info)
        monitor.run()
        log("start to exit")
        sys.exit(0)
    finally:
        if sock:
            release_port_lock(sock)
