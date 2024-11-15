import socket
import struct
import cv2
import numpy as np
from datetime import datetime, timezone
import subprocess
import threading

HOST = '0.0.0.0'
PORT = 9999

# Thiết lập TCP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

# Khởi tạo RTSP stream với ffmpeg
rtsp_url = "rtsp://localhost:8554/mystream"
ffmpeg_process = subprocess.Popen([
    'ffmpeg', '-re', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1280x720', '-r', '25',
    '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-f', 'rtsp', rtsp_url
], stdin=subprocess.PIPE)

def send_frame_to_rtsp(frame):
    """Gửi frame đến FFmpeg RTSP stream"""
    try:
        ffmpeg_process.stdin.write(frame.tobytes())
    except Exception as e:
        print(f"Error sending frame to FFmpeg: {e}")

def calculate_delay(server_timestamp_str, client_timestamp_str):
    """Tính toán độ trễ giữa server_timestamp và client_timestamp"""
    try:
        server_timestamp = datetime.strptime(server_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        client_timestamp = datetime.strptime(client_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        delay = (server_timestamp - client_timestamp).total_seconds() * 1000  # Độ trễ tính bằng miligiây
        return delay
    except Exception as e:
        print(f"Error calculating delay: {e}")
        return 0  # Trả về 0 khi có lỗi

def handle_client(client_socket):
    data = b""
    payload_size = struct.calcsize("Q")

    while True:
        # Đọc kích thước của frame
        while len(data) < payload_size:
            data += client_socket.recv(4096)
        packed_frame_size = data[:payload_size]
        data = data[payload_size:]
        frame_size = struct.unpack("Q", packed_frame_size)[0]

        # Đọc kích thước của timestamp
        while len(data) < payload_size:
            data += client_socket.recv(4096)
        packed_timestamp_size = data[:payload_size]
        data = data[payload_size:]
        timestamp_size = struct.unpack("Q", packed_timestamp_size)[0]

        # Đọc dữ liệu của timestamp
        while len(data) < timestamp_size:
            data += client_socket.recv(4096)
        timestamp_data = data[:timestamp_size]
        data = data[timestamp_size:]

        # Giải mã timestamp từ byte array
        timestamp_str = timestamp_data.decode('utf-8')

        # Đọc dữ liệu của frame dựa vào kích thước đã nhận
        while len(data) < frame_size:
            data += client_socket.recv(4096)
        frame_data = data[:frame_size]
        data = data[frame_size:]

        # Giải mã frame MJPEG thành BGR
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)

        # Lấy timestamp server (thời gian hiện tại của server)
        server_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
        #server_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')

        # Tính độ trễ
        delay = calculate_delay(server_timestamp, timestamp_str)

        # In độ trễ lên frame
        delay_text = f"Delay: {delay:.2f} ms"
        cv2.putText(frame, delay_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'Server UTC: {server_timestamp}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, f'Client UTC: {timestamp_str}', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (250, 0, 0), 2)

        # Hiển thị frame với OpenCV
        cv2.imshow("Received Video", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Gửi frame đến RTSP
        threading.Thread(target=send_frame_to_rtsp, args=(frame,)).start()

try:
    print("Server is listening...")
    client_socket, addr = server_socket.accept()
    print(f"Connection from {addr}")
    handle_client(client_socket)

finally:
    server_socket.close()
    cv2.destroyAllWindows()
    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()
