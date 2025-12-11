import socket
import threading
import sqlite3
import hashlib
import time

LOCAL_HOST = '127.0.0.1'
HOST = LOCAL_HOST
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()

clients = []
usernames = []
last_seen = {}
lock = threading.Lock()
files=[]
senders=[]
try:
    f1=open('files.txt','rt')
    f2=open('senders.txt','rt')
    files=f1.read().split(',')
    senders=f2.read().split(',')
except FileNotFoundError:
    pass

def safe_remove_and_notify(username, reason="left"):
    with lock:
        if username in usernames:
            index = usernames.index(username)
            
            if index < len(clients):
                try:
                    client = clients[index]
                    client.close()
                except:
                    pass
                clients.pop(index)
            
            if index < len(usernames):
                usernames.pop(index)
            
            if username in last_seen:
                del last_seen[username]
    
    if reason == "left":
        message = f"{username} left the chat.".encode('utf-8')
    else:
        message = f"{username} disconnected.".encode('utf-8')
    
    safe_broadcast(message, exclude_username=username)

def safe_broadcast(message, exclude_username=None):
    targets = []
    
    with lock:
        for i, client in enumerate(clients):
            if exclude_username and usernames[i] == exclude_username:
                continue
            
            try:
                client.send(message)
                targets.append((i, client, usernames[i]))
            except:
                pass

def broadcast(message, exclude_username=None):
    current_time = time.time()
    to_remove = []
    
    with lock:
        for i, client in enumerate(clients):
            if exclude_username and usernames[i] == exclude_username:
                continue
                
            try:
                client.send(message)
            except:
                to_remove.append(i)
        
        for idx in sorted(to_remove, reverse=True):
            if idx < len(clients):
                try:
                    clients[idx].close()
                except:
                    pass
                
                if idx < len(clients):
                    clients.pop(idx)
                if idx < len(usernames):
                    username = usernames.pop(idx)
                    
                    if username in last_seen:
                        del last_seen[username]
                    
                    safe_broadcast(f"{username} left the chat.".encode('utf-8'))

def send_to_client(target_username, message):
    with lock:
        if target_username in usernames:
            index = usernames.index(target_username)
            if index < len(clients):
                client = clients[index]
                try:
                    client.send(message.encode('utf-8'))
                    return True
                except:
                    safe_remove_and_notify(target_username, "disconnected")
                    return False
    return False

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

