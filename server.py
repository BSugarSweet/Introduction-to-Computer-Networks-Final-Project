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