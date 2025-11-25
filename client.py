import socket
import threading
import sys

LOCAL_HOST = '127.0.0.1'
PORT = 5000

nickname = input("Enter your nickname: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((LOCAL_HOST, 5000))
except ConnectionRefusedError:
    print("Unable to connect to the server. Please ensure the server is running.")
    sys.exit()

def receive():
    while True:
        try:
            msg = client.recv(1024).decode('utf-8')
            if msg == 'NICK':
                client.send(nickname.encode('utf-8'))
            else:
                print(msg)
        except OSError:
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            client.close()
            break

def write():
    while True:
        try:
            text = input("")
            print("\033[F\033[K", end="")
            if text == 'EXIT':
                client.close()
                print("You have left the chat.")
                sys.exit()

            message = f"{nickname}: {text}"
            client.send(message.encode('utf-8'))
        except:
            print("An error occurred while sending the message.")
            client.close()
            break

recv_thread = threading.Thread(target=receive)
recv_thread.daemon = True 
recv_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()