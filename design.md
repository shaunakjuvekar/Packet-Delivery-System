# Solution

## Challenges

Our solution mitigates the following problems:

1. Duplicate packets
2. Out of order packets
3. Corrupted packets
4. Lost packets

All of these problems apply both ways - to the packets that were sent *and* the
acks that are received.

## Protocol

- Sliding Window based protocol that has at most `WND_SIZE` packets in flight at
  any time. The Sliding Window is not strictly necessary for CP2, so we haven't
  truly implemented it.
- Cumulative Acks: Upon receipt of a packet, the receiver acks the highest
  cumulative packet it has received so far.
- Fast retransmit: Sender re-transmits packet `n` if it has received an ack for
  packet `n - 1` three times.
- Sequence has nothing to do with size of the packet; corruption detection is
  delegated to a checksum in the headers.
- Packets timeout if no ack is received for duration `TIMEOUT`.

## Packet Structure

JSON with the following fields:

- sqn: The sequence number.
- cksum: Checksum. Computed as the CRC32 hash of the packet in JSON with the
  `cksum` field set to `null`.
- data: the actual contents of the packet.
- eof: whether this is the last packet or not.

## Sender Architecture

There are four threads:

1. The input reader thread;
2. The socket writer thread;
3. The socket reader thread;
4. The timeout thread.

These threads communicate only via three queues:

1. Packets to send `PKSEND`;
2. Outstanding packets `PKOUT_Q`;
3. Sending status `STAT`.

Along with these queues, there is one shared list of outstanding packets
`PKOUT_L` with a mutex lock to manage access to it.

### Input Reader

The input reader thread reads from STDIN, chunks the input and then converts
those chunks into packets. It puts those packets into the `PKSEND` queue. Once
it reaches EOF on STDIN, it puts a packet with the `eof` flag set to 1 into the
`PKSEND` queue and then exits.

### Socket Writer

The socket writer thread reads packets from the `PKSEND` queue and writes them
to a UDP socket. It then puts *something* into `PKOUT_Q` - what it puts in there
doesn't matter. Along with that, it puts the packet into `PKOUT_L`. If the
packet it picks from the `PKSEND` queue has a special flag `quit` set to true,
it exits instead.

### Socket Reader

The socket reader thread reads acks from the socket and then processes them. If
the ack is processed succesfully, it pops one entry from `PKOUT_Q` and removes
the corresponding packet from `PKOUT_L`. If it succesfully processes an ack for
the `eof` packet, it then puts a packet with `quit` set to true into `PKSEND`
and `STAT` before quitting.

### Timeout

The timeout thread is constantly running a loop which ticks every n
milliseconds. Every tick, it checks the packets in `PKOUT_L` to ensure they
haven't been sent more than `TIMEOUT`s before. If they have, it removes them
from `PKOUT_L`, pops an entry from `PKOUT_Q` and puts the packet back into
`PKSEND`.


## Receiver Process

- The Receiver is running on one big loop.
- It keeps track of:
  1. The highes contiguous sequence number it has received thus far `hcseq`, and
  2. Other packets it has received until that point `opr`.
- For every packet it receives, it computes the checksum and ensures the packet
  is valid.
- If valid, it compares the sequence number with `hcseq` and `opr`. If the
  sequence number is less than hcseq or in opr, it simply drops the packet as it
  is a duplicate.
- If the sequence number is greater than `hcseq` and not in `opr`, it accpets
  the packet and acks it.
- `hcseq` and `opr` are updated accordingly.
- Howewver, if it receives an `eof` packet, it does NOT ack it immediately.
  Instead, it notes that it has received an eof packet, and the sequence number
  of the eof packet `eofseq`. Until `hcseq` has reached `eofseq - 1`, it will
  not ack the `eof`.
- Once it has received all the packets, it acks `eof` and quits.
