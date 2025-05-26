import json
import logging
import shlex

from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        self.file = FileInterface()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
    def proses_string(self, string_datamasuk=''):
        logging.info(f"Received command: {string_datamasuk[:100]}..." if len(string_datamasuk) > 100 else string_datamasuk)
        
        try:
            # Split only the first part to get the command and first parameter
            parts = string_datamasuk.split(' ', 2)
            c_request = parts[0].strip().lower()
            
            logging.info(f"Processing request: {c_request}")
            
            # Handle each command type differently due to potential large data
            if c_request == "list":
                params = []
            elif c_request == "get" or c_request == "delete":
                params = [parts[1]] if len(parts) > 1 else []
            elif c_request == "add":
                # For ADD command, we need to handle filename and content separately
                if len(parts) < 3:
                    return json.dumps(dict(status='ERROR', data='ADD command requires filename and content'))
                
                filename = parts[1]
                content = parts[2]  # This contains the base64 encoded file content
                params = [filename, content]
            else:
                return json.dumps(dict(status='ERROR', data='request tidak dikenali'))
            
            # Process the command
            cl = getattr(self.file, c_request)(params)
            
            # Create response
            result = json.dumps(cl)
            logging.info(f"Response length: {len(result)} bytes")
            
            return result
            
        except Exception as e:
            logging.error(f"Error processing request: {str(e)}")
            return json.dumps(dict(status='ERROR', data=f'Error: {str(e)}'))


if __name__=='__main__':
    #contoh pemakaian
    fp = FileProtocol()
    print(fp.proses_string("LIST"))