# client.py

import customtkinter as ctk
import socket
import threading
from tkinter import messagebox

HOST = '127.0.0.1'
PORT = 12345

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ChatClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ChatSocket GUI")
        self.geometry("800x600")

        self.client_socket = None
        self.nome = ""
        self.numero = ""
        self.chat_atual = "global"
        self.usuarios_ativos = {}
        self.contatos = {}
        self.historico_mensagens = {}

        self.frames = {}
        self.create_login_frame()

    def create_login_frame(self):
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True)

        label = ctk.CTkLabel(frame, text="Bem-vindo ao Chat", font=ctk.CTkFont(size=20))
        label.pack(pady=10)

        self.nome_entry = ctk.CTkEntry(frame, placeholder_text="Digite seu nome")
        self.nome_entry.pack(pady=5)

        self.numero_entry = ctk.CTkEntry(frame, placeholder_text="Digite seu número")
        self.numero_entry.pack(pady=5)

        login_btn = ctk.CTkButton(frame, text="Entrar", command=self.entrar_chat)
        login_btn.pack(pady=10)

        self.frames['login'] = frame

    def entrar_chat(self):
        nome = self.nome_entry.get().strip()
        numero = self.numero_entry.get().strip()

        if not nome or not numero:
            messagebox.showwarning("Erro", "Preencha nome e número.")
            return

        self.nome = nome
        self.numero = numero

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            self.client_socket.sendall(f"LOGIN|{nome}|{numero}".encode())
            resposta = self.client_socket.recv(1024).decode()

            if resposta.startswith("LOGIN_SUCCESS"):
                self.frames['login'].destroy()
                self.create_main_interface()
                threading.Thread(target=self.receber_mensagens, daemon=True).start()
            else:
                messagebox.showerror("Falha no login", resposta.split("|")[1])
                self.client_socket.close()
                self.client_socket = None
        except Exception as e:
            messagebox.showerror("Erro de conexão", str(e))

    def create_main_interface(self):
        # Layout principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill='both', expand=True)

        # Barra lateral
        sidebar = ctk.CTkFrame(main_frame, width=200)
        sidebar.pack(side='left', fill='y')

        self.lista_chats = ctk.CTkScrollableFrame(sidebar, label_text="Conversas")
        self.lista_chats.pack(fill='both', expand=True, padx=10, pady=10)

        # Adicionar Chat Global
        btn = ctk.CTkButton(self.lista_chats, text="Chat Global", command=lambda: self.trocar_chat("global"))
        btn.pack(pady=2, fill='x')
        self.contatos["global"] = btn

        # Área principal de mensagens
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(fill='both', expand=True)

        self.area_mensagens = ctk.CTkTextbox(right_frame, state='disabled', wrap='word')
        self.area_mensagens.pack(fill='both', expand=True, padx=10, pady=10)

        # Campo de entrada
        entry_frame = ctk.CTkFrame(right_frame)
        entry_frame.pack(fill='x', padx=10, pady=5)

        self.entrada_msg = ctk.CTkEntry(entry_frame)
        self.entrada_msg.pack(side='left', fill='x', expand=True, padx=(0, 10))

        enviar_btn = ctk.CTkButton(entry_frame, text="Enviar", command=self.enviar_mensagem)
        enviar_btn.pack(side='right')

        self.frames['main'] = main_frame

    def trocar_chat(self, chat_id):
        self.chat_atual = chat_id
        self.area_mensagens.configure(state='normal')
        self.area_mensagens.delete("1.0", "end")

        if chat_id == "global":
            self.area_mensagens.insert("end", "Você está no chat global.\n")
        else:
            nome = self.usuarios_ativos.get(chat_id, "Desconhecido")
            self.area_mensagens.insert("end", f"Você está conversando com {nome} ({chat_id}).\n")

        if chat_id not in self.historico_mensagens:
            self.historico_mensagens[chat_id] = []

        for linha in self.historico_mensagens[chat_id]:
            self.area_mensagens.insert("end", linha)

        self.area_mensagens.configure(state='disabled')

    def enviar_mensagem(self):
        msg = self.entrada_msg.get().strip()
        if not msg:
            return

        if self.chat_atual == "global":
            self.client_socket.sendall(f"MSG_GLOBAL|{msg}".encode())
        else:
            self.client_socket.sendall(f"MSG_PRIV|{self.chat_atual}|{msg}".encode())

        self.entrada_msg.delete(0, 'end')

    def adicionar_contato(self, numero, nome):
        if numero not in self.contatos:
            btn = ctk.CTkButton(self.lista_chats, text=f"{nome} ({numero})", command=lambda: self.trocar_chat(numero))
            btn.pack(pady=2, fill='x')
            self.contatos[numero] = btn
            self.usuarios_ativos[numero] = nome

    def receber_mensagens(self):
        while True:
            try:
                dados = self.client_socket.recv(4096).decode()
                if not dados:
                    break

                if dados.startswith("MSG_GLOBAL|"):
                    _, remetente, msg = dados.split("|", 2)
                    self.area_mensagens.configure(state='normal')
                    self.area_mensagens.insert("end", f"[Global] {remetente}: {msg}\n")
                    self.area_mensagens.configure(state='disabled')
                    self.historico_mensagens.setdefault("global", []).append(f"[Global] {remetente}: {msg}\n")
                elif dados.startswith("MSG_PRIV|"):
                    _, numero_remetente, nome_remetente, msg = dados.split("|", 3)
                    self.adicionar_contato(numero_remetente, nome_remetente)
                    self.historico_mensagens.setdefault(numero_remetente, []).append(f"[Privado] {nome_remetente}: {msg}\n")
                    if self.chat_atual == numero_remetente:
                        self.area_mensagens.configure(state='normal')
                        self.area_mensagens.insert("end", f"[Privado] {nome_remetente}: {msg}\n")
                        self.area_mensagens.configure(state='disabled')

                elif dados.startswith("NOTIFY|"):
                    _, texto = dados.split("|", 1)
                    self.area_mensagens.configure(state='normal')
                    self.area_mensagens.insert("end", f"* {texto}\n")
                    self.area_mensagens.configure(state='disabled')

                elif dados.startswith("LIST_USERS|"):
                    _, lista = dados.split("|", 1)
                    for item in lista.split(";"):
                        if not item:
                            continue
                        numero, nome = item.split(",")
                        if numero != self.numero:
                            self.adicionar_contato(numero, nome)

            except Exception as e:
                print("Erro ao receber:", e)
                break

        self.client_socket.close()

if __name__ == "__main__":
    app = ChatClient()
    app.mainloop()
