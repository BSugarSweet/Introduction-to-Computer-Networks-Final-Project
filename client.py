import socket
import threading
import sys
import os
import time 

LOCAL_HOST = '127.0.0.1'
PORT = 5000

chat_active = False

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((LOCAL_HOST, 5000))
except ConnectionRefusedError:
    print("Unable to connect to the server. Please ensure the server is running.")
    sys.exit()

def receive():
    global chat_active

    while True:
        try:
            msg = client.recv(1024).decode('utf-8')
            if not msg:
                print("Disconnected from server.")
                client.close()
                break
            if "Successfully connected" in msg:
                chat_active = True
            elif msg=='DOWNLOAD':
                print("READY TO DOWNLOAD!")
                file_name=client.recv(1024).decode('utf-8')
                file_size=int(client.recv(1024).decode('utf-8'))
                sender=client.recv(1024).decode('utf-8')
                print(f"name={file_name},size={file_size},sender={sender}")
                try:
                    with open(f'{file_name}', 'wb') as f:
                        received_size = 0
                        while received_size < file_size:
                            data = client.recv(1024)
                            f.write(data)
                            received_size += len(data)
                        f.close()
                        print(f"{sender} send:{file_name}")
                except FileNotFoundError:
                    print('file does not exist!')
                    break
            else:
                print(msg)
        except OSError:
            break
        except:
            print("You dropped from the chat.\n")
            client.close()
            break

def write():
    while True:
        try:
            text = input("")

            if chat_active:
                print("\033[F\033[K", end="")

            if text == 'EXIT':
                client.close()
                time.sleep(0.2)
                print("You have left the chat.")
                os._exit(0)
            file_name=""
            if "send:" in text:#send:{filename} send file commend
                index_of_colon=text.find(':')
                file_name=text[index_of_colon+1:]
                client.send('FILE'.encode('utf-8'))
                client.send(file_name.encode('utf-8'))
                try:
                    with open(file_name, 'rb') as f:
                        data = f.read()
                        client.send(str(len(data)).encode('utf-8')) # send file size
                        client.send(data)
                        print(f"send:{file_name}")
                        f.close()
                except FileNotFoundError:
                    print("file does not exist!")
            elif "download" in text:#download:{filename} download file commend
                index_of_colon=text.find(':')
                file_name=text[index_of_colon+1:]
                client.send('DOWNLOAD'.encode('utf-8'))
                client.send(file_name.encode('utf-8'))

            elif text == "showallfile":
                client.send('allfile'.encode('utf-8'))
            else:
                client.send(text.encode('utf-8'))
        except: 
            print("An error occurred while sending the message.")
            client.close()
            break


recv_thread = threading.Thread(target=receive)
recv_thread.daemon = True 
recv_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()