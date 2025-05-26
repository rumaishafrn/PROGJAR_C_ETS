from socket import socket, AF_INET, SOCK_STREAM
import base64
import json

SERVER_ADDRESS = ('localhost', 45000)

def send_request(command):
    with socket(AF_INET, SOCK_STREAM) as client_socket:
        client_socket.connect(SERVER_ADDRESS)
        client_socket.sendall(f"{command}\r\n".encode('utf-8'))

        full_response = b""
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            full_response += data
            if b"\r\n\r\n" in full_response:
                break
        
        response_text = full_response.decode('utf-8').strip()
        print("Response:\n", response_text)
        return response_text

def list_files():
    print("Requesting file list...")
    send_request("LIST")

def download_file():
    filename = input("Enter the filename to download: ").strip()
    response_text = send_request(f"GET {filename}")
    try:
        resp_json = json.loads(response_text)
        if resp_json.get("status") == "OK":
            file_data_b64 = resp_json.get("data_file", "")
            with open(filename, "wb") as f:
                f.write(base64.b64decode(file_data_b64))
            print(f"File '{filename}' berhasil didownload dan disimpan.")
        else:
            print("Error:", resp_json.get("data"))
    except Exception as e:
        print("Gagal memproses response server:", e)

def upload_file():
    filename = input("Enter the filename to upload: ").strip()
    try:
        with open(filename, "rb") as f:
            file_content_b64 = base64.b64encode(f.read()).decode('utf-8')
        print(f"Mengupload '{filename}'...")
        response_text = send_request(f"UPLOAD {filename} {file_content_b64}")
        print(response_text)
    except FileNotFoundError:
        print(f"File '{filename}' tidak ditemukan.")

def delete_file():
    filename = input("Enter the filename to delete on server: ").strip()
    response_text = send_request(f"DELETE {filename}")
    try:
        resp_json = json.loads(response_text)
        if resp_json.get("status") == "OK":
            print(f"File '{filename}' berhasil dihapus.")
        else:
            print("Error:", resp_json.get("data"))
    except Exception as e:
        print("Gagal memproses response server:", e)

def list_images():
    print("Requesting image file list...")
    response_text = send_request("IMAGE")
    try:
        resp_json = json.loads(response_text)
        if resp_json.get("status") == "OK":
            print("Daftar gambar:")
            for img in resp_json.get("data", []):
                print("-", img)
        else:
            print("Error:", resp_json.get("data"))
    except Exception as e:
        print("Gagal memproses response server:", e)

def main():
    print("File Client")
    print("Commands: LIST, GET, UPLOAD, DELETE, IMAGE, QUIT")
    while True:
        command = input("Enter command: ").strip().upper()
        if command == "LIST":
            list_files()
        elif command == "GET":
            download_file()
        elif command == "UPLOAD":
            upload_file()
        elif command == "DELETE":
            delete_file()
        elif command == "IMAGE":
            list_images()
        elif command == "QUIT":
            print("Exiting client.")
            break
        else:
            print("Invalid command. Please enter LIST, GET, UPLOAD, DELETE, IMAGE, or QUIT.")

if __name__ == "__main__":
    main()
