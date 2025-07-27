import customtkinter as ctk
import socket
import threading
from tkinter import messagebox

HOST = '127.0.0.1'
PORT = 12345

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ChatClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("xat.jg")
        self.geometry("850x650")

        self.client_socket = None
        self.nome = ""
        self.numero = ""
        self.chat_atual = "global"
        self.usuarios_ativos = {}
        self.contatos = {}
        self.historico_mensagens = {"global": []} #TODO 

        self.smilies = {
            '😀': ':)', '😂': ':D', '😉': ';)', '😢': ':(', '😎': '8)',
            '❤️': '<3', '👍': '(y)', '😡': '>:(', '😱': ':o'
        }

        self.frames = {}
        self.create_login_frame()

    def create_login_frame(self):
        frame = ctk.CTkFrame(self)
        frame.pack(expand=True)

        label = ctk.CTkLabel(frame, text="Bem-vindo ao xat.jg", font=ctk.CTkFont(size=24, weight="bold"))
        label.pack(pady=20, padx=50)

        self.nome_entry = ctk.CTkEntry(frame, placeholder_text="Digite seu nome", width=250)
        self.nome_entry.pack(pady=10)

        self.numero_entry = ctk.CTkEntry(frame, placeholder_text="Digite seu número (ID)", width=250)
        self.numero_entry.pack(pady=10)

        login_btn = ctk.CTkButton(frame, text="Entrar no xat", command=self.entrar_chat, height=40)
        login_btn.pack(pady=20)

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
            messagebox.showerror("Erro de conexão", f"Não foi possível conectar ao servidor.\nVerifique se o servidor está rodando.\n\nDetalhes: {e}")

    def create_main_interface(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)


        left_container = ctk.CTkFrame(self, fg_color="transparent")
        left_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_container.grid_rowconfigure(0, weight=1)
        left_container.grid_columnconfigure(0, weight=1)

        self.area_mensagens = ctk.CTkTextbox(
            left_container, state='disabled', wrap='word',
            font=("Consolas", 14), border_spacing=5
        )
        self.area_mensagens.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        smiley_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        smiley_frame.grid(row=1, column=0, sticky="ew", pady=5)

        for i, (smiley, code) in enumerate(self.smilies.items()):
            btn = ctk.CTkButton(
                smiley_frame, text=smiley, width=40,
                command=lambda s=code: self.inserir_smiley(s),
                font=("Arial", 16)
            )
            btn.pack(side="left", padx=2)

        entry_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        entry_frame.grid(row=2, column=0, sticky="ew")

        self.entrada_msg = ctk.CTkEntry(entry_frame, placeholder_text="Digite sua mensagem...", font=("Arial", 14))
        self.entrada_msg.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.entrada_msg.bind("<Return>", self.enviar_mensagem)

        enviar_btn = ctk.CTkButton(entry_frame, text="Enviar", command=self.enviar_mensagem, width=100)
        enviar_btn.pack(side='right')

        sidebar = ctk.CTkFrame(self, width=200)
        sidebar.grid(row=0, column=1, sticky="nswe", pady=10, padx=(0, 10))

        sidebar_label = ctk.CTkLabel(sidebar, text="Usuários", font=ctk.CTkFont(size=16, weight="bold"))
        sidebar_label.pack(pady=10)

        self.lista_chats = ctk.CTkScrollableFrame(sidebar, label_text="")
        self.lista_chats.pack(fill='both', expand=True, padx=5, pady=5)

        self.label_nome = ctk.CTkLabel(self.lista_chats, text=f"⭐ {self.nome} (Você)", font=ctk.CTkFont(size=13, weight="bold"))
        self.label_nome.pack(pady=(5, 10), fill='x')

        btn = ctk.CTkButton(self.lista_chats, text="🌐 Chat Global", command=lambda: self.trocar_chat("global"))
        btn.pack(pady=2, fill='x')
        self.contatos["global"] = btn

        self.trocar_chat("global")

    def inserir_smiley(self, smiley_code):
        self.entrada_msg.insert('end', f" {smiley_code} ")
        self.entrada_msg.focus()

    def trocar_chat(self, chat_id):
        self.chat_atual = chat_id
        self.area_mensagens.configure(state='normal')
        self.area_mensagens.delete("1.0", "end")

        if chat_id == "global":
            self.title(f"xat.jg - Chat Global")
        else:
            nome = self.usuarios_ativos.get(chat_id, "Desconhecido")
            self.title(f"xat.jg - Conversando com {nome}")

        if chat_id not in self.historico_mensagens:
            self.historico_mensagens[chat_id] = []

        for linha in self.historico_mensagens[chat_id]:
            self.area_mensagens.insert("end", linha)

        self.area_mensagens.yview_moveto(1.0)
        self.area_mensagens.configure(state='disabled')

    def enviar_mensagem(self, event=None):
        msg = self.entrada_msg.get().strip()
        if not msg:
            return

        for smiley, code in self.smilies.items():
            msg = msg.replace(code, smiley)

        if self.chat_atual == "global":
            self.client_socket.sendall(f"MSG_GLOBAL|{msg}".encode())
        else:
            self.client_socket.sendall(f"MSG_PRIV|{self.chat_atual}|{msg}".encode())

        self.entrada_msg.delete(0, 'end')

    def adicionar_contato(self, numero, nome):
        if numero not in self.contatos:
            btn = ctk.CTkButton(self.lista_chats, text=f"👤 {nome} ({numero})", command=lambda num=numero: self.trocar_chat(num))
            btn.pack(pady=2, fill='x')
            self.contatos[numero] = btn
            self.usuarios_ativos[numero] = nome

    def adicionar_linha_mensagem(self, linha, chat_id_msg): #TODO
        if self.chat_atual == chat_id_msg:
            self.area_mensagens.configure(state='normal')
            self.area_mensagens.insert("end", linha)
            self.area_mensagens.yview_moveto(1.0)
            self.area_mensagens.configure(state='disabled')

    def receber_mensagens(self):
        while True:
            try:
                dados = self.client_socket.recv(4096).decode()
                if not dados:
                    break

                partes = dados.split("|")
                comando = partes[0]

                if comando == "MSG_GLOBAL":
                    remetente, msg = partes[1], partes[2]
                    linha = f"<{remetente}> {msg}\n"
                    self.historico_mensagens.setdefault("global", []).append(linha)
                    self.adicionar_linha_mensagem(linha, "global")

                elif comando == "MSG_PRIV":
                    num_remetente, nome_remetente, msg = partes[1], partes[2], partes[3]
                    self.adicionar_contato(num_remetente, nome_remetente)
                    linha = f"[Privado] <{nome_remetente}> {msg}\n"
                    self.historico_mensagens.setdefault(num_remetente, []).append(linha)
                    self.adicionar_linha_mensagem(linha, num_remetente)

                elif comando == "NOTIFY":
                    texto = partes[1]
                    linha = f"*** {texto} ***\n"
                    self.historico_mensagens["global"].append(linha)
                    self.adicionar_linha_mensagem(linha, "global")

                elif comando == "LIST_USERS":
                    lista = partes[1]
                    for item in lista.split(";"):
                        if not item: continue
                        numero, nome = item.split(",")
                        if numero != self.numero:
                            self.adicionar_contato(numero, nome)
            except Exception as e:
                print("Erro ao receber:", e)
                break

        messagebox.showerror("Conexão perdida", "A conexão com o servidor foi perdida.")
        self.client_socket.close()

if __name__ == "__main__":
    app = ChatClient()
    app.mainloop()