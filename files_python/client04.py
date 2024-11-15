import socket
from datetime import datetime, timezone
import pytz
import pickle

# Thiết lập client
SERVER_IP = "127.0.0.1"  # Thay thế bằng địa chỉ IP của server
SERVER_PORT = 9999

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_IP, SERVER_PORT))

# Ghi nhận thời gian bắt đầu (start_time)
start_time = datetime.now(pytz.UTC).timestamp()
print(f"Start time (timestamp): {start_time}")

# Gửi yêu cầu đến server
client_socket.sendall(b"Request time from server")

# Nhận thời gian từ server
data = client_socket.recv(1024)
server_time = pickle.loads(data)

# Ghi nhận thời gian khi nhận được phản hồi
end_time = datetime.now(pytz.UTC).timestamp()
print(f"End time (timestamp): {end_time}")

# Hiển thị thời gian bắt đầu, thời gian từ server và thời gian kết thúc
print(f"Start time (timestamp): {start_time}")
print(f"Server time (timestamp): {server_time}")
print(f"End time (timestamp): {end_time}")

client_socket.close()
