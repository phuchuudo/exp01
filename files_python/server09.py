import socket
import struct
import cv2
import numpy as np
from datetime import datetime, timezone
import subprocess
import threading
import csv
import time

HOST = '0.0.0.0'
PORT = 9999

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

rtsp_url = "rtsp://localhost:8554/mystream"
ffmpeg_process = subprocess.Popen([ 
    'ffmpeg', '-re', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1280x720', '-r', '25', 
    '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'fast', '-f', 'rtsp', rtsp_url 
], stdin=subprocess.PIPE)

# Tạo file CSV và ghi header
csv_file = open('frame_data.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Frame', 'Start Time', 'End Time', 'Type', 'Delay (ms)'])

def send_frame_to_rtsp(frame):
    try:
        ffmpeg_process.stdin.write(frame.tobytes())
    except Exception as e:
        print(f"Error sending frame to FFmpeg: {e}")

def calculate_delay(server_timestamp_str, client_timestamp_str):
    try:
        server_timestamp = datetime.strptime(server_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        client_timestamp = datetime.strptime(client_timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        delay = (server_timestamp - client_timestamp).total_seconds() * 1000
        return delay
    except Exception as e:
        print(f"Error calculating delay: {e}")
        return 0

def generate_fake_frame():
    return np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)

def handle_client(client_socket):
    data = b""
    payload_size = struct.calcsize("Q")
    frame_count = 0
    batch_size = 25
    last_received_time = time.time()  # Thời gian nhận dữ liệu cuối cùng

    while True:
        # Kiểm tra xem đã qua 15 giây chưa
        if time.time() - last_received_time > 15:
            print("No data received from client for 15 seconds. Closing connection.")
            break  # Đóng kết nối nếu không nhận dữ liệu trong 15 giây

        # Nhận dữ liệu frame từ client
        for _ in range(batch_size):
            frame_count += 1
            while len(data) < payload_size:
                data += client_socket.recv(4096)
            packed_frame_size = data[:payload_size]
            data = data[payload_size:]
            frame_size = struct.unpack("Q", packed_frame_size)[0]

            while len(data) < payload_size:
                data += client_socket.recv(4096)
            packed_timestamp_size = data[:payload_size]
            data = data[payload_size:]
            timestamp_size = struct.unpack("Q", packed_timestamp_size)[0]

            while len(data) < timestamp_size:
                data += client_socket.recv(4096)
            timestamp_data = data[:timestamp_size]
            data = data[timestamp_size:]
            timestamp_str = timestamp_data.decode('utf-8')

            while len(data) < frame_size:
                data += client_socket.recv(4096)
            frame_data = data[:frame_size]
            data = data[frame_size:]

            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)

            server_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
            delay = calculate_delay(server_timestamp, timestamp_str)
            delay_text = f"Delay: {delay:.2f} ms"
            print(f'delay time from client: {delay} ms')
            cv2.putText(frame, delay_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f'Server UTC: {server_timestamp}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, f'Client UTC: {timestamp_str}', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (250, 0, 0), 2)
            cv2.putText(frame, f'Frame {frame_count}', (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

            # Ghi dữ liệu vào CSV
            csv_writer.writerow([frame_count, timestamp_str, server_timestamp, 'Client', delay])

            cv2.imshow("Received Video", frame)
            threading.Thread(target=send_frame_to_rtsp, args=(frame,)).start()

            # Cập nhật thời gian nhận dữ liệu cuối cùng
            last_received_time = time.time()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Sinh 25 frame giả
        t1 = time.time()
        for i in range(batch_size):
            frame_count += 1
            start_time_gen = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
            generated_frame = generate_fake_frame()
            end_time_gen = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
            delay_gen = calculate_delay(end_time_gen, start_time_gen)
            delay_text_gen = f"Delay: {delay_gen:.2f} ms"
            print(f'delay time from (generated): {delay_gen} ms')

            cv2.putText(generated_frame, delay_text_gen, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(generated_frame, "Generated from server", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(generated_frame, f'Frame {frame_count}', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(generated_frame, f'Start time gen: {start_time_gen}', (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(generated_frame, f'End time gen: {end_time_gen}', (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (250, 0, 0), 2)

            # Ghi dữ liệu vào CSV cho frame giả
            csv_writer.writerow([frame_count, start_time_gen, end_time_gen, 'Generated', delay_gen])

            cv2.imshow("Received Video", generated_frame)
            threading.Thread(target=send_frame_to_rtsp, args=(generated_frame,)).start()

            # Cập nhật thời gian nhận dữ liệu cuối cùng
            last_received_time = time.time()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        t2 = time.time()
        print(f'sum time for gen (25 frame): {t2 - t1} seconds')
        # Gửi tín hiệu đến client để tiếp tục gửi
        client_socket.sendall(b"CONTINUE")

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
    csv_file.close()  # Đóng file CSV sau khi hoàn thành
