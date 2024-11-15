import socket
import struct
import cv2
import numpy as np
import time
import subprocess
import threading
from datetime import datetime, timezone

HOST = '0.0.0.0'
PORT = 9999
BUFFER_SIZE = 65535
byte_start = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10'
byte_end = b'\x10\x09\x08\x07\x06\x05\x04\x03\x02\x01'

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((HOST, PORT))
server_socket.settimeout(1)

frames_dict = {}
max_key = 0
current_frame_id = -1
last_received_time = time.time()

# Khởi tạo ffmpeg để phát RTSP stream
rtsp_url = "rtsp://localhost:8554/mystream"  # Đây là RTSP stream URL bạn muốn phát
ffmpeg_process = subprocess.Popen([
    'ffmpeg', '-re', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1280x720', '-r', '25',
    '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-f', 'rtsp', rtsp_url
], stdin=subprocess.PIPE)

def calculate_time_difference(time1, time2):
    try:
        time_format = "%H:%M:%S.%f"
        t1 = datetime.strptime(time1, time_format)
        t2 = datetime.strptime(time2, time_format)
        time_diff = t2 - t1
        return time_diff.total_seconds() * 1000  # Chuyển từ giây sang mili giây
    except ValueError:
        return None

def send_frame_to_rtsp(frame):
    """Luồng để gửi frame video đến FFmpeg (RTSP stream)"""
    ret, jpeg_frame = cv2.imencode('.jpg', frame)
    if ret:
        try:
            print('start write!')
            ffmpeg_process.stdin.write(jpeg_frame.tobytes())
        except Exception as e:
            print(f"Error sending frame to FFmpeg: {e}")
    else:
        print("Failed to encode frame")

def start_ffmpeg():
    return subprocess.Popen([
        'ffmpeg',                   # Chạy ffmpeg
        '-re',                       # Điều chỉnh tốc độ khung hình video với tốc độ thực
        '-f', 'rawvideo',            # Chỉ định định dạng đầu vào là video thô
        '-pix_fmt', 'bgr24',         # Định dạng pixel màu (bgr24 cho video màu)
        '-s', '1280x720',            # Đặt kích thước video (HD)
        '-r', '25',                  # Đặt tỷ lệ khung hình (fps)
        '-i', '-',                   # Đọc video từ stdin
        '-an',                       # Tắt âm thanh
        '-c:v', 'libx264',           # Mã hóa video bằng codec x264
        '-preset', 'fast',           # Chọn cài đặt mã hóa nhanh
        '-f', 'rtsp',                # Định dạng đầu ra là RTSP
        "rtsp://localhost:8554/mystream"  # Địa chỉ RTSP nơi video sẽ được phát
    ], stdin=subprocess.PIPE)


def handle_client():
    global frames_dict, current_frame_id, max_key
    # Khởi tạo giá trị ban đầu cho last_received_time

    if 'last_received_time' not in locals():
        last_received_time = time.time()


    while True:
        try:
            packet, client_address = server_socket.recvfrom(BUFFER_SIZE)
            last_received_time = time.time()

            # Kiểm tra xem gói tin có phải timestamp không
            try:
                client_timestamp = packet.decode()
                server_timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]
                ack_message = f"ACK,{server_timestamp}"
                server_socket.sendto(ack_message.encode(), client_address)
                latency_time = calculate_time_difference(client_timestamp, server_timestamp)
                if latency_time is not None:
                    print(f"Received frame timestamp from client: {client_timestamp}, server timestamp: {server_timestamp}, latency: {latency_time} ms")
                continue
            except UnicodeDecodeError:
                pass  # Tiếp tục xử lý như là dữ liệu hình ảnh

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

                full_frame_data = b''.join(frames_dict[i] for i in range(max_key + 1))

                np_data = np.frombuffer(full_frame_data, np.uint8)
                frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

                if frame is not None:
                    '''
                    cv2.imshow('Received Video', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    '''
                    # Đẩy video vào luồng gửi RTSP
                    threading.Thread(target=send_frame_to_rtsp, args=(frame,)).start()

                frames_dict.clear()
                max_key = 0

                server_timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S.%f')[:-3]
                ack_message = f"ACK,{server_timestamp}"
                server_socket.sendto(ack_message.encode(), client_address)
            else:
                frames_dict[part_number] = data

        except socket.timeout:
            current_time = time.time()
            if current_time - last_received_time > 15:
                print("No data received for more than 15 seconds. Closing server...")
                break

# Chạy thread xử lý dữ liệu từ client
client_thread = threading.Thread(target=handle_client)
client_thread.start()

# Chờ đến khi luồng xử lý xong
client_thread.join()

server_socket.close()
ffmpeg_process.stdin.close()
ffmpeg_process.wait()
