from command_line_arguments_module import CommandLineArgs
import binascii
import shutil
import os
import re
args = CommandLineArgs.get_args()
inputFile = args.txt
data = []
directory_path = os.path.dirname(inputFile)
date = re.search(r'(\d{4}-\d{2}-\d{2})', inputFile).group(1)
new_path = directory_path.replace("test", "beacon_automatic")
print(directory_path)

with open(inputFile, 'rb') as f:
    content = f.read()
    content = content.split(b']')
    for c in content:
        c = c.decode('latin1')
        if not "Frame=" in c:
            pass
        elif not "time" in c and len(c) > 2:
            c = c.split("Frame=")[1]
            hex_data = binascii.hexlify(c.encode('latin1')).decode('utf-8')
            data.append(hex_data)
    content = ''
    f.close()
with open(new_path+"\\"+date+'_hex.txt', "w") as f:  
    for d in data:
        f.write(d)
        f.write('\n')
    f.close()
    data = []
    
with open(new_path+"\\"+date+'_output.txt', 'a') as f:
    f.close()
shutil.move(inputFile, directory_path+'\\ascii')