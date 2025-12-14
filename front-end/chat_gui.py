import socket
import threading
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime
import time
import os

LOCAL_HOST = '127.0.0.1'
PORT = 5000

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class ModernChatClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Chat Room")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.username = ""

        try:
            self.client.connect((LOCAL_HOST, PORT))
            self.connected = True
        except ConnectionRefusedError:
            messagebox.showerror("Error", "無法連線到 Server")
            self.destroy()
            return

        # Initialize UI Frames
        self.login_frame = None
        self.register_frame = None
        self.chat_frame = None

        # Start with Login Screen
        self.show_login_screen()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def clear_frames(self):
        """Helper to hide all frames before showing a new one"""
        if self.login_frame:
            self.login_frame.grid_forget()
        if self.register_frame:
            self.register_frame.grid_forget()
        if self.chat_frame:
            self.chat_frame.grid_forget()

    def show_login_screen(self):
        self.clear_frames()
        if self.login_frame is None:
            self.setup_login_ui()
        self.login_frame.grid(row=0, column=0, sticky="nsew")

    def show_register_screen(self):
        self.clear_frames()
        if self.register_frame is None:
            self.setup_register_ui()
        self.register_frame.grid(row=0, column=0, sticky="nsew")

    def show_chat_screen(self):
        self.clear_frames()
        if self.chat_frame is None:
            self.setup_chat_ui()
        self.chat_frame.grid(row=0, column=0, sticky="nsew")

        # Start receiving messages only after login is successful
        self.connected = True
        # update displayed username in sidebar
        try:
            self.user_label.configure(text=f"User: {self.username}")
        except Exception:
            pass
        recv_thread = threading.Thread(target=self.receive_messages)
        recv_thread.daemon = True
        recv_thread.start()

    def setup_login_ui(self):
        self.login_frame = ctk.CTkFrame(self, corner_radius=15)

        # Center container
        inner_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        inner_frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner_frame, text=f"Log in", font=("Roboto", 30, "bold")
        ).pack(pady=20)

        self.login_user_entry = ctk.CTkEntry(
            inner_frame, placeholder_text="Username", width=300, height=40
        )
        self.login_user_entry.pack(pady=10)

        self.login_pass_entry = ctk.CTkEntry(
            inner_frame, placeholder_text="Password", show="*", width=300, height=40
        )
        self.login_pass_entry.pack(pady=10)

        ctk.CTkButton(
            inner_frame, text="Login", width=300, height=40, command=self.perform_login
        ).pack(pady=20)

        ctk.CTkLabel(
            inner_frame, text="Don't have an account?", text_color="gray"
        ).pack(pady=(10, 5))
        ctk.CTkButton(
            inner_frame,
            text="Register Now",
            fg_color="transparent",
            border_width=1,
            command=self.show_register_screen,
        ).pack(pady=5)

    def perform_login(self):
        username = self.login_user_entry.get()
        password = self.login_pass_entry.get()

        if not username or not password:
            messagebox.showwarning(
                "Warning", "Please enter both username and password."
            )
            return

        try:
            # 1. Send LOGIN command
            self.client.send("LOGIN".encode("utf-8"))

            # 2. Wait for Username prompt
            time.sleep(0.1)
            self.client.recv(1024)
            self.client.send(username.encode("utf-8"))

            # 3. Wait for Password prompt
            time.sleep(0.1)
            self.client.recv(1024)
            self.client.send(password.encode("utf-8"))

            # 4. Check Result
            response = self.client.recv(1024).decode("utf-8")

            if "Welcome back" in response:
                self.username = username
                self.show_chat_screen()
            else:
                # Login failed, likely "Login failed! Wrong username..."
                # The server loop resets, so we are back to "Type LOGIN or REGISTER"
                messagebox.showerror("Login Failed", "Invalid username or password.")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {e}")
            self.destroy()

    def perform_logout(self):
        if self.connected:
            try:
                self.client.send("EXIT".encode("utf-8"))
            except:
                pass

        self.connected = False
        try:
            self.client.close()
        except:
            pass

        self.username = ""
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((LOCAL_HOST, PORT))
            self.connected = True
        except ConnectionRefusedError:
            messagebox.showerror("Error", "無法連線到 Server")
            self.destroy()
            return

        try:
            self.user_label.configure(text=f"User: {self.username}")
        except Exception:
            pass

        self.show_login_screen()

    def setup_register_ui(self):
        self.register_frame = ctk.CTkFrame(self, corner_radius=15)

        inner_frame = ctk.CTkFrame(self.register_frame, fg_color="transparent")
        inner_frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner_frame, text="Create Account", font=("Roboto", 30, "bold")
        ).pack(pady=20)

        self.reg_user_entry = ctk.CTkEntry(
            inner_frame, placeholder_text="New Username", width=300, height=40
        )
        self.reg_user_entry.pack(pady=10)

        self.reg_pass_entry = ctk.CTkEntry(
            inner_frame, placeholder_text="New Password", show="*", width=300, height=40
        )
        self.reg_pass_entry.pack(pady=10)

        ctk.CTkButton(
            inner_frame,
            text="Register & Login",
            width=300,
            height=40,
            command=self.perform_register,
        ).pack(pady=20)
        ctk.CTkButton(
            inner_frame,
            text="Back to Login",
            fg_color="gray",
            width=300,
            command=self.show_login_screen,
        ).pack(pady=5)

    def perform_register(self):
        username = self.reg_user_entry.get()
        password = self.reg_pass_entry.get()

        if not username or not password:
            messagebox.showwarning("Warning", "Please fill in all fields.")
            return

        try:
            # 1. Send REGISTER command
            self.client.send("REGISTER".encode("utf-8"))

            # 2. Server: Enter new username
            time.sleep(0.1)
            self.client.recv(1024)
            self.client.send(username.encode("utf-8"))

            # 3. Server: Enter new password
            time.sleep(0.1)
            self.client.recv(1024)
            self.client.send(password.encode("utf-8"))

            # 4. Check Result
            response = self.client.recv(1024).decode("utf-8")

            if "Registration successful" in response:
                messagebox.showinfo("Success", f"Account created! Logging in with {username}.")
                # Auto Login Logic
                # Server sends "Please type 'LOGIN' to continue" then waits for command
                self.login_user_entry.delete(0, "end")
                self.login_user_entry.insert(0, username)
                self.login_pass_entry.delete(0, "end")
                self.login_pass_entry.insert(0, password)
                self.perform_login()  # Call login directly
            else:
                messagebox.showerror("Registration Failed", "Username might be taken.")
                # Server resets loop
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {e}")

    def setup_chat_ui(self):
        self.chat_frame = ctk.CTkFrame(self)
        self.chat_frame.grid_columnconfigure(1, weight=1)
        self.chat_frame.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self.chat_frame, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.btn_logout = ctk.CTkButton(
            self.sidebar_frame,
            text="Logout",
            fg_color="#C0392B",
            hover_color="#E74C3C",
            command=self.perform_logout,
        )
        self.btn_logout.grid(row=5, column=0, padx=20, pady=20, sticky="s")

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TCP Chat", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.user_label = ctk.CTkLabel(self.sidebar_frame, text=f"User: {self.username}", text_color="#1E90FF")
        self.user_label.grid(row=1, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Connected", text_color="#00FF00")
        self.status_label.grid(row=2, column=0, padx=20, pady=10)

        self.info_label = ctk.CTkLabel(self.sidebar_frame, text="Commands:\n/list\n/pm\n/help", text_color="gray")
        self.info_label.grid(row=3, column=0, padx=20, pady=10)

        self.chat_display = ctk.CTkTextbox(self.chat_frame, width=250, font=("Roboto Medium", 14))
        self.chat_display.grid(row=0, column=1, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.chat_display.configure(state="disabled")

        self.input_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")

        self.entry_msg = ctk.CTkEntry(self.input_frame, placeholder_text="Type a message...", height=40)
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_msg.bind("<Return>", self.send_message)

        self.btn_send = ctk.CTkButton(self.input_frame, text="Send", height=40, command=self.send_message)
        self.btn_send.pack(side="right")

        self.btn_file = ctk.CTkButton(
            self.input_frame, 
            text="📂",
            width=40, 
            height=40, 
            fg_color="#555555",
            hover_color="#777777",
            command=self.upload_file
        )
        self.btn_file.pack(side="right", padx=(0, 10))

    def append_message(self, message):
        """將訊息顯示在畫面上，自動換行與捲動"""
        self.chat_display.configure(state="normal")

        time_str = datetime.now().strftime("%H:%M")

        full_msg = f"[{time_str}] {message}\n"

        self.chat_display.insert("end", full_msg)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def receive_messages(self):
        while self.connected:
            try:
                msg = self.client.recv(1024).decode('utf-8')
                if not msg:
                    self.connected = False
                    self.append_message("!!! Disconnected from server !!!")
                    self.client.close()
                    break
                self.append_message(msg)
            except Exception as e:
                print(e)
                self.connected = False
                break

    def send_message(self, event=None):
        msg = self.entry_msg.get()
        if msg:
            try:
                self.client.send(msg.encode('utf-8'))
                self.entry_msg.delete(0, "end")
            except:
                self.connected = False
                self.append_message("!!! Send failed !!!")

    def on_closing(self):
        if self.connected:
            try:
                self.client.send("EXIT".encode('utf-8'))
                self.client.close()
            except:
                pass
        self.destroy()

    def upload_file(self):
        file_path = ctk.filedialog.askopenfilename(
            title="Select a File",
            filetypes=(("All Files", "*.*"),)
        )

        if file_path:
            try:
                file_name = os.path.basename(file_path).replace(" ", "")

                with open(file_path, 'rb') as f:
                    content = f.read()

                self.client.sendall(f"/upload {file_name}".encode('utf-8'))
                self.client.sendall(len(content).to_bytes(8, "big"))
                self.client.sendall(content)
            except Exception as e:
                messagebox.showerror("Error", f"Could not read file: {e}")


if __name__ == "__main__":
    app = ModernChatClient()
    app.mainloop()
