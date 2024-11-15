import socket
import pickle
import struct
import time
import csv
import subprocess
import numpy as np
import cv2

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 9999))
server_socket.listen(5)
print("Server is listening...")

client_socket, addr = server_socket.accept()
print(f"Connection from {addr}")

data = b"" 
payload_size = struct.calcsize("L")
print(payload_size)

with open('latency_data_h264.csv', mode='w', newline='') as csvfile:
    latency_writer = csv.writer(csvfile)
    latency_writer.writerow(['Packet Number', 'Latency (seconds)', 'Average Latency (seconds)'])

    frame_number = 0
    total_latency = 0.0

    with open('received_video.h264', 'wb') as video_file:
        while True:
            while len(data) < payload_size:
                packet = client_socket.recv(4096)
                if not packet:
                    break
                data += packet

            if len(data) < payload_size:
                break

            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("L", packed_msg_size)[0]
            print(msg_size)

            while len(data) < msg_size:
                packet = client_socket.recv(4096)
                if not packet:
                    break
                data += packet

            if len(data) < msg_size:
                break

            end_time = time.time()
            packet_data = data[:msg_size]
            data = data[msg_size:]

            start_time, frame_encoded = pickle.loads(packet_data)

            video_file.write(frame_encoded)

            latency = end_time - start_time
            print(f"Packet {frame_number} - Latency: {latency:.4f} seconds")

            total_latency += latency
            average_latency = total_latency / (frame_number + 1)

            latency_writer.writerow([frame_number, latency, average_latency])

            frame_number += 1

client_socket.close()
server_socket.close()

# Decode and display video
video_path = 'received_video.h264'
ffmpeg_command = [
    'ffmpeg',
    '-i', video_path,
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-'
]

ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)

width, height = 1280, 720
frame_size = width * height * 3

while True:
    frame_data = ffmpeg_process.stdout.read(frame_size)
    if not frame_data:
        break

    frame = np.frombuffer(frame_data, np.uint8).reshape((height, width, 3))
    cv2.imshow('Video - h264', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

ffmpeg_process.stdout.close()
ffmpeg_process.wait()
cv2.destroyAllWindows()
