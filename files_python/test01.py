import cv2
import subprocess

# Thiết lập nguồn video (0 là webcam)
#video_source = "output_video.avi"
video_source = 0
cap = cv2.VideoCapture(video_source)

# Kiểm tra nếu mở được video source
if not cap.isOpened():
    print("Không thể mở video source")
    exit()

# Cấu hình ffmpeg để stream tới mediamtx server
ffmpeg_cmd = (
    f"ffmpeg -re -f rawvideo -pix_fmt bgr24 -s {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
    f"-i - -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://localhost:8554/mystream"
)

# Khởi chạy ffmpeg
ffmpeg_process = subprocess.Popen(ffmpeg_cmd, shell=True, stdin=subprocess.PIPE)

try:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Gửi frame tới ffmpeg để stream qua RTSP
        ffmpeg_process.stdin.write(frame.tobytes())

finally:
    # Đóng camera và ffmpeg khi kết thúc
    cap.release()
    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()