#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess
import socket
import time
from datetime import datetime

HOST = 'www.baidu.com'


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def is_network_ok():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # 设置超时时间为5秒
    try:
        sock.connect((HOST, 80))
        return True
    except socket.error:
        return False
    finally:
        sock.close()


def check_network_connection():
    # 使用ping命令检测网络连接
    error_count = 0
    while True:
        if is_network_ok():
            return True
        else:
            error_count += 1
            log(f"失败次数 {error_count}")
            if error_count >= 3:
                return False
            else:
                time.sleep(10)


def restart_machine():
    # 执行重启机器的命令，具体命令根据操作系统可能会有所不同
    subprocess.call(['reboot'])


def main():
    if not check_network_connection():
        log("网络连接不通，正在重启机器...")
        restart_machine()
    else:
        log("网络通的")


if __name__ == '__main__':
    main()
