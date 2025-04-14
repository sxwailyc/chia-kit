#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import concurrent.futures


def generate_ips(prefix):
    """根据前三位生成所有可能的IP地址（第四位 1-254）"""
    base = f"{prefix}."
    return [f"{base}{i}" for i in range(1, 255)]


def scan_port(ip, port=80, timeout=1):
    """检测指定IP的端口是否开放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            return ip if result == 0 else None
    except (socket.error, socket.timeout):
        return None


def validate_prefix(prefix):
    """验证用户输入的IP前缀格式"""
    parts = prefix.split('.')
    if len(parts) != 3 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        raise ValueError("请输入合法的前三位IP地址，例如: 192.168.1")


if __name__ == "__main__":
    # 用户输入IP前三位
    prefix = input("请输入IP前三位（例如 192.168.1）: ").strip()
    validate_prefix(prefix)

    # 生成目标IP列表
    targets = generate_ips(prefix)
    print(f"正在扫描 {len(targets)} 个主机...")

    # 多线程扫描
    open_ips = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(scan_port, ip): ip for ip in targets}
        for future in concurrent.futures.as_completed(futures):
            ip = futures[future]
            result = future.result()
            if result:
                open_ips.append(result)
                print(f"发现开放80端口: {result}")

    # 输出结果
    print("\n扫描完成，开放80端口的IP列表:")
    print('\n'.join(open_ips) if open_ips else "未发现开放80端口的设备")
