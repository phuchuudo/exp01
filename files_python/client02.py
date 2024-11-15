import socket
import cv2
import pickle
import struct
import time
import subprocess
from datetime import datetime, timezone

# Server connection information
SERVER_IP = 'localhost'
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

    print(f"{fps}, {width}, {height}")

    video_path = f'data/batch_video_{video_counter}.avi'
    out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

    print(f"Capturing batch video {video_counter}...")

    # Read and save batch frames from the video
    for _ in range(BATCH_SIZE):
        ret, frame = cap.read()
        if not ret:
            print("End of video. Stopping thread.")
            out.release()
            return None  # Return None if no more frames

        out.write(frame)

    out.release()
    print(f"Batch video {video_counter} completed.")
    return video_path

# Thread 2: Encode in H264 and send data
# In the encode_and_send function
def encode_and_send(video_path):
    if video_path is None:
        print("No video to send. Stopping thread.")
        return  # Stop thread if no video

    print(f"Starting to encode and send {video_path}...")

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

        # Get UTC-aware timestamp
        start_time = datetime.now(timezone.utc).timestamp()
        packet = pickle.dumps((start_time, frame_data), 0)
        message_size = struct.pack("L", len(packet))
        client_socket.sendall(message_size + packet)

    ffmpeg_process.stdout.close()
    print(f"Finished sending {video_path}.")

# Main thread: Continuously read and send batches
def main():
    global sum_time  # Declare sum_time as global to modify it here
    video_counter = 0
    while True:
        # Read a new batch video
        video_path = capture_video_batch(video_counter)
        
        # Encode and send the new batch video
        t1 = time.time()
        
        encode_and_send(video_path)
        
        t2 = time.time()
        sum_time += (t2 - t1)

        if video_path is None:
            break  # Stop loop if no more video

        video_counter += 1
        # Check for exit condition as needed or keep looping indefinitely
        #if cv2.waitKey(1) & 0xFF == ord('q'):
        #    break

    client_socket.close()
    cap.release()  # Release video capture resources

if __name__ == "__main__":
    sum_time = 0    
    main()
    print(f'sum = {sum_time} seconds')
