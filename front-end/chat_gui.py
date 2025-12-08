import socket
import threading
import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

LOCAL_HOST = '127.0.0.1'
PORT = 5000

ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

class ModernChatClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Chat Room")
        self.geometry("800x600")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        try:
            self.client.connect((LOCAL_HOST, PORT))
            self.connected = True
        except ConnectionRefusedError:
            messagebox.showerror("Error", "無法連線到 Server")
            self.destroy()
            return

        self.setup_ui()

        recv_thread = threading.Thread(target=self.receive_messages)
        recv_thread.daemon = True
        recv_thread.start()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="TCP Chat", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Connected", text_color="#00FF00")
        self.status_label.grid(row=1, column=0, padx=20, pady=10)
        
        self.info_label = ctk.CTkLabel(self.sidebar_frame, text="Commands:\nLOGIN\nREGISTER", text_color="gray")
        self.info_label.grid(row=2, column=0, padx=20, pady=10)

        self.chat_display = ctk.CTkTextbox(self, width=250, font=("Roboto Medium", 14))
        self.chat_display.grid(row=0, column=1, padx=(20, 20), pady=(20, 0), sticky="nsew")
        self.chat_display.configure(state="disabled")

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        
        self.entry_msg = ctk.CTkEntry(self.input_frame, placeholder_text="Type a message...", height=40)
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry_msg.bind("<Return>", self.send_message)

        self.btn_send = ctk.CTkButton(self.input_frame, text="Send", height=40, command=self.send_message)
        self.btn_send.pack(side="right")

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
            except:
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

if __name__ == "__main__":
    app = ModernChatClient()
    app.mainloop()