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
is_uploading = {}
lock = threading.Lock()

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
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS files 
                   (file_name TEXT PRIMARY KEY, content BLOB NOT NULL, 
                   upload_by TEXT NOT NULL, upload_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
                   FOREIGN KEY (upload_by) REFERENCES users(username))''')
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

def check_file_exists(filename):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM files WHERE file_name = ?", (filename,))
    file_exists = cursor.fetchone() is not None

    conn.close()
    return file_exists

def get_file_content(filename):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT content FROM files WHERE file_name = ?",
        (filename,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return row[0]

def upload_file(username, filename, file_content):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO files (file_name, content, upload_by)
            VALUES (?, ?, ?)
            ''',
            (filename, file_content, username)
        )

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def handle_command(client: socket.socket, username: str, command: str):
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
    elif cmd == '/upload' and len(parts) > 1:
        upload_parts = parts[1].split(' ', 1)
        if len(upload_parts) < 1:
            try:
                client.send("Usage: /upload [filename]".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")
            return
        
        filename = upload_parts[0]
        
        client.send("Ready to receive content.".encode('utf-8'))

        is_uploading[username] = True
        content_size = int.from_bytes(client.recv(8), 'big')

        try:
            content = client.recv(content_size)

            # todo: check it first before message send
            if check_file_exists(filename):
                client.send(f"There's file with same filename exists in database.".encode('utf-8'))
            elif upload_file(username, filename, content):
                client.send(f"Upload {filename} successfully.".encode('utf-8'))
                safe_broadcast(f"{username}: [File: {filename}]".encode('utf-8'), exclude_username=username)
            else:
                client.send(f"Failed to upload file {filename} to database, please try to upload again.".encode('utf-8'))
        except:
            try:
                client.send(f"Failed to transmit file {filename}, please try to upload again.".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")
        finally:
            is_uploading[username] = False
        pass
    elif cmd == '/download' and len(parts) > 1:
        download_parts = parts[1].split(' ', 1)
        if len(download_parts) < 1:
            client.send("Usage: /download [filename]".encode('utf-8'))
            return
    
        filename = download_parts[0]

        try:
            if not check_file_exists(filename):
                client.send(f"File {filename} does not exist.".encode('utf-8'))
                return
        
            content = get_file_content(filename) # Assumes this returns bytes
            if content is None:
                client.send(f"Failed to read file {filename}.".encode('utf-8'))
                return

            content_size = len(content)

            client.send("Ready to send content.".encode('utf-8'))
        
            header_packet = b'\xF1\x1E' + filename.encode('utf-8') + b'\xF1\x1E'
            size_packet = content_size.to_bytes(8, 'big')
        
            client.sendall(header_packet + size_packet)
            client.sendall(content)
            
            time.sleep(0.1) 
            client.send(f"Download {filename} successfully.".encode('utf-8'))

        except Exception as e:
            logging.exception(traceback.format_exc())
            try:
                client.send(f"Failed to download file {filename}.".encode('utf-8'))
            except:
                safe_remove_and_notify(username, "disconnected")

        except:
            try:
                logging.exception(traceback.format_exc())
                client.send(f"Failed to download file {filename}, please try again.".encode('utf-8'))
            except:
                logging.exception(traceback.format_exc())
                safe_remove_and_notify(username, "disconnected")
    else:
        help_msg = """Available commands:
/list - Show online users
/pm [username] [message] - Send private message
/download [filename] - Download file from server
/help - Show this help"""
        try:
            client.send(help_msg.encode('utf-8'))
        except:
            safe_remove_and_notify(username, "disconnected")

def handle(client: socket.socket, username):
    try:
        client.send(f"Welcome to the chat room, {username}! Type /help for commands.".encode('utf-8'))
    except:
        safe_remove_and_notify(username, "disconnected")
        return
    
    while True:
        try:
            msg = client.recv(1024)

            if is_uploading.setdefault(username, False):
                continue
            
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