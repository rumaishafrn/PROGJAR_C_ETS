import socket
import json
import base64
import os
import time
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

server_address = ('127.0.0.1', 13337)  

def send_command(command_str):
    try:
        with socket.create_connection(server_address, timeout=300) as sock:  
            sock.sendall(command_str.encode())
            
            data_received = b""
            end_marker = b"\r\n\r\n"
            
            while True:
                chunk = sock.recv(2**20)  
                if not chunk:
                    break
                data_received += chunk
                if end_marker in data_received[-8:]:  
                    break
            response_str = data_received.decode()
            response_str = response_str.strip()
            
            return json.loads(response_str)
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "ERROR", "message": str(e)}

def remote_list():
    command_str = "LIST\r\n\r\n"
    hasil = send_command(command_str)
    if hasil['status'] == 'OK':
        print("\n\nDaftar File yang Tersedia:")
        print("=============================")
        for nmfile in hasil['data']:
            print(f"  • {nmfile}")
        print("=============================\n\n")
        return True, "Success"
    else:
        print(f"Gagal: {hasil.get('data', 'Unknown error')}")
        return False, "Gagal"

def remote_get(filename=""):
    command_str = f"GET {filename}\r\n\r\n"
    print(f"Sending GET request for {filename}...")
    
    start_time = time.time()
    hasil = send_command(command_str)
    end_time = time.time()
    
    print(f"Response received in {end_time - start_time:.2f} seconds")
    
    if (hasil['status']=='OK'):
        namafile = hasil['data_namafile']
        print(f"Decoding file data for {namafile}...")
        isifile = base64.b64decode(hasil['data_file'])
        
        print(f"Writing {len(isifile)} bytes to file...")
        with open(namafile, 'wb') as fp:
            fp.write(isifile)
        
        print(f"File {filename} berhasil didownload ({len(isifile)} bytes)")
        return True, "Success"
    else:
        print(f"Gagal: {hasil.get('data', 'Unknown error')}")
        return False, "Gagal"
    
def remote_add(filename=""):
    isFileExist = os.path.exists(filename)

    if not isFileExist:
        print(f"File {filename} tidak ditemukan...")
        return False, "File tidak ditemukan"
    
    file_size = os.path.getsize(filename)
    print(f"Reading file {filename} ({file_size} bytes)...")
    
    with open(filename, 'rb') as f:
        content = f.read()
    
    print(f"Encoding file data ({file_size} bytes)...")
    encodedContent = base64.b64encode(content).decode()
    encoded_size = len(encodedContent)
    print(f"Encoded size: {encoded_size} bytes")
    
    command_str = f"ADD {filename} {encodedContent}\r\n\r\n"
    print(f"Sending ADD request ({len(command_str)} bytes total)...")
    
    start_time = time.time()
    result = send_command(command_str)
    end_time = time.time()
    
    print(f"Response received in {end_time - start_time:.2f} seconds")
    
    if (result['status']=='OK'):
        print(f"File {filename} berhasil diupload")
        return True, "Success"
    else:
        print(f"Gagal: {result.get('data', 'Unknown error')}")
        return False, "Gagal"
    
def remote_delete(filename=""):
    command_str = f"DELETE {filename}\r\n\r\n"
    hasil = send_command(command_str)
    
    if (hasil['status']=='OK'):
        print(f"File {filename} berhasil dihapus")
        return True, "Success"
    else:
        print(f"Gagal: {hasil.get('data', 'Unknown error')}")
        return False, "Gagal"

def stress_worker(task_type, filename):
    start = time.time()
    print(f"----> Starting {task_type} for {filename}")
    if task_type == "upload":
        success, res = remote_add(filename)
        print(f"----> Uploading {filename} completed")
    else:
        success, res = remote_get(filename)
    end = time.time()
    size = os.path.getsize(filename) if os.path.exists(filename) else 0
    elapsed = end - start
    return {
        "task": task_type,
        "filename": filename,
        "success": success,
        "time": elapsed,
        "throughput": size / elapsed if success and elapsed > 0 else 0,
        "message": res if not success else "OK"
    }

