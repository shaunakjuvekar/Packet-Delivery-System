import heapq
import json
from queue import PriorityQueue, Queue
from socket import socket
from threading import RLock
import time
from typing import Dict, Tuple

from src.constants import QUIT, SEQUENCE_NUMBER
from src.logging import get_logger


class SocketWriter:
    """
    Class to bind together state and behaviour for the thread that sends packets
    out of the socket.
    """

    def __init__(
        self,
        sock: socket,
        packets_to_send: "PriorityQueue[Tuple[int,Dict]]",
        outstanding_packets: Dict[int, Tuple[Dict, float]],
        outstanding_packets_lock: RLock,
        destination: Tuple[str, int],
    ):
        self.sock = sock

        self.packets_to_send = packets_to_send

        self.outstanding_packets = outstanding_packets
        self.outstanding_packets_lock = outstanding_packets_lock

        self.destination = destination

        self.logger = get_logger("[4254send] SocketWriter")

    def run(self):
        """
        Block on the packets_to_send queue and send any packets in it out the
        socket, putting them into outstanding_packets when doing so.
        """

        self.logger.info("Starting to send to %s", self.destination)
        while True:
            (_, packet_to_send) = self.packets_to_send.get()

            if QUIT in packet_to_send and packet_to_send[QUIT]:
                self.logger.info("Received QUIT message on queue; quitting.")
                return

            data_to_send = json.dumps(packet_to_send)
            pn = packet_to_send[SEQUENCE_NUMBER]
            self.logger.debug(
                "Sending %s bytes of packet %s",
                len(data_to_send),
                pn,
            )

            sent_data_size = self.sock.sendto(data_to_send.encode(), self.destination)

            if sent_data_size < len(data_to_send):
                # Unable to send full packet?
                self.logger.critical("Unable to send full packet!")
            else:
                with self.outstanding_packets_lock:
                    self.outstanding_packets[pn] = (packet_to_send, time.monotonic())
