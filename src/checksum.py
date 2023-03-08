import json
import zlib
from typing import Dict

from src.constants import CHECKSUM


def compute_checksum(packet: Dict) -> int:
    """
    Computes a checksum for the packet and returns it.

    Note that this mutates the input packet, to set `cksum` to None.
    However, it does NOT set the cksum field to the computed value.
    """

    packet[CHECKSUM] = None
    return zlib.crc32(json.dumps(packet).encode())


def verify_checksum(packet: Dict) -> bool:
    """
    Checks the packet against the expected checksum and returns true if they
    match.

    Note that this mutates packet to set `cksum` to None.
    """

    try:
        actual_checksum = packet[CHECKSUM]
        packet[CHECKSUM] = None
        expected_checksum = zlib.crc32(json.dumps(packet).encode())
        return expected_checksum == actual_checksum
    except KeyError:
        # The packet has no checksum field, so it by default doesn't match.
        return False
