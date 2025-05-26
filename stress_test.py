import os
import time
import base64
import json
import socket
from socket import AF_INET, SOCK_STREAM
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

SERVER_ADDRESS = ('localhost', 45000)

# Membaca file dan encode base64
def read_file_base64(filename):
    with open(filename, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

# Fungsi upload
def upload_file_worker(filename):
    try:
        file_content_b64 = read_file_base64(filename)
        with socket(AF_INET, SOCK_STREAM) as s:
            s.connect(SERVER_ADDRESS)
            request = f"UPLOAD {os.path.basename(filename)} {file_content_b64}\r\n"
            s.sendall(request.encode('utf-8'))
            
            full_response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                full_response += data
                if b"\r\n\r\n" in full_response:
                    break
            response = full_response.decode('utf-8').strip()
            resp_json = json.loads(response)
            if resp_json.get("status") == "OK":
                return True, len(file_content_b64) * 3 // 4  # approx size in bytes after base64 decode
            else:
                return False, 0
    except Exception as e:
        return False, 0

# Fungsi download
def download_file_worker(filename):
    try:
        with socket(AF_INET, SOCK_STREAM) as s:
            s.connect(SERVER_ADDRESS)
            request = f"GET {filename}\r\n"
            s.sendall(request.encode('utf-8'))

            full_response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                full_response += data
                if b"\r\n\r\n" in full_response:
                    break
            response = full_response.decode('utf-8').strip()
            resp_json = json.loads(response)
            if resp_json.get("status") == "OK":
                file_b64 = resp_json.get("data_file", "")
                size_bytes = len(file_b64) * 3 // 4
                return True, size_bytes
            else:
                return False, 0
    except Exception as e:
        return False, 0

def stress_test_pool(filename, num_workers, mode='thread', operation='upload'):
    """
    filename: file yang dipakai
    num_workers: jumlah worker concurrent
    mode: 'thread' atau 'process'
    operation: 'upload' atau 'download'
    """
    print(f"Starting stress test: mode={mode}, workers={num_workers}, operation={operation}, file={filename}")

    executor_class = ThreadPoolExecutor if mode == 'thread' else ProcessPoolExecutor
    start_time = time.time()
    successes = 0
    failures = 0
    total_bytes = 0

    with executor_class(max_workers=num_workers) as executor:
        futures = []
        for _ in range(num_workers):
            if operation == 'upload':
                futures.append(executor.submit(upload_file_worker, filename))
            else:
                futures.append(executor.submit(download_file_worker, os.path.basename(filename)))
        
        for future in as_completed(futures):
            success, bytes_processed = future.result()
            if success:
                successes += 1
                total_bytes += bytes_processed
            else:
                failures += 1

    end_time = time.time()
    total_time = end_time - start_time
    throughput = total_bytes / total_time if total_time > 0 else 0

    print(f"Results: total_time={total_time:.2f}s, throughput={throughput:.2f} B/s, success={successes}, fail={failures}")

    return {
        "total_time": total_time,
        "throughput": throughput,
        "successes": successes,
        "failures": failures,
        "workers": num_workers,
        "operation": operation,
        "mode": mode,
        "filename": filename
    }

def generate_dummy_file(filename, size_mb):
    if os.path.exists(filename) and os.path.getsize(filename) == size_mb * 1024 * 1024:
        print(f"File {filename} sudah ada.")
        return
    print(f"Generating dummy file {filename} of size {size_mb} MB...")
    with open(filename, 'wb') as f:
        f.write(os.urandom(size_mb * 1024 * 1024))

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Stress test client for file server")
    parser.add_argument('--mode', choices=['thread', 'process'], default='thread', help='Execution mode')
    parser.add_argument('--workers', type=int, default=5, help='Number of concurrent workers')
    parser.add_argument('--operation', choices=['upload', 'download'], default='upload', help='Operation to perform')
    parser.add_argument('--file_size', type=int, default=10, help='File size in MB')
    args = parser.parse_args()

    filename = f"dummy_{args.file_size}mb.bin"
    generate_dummy_file(filename, args.file_size)

    # If operation is download, file must exist on server, so upload it first for a single time
    if args.operation == 'download':
        print("Uploading file once for download test...")
        success, _ = upload_file_worker(filename)
        if not success:
            print("Upload failed, cannot proceed with download test.")
            return

    stress_test_pool(filename, args.workers, mode=args.mode, operation=args.operation)

if __name__ == "__main__":
    main()
