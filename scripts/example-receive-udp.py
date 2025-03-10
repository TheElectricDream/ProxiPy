import socket

UDP_IP = "0.0.0.0"
UDP_PORT = 53673

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for UDP packets on port {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
    print(f"Received message: {data} from {addr}")