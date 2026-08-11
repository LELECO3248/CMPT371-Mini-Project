import socket
import os
from datetime import datetime
import threading

def  handle_client(clientConnection, clientAddress):
        try:
            request = clientConnection.recv(1025).decode('utf-8')
            print(f"Received request:\n{request}")

            if not request:
                return

            lines = request.splitlines()
            if not lines:
                return
            
            requestLine = lines[0]

            parts = requestLine.split(' ')

            if len(parts) == 3:
                method = parts[0]
                path = parts[1]
                version = parts[2]

                print(f"Method: {method} | Path: {path} | Version: {version}")
            else:
                print("Malformed request received.")
                return
            
            if version != "HTTP/1.1":
                body = "<html><body><h1>505 HTTP Version Not Supported</h1></body></html>"

                response = (
                    "HTTP/1.1 505 HTTP Version Not Supported\r\n"
                    "Content-Type: text/html\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "\r\n"
                    f"{body}")
        
                clientConnection.sendall(response.encode('utf-8'))
                return        

            if path.startswith('/'):
                path = path[1:]

            if path == "":
                path = "test.html"

            if os.path.isfile(path):
                try:
                    with open(path, 'r') as file:
                        body = file.read()

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
                                response = "HTTP/1.1 304 Not Modified\r\n\r\n"
                                clientConnection.sendall(response.encode('utf-8'))
                                return            
                        except ValueError:
                            pass

                    response = (
                        "HTTP/1.1 200 OK\r\n"
                        "Content-Type: text/html\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "\r\n"
                        f"{body}"
                    )
                    clientConnection.sendall(response.encode('utf-8'))
                    

                except PermissionError:
                    body = "<html><body><h1>403 Forbidden</h1></body></html>"
                    response = (
                        "HTTP/1.1 403 Forbidden\r\n"
                        "Content-Type: text/html\r\n"
                        f"Content-Length: {len(body)}\r\n"
                        "\r\n"
                        f"{body}")
        
                    clientConnection.sendall(response.encode('utf-8'))
                    
            else:
                body = "<html><body><h1>404 Not Found</h1></body></html>"

                response = (
                    "HTTP/1.1 404 Not Found\r\n"
                    "Content-Type: text/html\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "\r\n"
                    f"{body}"
                )    
        
                clientConnection.sendall(response.encode('utf-8'))
        except Exception as e:
            print(f"Error handling client {clientAddress}: {e}")
        finally:
            clientConnection.close()


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
        client_thread = threading.Thread(target=handle_client, args=(clientConnection, clientAddress))
        client_thread.start()



if __name__ == "__main__":
    startServer()