def handle_command(client, username, command):
    command = command.strip()
    parts = command.split(' ', 1)
    cmd = parts[0].lower()
    
    if cmd == '/list':
        with lock:
            if len(usernames) == 0:
                client.send("No other users online.".encode('utf-8'))
            else:
                user_list = []
                for i, user in enumerate(usernames):
                    status = " (you)" if user == username else ""
                    user_list.append(f"{i+1}. {user}{status}")
                
                list_msg = f"Online users ({len(usernames)}):\n"
                list_msg += "\n".join(user_list)
                try:
                    client.send(list_msg.encode('utf-8'))
                except:
                    safe_remove_and_notify(username, "disconnected")
    
    elif cmd == '/pm' and len(parts) > 1:
        pm_parts = parts[1].split(' ', 1)
        if len(pm_parts) < 2:
            try:
                client.send("Usage: /pm [username] [message]".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")
            return
        
        target_username = pm_parts[0]
        pm_message = pm_parts[1]
        
        if target_username == username:
            try:
                client.send("Cannot send PM to yourself.".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")
            return
        
        if send_to_client(target_username, f"[PM from {username}]: {pm_message}"):
            try:
                client.send(f"[PM sent to {target_username}]: {pm_message}".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")
        else:
            try:
                client.send(f"User {target_username} is offline or doesn't exist.".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")
    
    else:
        help_msg = """Available commands:
/list - Show online users
/pm [username] [message] - Send private message
/help - Show this help
send:[filename] - Send a file to the server 
download:[filename] - Download a file from the server
showallfile - Show all available on the server"""
        try:
            client.send(help_msg.encode('utf-8'))
        except:
            safe_remove_and_notify(username, "disconnected")

def handle(client, username):
    try:
        client.send(f"Welcome to the chat room, {username}! Type /help for commands.".encode('utf-8'))
    except:
        safe_remove_and_notify(username, "disconnected")
        return
    
    while True:
        try:
            msg = client.recv(1024)
            
            if not msg:
                safe_remove_and_notify(username, "left")
                break
            
            msg_str = msg.decode('utf-8')
            
            if msg_str.strip().upper() == 'EXIT':
                safe_remove_and_notify(username, "left")
                break
            
            if msg_str.startswith('/'):
                handle_command(client, username, msg_str)
                continue
            
            formatted_msg = f"{username}: {msg_str}".encode('utf-8')
            if msg.decode('utf-8')=='FILE':
                print("ready to receive file!!!")
                file_name=client.recv(1024)
                file_size=client.recv(1024)
                sender=usernames[clients.index(client)]
                print(f"name={file_name},size={file_size},sender={sender}")
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
                try:
                    client.send(formatted_msg)
                except:
                    safe_remove_and_notify(username, "disconnected")
                    break
                broadcast(formatted_msg, exclude_username=username)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            safe_remove_and_notify(username, "disconnected")
            break
        except:
            safe_remove_and_notify(username, "disconnected")
            break

def handle_login(client):
    try:
        client.send("Welcome! Type 'LOGIN' or 'REGISTER': ".encode('utf-8'))
    except:
        return None
    
    while True:
        try:
            command = client.recv(1024).decode('utf-8').strip().upper()
            
            if command == 'REGISTER':
                try:
                    client.send("Enter new username: ".encode('utf-8'))
                    username = client.recv(1024).decode('utf-8').strip()
                    client.send("Enter new password: ".encode('utf-8'))
                    password = client.recv(1024).decode('utf-8').strip()
                except:
                    return None
                
                if register_user(username, password):
                    try:
                        client.send("Registration successful! Please type 'LOGIN' to continue.\n".encode('utf-8'))
                    except:
                        return None
                else:
                    try:
                        client.send("Username already taken. Try again or type 'LOGIN'.\n".encode('utf-8'))
                    except:
                        return None

            elif command == 'LOGIN':
                try:
                    client.send("Username: ".encode('utf-8'))
                    username = client.recv(1024).decode('utf-8').strip()
                    client.send("Password: ".encode('utf-8'))
                    password = client.recv(1024).decode('utf-8').strip()
                except:
                    return None
                
                if login_user(username, password):
                    with lock:
                        if username in usernames:
                            try:
                                client.send("This user is already online.\n".encode('utf-8'))
                            except:
                                return None
                            continue
                    
                    try:
                        client.send(f"Welcome back, {username}!\n".encode('utf-8'))
                        client.send("Successfully connected to the chat!\n".encode('utf-8'))
                    except:
                        return None
                    
                    return username
                else:
                    try:
                        client.send("Login failed! Wrong username or password.\nType 'LOGIN' or 'REGISTER': ".encode('utf-8'))
                    except:
                        return None
            
            else:
                try:
                    client.send("Invalid command. Type 'LOGIN' or 'REGISTER': ".encode('utf-8'))
                except:
                    return None
                
        except:
            return None

def receive():
    init_db()
    print(f"Server is listening on port {PORT} ...")
    
    while True:
        try:
            client, address = server.accept()
            print(f"New connection from {str(address)}")

            thread = threading.Thread(target=client_lifecycle, args=(client,))
            thread.start()
        except Exception as e:
            print(f"Error accepting connection: {e}")

def client_lifecycle(client):
    try:
        username = handle_login(client)
        
        if username:
            with lock:
                usernames.append(username)
                clients.append(client)
            print(f"User logged in: {username}")
            
            safe_broadcast(f"{username} joined the chat!".encode('utf-8'), exclude_username=username)
            
            handle(client, username)
        else:
            try:
                client.close()
            except:
                pass
    except:
        try:
            client.close()
        except:
            pass

if __name__ == "__main__":
    receive()