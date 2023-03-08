import heapq
import json
import socket
from queue import Empty, Queue, PriorityQueue
from threading import RLock
from typing import Dict, Tuple

from src.checksum import verify_checksum
from src.constants import ACKNOWLEDGED, END_OF_FILE, QUIT, SEQUENCE_NUMBER
from src.logging import get_logger

DUPLICATES_FOR_RETRANSMIT = 2


class SocketReader:
    """
    Class that binds together data and behaviour for the thread that reads acks
    from the socket.
    """

    def __init__(
        self,
        sock: socket.socket,
        packets_to_send: "PriorityQueue[Tuple[int,Dict]]",
        all_packets: Dict[int, Dict],
        outstanding_packets: Dict[int, Tuple[Dict, float]],
        outstanding_packets_lock: RLock,
        timeout_messagebox: Queue,
        destination: Tuple[str, int],
        message_size: int,
    ):
        self.sock = sock

        self.packets_to_send = packets_to_send
        self.timeout_messagebox = timeout_messagebox

        self.all_packets = all_packets
        self.outstanding_packets = outstanding_packets
        self.outstanding_packets_lock = outstanding_packets_lock

        self.destination = destination
        self.message_size = message_size

        # Highest Cumulative Acknowledged Packet
        #
        # Normally, I wouldn't abbreviate, but in this case this was leading to
        # excessive line lengths and therefore questionable formatting.
        self.hcap: int = 0
        self.duplicate_acks_count = 0

        self.logger = get_logger("[4254send] SocketReader")

    def __handle_duplicate_ack(self):
        # At this point, we know that we're received an ack for a packet number
        # equal to the hcap.

        self.duplicate_acks_count += 1

        if self.duplicate_acks_count == DUPLICATES_FOR_RETRANSMIT:
            self.logger.debug("Received triple ack for packet %s", self.hcap)
            packet_to_resend = None
            pn_to_resend = self.hcap + 1
            packet_to_resend = self.all_packets[pn_to_resend]

            self.packets_to_send.put((pn_to_resend, packet_to_resend), block=True)
            self.logger.debug("Put packet %s back into the send queue.", pn_to_resend)

            self.duplicate_acks_count = 0

    def __accept_acknowledgement(self, apn: int):
        if apn < self.hcap:
            # We've already received an ack higher than this, so we
            # don't need to do anything.
            return

        if apn == self.hcap:
            self.logger.debug("Ack for packet %s was duplicate.", apn)
            self.__handle_duplicate_ack()

        if apn > self.hcap:
            with self.outstanding_packets_lock:
                # Keep popping packets from outstanding packets until we get
                # to apn.
                for pn_to_pop in range(self.hcap, apn + 1):
                    if pn_to_pop in self.outstanding_packets:
                        (packet, _) = self.outstanding_packets.pop(pn_to_pop)
                        self.all_packets[pn_to_pop] = packet

            self.hcap = apn

    def run(self):
        """
        Read acks from the socket, removing packets from outstanding_packets
        when acked, re-transmitting on duplicate acks and quitting on an EOF
        ack.
        """

        self.logger.info("Starting to read acks from socket.")

        while True:
            try:
                # It's possible that the EOF ack gets dropped, and we don't want
                # this thread to block forever if that happens. So the timeout
                # thread can signal to this thread to shut down.
                message = self.timeout_messagebox.get_nowait()

                if message and message[QUIT]:
                    self.logger.info(
                        "Received QUIT message from timeout thread; shutting down."
                    )
                    self.packets_to_send.put((0, {QUIT: True}), block=True)
                    return
            except Empty:
                pass

            received_data = self.sock.recvfrom(self.message_size)

            if not received_data:
                self.logger.info("Socket timed out; quitting.")
                break

            (received_packet, _) = received_data
            received_packet = received_packet.decode()
            decoded_packet = json.loads(received_packet)

            if not verify_checksum(decoded_packet):
                # Received a corrupted ack.
                continue

            # Acknowledged Packet Number
            #
            # See note on self.hcap above.
            apn = decoded_packet[ACKNOWLEDGED]

            self.logger.debug("Received ack for %s.", apn)

            if apn == END_OF_FILE:
                self.logger.info("EOF ack received, quitting.")
                self.packets_to_send.put((0, {QUIT: True}), block=True)
                self.timeout_messagebox.put({QUIT: True}, block=True)
                return

            apn = int(apn)
            self.__accept_acknowledgement(apn)
