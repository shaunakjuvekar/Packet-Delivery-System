import heapq
import time
from queue import PriorityQueue, Queue
from threading import RLock
from typing import Dict, Tuple

from src.constants import QUIT, SEQUENCE_NUMBER
from src.logging import get_logger

TIMEOUT = 0.6  # seconds


class Timeouts:
    """
    Class to bind together state and behaviour for the thread that handles
    timimg out packets.
    """

    def __init__(
        self,
        packets_to_send: "PriorityQueue[Tuple[int, Dict]]",
        outstanding_packets: Dict[int, Tuple[Dict, float]],
        outstanding_packets_lock: RLock,
        timeout_messagebox: Queue,
    ):
        self.packets_to_send = packets_to_send
        self.outstanding_packets = outstanding_packets
        self.outstanding_packets_lock = outstanding_packets_lock
        self.timeout_messagebox = timeout_messagebox

        self.logger = get_logger("[4254send] Timeouts")
        self.ticks_without_packets = 0

    def run(self):
        self.logger.info("Starting timeout thread.")
        while True:
            try:
                message = self.timeout_messagebox.get_nowait()

                if message and message[QUIT]:
                    self.logger.info(
                        "Timer thread received QUIT message; shutting down."
                    )
                    return
            except:
                pass

            resend_these_packets = []

            with self.outstanding_packets_lock:
                if len(self.outstanding_packets) == 0:
                    # We don't want to spend too long waiting for the EOF acks
                    # so if we have no packets in flight and aren't waiting for
                    # any acks, why not just quit?
                    # The only reason we're counting ticks is to ensure we don't
                    # quit too early, i.e. before any packets have been sent.
                    self.ticks_without_packets += 1
                    if self.ticks_without_packets == 3:
                        self.logger.info(
                            "Spent 5 ticks with no outstanding packets, quitting."
                        )
                        self.timeout_messagebox.put({QUIT: True})
                        return
                else:
                    self.ticks_without_packets = 0

                pns_to_pop = []
                current_time = time.monotonic()

                for (pn, (packet, sent_time)) in self.outstanding_packets.items():
                    if current_time - sent_time >= TIMEOUT:
                        self.logger.debug("Packet %s timed out!", pn)
                        resend_these_packets.append(packet)
                        pns_to_pop.append(pn)

                for pn in pns_to_pop:
                    self.outstanding_packets.pop(pn)

            for packet in resend_these_packets:
                self.packets_to_send.put((packet[SEQUENCE_NUMBER], packet), block=True)

            time.sleep(0.2)
