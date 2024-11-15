import socket
import struct
import cv2
import numpy as np
from datetime import datetime, timezone
import subprocess
import threading
import csv
import time
import torch

from utils.util import *
from model.model import Model
import os
import warnings
warnings.filterwarnings("ignore")


# Server setup
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

# Create CSV file and write header
csv_file = open('frame_data.csv', 'w', newline='')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Frame', 'Start Time', 'End Time', 'Type', 'Delay (ms)'])

# Load pre-trained AI model
device = torch.device("cuda")
model = Model(load_path='pretrained_models/dmvfn_kitti.pkl', training=False)

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

def predict_frame(prev_frame, curr_frame, model):
    # Function to predict the next frame based on the previous two frames
    with torch.no_grad():
        # Assume prev_frame and curr_frame are NumPy arrays (no need to use cv2.imread)
        img_0 = prev_frame.transpose(2, 0, 1).astype('float32')
        img_1 = curr_frame.transpose(2, 0, 1).astype('float32')

        img = torch.cat([torch.tensor(img_0), torch.tensor(img_1)], dim=0)
        img = img.unsqueeze(0).unsqueeze(0).to(device) / 255.0

        pred = model.eval(img, 'single_test')
        pred_frame = np.array(pred.cpu().squeeze() * 255).transpose(1, 2, 0)
        return pred_frame


def handle_client(client_socket):
    data = b""
    payload_size = struct.calcsize("Q")
    frame_count = 0
    batch_size = 2
    last_received_time = time.time()  # Last data received time

    frame_buffer = []  # Store received frames for prediction

    while True:
        # Check if 15 seconds have passed
        if time.time() - last_received_time > 15:
            print("No data received from client for 15 seconds. Closing connection.")
            break  # Close the connection if no data is received for 15 seconds

        # Receive frame data from client
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

            # Write data to CSV
            csv_writer.writerow([frame_count, timestamp_str, server_timestamp, 'Client', delay])

            threading.Thread(target=send_frame_to_rtsp, args=(frame,)).start()

            # Store the frame in buffer
            frame_buffer.append(frame)

            # Update last received data time
            last_received_time = time.time()

        # Generate 25 frames from the received buffer
        if len(frame_buffer) >= 2:
            for i in range(batch_size):
                # Predict the next frame from the last two frames
                start_time_gen = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                pred_frame = predict_frame(frame_buffer[-2], frame_buffer[-1], model)
                # pred_frame = generate_fake_frame()
                frame_count += 1
                end_time_gen = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
                delay_gen = calculate_delay(end_time_gen, start_time_gen)
                delay_text_gen = f"Delay: {delay_gen:.2f} ms"
                print(f'delay time from (generated): {delay_gen} ms')

                # Write predicted frame data to CSV
                csv_writer.writerow([frame_count, start_time_gen, end_time_gen, 'Predicted', delay_gen])

                threading.Thread(target=send_frame_to_rtsp, args=(pred_frame,)).start()
                # Add predicted frame to buffer
                frame_buffer.append(pred_frame)

    client_socket.close()

while True:
    print('start server!')
    client_socket, addr = server_socket.accept()
    print(f"Connection from {addr}")
    client_thread = threading.Thread(target=handle_client, args=(client_socket,))
    client_thread.start()
