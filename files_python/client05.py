import socket
import cv2
import pickle
import struct
import time
import subprocess
from datetime import datetime, timezone

# Server connection information
#SERVER_IP = "172.16.4.156"
SERVER_IP = "172.16.204.14"

SERVER_PORT = 9999
BATCH_SIZE = 25  # Number of frames in each batch

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))

# Change the path to the video file
video_file_path = 'dataset/record.avi'  # Adjust this path
cap = cv2.VideoCapture(video_file_path)

# Thread 1: Read batch frames from video file and save to file
def capture_video_batch(video_counter):
    fps = 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    video_path = f'data/batch_video_{video_counter}.avi'
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    for _ in range(BATCH_SIZE):
        ret, frame = cap.read()
        if not ret:
            out.release()
            return None  # Return None if no more frames
        out.write(frame)

    out.release()
    return video_path

# Thread 2: Encode and send data for odd-numbered batches
def encode_and_send(video_path):
    if video_path is None:
        return  # Stop if no video

    ffmpeg_command = [
        'ffmpeg',
        '-i', video_path,
        '-f', 'h264',
        '-codec:v', 'libx264',
        '-preset', 'ultrafast',
        '-movflags', 'faststart',
        '-an',
        'pipe:1'
    ]
    ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE)

    while True:
        frame_data = ffmpeg_process.stdout.read(1024)
        if not frame_data:
            break

        start_time = time.time()
        packet = pickle.dumps((start_time, frame_data), 0)
        message_size = struct.pack("Q", len(packet))
        client_socket.sendall(message_size + packet)

    ffmpeg_process.stdout.close()

# Main thread: Continuously read and send batches
def main():
    video_counter = 0
    while True:
        video_path = capture_video_batch(video_counter)
        
        # Only send odd-numbered batches
        if video_counter % 2 != 0:
            encode_and_send(video_path)

        if video_path is None:
            break  # Stop loop if no more video

        video_counter += 1

    client_socket.close()
    cap.release()

if __name__ == "__main__":
    main()
