import socket
import sys
import threading
import signal
from queue import Queue

running = True
connections_queue = Queue()
active_connections = []

def signal_handler(signum, frame):
    global running
    running = False
    while not connections_queue.empty():
        conn, _ = connections_queue.get()
        conn.close()
    for conn in active_connections:
        conn.close()
    print("Server shutting down...", file=sys.stderr)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)

def handle_client(connection, client_address):
    try:
        active_connections.append(connection)
        connection.sendall(b'accio\r\n')
        connection.settimeout(10)
        
        data_received = 0
        while True:
            data = connection.recv(1024)
            if not data:
                break
            data_received += len(data)
        
        if data_received == 0:
            print("ERROR: No data received for over 10 seconds.", file=sys.stderr)
            connection.sendall(b'ERROR')
        else:
            print(f"Received {data_received} bytes from {client_address}", file=sys.stderr)
    except socket.timeout:
        print("ERROR", file=sys.stderr)
        connection.sendall(b'ERROR')
    finally:
        active_connections.remove(connection)
        connection.close()

def start_server(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(10)
        print(f"Server listening on port {port}", file=sys.stderr)
        
        while running:
            try:
                connection, client_address = server_socket.accept()
                connections_queue.put((connection, client_address))
                threading.Thread(target=handle_client, args=(connection, client_address)).start()
            except socket.error as e:
                print(f"Server accept error: {e}", file=sys.stderr)
                continue

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 server-s.py <PORT>", file=sys.stderr)
        sys.exit(1)
        
    port = int(sys.argv[1])
    if not 1 <= port <= 65535:
        print("ERROR: Port number must be between 1 and 65535.", file=sys.stderr)
        sys.exit(1)

    start_server(port)
