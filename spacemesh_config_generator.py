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

boot_nodes = """"bootnodes": [
      "/dns4/mainnet-bootnode-0.spacemesh.network/tcp/5000/p2p/12D3KooWPStnitMbLyWAGr32gHmPr538mT658Thp6zTUujZt3LRf",
      "/dns4/mainnet-bootnode-2.spacemesh.network/tcp/5000/p2p/12D3KooWAsMgXLpyGdsRNjHBF3FaXwnXhyMEqWQYBXUpvCHNzFNK",
      "/dns4/mainnet-bootnode-4.spacemesh.network/tcp/5000/p2p/12D3KooWRcTWDHzptnhJn5h6CtwnokzzMaDLcXv6oM9CxQEXd5FL",
      "/dns4/mainnet-bootnode-6.spacemesh.network/tcp/5000/p2p/12D3KooWRS47KAs3ZLkBtE2AqjJCwxRYqZKmyLkvombJJdrca8Hz",
      "/dns4/mainnet-bootnode-8.spacemesh.network/tcp/5000/p2p/12D3KooWFYv99aGbtXnZQy6UZxyf72NpkWJp3K4HS8Py35WhKtzE",
      "/dns4/mainnet-bootnode-10.spacemesh.network/tcp/5000/p2p/12D3KooWHK5m83sNj2eNMJMGAngcS9gBja27ho83t79Q2CD4iRjQ",
      "/dns4/mainnet-bootnode-12.spacemesh.network/tcp/5000/p2p/12D3KooWG4gk8GtMsAjYxHtbNC7oEoBTMRLbLDpKgSQMQkYBFRsw",
      "/dns4/mainnet-bootnode-14.spacemesh.network/tcp/5000/p2p/12D3KooWRkZMjGNrQfRyeKQC9U58cUwAfyQMtjNsupixkBFag8AY",
      "/dns4/mainnet-bootnode-16.spacemesh.network/tcp/5000/p2p/12D3KooWDAFRuFrMNgVQMDy8cgD71GLtPyYyfQzFxMZr2yUBgjHK",
      "/dns4/mainnet-bootnode-18.spacemesh.network/tcp/5000/p2p/12D3KooWMJmdfwxDctuGGoTYJD8Wj9jubQBbPfrgrzzXaQ1RTKE6"
    ],"""

def generate(output_dir, start_port, direct_port=7514, direct_id=None):
    """generator config"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    grpc_public_listener = start_port
    grpc_private_listener = start_port + 1
    grpc_json_listener = start_port + 2
    log("grpc-public-listener:%s" % grpc_public_listener)
    log("grpc-private-listener:%s" % grpc_private_listener)
    log("grpc-json-listener:%s" % grpc_json_listener)
    template = os.path.join(os.path.join(os.path.dirname(__file__), "config"), "config.mainnet.json")
    with open(template, "r") as f:
        content = f.read()
        content = content.replace('${grpc-public-listener}', '%s' % grpc_public_listener)
        content = content.replace('${grpc-private-listener}', '%s' % grpc_private_listener)
        content = content.replace('${grpc-json-listener}', '%s' % grpc_json_listener)

        min_peers = 30
        lower_peers = 80
        high_peers = 80

        if direct_id:
            min_peers = 1
            lower_peers = 10
            high_peers = 20
            node_settings = f""""disable-dht": true,
    "bootnodes": [],
    "direct": [
        "/ip4/0.0.0.0/tcp/{direct_port}/p2p/{direct_id}"
    ],"""
        else:
            node_settings = boot_nodes

        content = content.replace('${node-settings}', '%s' % node_settings)
        content = content.replace('${min-peers}', '%s' % min_peers)
        content = content.replace('${lower-peers}', '%s' % lower_peers)
        content = content.replace('${high-peers}', '%s' % high_peers)

        target = os.path.join(output_dir, "config.mainnet.json")
        with open(target, "w") as of:
            of.write(content)
            log("success write config.mainnet.json to %s" % output_dir)


def is_root():
    return os.getuid() == 0


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="""
       This script is for monitor the harvester server and report to the server.
    """)
    parser.add_argument("-o", "--output-dir", metavar="", help="output dir", default='./')
    parser.add_argument("-p", "--start-port", metavar="", type=int, help="start port, default is 9092",
                        default=9092)
    parser.add_argument("--direct-port", metavar="", type=int, help="direct port, default is 0",
                        default=0)
    parser.add_argument("--direct-id", metavar="", help="direct id, default is empty",
                        default=0)

    args = parser.parse_args()
    output_dir = args.output_dir
    start_port = args.start_port
    direct_port = args.direct_port
    direct_id = args.direct_id
    generate(output_dir, start_port, direct_port=direct_port, direct_id=direct_id)
