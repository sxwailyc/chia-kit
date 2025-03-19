#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
import shutil
import hashlib


def calculate_md5(file_path):
    """计算文件的MD5值（支持大文件）"""
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):  # 每次读取8KB
            md5.update(chunk)
    return md5.hexdigest()


def sync_files(source_dir, target_dir):
    """同步源目录文件到目标目录"""
    # 创建目标目录（如果不存在）
    os.makedirs(target_dir, exist_ok=True)

    # 遍历源目录文件（忽略子目录）
    for filename in os.listdir(source_dir):
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)

        # 跳过目录处理
        if not os.path.isfile(source_path):
            continue

        # 处理目标文件存在的情况
        if os.path.exists(target_path):
            # 计算两个文件的MD5
            source_md5 = calculate_md5(source_path)
            target_md5 = calculate_md5(target_path)

            if source_md5 == target_md5:
                # 删除源文件（内容相同）
                os.remove(source_path)
                print(f"✅ 删除重复文件：{filename}")
            else:
                # 删除目标文件并移动源文件
                os.remove(target_path)
                shutil.move(source_path, target_path)
                print(f"🔄 覆盖更新文件：{filename}")
        else:
            # 直接移动文件
            shutil.move(source_path, target_path)
            print(f"⏩ 移动新文件：{filename}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
           This script is mount disk or make file system.
        """)
    parser.add_argument("source_dir", help="source dir")
    parser.add_argument("target_dir", help="target dir")

    args = parser.parse_args()

    action = args.action
    source_dir = args.source_dir
    target_dir = args.target_dir
    sync_files(source_dir, target_dir)