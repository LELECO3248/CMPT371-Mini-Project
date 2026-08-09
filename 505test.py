import socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 8080))
client.sendall("GET /test.html HTTP/3.0\r\nHost: localhost\r\n\r\n".encode('utf-8'))
print(client.recv(1024).decode('utf-8'))
client.close()