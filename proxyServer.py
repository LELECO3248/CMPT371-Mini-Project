import socket
import os
import threading

def handle_proxy_client(clientConnection, clientAddress):
    try:
        request = clientConnection.recv(4096)
        if not request:
            return

        requestStr = request.decode('utf-8', errors='ignore')
        lines = requestStr.splitlines()
        
        if not lines:
            return

        requestLine = lines[0]
        parts = requestLine.split(' ')

        if len(parts) == 3:
            method, url, version = parts
        else:
            print("Malformed request received.")
            return

        # Parse destination hostname and port
        host = ""
        port = 80
        path = ""
        host_port = ""

        if url.startswith("http://"):
            url_no_http = url[7:]
            if '/' in url_no_http:
                slash_pos = url_no_http.find('/')
                host_port = url_no_http[:slash_pos]
                path = url_no_http[slash_pos:]
            else:
                host_port = url_no_http
                path = "/"
        else:
            path = url
            for line in lines[1:]:
                if line.lower().startswith("host:"):
                    host_port = line.split(":", 1)[1].strip()
                    break
        
        if not host_port:
            return

        if ":" in host_port:
            host, port_str = host_port.split(":")
            port = int(port_str)
        else:
            host = host_port
            port = 80

        # If a request points to the proxy port directly, re-route to base server port 8080
        if (host == "127.0.0.1" or host == "localhost") and port == 8888:
            port = 8080
            
        print(f"Proxy Target -> Host: {host} | Port: {port} | Path: {path}")

        ## Request Forwarding and Local Caching
        # Replace '/' with '_' to create a safe filename
        safe_path = path.replace('/', '_')
        if safe_path == "_" or safe_path == "":
            safe_path = "_index.html"
        cache_file = os.path.join("cache", f"{host}_{port}{safe_path}")

        # Search the cache for cache_file. If it already exists, handle the request
        if os.path.isfile(cache_file):
            print(f"Serving {cache_file} from local cache.")
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = f.read()
                clientConnection.sendall(cached_data)
            except Exception as e:
                print(f"Cache read error: {e}")
            return

        # Otherwise, forward the request to the base server and create a new cache entry
        try:
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverSocket.connect((host, port))

            # Rebuild the request line to use a relative path for the target server
            first_line_end = requestStr.find('\n')
            rebuilt_request_str = f"{method} {path} {version}\r\n" + requestStr[first_line_end+1:]
            
            serverSocket.sendall(rebuilt_request_str.encode('utf-8'))

            # Receive the response back from the destination server
            response_data = b""
            while True:
                serverSocket.settimeout(1.0)
                try:
                    chunk = serverSocket.recv(4096)
                    if len(chunk) == 0:
                        break
                    response_data += chunk
                except socket.timeout:
                    break
            
            serverSocket.close()

            # Save the response to the local cache directory
            if response_data:
                with open(cache_file, 'wb') as f:
                    f.write(response_data)
                print(f"Saved response to cache: {cache_file}")

            # Send the response back to the client
            clientConnection.sendall(response_data)

        # If the connection to the base server fails, the correct response code is 502 bad gateway
        except Exception as e:
            print(f"Error connecting to target server: {e}")
            error_body = "<html><body><h1>502 Bad Gateway</h1></body></html>"
            error_response = (
                "HTTP/1.1 502 Bad Gateway\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(error_body)}\r\n"
                "\r\n"
                f"{error_body}"
            )
            clientConnection.sendall(error_response.encode('utf-8'))

    except Exception as e:
        print(f"Error handling client {clientAddress} in proxy thread: {e}")
    finally:
        clientConnection.close()

        
def startProxy():
    # Setup for the cache directory
    if not os.path.exists("cache"):
        os.makedirs("cache")

    proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    proxySocket.bind(('127.0.0.1', 8888))
    proxySocket.listen(5)
    print("Proxy is listening on http://127.0.0.1:8888")

    while True:
        clientConnection, clientAddress = proxySocket.accept()
        print(f"\nAccepted connection from {clientAddress}")

        # Threads
        client_thread = threading.Thread(target=handle_proxy_client, args=(clientConnection, clientAddress))
        client_thread.start()

if __name__ == "__main__":
    startProxy()