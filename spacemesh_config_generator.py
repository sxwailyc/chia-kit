#!/usr/bin/python
# -*- coding: utf-8 -*-

#https://configs.spacemesh.network/config.mainnet.metrics.json

import argparse
import ipaddress
import os
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def is_valid_ip(address):
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


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


def generate(output_dir, start_port, directs=[]):
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

        min_peers = 60
        low_peers = 120
        high_peers = 120

        if directs:
            min_peers = 1
            low_peers = 10
            high_peers = 20

            direct_list = []
            for direct in directs:
                datas = direct.split(":")
                direct_ip = datas[0]
                direct_port = datas[1]
                direct_id = datas[2]
                protocol = "ip4" if is_valid_ip(direct_ip) else "dns4"
                direct_list.append(f"/{protocol}/{direct_ip}/tcp/{direct_port}/p2p/{direct_id}")

            direct = ",\n".join(["        \"%s\"" % s for s in direct_list])
            print(direct)

            node_settings = f""""disable-dht": true,
    "bootnodes": [],
    "direct": [
{direct}
    ],"""
        else:
            node_settings = boot_nodes

        print(min_peers)
        content = content.replace('${node-settings}', '%s' % node_settings)
        content = content.replace('${min-peers}', '%s' % min_peers)
        content = content.replace('${low-peers}', '%s' % low_peers)
        content = content.replace('${high-peers}', '%s' % high_peers)

        print(content)

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
    parser.add_argument("-d", "--direct", nargs='+', action='append', help="directs")

    args = parser.parse_args()
    output_dir = args.output_dir
    start_port = args.start_port
    directs = args.direct
    if directs:
        directs = [x[0] for x in directs]
    generate(output_dir, start_port, directs=directs)
