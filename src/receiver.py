import heapq
import json
import sys
from base64 import b64decode
from socket import socket
from typing import Any, Dict, Optional

from src.checksum import compute_checksum, verify_checksum
from src.constants import ACKNOWLEDGED, CHECKSUM, END_OF_FILE, SEQUENCE_NUMBER
from src.logging import get_logger


class Receiver:
    """
    Class that binds together data and behaviour for the thread that receives
    data in 4254recv.
    """

    def __init__(self, sock: socket, message_size: int):
        self.sock = sock
        self.message_size = message_size

        # ACK and duplicate handling

        # Highest Cumulative Packet number
        self.hcp = 0
        # Other packet numbers received with sequence > hcp
        self.other_packets = []

        # Ordering handling

        # All packets received so far
        self.received_packets = []

        # EOF handling (since the EOF can arrive out of order.)

        # Whether we've received the EOF packet or not
        self.reached_eof = False
        # The sequence number of the EOF packet - 1
        self.max_packets = 0
        self.eof_address = None

        self.logger = get_logger("[4254recv] Receiver")

    def __generate_ack_packet(self, pn: Any) -> Dict:
        """
        Generate an ack packet for packet number pn with the checksum included.
        """

        packet = {ACKNOWLEDGED: pn}
        cksum = compute_checksum(packet)
        packet[CHECKSUM] = cksum

        return packet

    def __handle_eof_packet(self, pn: int, addr):
        """
        Set all the fields which are required to handle an EOF packet.
        """

        self.logger.debug("Received an EOF packet.")
        self.max_packets = pn - 1
        self.logger.debug(
            "EOF packet has sequence %s, %s will be taken as the last non-EOF packet.",
            pn,
            self.max_packets,
        )
        self.reached_eof = True
        self.eof_address = addr

    def __packet_number_to_ack(self, pn: int) -> Optional[int]:
        """
        Compute which packet number to send in the ack when a packet with number
        pn is received.
        """

        self.logger.debug("Ack logic for pn %s, curent hcp %s", pn, self.hcp)

        if pn <= self.hcp or pn in self.other_packets:
            # Duplicate packet, do nothing.
            return None

        if pn == self.hcp + 1:
            # Next packet
            self.hcp = pn

            # If the lowest packet in other_packets is sequentially after hcp,
            # pop it and incrememnt hcp.
            while len(self.other_packets) > 0:
                lowest_other_packet = self.other_packets[0]

                if lowest_other_packet == self.hcp + 1:
                    self.hcp = lowest_other_packet
                    heapq.heappop(self.other_packets)
                else:
                    break
        else:
            heapq.heappush(self.other_packets, pn)

        return self.hcp

    def __ack_eof(self):
        # Doing it 10 times so that the chances of it getting dropped are low.
        self.logger.debug("Acking EOF 10 times.")
        ack_packet = json.dumps(self.__generate_ack_packet(END_OF_FILE)).encode()
        for _ in range(10):
            self.sock.sendto(ack_packet, self.eof_address)

    def run(self):
        """
        Reads from the socket, puts non-duplicate received packets into the
        received_packets heap, and acks as described in the design.
        """

        self.logger.info("Starting to read from socket.")

        while True:
            if self.reached_eof and self.hcp == self.max_packets:
                self.logger.info(
                    "Received EOF and all packets; acking EOF and quitting."
                )
                self.__ack_eof()
                break

            received_data = self.sock.recvfrom(self.message_size)

            if not received_data:
                self.logger.info("Socket timed out; quitting.")
                break

            (data, address) = received_data
            decoded_data = data.decode()
            packet = json.loads(decoded_data)

            if not verify_checksum(packet):
                # Corrupted packet, ignore.
                continue

            pn = int(packet[SEQUENCE_NUMBER])
            self.logger.debug("Received %s bytes of packet %s", len(decoded_data), pn)

            if packet[END_OF_FILE]:
                self.__handle_eof_packet(pn, address)
                # We don't expect the EOF packet to have any data!
                continue

            pn_to_ack = self.__packet_number_to_ack(pn)
            if pn_to_ack is None:
                self.logger.debug("Packet received was duplicate, doing nothing.")
                continue

            self.logger.debug(
                "Acking packet number %s for received packet %s", pn_to_ack, pn
            )
            ack_packet = self.__generate_ack_packet(pn_to_ack)
            self.sock.sendto(json.dumps(ack_packet).encode(), address)

            heapq.heappush(self.received_packets, (pn, packet))

    def print(self):
        """
        Prints the received packets in order.
        """

        self.logger.info("Proceeding to print received data to STDOUT")
        self.logger.info("Received: %s packets", len(self.received_packets))
        while len(self.received_packets) > 0:
            (_, decoded) = heapq.heappop(self.received_packets)
            if decoded["data"]:
                data = b64decode(decoded["data"].encode())
                sys.stdout.buffer.write(data)
