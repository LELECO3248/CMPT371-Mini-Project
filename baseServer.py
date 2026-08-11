import socket
import os
from datetime import datetime
import threading
import struct

FRAME_TYPE_HEADERS = 0x01
FRAME_TYPE_DATA = 0x02
FRAME_TYPE_END = 0x03

def send_frame(connection, lock, stream_id, frame_type, payload=b""):
    length = len(payload)
    header = struct.pack("!HBH", stream_id, frame_type, length)
    with lock:
        connection.sendall(header + payload)

def receive_frame(connection):
    header_bytes = b""
    while len(header_bytes) < 5:
        try: 
            chunk = connection.recv(5 - len(header_bytes))
            if not chunk:
                return None, None, None
            header_bytes += chunk
        except Exception:
            return None, None, None

    stream_id, frame_type, length = struct.unpack("!HBH", header_bytes)

    payload = b""
    while len(payload) < length:
        try:
            chunk = connection.recv(length - len(payload))
            if not chunk:
                break
            payload += chunk
        except Exception:
            break

    return stream_id, frame_type, payload

def process_stream(clientConnection, send_lock, stream_id, request, if_modified_since=None):
    try:
        lines = request.splitlines()
        if not lines:
            return
        
        requestLine = lines[0]
        parts = requestLine.split(' ')

        if len(parts) == 3:
            method, path, version = parts[0], parts[1], parts[2]
            print(f"Method: {method} | Path: {path} | Version: {version}")
        else:
            print("Malformed request received.")
            return
        
        if version != "HTTP/1.1":
            body = b"<html><body><h1>505 HTTP Version Not Supported</h1></body></html>"
            headers = f"HTTP/1.1 505 HTTP Version Not Supported\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n".encode('utf-8')
            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_HEADERS, headers)
            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_DATA, body)
            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_END, b"")
            return        

        if path.startswith('/'):
            path = path[1:]
        if path == "":
            path = "test.html"

        if os.path.isfile(path):
            try:
                clientDateString = None
                for line in lines[1:]:
                    if line.startswith("If-Modified-Since:"):
                        clientDateString = line.split(":", 1)[1].strip()
                        break

                if clientDateString:
                    try:
                        browserTime = datetime.strptime(clientDateString, "%a, %d %b %Y %H:%M:%S GMT").timestamp()
                        osTimeUtc = datetime.utcfromtimestamp(os.path.getmtime(path)).timestamp()

                        if osTimeUtc <= browserTime:
                            headers = b"HTTP/1.1 304 Not Modified\r\n\r\n"
                            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_HEADERS, headers)
                            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_END, b"")
                            return            
                    except ValueError:
                        pass

                with open(path, 'rb') as file:
                    body = file.read()

                headers = f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n".encode('utf-8')
                send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_HEADERS, headers)
                
                chunk_size = 512
                for i in range(0, len(body), chunk_size):
                    chunk = body[i:i + chunk_size]
                    send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_DATA, chunk)

                send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_END, b"")
            
            except PermissionError:
                body = b"<html><body><h1>403 Forbidden</h1></body></html>"
                headers = f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n".encode('utf-8')
                send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_HEADERS, headers)
                send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_DATA, body)
                send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_END, b"")
        else:
            body = b"<html><body><h1>404 Not Found</h1></body></html>"
            headers = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n".encode('utf-8')
            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_HEADERS, headers)
            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_DATA, body)
            send_frame(clientConnection, send_lock, stream_id, FRAME_TYPE_END, b"")
 
    except Exception as e:
        print(f"[Stream {stream_id}] Error: {e}")

def handle_multiplexed_client(connection, address):
    send_lock = threading.Lock()
    try:
        while True:
            stream_id, frame_type, payload = receive_frame(connection)

            if stream_id is None:
                break

            if frame_type == FRAME_TYPE_HEADERS:
                request_str = payload.decode('utf-8', errors='ignore')

                stream_thread = threading.Thread(
                    target=process_stream,
                    args=(connection, send_lock, stream_id, request_str)
                )
                stream_thread.start()

    except Exception as e:
        print(f"Error handling connection {address}: {e}")
    finally:
        connection.close()

def startServer():
    
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    serverSocket.bind(('127.0.0.1', 8080))
    serverSocket.listen(5)
    print("Server is listening on http://127.0.0.1:8080")

    while True:

        clientConnection, clientAddress = serverSocket.accept()
        print(f"Accepted connection from {clientAddress}")

        #Create and start a new thread for each connection
        client_thread = threading.Thread(target=handle_multiplexed_client, args=(clientConnection, clientAddress))
        client_thread.start()

if __name__ == "__main__":
    startServer()