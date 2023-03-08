from base64 import b64encode
import datetime
import json
from queue import Queue

import sys


def log(string):
    sys.stderr.write(
        datetime.datetime.now().strftime("%H:%M:%S.%f") + " 4254send: " + string + "\n"
    )


def input(queue: Queue, data_size: int = 1000):
    pn = 0

    while True:
        data = sys.stdin.buffer.read(data_size)
        pn += 1
        if len(data) > 0:
            msg = {
                "pn": pn,
                "data": b64encode(data).decode(),
                "ack": False,
                "eof": False,
            }
            queue.put(msg, block=True)
        else:
            msg = {
                "pn": pn,
                "data": "",
                "ack": False,
                "eof": True,
            }

            queue.put(msg, block=True)
            break
