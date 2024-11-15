import socket
import cv2
import struct
import time
from datetime import datetime, timezone

SERVER_IP = "localhost"
PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, PORT))

fps = 25
width = 1280
height = 720
#cap = cv2.VideoCapture(0)
cap = cv2.VideoCapture("output_video.avi")
cap.set(cv2.CAP_PROP_FPS, fps)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

frame_count = 0
batch_size = 25  # Số frame mỗi batch gửi đi

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Lấy timestamp UTC
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')

        # Mã hóa frame thành MJPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_data = buffer.tobytes()

        # Đóng gói timestamp và frame
        timestamp_encoded = timestamp.encode('utf-8')
        frame_length = struct.pack("Q", len(frame_data))
        timestamp_length = struct.pack("Q", len(timestamp_encoded))

        # Kiểm tra và gửi các frame trong các khối từ 1-25, 51-75, 101-125,...
        if (frame_count - 1) // batch_size % 2 == 0:
            client_socket.sendall(frame_length + timestamp_length + timestamp_encoded + frame_data)
            print(f"Sent frame {frame_count}")

        # Điều chỉnh thời gian gửi để khớp với FPS
        time.sleep(1 / fps)

except Exception as e:
    print(f"Error: {e}")

finally:
    cap.release()
    client_socket.close()
