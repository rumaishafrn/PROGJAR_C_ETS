import os
import json
import base64
from glob import glob
import logging

class FileInterface:
    def __init__(self):
        # Ensure uploads directory exists
        if not os.path.exists('uploads'):
            os.makedirs('uploads')
        os.chdir('uploads/')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def list(self, params=[]):
        try:
            filelist = glob('*.*')
            return dict(status='OK', data=filelist)
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            return dict(status='ERROR', data=str(e))

    def get(self, params=[]):
        try:
            if not params or len(params) == 0:
                logging.error("GET called with no filename parameter")
                return dict(status='ERROR', data="No filename provided")
                
            filename = params[0]
            logging.info(f"GET request for file: {filename}")
            
            if not os.path.exists(filename):
                logging.error(f"File {filename} not found")
                return dict(status='ERROR', data=f"File {filename} not found")
                
            logging.info(f"Reading file {filename} for GET request")
            file_size = os.path.getsize(filename)
            
            # For very large files, read in chunks
            if file_size > 10 * 1024 * 1024:  # If file is larger than 10MB
                logging.info(f"Large file detected ({file_size} bytes), reading in chunks")
                
                try:
                    # Read file in chunks and encode each chunk
                    with open(filename, 'rb') as fp:
                        content = fp.read()
                    
                    logging.info(f"Successfully read all {file_size} bytes")
                    encoded_content = base64.b64encode(content).decode()
                    logging.info(f"Successfully encoded content, encoded size: {len(encoded_content)} bytes")
                    
                    return dict(status='OK', data_namafile=filename, data_file=encoded_content)
                    
                except Exception as chunk_error:
                    logging.error(f"Error reading file in chunks: {str(chunk_error)}")
                    return dict(status='ERROR', data=str(chunk_error))
            else:
                # For smaller files, read at once
                try:
                    with open(filename, 'rb') as fp:
                        file_content = fp.read()
                    
                    file_size = len(file_content)
                    logging.info(f"File read successfully, size: {file_size} bytes")
                    
                    logging.info(f"Encoding file {filename}")
                    encoded_content = base64.b64encode(file_content).decode()
                    encoded_size = len(encoded_content)
                    logging.info(f"Encoded size: {encoded_size} bytes")
                    
                    return dict(status='OK', data_namafile=filename, data_file=encoded_content)
                    
                except Exception as e:
                    logging.error(f"Error reading file: {str(e)}")
                    return dict(status='ERROR', data=str(e))
        except Exception as e:
            logging.error(f"Unexpected error in GET operation: {str(e)}")
            return dict(status='ERROR', data=str(e))
        
    def add(self, params=[]):
        try:
            if not params or len(params) < 2:
                return dict(status='ERROR', data="Parameter tidak lengkap")

            filename = params[0]
            encoded_content = params[1]
            
            logging.info(f"Receiving file {filename}")
            logging.info(f"Encoded content size: {len(encoded_content)} bytes")
            
            logging.info(f"Decoding file {filename}")
            try:
                file_content = base64.b64decode(encoded_content)
            except Exception as e:
                logging.error(f"Base64 decoding error: {str(e)}")
                return dict(status='ERROR', data=f"Base64 decoding error: {str(e)}")
                
            logging.info(f"Writing {len(file_content)} bytes to {filename}")
            
            with open(filename, 'wb') as file:
                file.write(file_content)
            
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                logging.info(f"File {filename} successfully written ({file_size} bytes)")
                return dict(status='OK', data=f"File {filename} berhasil diupload ({file_size} bytes)")
            else:
                logging.error(f"File {filename} failed to write")
                return dict(status='ERROR', data=f"File {filename} gagal diupload")
            
        except Exception as e:
            logging.error(f"Error in ADD operation: {str(e)}")
            return dict(status='ERROR', data=str(e))
    
    def delete(self, params=[]):
        try:
            if not params or len(params) == 0:
                return dict(status='ERROR', data="No filename provided")
                
            filename = params[0]
            
            if not os.path.exists(filename):
                return dict(status='ERROR', data=f"File {filename} not found")
            
            logging.info(f"Deleting file {filename}")
            os.remove(filename)
            
            if os.path.exists(filename):
                logging.error(f"Failed to delete {filename}")
                return dict(status='ERROR', data=f"File {filename} gagal dihapus")
            
            logging.info(f"File {filename} successfully deleted")
            return dict(status='OK', data=f"File {filename} berhasil dihapus")
        except Exception as e:
            logging.error(f"Error in DELETE operation: {str(e)}")
            return dict(status='ERROR', data=str(e))


if __name__=='__main__':
    f = FileInterface()
    print(f.list())