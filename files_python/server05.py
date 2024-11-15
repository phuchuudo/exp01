import socket
import pickle
import struct
import time
import csv
import numpy as np
import cv2
import torch
from utils.util import *
from model.model import Model
import warnings
warnings.filterwarnings("ignore")

# Server setup
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 9999))
server_socket.listen(5)
print("Server is listening...")

client_socket, addr = server_socket.accept()
print(f"Connection from {addr}")

data = b""
payload_size = struct.calcsize("Q")

frame_buffer = []  # Stores frames for inference
BATCH_SIZE = 25

# Initialize model for inference
device = torch.device("cuda")
model = Model(load_path='pretrained_models/dmvfn_kitti.pkl', training=False)

def predict_frame(prev_frame, curr_frame, model):
    with torch.no_grad():
        print(prev_frame)
        print(cv2.imread(prev_frame))
        img_0 = cv2.imread(prev_frame).transpose(2, 0, 1).astype('float32')
        img_1 = cv2.imread(curr_frame).transpose(2, 0, 1).astype('float32')
        img = torch.cat([torch.tensor(img_0), torch.tensor(img_1)], dim=0)
        img = img.unsqueeze(0).unsqueeze(0).to(device) / 255.0

        pred = model.eval(img, 'single_test')
        pred_frame = np.array(pred.cpu().squeeze() * 255).transpose(1, 2, 0)
        return pred_frame

with open('latency_data_h264.csv', mode='w', newline='') as csvfile:
    latency_writer = csv.writer(csvfile)
    latency_writer.writerow(['Packet Number', 'Latency (seconds)', 'Average Latency (seconds)'])

    frame_number = 0
    total_latency = 0.0

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
        msg_size = struct.unpack("Q", packed_msg_size)[0]

        while len(data) < msg_size:
            packet = client_socket.recv(4096)
            if not packet:
                break
            data += packet

        if len(data) < msg_size:
            break

        packet_data = data[:msg_size]
        data = data[msg_size:]

        # Unpack the start time and encoded frame data
        start_time, frame_encoded = pickle.loads(packet_data)
        end_time = time.time()

        frame_path = f"received_frames/frame_{frame_number}.jpg"
        with open(frame_path, "wb") as f:
            f.write(frame_encoded)

        frame_buffer.append(frame_path)

        # Predict frames for even-numbered batches
        if frame_number % (2 * BATCH_SIZE) >= BATCH_SIZE and len(frame_buffer) >= 2:
            pred_frame = predict_frame(frame_buffer[-2], frame_buffer[-1], model)
            pred_path = f"predicted_frames/pred_frame_{frame_number}.jpg"
            cv2.imwrite(pred_path, pred_frame)

        # Calculate latency
        latency = end_time - start_time
        total_latency += latency
        average_latency = total_latency / (frame_number + 1)
        latency_writer.writerow([frame_number, latency, average_latency])
        frame_number += 1

client_socket.close()
server_socket.close()
