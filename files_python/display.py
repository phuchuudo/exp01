# display.py

import subprocess
import numpy as np
import cv2
import threading
import time

# Đường dẫn đến file video
video_file_path = 'received_video.h264'

# Hàm để giải mã và hiển thị video
def display_video(video_path):
    # Chạy FFmpeg để giải mã video
    ffmpeg_command = [
        'ffmpeg',
        '-i', video_path,
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-an',
        'pipe:1'
    ]

    ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    width, height = 1280, 720  # Kích thước khung hình
    frame_size = width * height * 3  # Kích thước mỗi frame (3 cho BGR)

    while True:
        frame_data = ffmpeg_process.stdout.read(frame_size)
        if not frame_data:
            print("No more frames to read. Waiting for new data...")
            time.sleep(1)  # Chờ một chút trước khi kiểm tra lại
            continue

        frame = np.frombuffer(frame_data, np.uint8).reshape((height, width, 3))
        cv2.imshow('Video - h264', frame)

        # Kiểm tra phím nhấn để dừng hiển thị
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Đóng các cửa sổ sau khi hoàn tất
    cv2.destroyAllWindows()

# Khởi tạo luồng cho việc hiển thị video
display_thread = threading.Thread(target=display_video, args=(video_file_path,))
display_thread.start()

# Tiếp tục thực hiện các tác vụ khác nếu cần
# ...

# Đợi luồng hiển thị video kết thúc trước khi kết thúc chương trình
display_thread.join()
