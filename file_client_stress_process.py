import socket
import json
import base64
import os
import time
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

server_address = ('127.0.0.1', 6666)  

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

def run_stress_test(task_type, filename, pool_type, num_clients):
    print(f"\nTesting {task_type.upper()} - File: {filename} | Pool: process (forced), Clients: {num_clients}")
    results = []

    start_all = time.time()
    with multiprocessing.Pool(processes=num_clients) as pool:  # Menggunakan ProcessPool
        # Membuat list argumen untuk setiap proses
        args = [(task_type, filename) for _ in range(num_clients)]
        # Menggunakan pool.starmap untuk memetakan fungsi dengan multiple arguments
        results = pool.starmap(stress_worker, args)
    end_all = time.time()

    success = sum(1 for r in results if r["success"])
    failure = num_clients - success
    total_throughput = sum(r["throughput"] for r in results if r["success"])
    total_time = end_all - start_all

    return {
        "task": task_type,
        "file": filename,
        "pool": "process",  # Mengubah ini menjadi "process"
        "clients": num_clients,
        "success": success,
        "fail": failure,
        "total_time": round(total_time, 2),
        "avg_throughput": round(total_throughput / success, 2) if success else 0
    }

def create_files():
    sizes = {
        "1B.bin": 1,
        "1KB.bin": 1*1024,
        "100KB.bin": 100*1024,
        "1MB.bin": 1*1024*1024,
        "10MB.bin": 10*1024*1024,
        "100MB.bin": 100*1024*1024,
    }
    
    for name, size in sizes.items():
        if not os.path.exists(name):
            print(f"Generating {name}...")
            with open(name, "wb") as f:
                f.write(os.urandom(size))

def main():
    
    combinations = [
        (t, f, p, c)
        for t in ["download", "upload"]
        for f in ["1B.bin", "1KB.bin", "100KB.bin", "1MB.bin", "10MB.bin", "100MB.bin"]  
        for p in ["thread"]
        for c in [1]
    ]
    
    print("Test combinations:", combinations)
    results = []
    
    for task, file, pool, clients in combinations:
        r = run_stress_test(task, file, pool, clients)
        results.append(r)

    with open("final_results.csv", "w") as f:
        f.write("task,file,pool,clients,total_time,avg_throughput,success,fail\n")
        for r in results:
            f.write(f"{r['task']},{r['file']},{r['pool']},{r['clients']},{r['total_time']},{r['avg_throughput']},{r['success']},{r['fail']}\n")
    print("✅ Results saved to final_results.csv")

if __name__ == "__main__":
    main()