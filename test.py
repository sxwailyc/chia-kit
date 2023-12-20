import fcntl
import socket
import time

from datetime import datetime

def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def acquire_port_lock(port):
    try:
        print(1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(2)
        sock.bind(('localhost', port))
        print(3)
        sock.listen(1)
        print(4)
        fcntl.flock(sock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return sock
    except IOError:
        log(f"Another process is already listening on port {port}. Exiting.")
        exit(1)


def release_port_lock(sock):
    fcntl.flock(sock.fileno(), fcntl.LOCK_UN)
    sock.close()


def main():
    sock = None
    try:
        sock = acquire_port_lock(10000)
        time.sleep(1000)
    finally:
        release_port_lock(sock)


if __name__ == '__main__':
    main()