from collections import namedtuple
import datetime
import heapq
import json
import os
from queue import Queue
import signal
import socket
import sys
from threading import Lock

Destination = namedtuple("Destination", ["ip", "port"])


def log(string):
    sys.stderr.write(
        datetime.datetime.now().strftime("%H:%M:%S.%f") + " 4254send: " + string + "\n"
    )


def send_to_socket(
    queue: Queue,
    sent_packets: list,
    sent_lock: Lock,
    sock: socket.socket,
    dest: Destination,
):
    while True:
        msg = queue.get(block=True)

        if "die" in msg:
            return

        sent_data_size = sock.sendto(json.dumps(msg).encode(), dest)

        if sent_data_size < len(msg):
            log("[error] unable to fully send packet")
        else:
            log(f"[send data] {len(msg)} {msg['pn']}")
            with sent_lock:
                heapq.heappush(sent_packets, (msg["pn"], msg))


def read_from_socket(
    queue: Queue,
    sock: socket.socket,
    sent_packets: list,
    sent_lock: Lock,
    message_size: int,
):
    duplicates = 0

    while True:
        result = sock.recvfrom(message_size)

        if result:
            (data, _) = result
            decoded = json.loads(data.decode())
            log("[recv pkt] " + str(decoded))
            acked_packet_number = decoded["ack"]
            log("[recv ack] " + str(acked_packet_number))
            if acked_packet_number == "eof":
                queue.put({"die": True})
                return

            else:
                with sent_lock:
                    log(str([packet[0] for packet in sent_packets]))
                    lowest_packet = sent_packets[0][0]
                    if acked_packet_number < lowest_packet:
                        log(f"Received duplicate ack: {acked_packet_number}")
                        duplicates += 1

                        if duplicates == 3:
                            log(
                                f"Received three duplicates; sending smallest packet again."
                            )
                            (_, lowest_packet) = heapq.heappop(sent_packets)
                            duplicates = 0
                            queue.put(lowest_packet, block=True)

                    elif acked_packet_number == lowest_packet:
                        heapq.heappop(sent_packets)
                    else:
                        log(
                            f"Received an ack for a non-lowest packet: {acked_packet_number}"
                        )
                        log(f"Current lowest packet: {lowest_packet}")
                        while lowest_packet > acked_packet_number:
                            heapq.heappop(sent_packets)
                            lowest_packet = sent_packets[0][0]

        else:
            break
