import sys
from base64 import b64encode
from queue import PriorityQueue, Queue
from typing import Dict, TextIO, Tuple

from src import checksum
from src.constants import CHECKSUM, DATA, END_OF_FILE, SEQUENCE_NUMBER
from src.logging import get_logger


class InputReader:
    """
    Class to bind together state and behaviour for the thread that reads from
    STDIN.
    """

    def __init__(
        self,
        packets_to_send: "PriorityQueue[Tuple[int, Dict]]",
        all_packets: Dict[int, Dict],
        data_size: int,
        stream: TextIO = sys.stdin,
    ):
        self.packets_to_send = packets_to_send
        self.all_packets = all_packets
        self.stream = stream
        self.data_size = data_size
        self.sequence_number = 0

        self.logger = get_logger("[4254send] InputReader")

    def run(self):
        """
        Read from the stream, chunk data into packets of data_size, and put
        them into the packets_to_send queue.

        Run this in a thread or you'll block!
        """

        self.logger.info("Starting to read from STDIN")

        while True:
            data = self.stream.buffer.read(self.data_size)
            self.sequence_number += 1

            if len(data) > 0:
                msg = {
                    SEQUENCE_NUMBER: self.sequence_number,
                    DATA: b64encode(data).decode(),
                    END_OF_FILE: False,
                }

                self.queue_packet(msg)
            else:
                msg = {
                    SEQUENCE_NUMBER: self.sequence_number,
                    DATA: "",
                    END_OF_FILE: True,
                }

                self.queue_packet(msg)
                break

        self.logger.info("Read all of STDIN; ending thread.")

    def queue_packet(self, msg):
        cksum = checksum.compute_checksum(msg)
        msg[CHECKSUM] = cksum

        self.packets_to_send.put((self.sequence_number, msg), block=True)
        self.all_packets[self.sequence_number] = msg
