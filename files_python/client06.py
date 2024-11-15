import socket
import struct
import cv2
import time
import datetime

SERVER_IP = '127.0.0.1'
PORT = 9999  # Cập nhật port thành 9999
BUFFER_SIZE = 65535
partition_size = 1000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(2)

cap = cv2.VideoCapture(0)
byte_start = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10'
byte_end = b'\x10\x09\x08\x07\x06\x05\x04\x03\x02\x01'

frame_id = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Mã hóa frame thành định dạng JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    frame_data = buffer.tobytes()
    payload = byte_start + frame_data + byte_end

    # Lấy timestamp ở client trước khi gửi
    client_timestamp = datetime.datetime.utcnow().isoformat()

    partition_num = 0
    window_start = 0
    window_end = partition_size

    # Chia payload thành các phần nhỏ và gửi từng phần
    while window_end < len(payload):
        part_number = struct.pack('I', partition_num)
        frame_number = struct.pack('I', frame_id)
        part_payload = part_number + frame_number + payload[window_start:window_end]
        client_socket.sendto(part_payload, (SERVER_IP, PORT))

        window_start = window_end
        window_end += partition_size
        partition_num += 1
        time.sleep(0.001)

    # Gửi phần còn lại nếu có
    if window_start < len(payload):
        part_number = struct.pack('I', partition_num)
        frame_number = struct.pack('I', frame_id)
        part_payload = part_number + frame_number + payload[window_start:]
        client_socket.sendto(part_payload, (SERVER_IP, PORT))

    # Gửi timestamp đến server
    client_socket.sendto(client_timestamp.encode(), (SERVER_IP, PORT))

    # Đợi xác nhận từ server
    try:
        ack, _ = client_socket.recvfrom(1024)
        server_timestamp = ack.decode().split(",")[1]
        print(f"Frame {frame_id} sent and acknowledged with server timestamp: {server_timestamp}")
    except socket.timeout:
        print("Server did not respond, retrying...")

    frame_id += 1
    time.sleep(0.03)

print("Video transmission completed.")
cap.release()
client_socket.close()
