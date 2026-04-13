import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Force the socket to allow immediate rebinding after a crash
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Request a massive 8MB buffer from the Linux VM kernel
sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
sock.bind(('0.0.0.0', 8765))
print("Listening for raw UDP...")
while True:
    data, addr = sock.recvfrom(1024)
    print(f"🔥 RECEIVED {len(data)} bytes from {addr}")