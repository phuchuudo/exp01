import socket
from datetime import datetime, timezone
import pytz
import pickle
import time

# Thiết lập server
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 9999))
server_socket.listen(5)
print("Server is listening...")

client_socket, addr = server_socket.accept()
print(f"Connection from {addr}")

while True:
    # Nhận request từ client
    data = client_socket.recv(1024)
    if not data:
        break
    
    # Thêm độ trễ giả lập
    #time.sleep(1)  # Chờ 1 giây trước khi ghi nhận thời gian server

    # Ghi nhận thời gian hiện tại trên server (UTC)
    server_time = datetime.now(pytz.UTC).timestamp()
    print(f"Server time (timestamp): {server_time}")

    # Gửi server_time về client
    client_socket.sendall(pickle.dumps(server_time))

client_socket.close()
server_socket.close()
