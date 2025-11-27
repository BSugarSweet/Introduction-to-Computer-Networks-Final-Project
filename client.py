import socket
import threading

nickname = input("Enter your nickname: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 5000))

def receive():
    while True:
        try:
            msg = client.recv(1024).decode('utf-8')
            if msg == 'NICK':
                client.send(nickname.encode('utf-8'))
            elif msg=='FILE':
                file_name=client.recv(1024).decode('utf-8')
                file_size=client.recv(1024).decode('utf-8')
                sender=client.recv(1024).decode('utf-8')
                print(f"name={file_name},size={file_size},sender={sender}")
                try:
                    with open(f'{file_name}', 'wb') as f:
                        received_size = 0
                        while received_size < int(file_size):
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
        except:
            print("You dropped from the chat.\n")
            client.close()
            break

def write():
    while True:
        message = f"{nickname}: {input('')}"
        if message == f"{nickname}: EXIT":
            client.send(f"{nickname} has left the chat.\n".encode('utf-8'))
            client.close()
            break
        index_of_send=message.find('send:')
        file_name=""
        if index_of_send>=0:
            for i in range(index_of_send,len(message)):
                if message[i]==':':
                    file_name=message[i+1:]
                    break
            client.send('FILE'.encode('utf-8'))
            client.send(file_name.encode('utf-8'))
            try:
                with open(file_name, 'rb') as f:
                    data = f.read()
                    client.send(str(len(data)).encode('utf-8')) # 傳送檔案大小
                    client.send(data)
                    print(f"send:{file_name}")
                    f.close()
            except FileNotFoundError:
                print("file does not exist!")
        else:
            client.send(message.encode('utf-8'))

recv_thread = threading.Thread(target=receive)
recv_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()