import socket

def startServer():
    
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    serverSocket.bind(('127.0.0.1', 8080))
    serverSocket.listen(5)
    print("Server is listening on http://127.0.0.1:8080")

    while True:

        clientConnection, clientAddress = serverSocket.accept()
        print(f"Accepted connection from {clientAddress}")

        request = clientConnection.recv(1024).decode('utf-8')
        print(f"Received request:\n{request}")

        body = "<html><body><h1>Server works</h1></body></html>"

        response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
        )
        
        clientConnection.sendall(response.encode('utf-8'))
        clientConnection.close()

if __name__ == "__main__":
    start_server()
            
