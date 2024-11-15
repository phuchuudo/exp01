import socket
import pickle
import struct
import time
import csv
import subprocess
import numpy as np
import cv2
from datetime import datetime, timezone


# Server setup
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', 9999))
server_socket.listen(5)
print("Server is listening...")

client_socket, addr = server_socket.accept()
print(f"Connection from {addr}")

data = b"" 
payload_size = struct.calcsize("L")
print("Payload size:", payload_size)

# CSV to log latency data
with open('latency_data_h264.csv', mode='w', newline='') as csvfile:
    latency_writer = csv.writer(csvfile)
    latency_writer.writerow(['Packet Number', 'Latency (seconds)', 'Average Latency (seconds)'])

    frame_number = 0
    total_latency = 0.0

    # Write received video stream to .h264 file
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
            print("Message size:", msg_size)

            while len(data) < msg_size:
                packet = client_socket.recv(4096)
                if not packet:
                    break
                data += packet

            if len(data) < msg_size:
                break

            end_time = datetime.now(timezone.utc).timestamp()
            packet_data = data[:msg_size]
            data = data[msg_size:]

            # Unpack the start time and encoded frame data
            start_time, frame_encoded = pickle.loads(packet_data)
            video_file.write(frame_encoded)

            # Calculate latency
            latency = end_time - start_time
            print(f"Packet {frame_number} - Latency: {latency:.4f} seconds")

            total_latency += latency
            average_latency = total_latency / (frame_number + 1)
            latency_writer.writerow([frame_number, latency, average_latency])
            frame_number += 1

client_socket.close()
server_socket.close()

# Convert the received .h264 file to .avi using FFmpeg
video_path_h264 = 'received_video.h264'
output_avi_path = 'output_video.avi'
ffmpeg_command = [
    'ffmpeg',
    '-i', video_path_h264,
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    output_avi_path
]

# Run FFmpeg to convert and save as AVI format
subprocess.run(ffmpeg_command)
print(f"Video saved as {output_avi_path}")
