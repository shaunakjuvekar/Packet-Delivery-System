# Solution

## High-level approach

Our solution is in python. We reach correctness by:

- Having cumulative acks from the receiver
- Having a timeout of 1 second on the sender
- Retransmitting on receiving two duplicate acks from the receiver.

We handle out of order, duplicate and delayed delivery by storing packets in a min heap on the receiver, which is then popped in order to output data.

For more low-level details, our solution uses four threads in the sender, one for reading input, one for sending it out via the socket, one for receiving acks from the socket and one that runs a clock to handle timeouts. On the receiver, there is only one thread that simply blocks on the socket.

## Challenges

The main challenge we faced is performance. Our solution does not meet the performance requirements when there is significant loss, as in those caes we need timeouts to retransmit packets, and timeouts take time.

## Testing

We used `nettest` to test our solution, first by running `testall` to get a feel for where we might be lacking and then simulating similar conditions using `netsim`. We tested on a pretty wide variety of conditions and used `testall` as an index of what could be going wrong.
