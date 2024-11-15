import socket
import cv2
import struct
import time
from datetime import datetime, timezone

#SERVER_IP = '192.168.118.128'
SERVER_IP = "localhost"
PORT = 9999

# Thiết lập TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, PORT))

# Thiết lập camera
fps = 25
width = 1280
height = 720
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FPS, fps)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Lấy timestamp UTC
        #timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')

        # Mã hóa frame thành MJPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_data = buffer.tobytes()

        # Đóng gói timestamp thành byte và tính độ dài
        timestamp_encoded = timestamp.encode('utf-8')  # Encoding UTC timestamp
        frame_length = struct.pack("Q", len(frame_data))
        timestamp_length = struct.pack("Q", len(timestamp_encoded))

        # Gửi độ dài timestamp và frame, sau đó là timestamp và dữ liệu frame
        client_socket.sendall(frame_length + timestamp_length + timestamp_encoded + frame_data)

        # Điều chỉnh thời gian gửi để khớp với FPS mong muốn
        time.sleep(1 / fps)

except Exception as e:
    print(f"Error: {e}")

finally:
    cap.release()
    client_socket.close()
