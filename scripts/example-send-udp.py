import socket
import signal
import sys
import struct

def send_udp_values():
    udp_ip = "127.0.0.1"
    udp_port = 48291
    values = [568471.0, 5.0, 50.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # List of 10 floats

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Pack the values as doubles
    message = struct.pack('d' * len(values), *values)
    sock.sendto(message, (udp_ip, udp_port))
    print(f"Sent: {values}")

    sock.close()

if __name__ == "__main__":

    def signal_handler(sig, frame):
        print('Exiting...')
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        send_udp_values()