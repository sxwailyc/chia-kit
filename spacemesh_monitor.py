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
            requests.post("https://api.mingyan.com/api/spacemesh/monitor", data)
            break
        except:
            time.sleep(10)
        try_times += 1


def get_nodes(secert, host_name):
    return [{
        'public': 9092,
        'private_port': 9093
    }]


def get_node_info(public_port, private_port):
    try:
        node_result = call_grpc(public_port, "spacemesh.v1.NodeService.Status")
        connected_peers = node_result["status"]["connectedPeers"]
        is_synced = node_result["status"]["isSynced"]
        synced_layer = node_result["status"]["syncedLayer"]["number"]
        top_layer = node_result["status"]["topLayer"]["number"]
        verified_layer = node_result["status"]["verifiedLayer"]["number"]

        post_result = call_grpc(private_port, "spacemesh.v1.SmesherService.PostSetupStatus")
        post_state = post_result["status"]["state"]
        data_dir = post_result["status"]["opts"]["dataDir"]
        num_units = post_result["status"]["opts"]["numUnits"]
        max_filesize = post_result["status"]["opts"]["maxFileSize"]

        smeshing_result = call_grpc(public_port, "spacemesh.v1.SmesherService.IsSmeshing")
        is_smeshing = smeshing_result["isSmeshing"]
        node_info = {
            'connected_peers': connected_peers,
            'is_synced': is_synced,
            'synced_layer': synced_layer,
            'top_layer': top_layer,
            'verified_layer': verified_layer,
            'post_state': post_state,
            'data_dir': data_dir,
            'num_units': num_units,
            'max_filesize': max_filesize,
            'is_smeshing': is_smeshing,
        }
        return True, node_info
    except Exception as e:
        print(e)
    return False, {}


def main(secret, host_name):
    if not host_name:
        host_name = socket.gethostname()
        print(host_name)

    nodes = get_nodes(secret, host_name)
    node_infos = []
    all_size = 0
    for node in nodes:
        success, node_info = get_node_info(node['public_port'], node['private_port'])
        if success:
            num_units = node_info["num_units"]
            all_size += num_units * 64 * 1024 * 1024
            node_infos.append(node_info)

    machine_info = {
        'host_name': host_name,
        'ip': get_local_ip(),
        'all_size': all_size,
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
    parser.add_argument("--lock-port", metavar="", type=int, help="lock port, default is 8000",
                        default=8000)

    args = parser.parse_args()
    secret = args.secret
    port = args.lock_port
    if not secret:
        print("please input secret with --secret")
        sys.exit(0)
    host_name = args.host_name
    sock = None
    try:
        sock = acquire_port_lock(port)
        print('lock success')
        main(secret=secret, host_name=host_name)
    finally:
        if sock:
            release_port_lock(sock)
