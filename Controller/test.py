import socket
import struct
import time

UDP_IP = "192.168.43.42"
UDP_PORT = 2390

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_thrust(roll, pitch, yaw, thrust):
    header = 0x30
    packet = bytearray([header])
    packet.extend(struct.pack('<fffH', roll, pitch, yaw, thrust))
    checksum = sum(packet) & 0xFF
    packet.append(checksum)
    sock.sendto(packet, (UDP_IP, UDP_PORT))

# Test individual motor control with roll/pitch/yaw
print("Testing motors individually...")

# Spin each motor by tilting (reversed for correct rotation)
tests = [
    (0, 0, 0, 25000),      # All motors equal
    (-5, 0, 0, 25000),     # More power to one side (roll)
    (5, 0, 0, 25000),      # Opposite side
    (0, -5, 0, 25000),     # Front/back (pitch)
    (0, 5, 0, 25000),      # Opposite
    (0, 0, -5, 25000),     # Yaw rotation
]
send_thrust(0,0,0,25000)


