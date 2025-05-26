from socket import *
import socket
import threading
import logging
import time
import sys
import multiprocessing
from multiprocessing import Process, Queue, Pool
import io

from file_protocol import FileProtocol

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
fp = FileProtocol()

def ProcessTheClient(client_data):
    connection, address = client_data
    buffer = b''
    try:
        logging.info(f"Processing client {address}")
        while True:
            chunk = connection.recv(2**20) 
            if not chunk:
                break
                
            buffer += chunk
            
            if b"\r\n\r\n" in buffer:
                # Get the complete message
                request = buffer.decode()
                logging.info(f"Complete request received from {address} ({len(buffer)} bytes)")
                
                # Process the request
                start_time = time.time()
                processed = fp.proses_string(request.strip())
                end_time = time.time()
                
                logging.info(f"Request processed in {end_time - start_time:.2f} seconds")
                
                response = processed + "\r\n\r\n"
                
                response_bytes = response.encode()
                total_bytes = len(response_bytes)
                logging.info(f"Sending response ({total_bytes} bytes)")
                
                chunk_size = 2**16
                for i in range(0, total_bytes, chunk_size):
                    connection.sendall(response_bytes[i:i+chunk_size])
                
                logging.info(f"Response sent to {address}")
                buffer = b''  
                
    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")
    finally:
        logging.info(f"Closing connection with {address}")
        connection.close()

class Server:
    def __init__(self, ipaddress='0.0.0.0', port=6666, max_workers=10):
        self.ipinfo = (ipaddress, port)
        self.max_workers = max_workers
        
    def handle_connection(self, connection, address):
        ProcessTheClient((connection, address))
        
    def run(self):
        my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2**20)  
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2**20)
        
        logging.warning(f"Server running on {self.ipinfo}")
        my_socket.bind(self.ipinfo)
        my_socket.listen(10)
        
        pool = multiprocessing.Pool(processes=self.max_workers)
        
        try:
            while True:
                connection, address = my_socket.accept()
                p = Process(target=self.handle_connection, args=(connection, address))
                p.daemon = True
                p.start()
                connection.close()
                
        except KeyboardInterrupt:
            logging.warning("Server shutting down.")
        finally:
            pool.close()
            pool.join()
            my_socket.close()


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
        max_workers = 10  
        
    svr = Server(ipaddress='0.0.0.0', port=13337, max_workers=max_workers)
    svr.run()


if __name__ == "__main__":
    main()