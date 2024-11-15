import cv2
import subprocess
import threading
import time

# Khởi tạo kết nối với camera
cap = cv2.VideoCapture(0)

# Kiểm tra xem camera có mở thành công không
if not cap.isOpened():
    print("Error: Unable to open camera.")
    exit()

# Định nghĩa các tham số video
fps = 25  # Số khung hình mỗi giây (FPS)
width = 640  # Chiều rộng video
height = 480  # Chiều cao video
rtsp_url = 'rtsp://localhost:8554/mystream'  # URL RTSP

# Cấu hình FFmpeg để stream video
ffmpeg_cmd = [
    'ffmpeg',
    '-y',  # Ghi đè nếu file tồn tại
    '-f', 'rawvideo',  # Định dạng video thô
    '-vcodec', 'rawvideo',  # Video codec
    '-pix_fmt', 'bgr24',  # Định dạng pixel (tương thích với OpenCV)
    '-s', f'{width}x{height}',  # Độ phân giải video
    '-r', str(fps),  # FPS
    '-i', '-',  # Đầu vào là dữ liệu từ stdin
    '-c:v', 'libx264',  # Codec video (H.264)
    '-preset', 'ultrafast',  # Thiết lập tốc độ mã hóa
    '-tune', 'zerolatency',  # Giảm độ trễ
    '-f', 'rtsp',  # Định dạng RTSP
    rtsp_url  # URL RTSP
]

# Thiết lập ffmpeg process để gửi video stream
ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

# Hàm đọc video từ camera
def read_camera():
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break
        # Gửi frame qua FFmpeg stdin
        ffmpeg_process.stdin.write(frame.tobytes())
        time.sleep(1 / fps)  # Điều chỉnh FPS

# Hàm hiển thị video
def show_video():
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame.")
            break
        cv2.imshow('Camera Feed', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Tạo hai luồng, một để đọc video và một để hiển thị video
read_thread = threading.Thread(target=read_camera)
show_thread = threading.Thread(target=show_video)

# Bắt đầu luồng
read_thread.start()
show_thread.start()

# Chờ các luồng kết thúc
read_thread.join()
show_thread.join()

# Giải phóng tài nguyên
cap.release()
ffmpeg_process.stdin.close()
ffmpeg_process.wait()
cv2.destroyAllWindows()
