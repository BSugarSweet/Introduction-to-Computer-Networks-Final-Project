import socket
import threading
import sys

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

            if chat_active:
                print("\033[F\033[K", end="")

            if text == 'EXIT':
                client.close()
                print("You have left the chat.")
                sys.exit()

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