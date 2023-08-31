#!/usr/bin/python
# -*- coding: utf-8 -*-

import fcntl
import sys
import socket
import json
import time

import requests
import subprocess

import argparse
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def to_int(s):
    try:
        return int(s)
    except:
        return 0


def call_grpc(port, service, data={}):
    """call grpc"""
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "grpcurl")
    result = subprocess.check_output([cmd, '--plaintext', '-d', json.dumps(data), f'127.0.0.1:{port}', service])

    dict_result = json.loads(result)
    return dict_result


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"


def split_line(line):
    datas = line.split(" ")
    ndatas = []
    for data in datas:
        if data:
            ndatas.append(data)
    return ndatas


def is_root():
    return os.getuid() == 0


def report(secret, machine_info, node_infos):
    data = json.dumps({
        "secret": secret,
        "machine": machine_info,
        "nodes": node_infos
    })
    try_times = 0
    while try_times < 3:
        try:
            response = requests.post("https://api.mingyan.com/api/spacemesh/monitor", data)
            break
        except:
            time.sleep(10)
        try_times += 1


def get_nodes(secret, host_name):
    response = requests.get(f"https://api.mingyan.com/api/spacemesh/nodes?secret={secret}&hostname={host_name}")
    data = json.loads(response.text)
    return data["data"]["nodes"]


def get_node_info(public_port, private_port):
    try:
        node_result = call_grpc(public_port, "spacemesh.v1.NodeService.Status")
        connected_peers = node_result["status"].get("connectedPeers", 0)
        is_synced = node_result["status"].get("isSynced", False)
        synced_layer = node_result["status"]["syncedLayer"]["number"]
        top_layer = node_result["status"]["topLayer"]["number"]
        verified_layer = node_result["status"]["verifiedLayer"]["number"]

        version_result = call_grpc(public_port, "spacemesh.v1.NodeService.Version")
        version = version_result["versionString"]["value"]

        post_result = call_grpc(private_port, "spacemesh.v1.SmesherService.PostSetupStatus")
        post_state = post_result["status"].get["state"]
        num_labels_written = post_result["status"].get("numLabelsWritten", 0)
        opts = post_result["status"]["opts"]
        if opts:
            data_dir = opts["dataDir"]
            num_units = opts["numUnits"]
            max_filesize = opts["maxFileSize"]
        else:
            data_dir = ""
            num_units = 0
            max_filesize = 0

        smeshing_result = call_grpc(private_port, "spacemesh.v1.SmesherService.IsSmeshing")
        is_smeshing = smeshing_result["isSmeshing"]

        node_info = {
            'connected_peers': connected_peers,
            'is_synced': is_synced,
            'synced_layer': synced_layer,
            'top_layer': top_layer,
            'verified_layer': verified_layer,
            'post_state': post_state,
            'num_labels_written': num_labels_written,
            'data_dir': data_dir,
            'num_units': num_units,
            'max_filesize': max_filesize,
            'is_smeshing': is_smeshing,
            'version': version
        }
        return True, node_info
    except Exception as e:
        print(f"error:{e}")
    return False, {}


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    nodes = get_nodes(secret, host_name)
    node_infos = []
    all_size = 0
    finish_size = 0
    node_count = 0
    for node in nodes:
        success, node_info = get_node_info(node['publicPort'], node['privatePort'])
        node_count += 1
        if success:
            num_units = node_info["num_units"]
            state = node_info['post_state']
            size = num_units * 64 * 1024 * 1024 * 1024
            all_size += size
            if state == 'STATE_COMPLETE':
                finish_size += size

            node_info['node_id'] = node['id']
            node_infos.append(node_info)
            print(f"node info:{node_info}")
        else:
            print(f"get node info error: {node['publicPort']}")

    machine_info = {
        'host_name': host_name,
        'ip': get_local_ip(),
        'all_size': all_size,
        'finish_size': finish_size,
        'node_count': node_count
    }

    report(secret, machine_info, node_infos)


def acquire_port_lock(port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', port))
        sock.listen(1)
        fcntl.flock(sock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return sock
    except IOError:
        print(f"Another process is already listening on port {port}. Exiting.")
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
    parser.add_argument("--lock-port", metavar="", type=int, help="lock port, default is 9000",
                        default=9000)

    args = parser.parse_args()
    secret = args.secret
    port = args.lock_port
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)
    host_name = args.host_name
    sock = None
    try:
        # sock = acquire_port_lock(port)
        print('lock success')
        main(secret=secret, host_name=host_name)
    finally:
        if sock:
            release_port_lock(sock)
