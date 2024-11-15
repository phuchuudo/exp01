import socket
import struct
import cv2
import numpy as np
import datetime

HOST = '0.0.0.0'
PORT = 9999  # Cập nhật port thành 9999
BUFFER_SIZE = 65535
byte_start = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10'
byte_end = b'\x10\x09\x08\x07\x06\x05\x04\x03\x02\x01'

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((HOST, PORT))
print("Server is listening...")

frames_dict = {}
max_key = 0
current_frame_id = -1

while True:
    packet, client_address = server_socket.recvfrom(BUFFER_SIZE)

    # Kiểm tra xem gói tin có phải timestamp không
    try:
        client_timestamp = packet.decode()  # Nếu đây là timestamp, sẽ decode được
        server_timestamp = datetime.datetime.utcnow().isoformat()
        ack_message = f"ACK,{server_timestamp}"
        server_socket.sendto(ack_message.encode(), client_address)
        print(f"Received frame timestamp from client: {client_timestamp}, server timestamp: {server_timestamp}")
        continue
    except UnicodeDecodeError:
        pass  # Nếu không decode được, tiếp tục xử lý gói tin như dữ liệu hình ảnh

    # Phân tích dữ liệu từ packet
    part_number = struct.unpack('I', packet[:4])[0]
    frame_id = struct.unpack('I', packet[4:8])[0]
    data = packet[8:]

    if frame_id != current_frame_id:
        frames_dict.clear()
        max_key = 0
        current_frame_id = frame_id

    if data.startswith(byte_start):
        data = data[len(byte_start):]
    if data.endswith(byte_end):
        data = data[:-len(byte_end)]
        frames_dict[part_number] = data
        max_key = max(max_key, part_number)

        # Ghép lại toàn bộ frame khi đã nhận đủ
        full_frame_data = b''.join(frames_dict[i] for i in range(max_key + 1))

        np_data = np.frombuffer(full_frame_data, np.uint8)
        frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

        if frame is not None:
            cv2.imshow('Received Video', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        frames_dict.clear()
        max_key = 0

        # Gửi lại ACK với timestamp từ server
        server_timestamp = datetime.datetime.utcnow().isoformat()
        ack_message = f"ACK,{server_timestamp}"
        server_socket.sendto(ack_message.encode(), client_address)
    else:
        frames_dict[part_number] = data

server_socket.close()
cv2.destroyAllWindows()