def run_stress_test(task_type, filename,  num_clients, server_pool_size=1):
    print(f"\nTesting {task_type.upper()} - File: {filename} | Server Pool: {server_pool_size}, Clients: {num_clients}")
    client_results = []

    start_all = time.time()
    with ThreadPoolExecutor(max_workers=num_clients) as executor:
        futures = [executor.submit(stress_worker, task_type, filename) for _ in range(num_clients)]
        for future in tqdm(futures):
            client_results.append(future.result())
    end_all = time.time()

    total_client_time = sum(r["time"] for r in client_results)
    avg_client_time = total_client_time / num_clients
    
    client_success = sum(1 for r in client_results if r["success"])
    client_failure = num_clients - client_success
    
    total_throughput = sum(r["throughput"] for r in client_results if r["success"])
    avg_throughput = total_throughput / client_success if client_success else 0
    server_success = client_success
    server_failure = client_failure
    total_time = end_all - start_all
    
    return {
        "task": task_type,
        "file": filename,
        "client_pool": "thread",  # This is fixed as ThreadPoolExecutor
        "server_pool": server_pool_size,
        "clients": num_clients,
        "client_success": client_success,
        "client_fail": client_failure,
        "server_success": server_success,
        "server_fail": server_failure,
        "total_time": round(total_time, 2),
        "avg_client_time": round(avg_client_time, 2),
        "avg_throughput": round(avg_throughput, 2) if client_success else 0
    }

def create_files():
    sizes = {
        "10MB.bin": 10*1024*1024,
        "50MB.bin": 50*1024*1024,
        "100MB.bin": 100*1024*1024,
    }
    
    for name, size in sizes.items():
        if not os.path.exists(name):
            print(f"Generating {name}...")
            with open(name, "wb") as f:
                f.write(os.urandom(size))
                
def write_result(results):
    """
    Write test results to CSV with continuous row numbering
    """
    file_path = "final_results.csv"
    file_exists = os.path.isfile(file_path) and os.path.getsize(file_path) > 0
    
    # Get the next row number if file exists
    next_row_num = 1
    if file_exists:
        try:
            # Read the existing file to determine the last row number
            with open(file_path, "r") as f:
                lines = f.readlines()
                if len(lines) > 1:  # Header + at least one data row
                    last_line = lines[-1].strip()
                    if last_line:
                        try:
                            next_row_num = int(last_line.split(',')[0]) + 1
                        except (ValueError, IndexError):
                            # If we can't parse the last row number, start from 1
                            next_row_num = 1
        except Exception as e:
            print(f"Warning: Error reading existing CSV file: {e}. Starting row numbers from 1.")
            next_row_num = 1
    
    # Update row numbers in results
    for i, r in enumerate(results):
        r["no"] = next_row_num + i
    
    # Write or append results to CSV
    with open(file_path, "a" if file_exists else "w") as f:
        if not file_exists:
            # Write header
            f.write("no,operation,volume,client_pool_size,server_pool_size,avg_client_time,avg_throughput,client_success,client_fail,server_success,server_fail\n")
        
        # Write data rows
        for r in results:
            f.write(f"{r['no']},{r['task']},{r['file']},{r['clients']},{r['server_pool']},"
                    f"{r['avg_client_time']},{r['avg_throughput']},{r['client_success']},"
                    f"{r['client_fail']},{r['server_success']},{r['server_fail']}\n")
    
    print(f"✅ Results appended to {file_path} (rows {results[0]['no']} to {results[-1]['no']})")


def main():
    create_files()
    combinations = [
        (t, f, c)
        for t in ["download", "upload"]
        for f in ["10MB.bin", "50MB.bin", "100MB.bin"]  
        for c in [1, 5, 50]
    ]
    
    print("Test combinations:", combinations)
    results = []
    
    for task, file, clients in combinations:
        r = run_stress_test(task, file, clients)
        results.append(r)

    write_result(results)

if __name__ == "__main__":
    main()