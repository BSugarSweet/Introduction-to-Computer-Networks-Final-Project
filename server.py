import socket
import threading
import sqlite3
import hashlib

LOCAL_HOST = '127.0.0.1'
HOST = LOCAL_HOST
PORT = 5000


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# This avoids the "Address already in use" error.
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = []
usernames = []
files=[]
senders=[]
try:
    f1=open('files.txt','rt')
    f2=open('senders.txt','rt')
    files=f1.read().split(',')
    senders=f2.read().split(',')
except FileNotFoundError:
    pass


def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                       (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    data = cursor.fetchone()
    conn.close()
    if data:
        if data[0] == hash_password(password):
            return True
    return False

def broadcast(message):
        
    for client in clients:
        try:
            client.send(message)
        except:
            pass

def handle(client, username):
    while True:
        try:
            msg = client.recv(1024)
            if not msg:
                raise Exception("Client disconnected")
            
            formatted_msg = f"{username}: {msg.decode('utf-8')}".encode('utf-8')
            if msg.decode('utf-8')=='FILE':
                print("ready to receive file!!!")
                #broadcast('FILE'.encode('utf-8'))
                file_name=client.recv(1024)
                file_size=client.recv(1024)
                sender=usernames[clients.index(client)]
                print(f"name={file_name},size={file_size},sender={sender}")
                #broadcast(file_name)
                #print("broadcast file name completed!!")
                #broadcast(file_size)
                #print("brocast file size completed!!")
                #broadcast(sender.encode('utf-8'))
                #print("fininsh broadcast!!!!")
                file_size_int=int(file_size.decode('utf-8'))
                file_name=file_name.decode('utf-8')

                files.append(file_name)
                senders.append(sender)
                f1=open('files.txt','wt')
                f2=open('senders.txt','wt')
                s1=''
                s2=''
                for i in range(len(files)):
                    if i<len(files)-1:
                        s1=s1+files[i]+','
                        s2=s2+senders[i]+','
                    else:
                        s1=s1+files[i]
                        s2=s2+senders[i]
                f1.write(s1)
                f2.write(s2)


                print(f"file size is {file_size_int}Bytes")
                broadcast(f"name={file_name},size={file_size},sender={sender}".encode('utf-8'))
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
            elif msg.decode('utf-8')=='DOWNLOAD':
                file_name=client.recv(1024).decode('utf-8')
                if files.count(file_name)==0:
                    client.send('file does not exist'.encode('utf-8'))
                else:
                    client.send("DOWNLOAD".encode('utf-8'))
                    client.send(file_name.encode('utf-8'))
                    try:
                        with open(file_name, 'rb') as f:
                            data = f.read()
                            client.send(str(len(data)).encode('utf-8')) # 傳送檔案大小
                            client.send(senders[files.index(file_name)].encode('utf-8'))
                            client.sendall(data)
                            print(f"send:{file_name}")
                            f.close()
                    except FileNotFoundError:
                        print("file does not exist!")
            elif msg.decode('utf-8')=='allfile':
                s=''
                for i in range(len(files)):
                    if i<len(files)-1:
                        s=s+files[i]+','
                    else:
                        s=s+files[i]
                if s=='':
                    client.send('no file currently exists!'.encode('utf-8'))
                else:
                    client.send(s.encode('utf-8'))
            else:
                broadcast(formatted_msg)
        except:
            if client in clients:
                clients.remove(client)
                client.close()
                if username in usernames:  
                    usernames.remove(username) 
                broadcast(f"{username} left the chat.".encode('utf-8')) 
            break

def handle_login(client):
    client.send("Welcome! Type 'LOGIN' or 'REGISTER': ".encode('utf-8'))
    
    while True:
        try:
            command = client.recv(1024).decode('utf-8').strip().upper()
            
            if command == 'REGISTER':
                client.send("Enter new username: ".encode('utf-8'))
                username = client.recv(1024).decode('utf-8').strip()
                client.send("Enter new password: ".encode('utf-8'))
                password = client.recv(1024).decode('utf-8').strip()
                
                if register_user(username, password):
                    client.send("Registration successful! Please type 'LOGIN' to continue.\n".encode('utf-8'))
                else:
                    client.send("Username already taken. Try again or type 'LOGIN'.\n".encode('utf-8'))

            elif command == 'LOGIN':
                client.send("Username: ".encode('utf-8'))
                username = client.recv(1024).decode('utf-8').strip()
                client.send("Password: ".encode('utf-8'))
                password = client.recv(1024).decode('utf-8').strip()
                
                if login_user(username, password):
                    client.send(f"Welcome back, {username}!\n".encode('utf-8'))
                    client.send("Successfully connected to the chat!\n".encode('utf-8'))
                    return username
                else:
                    client.send("Login failed! Wrong username or password.\nType 'LOGIN' or 'REGISTER': ".encode('utf-8'))
            
            else:
                client.send("Invalid command. Type 'LOGIN' or 'REGISTER': ".encode('utf-8'))
                
        except:
            client.close()
            return None

def receive():
    init_db()
    print(f"Server is listening to {PORT} ...")
    while True:
        try:
            client, address = server.accept()
            print(f"Connected from {str(address)}")

            thread = threading.Thread(target=client_lifecycle, args=(client,))
            thread.start()
        except Exception as e:
            print(f"Error accepting connection: {e}")

def client_lifecycle(client):
    try:
        username = handle_login(client)
        
        if username:
            usernames.append(username)  
            clients.append(client)
            print(f"Username: {username}")  
            broadcast(f"{username} entered the chat.".encode('utf-8'))  
            
            handle(client, username) 
        else:
            client.close()
    except:
        client.close()

if __name__ == "__main__":
    receive()