import socket
import threading

HOST = '0.0.0.0'
PORT = 5000

# tcp
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []
nicknames = []

def broadcast(message):
        
    for client in clients:
        client.send(message)
    

def handle(client):
    while True:
        try:
            msg = client.recv(1024)
            if msg.decode('utf-8')=='FILE':
                print("ready to receive file!!!")
                broadcast('FILE'.encode('utf-8'))
                file_name=client.recv(1024)
                file_size=client.recv(1024)
                sender=nicknames[clients.index(client)]
                print(f"name={file_name},size={file_size},sender={sender}")
                broadcast(file_name)
                print("broadcast file name completed!!")
                broadcast(file_size)
                print("brocast file size completed!!")
                broadcast(sender.encode('utf-8'))
                print("fininsh broadcast!!!!")
                file_size_int=int(file_size.decode('utf-8'))
                file_name=file_name.decode('utf-8')
                print(f"file size is{file_size_int}Bytes")
                try:
                    with open(f'{file_name}', 'wb') as f:#寫入
                        received_size = 0
                        while received_size < file_size_int:
                            data = client.recv(1024)
                            f.write(data)
                            received_size += len(data)
                        print(f"{sender} send:{file_name}")
                        f.close()
                except FileNotFoundError:
                    print('file does not exist!')
                    break
                try:
                    with open(f'{file_name}', 'rb') as t:
                        print("reading!")
                        data=t.read()
                        broadcast(data)
                        t.close()
                except FileNotFoundError:
                    print('file does not exist!')
                    break
            else:
                broadcast(msg)   
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            broadcast(f"{nickname} has left the chat.\n".encode('utf-8'))
            nicknames.remove(nickname)
            break

def receive():
    print(f"Server is listening to {PORT} ...")
    while True:
        client, address = server.accept()
        print(f"Connection from {str(address)}")

        client.send("NICK".encode('utf-8'))
        nickname = client.recv(1024).decode('utf-8')

        nicknames.append(nickname)
        clients.append(client)

        print(f"Nickname: {nickname}")
        broadcast(f"{nickname} entered the chat.".encode('utf-8'))
        client.send("Connected to the chat!\n".encode('utf-8'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

receive()