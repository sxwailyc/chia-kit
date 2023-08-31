#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import subprocess

import sys
from subprocess import PIPE, Popen
from threading import Thread
from queue import Queue, Empty

import os

def test():
    cmd = os.path.join(os.path.join(os.path.dirname(__file__), "bin"), "grpcurl")
    data = {}
    service = "spacemesh.v1.AdminService.EventsStream"
    p = subprocess.Popen([cmd, '--plaintext', '-d', json.dumps(data), '127.0.0.1:9096', service], stdout=subprocess.PIPE)

    ON_POSIX = 'posix' in sys.builtin_module_names

    def enqueue_output(out, queue):
        for line in iter(out.readline, b''):
            queue.put(line)
        out.close()

    p = Popen(['myprogram.exe'], stdout=PIPE, bufsize=1, close_fds=ON_POSIX)
    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True  # thread dies with the program
    t.start()

    # ... do other things here

    # read line without blocking
    try:
        line = q.get_nowait()  # or q.get(timeout=.1)
    except Empty:
        print('no output yet')
    else:  # got line
        print(line)


# ... do something with line

if __name__ == '__main__':
    test()