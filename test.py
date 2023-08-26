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
import select

def test():
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "grpcurl")
    data = {}
    service = "spacemesh.v1.AdminService.EventsStream"
    p = subprocess.Popen([cmd, '--plaintext', '-d', json.dumps(data), '127.0.0.1:9096', service], stdout=subprocess.PIPE)
    poll_obj = select.poll()
    poll_obj.register(p.stdout, select.POLLIN)
    while True:
        poll_result = poll_obj.poll(0)
        if poll_result:
            line = p.stdout.readline()
            if line:
                print(line)
            else:
                break

if __name__ == '__main__':
    test()