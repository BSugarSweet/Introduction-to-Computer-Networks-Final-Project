import socket
import threading

LOCAL_HOST = '127.0.0.1'
HOST = LOCAL_HOST
PORT = 5000


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# This avoids the "Address already in use" error.
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = []
nicknames = []

def broadcast(message):
    """
    Send a message to all connected clients.
    Uses a try-except block to ensure one failed client doesn't crash the broadcast loop.
    """
    for client in clients:
        try:
            client.send(message)
        except:
            # If sending fails (e.g., connection lost), we ignore it here.
            pass

def handle(client):
    while True:
        try:
            msg = client.recv(1024)

            if(not msg):
                raise Exception("Client disconnected")
            
            broadcast(msg)
        except:
            if client in clients:
                index = clients.index(client)
                clients.remove(client)
                client.close()
                nickname = nicknames[index]
                broadcast(f"{nickname} left the chat.".encode('utf-8'))
                nicknames.remove(nickname)
                
            break


def receive():
    print(f"Server is listening to {PORT} ...")
    while True:
        try:
            client, address = server.accept()
            print(f"Connected from {str(address)}")

            client.send('NICK'.encode('utf-8'))
            nickname = client.recv(1024).decode('utf-8')
            nicknames.append(nickname)
            clients.append(client)

            print(f"Nickname: {nickname}")
            broadcast(f"{nickname} entered the chat.".encode('utf-8'))
            client.send('Connected to the chat!\n'.encode('utf-8'))

            thread = threading.Thread(target=handle, args=(client,))
            thread.start()
        except Exception as e:
            print(f"Error accepting connection: {e}")

if __name__ == "__main__":
    receive()