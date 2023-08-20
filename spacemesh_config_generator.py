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


def generate(output_dir, start_port):
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
        target = os.path.join(output_dir, "config.mainnet.json")
        with open(target, "w") as of:
            of.write(content)
            log("success write config.mainnet.json to %s" % output_dir)


def is_root():
    return os.getuid() == 0


if __name__ == '__main__':
    if not is_root():
        print("must run by root")
        sys.exit(0)

    parser = argparse.ArgumentParser(description="""
       This script is for monitor the harvester server and report to the server.
    """)
    parser.add_argument("-o", "--output-dir", metavar="", help="output dir", default='')
    parser.add_argument("-p", "--start-port", metavar="", type=int, help="start port, default is 9092",
                        default=9092)

    args = parser.parse_args()
    output_dir = args.output_dir
    start_port = args.start_port
    generate(output_dir, start_port)
