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

def broadcast(message, exclude_client=None, exclude_username=None):
    current_time = time.time()
    to_remove = []
    
    for i, client in enumerate(clients):
        if client == exclude_client:
            continue
        if exclude_username and usernames[i] == exclude_username:
            continue
            
        try:
            client.send(message)
            last_seen[usernames[i]] = current_time
        except:
            to_remove.append(i)
    
    for idx in sorted(to_remove, reverse=True):
        remove_client(idx)

def send_to_client(target_username, message):
    if target_username in usernames:
        index = usernames.index(target_username)
        client = clients[index]
        try:
            client.send(message.encode('utf-8'))
            last_seen[target_username] = time.time()
            return True
        except:
            remove_client(index)
            return False
    return False

def remove_client(index):
    if index < len(clients):
        client = clients[index]
        username = usernames[index]
        
        try:
            client.close()
        except:
            pass
        
        clients.pop(index)
        usernames.pop(index)
        
        if username in last_seen:
            del last_seen[username]
        
        broadcast(f"{username} left the chat.".encode('utf-8'))

def handle_command(client, username, command):
    command = command.strip()
    parts = command.split(' ', 1)
    cmd = parts[0].lower()
    
    if cmd == '/list':
        if len(usernames) == 0:
            client.send("No other users online.".encode('utf-8'))
        else:
            user_list = []
            for i, user in enumerate(usernames):
                status = " (you)" if user == username else ""
                
                active = ""
                if user in last_seen:
                    inactive_time = time.time() - last_seen[user]
                    if inactive_time > 60:
                        active = f" [inactive {int(inactive_time/60)}min]"
                
                user_list.append(f"{i+1}. {user}{status}{active}")
            
            list_msg = f"Online users ({len(usernames)}):\n"
            list_msg += "\n".join(user_list)
            client.send(list_msg.encode('utf-8'))
    
    elif cmd == '/pm' and len(parts) > 1:
        pm_parts = parts[1].split(' ', 1)
        if len(pm_parts) < 2:
            client.send("Usage: /pm [username] [message]".encode('utf-8'))
            return
        
        target_username = pm_parts[0]
        pm_message = pm_parts[1]
        
        if target_username == username:
            client.send("Cannot send PM to yourself.".encode('utf-8'))
            return
        
        if send_to_client(target_username, f"[PM from {username}]: {pm_message}"):
            client.send(f"[PM sent to {target_username}]: {pm_message}".encode('utf-8'))
        else:
            client.send(f"User {target_username} is offline or doesn't exist.".encode('utf-8'))
    
    else:
        help_msg = """Available commands:
/list - Show online users
/pm [username] [message] - Send private message
/help - Show this help"""
        client.send(help_msg.encode('utf-8'))

def handle(client, username):
    last_seen[username] = time.time()
    
    client.send(f"Welcome to the chat room, {username}! Type /help for commands.".encode('utf-8'))
    
    while True:
        try:
            msg = client.recv(1024)
            
            if not msg:
                raise Exception("Client disconnected")
            
            msg_str = msg.decode('utf-8')
            last_seen[username] = time.time()
            
            if msg_str.startswith('/'):
                handle_command(client, username, msg_str)
                continue
            
            formatted_msg = f"{username}: {msg_str}".encode('utf-8')
            broadcast(formatted_msg, exclude_client=client)
            
        except:
            if username in usernames:
                index = usernames.index(username)
                remove_client(index)
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
                    if username in usernames:
                        client.send("This user is already online.\n".encode('utf-8'))
                        continue
                    
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
    print(f"Server is listening on port {PORT} ...")
    
    def cleanup_inactive():
        while True:
            time.sleep(60)
            current_time = time.time()
            to_remove = []
            
            for i, username in enumerate(usernames):
                if username in last_seen:
                    inactive_time = current_time - last_seen[username]
                    if inactive_time > 300:
                        to_remove.append(i)
            
            for idx in sorted(to_remove, reverse=True):
                remove_client(idx)
                print(f"Cleaned up inactive user: {usernames[idx] if idx < len(usernames) else 'unknown'}")
    
    cleanup_thread = threading.Thread(target=cleanup_inactive, daemon=True)
    cleanup_thread.start()
    
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
            usernames.append(username)
            clients.append(client)
            print(f"User logged in: {username}")
            
            broadcast(f"{username} joined the chat!".encode('utf-8'), exclude_client=client)
            
            handle(client, username)
        else:
            client.close()
    except:
        client.close()

if __name__ == "__main__":
    receive()