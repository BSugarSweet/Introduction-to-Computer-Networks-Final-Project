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

        client.send(message.encode('utf-8'))

recv_thread = threading.Thread(target=receive)
recv_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()