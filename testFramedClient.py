import socket
import struct
import threading
import time

FRAME_TYPE_HEADERS = 0x01
FRAME_TYPE_DATA    = 0x02
FRAME_TYPE_END     = 0x03

def send_frame(conn, stream_id, frame_type, payload=b""):
    length = len(payload)
    header = struct.pack("!HBH", stream_id, frame_type, length)
    conn.sendall(header + payload)

def receive_frame(conn):
    header_bytes = b""
    while len(header_bytes) < 5:
        try:
            chunk = conn.recv(5 - len(header_bytes))
            if not chunk:
                return None, None, None
            header_bytes += chunk
        except Exception:
            return None, None, None

    stream_id, frame_type, length = struct.unpack("!HBH", header_bytes)

    payload = b""
    while len(payload) < length:
        try:
            chunk = conn.recv(length - len(payload))
            if not chunk:
                break
            payload += chunk
        except Exception:
            break

    return stream_id, frame_type, payload

def response_listener(client_socket):
    print("\n--- Listening for Frames from Server ---")
    while True:
        stream_id, frame_type, payload = receive_frame(client_socket)
        if stream_id is None:
            print("[Client] Server closed connection.")
            break

        if frame_type == FRAME_TYPE_HEADERS:
            print(f"\n[RECEIVED HEADERS - Stream {stream_id}]:\n{payload.decode('utf-8', errors='ignore')}")
        elif frame_type == FRAME_TYPE_DATA:
            print(f"[RECEIVED DATA - Stream {stream_id}]: {payload.decode('utf-8', errors='ignore')}")
        elif frame_type == FRAME_TYPE_END:
            print(f"[STREAM END - Stream {stream_id}] Completed!")

def run_test():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 8080))
    print("[Client] Connected to server on 127.0.0.1:8080")

    listener = threading.Thread(target=response_listener, args=(client_socket,), daemon=True)
    listener.start()

    time.sleep(0.2)

    req1 = "GET /test.html HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode('utf-8')
    print("[Client] Sending Stream 1 (GET /test.html)")
    send_frame(client_socket, stream_id=1, frame_type=FRAME_TYPE_HEADERS, payload=req1)

    req2 = "GET /missing.html HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".encode('utf-8')
    print("[Client] Sending Stream 2 (GET /missing.html)")
    send_frame(client_socket, stream_id=2, frame_type=FRAME_TYPE_HEADERS, payload=req2)

    time.sleep(3)
    client_socket.close()

if __name__ == "__main__":
    run_test()