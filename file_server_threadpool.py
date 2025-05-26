from socket import *
import socket
import threading
import logging
import time
import sys
from concurrent.futures import ThreadPoolExecutor
import io

from file_protocol import FileProtocol

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
fp = FileProtocol()

def ProcessTheClient(connection, address):
    buffer = b''
    try:
        logging.info(f"Processing client {address}")
        while True:
            chunk = connection.recv(2**20) 
            if not chunk:
                break
                
            buffer += chunk
            
            if b"\r\n\r\n" in buffer:
                request = buffer.decode()
                logging.info(f"Complete request received from {address} ({len(buffer)} bytes)")
                
                start_time = time.time()
                processed = fp.proses_string(request.strip())
                end_time = time.time()
                logging.info(f"Request processed in {end_time - start_time:.2f} seconds")
                response = processed + "\r\n\r\n"
                
                response_bytes = response.encode()
                total_bytes = len(response_bytes)
                logging.info(f"Sending response ({total_bytes} bytes)")
                
                chunk_size = 2**20
                for i in range(0, total_bytes, chunk_size):
                    connection.sendall(response_bytes[i:i+chunk_size])
                
                logging.info(f"Response sent to {address}")
                buffer = b''  # Reset buffer for next request
                
    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")
    finally:
        logging.info(f"Closing connection with {address}")
        connection.close()

class Server:
    def __init__(self, ipaddress='0.0.0.0', port=13337, max_workers=10):
        self.ipinfo = (ipaddress, port)
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Set buffer sizes for better performance
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**20)  
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**20) 
        self.max_workers = max_workers

    def run(self):
        logging.warning(f"Server running on {self.ipinfo}")
        self.my_socket.bind(self.ipinfo)
        self.my_socket.listen(10)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            try:
                while True:
                    connection, address = self.my_socket.accept()
                    logging.warning(f"Accepted connection from {address}")
                    # Increase socket timeout
                    connection.settimeout(300)  # 5-minute timeout
                    executor.submit(ProcessTheClient, connection, address)
            except KeyboardInterrupt:
                logging.warning("Server shutting down.")
            finally:
                self.my_socket.close()


def main():
    if len(sys.argv) > 1:
        try:
            max_workers = int(sys.argv[1])
            if max_workers <= 0:
                raise ValueError("Number of workers must be positive.")
        except ValueError as e:
            print(f"Invalid argument: {e}. Using default value of 10.")
            max_workers = 10
    else:
        max_workers = 10  # Default value
        
    
    
    svr = Server(ipaddress='0.0.0.0', port=13337, max_workers=max_workers)  # Increased max workers
    svr.run()


if __name__ == "__main__":
    main()