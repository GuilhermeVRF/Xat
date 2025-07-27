# server.py

import socket
import threading
from datetime import datetime

# Usuários ativos: {numero: {...}}
usuarios_ativos = {}

# Lock para acesso concorrente ao dict de usuários
usuarios_lock = threading.Lock()

# Funções utilitárias
def timestamp():
    return datetime.now().strftime('%H:%M:%S')

def enviar(socket_cliente, mensagem):
    try:
        socket_cliente.sendall(mensagem.encode())
    except:
        pass  # Cliente pode estar desconectado

# Broadcast para todos (menos quem enviou)
def broadcast(mensagem, ignorar_numero=None):
    with usuarios_lock:
        for numero, usuario in usuarios_ativos.items():
            if numero != ignorar_numero:
                enviar(usuario['socket'], mensagem)

# Envia lista de usuários ativos
def enviar_lista_usuarios(socket_cliente):
    with usuarios_lock:
        dados = [f"{nro},{info['nome']}" for nro, info in usuarios_ativos.items()]
        enviar(socket_cliente, f"LIST_USERS|{';'.join(dados)}")

# Thread que trata cada cliente
def tratar_cliente(socket_cliente, endereco):
    try:
        # Receber login
        dados = socket_cliente.recv(1024).decode()
        if not dados.startswith("LOGIN|"):
            enviar(socket_cliente, "LOGIN_FAIL|Formato inválido")
            socket_cliente.close()
            return

        _, nome, numero = dados.strip().split("|")

        with usuarios_lock:
            if numero in usuarios_ativos:
                enviar(socket_cliente, "LOGIN_FAIL|Número já está em uso")
                socket_cliente.close()
                return

            usuarios_ativos[numero] = {
                'nome': nome,
                'socket': socket_cliente,
                'thread': threading.current_thread(),
                'historico_global': [],
                'historico_privado': {}
            }

        enviar(socket_cliente, f"LOGIN_SUCCESS|Bem-vindo, {nome}!")
        broadcast(f"NOTIFY|{nome} entrou no chat", ignorar_numero=numero)
        enviar_lista_usuarios(socket_cliente)

        print(f"[{timestamp()}] {nome} ({numero}) conectado de {endereco}")

        # Loop principal de recebimento
        while True:
            mensagem = socket_cliente.recv(2048).decode()
            if not mensagem:
                break

            if mensagem.startswith("MSG_GLOBAL|"):
                texto = mensagem.split("|", 1)[1]
                log = f"{timestamp()} - {nome}: {texto}"
                print("[GLOB]", log)

                # Armazena no histórico
                with usuarios_lock:
                    usuarios_ativos[numero]['historico_global'].append((nome, texto, timestamp()))

                broadcast(f"MSG_GLOBAL|{nome}|{texto}", ignorar_numero=None)

            elif mensagem.startswith("MSG_PRIV|"):
                try:
                    _, destino, texto = mensagem.split("|", 2)
                except:
                    enviar(socket_cliente, "NOTIFY|Erro no envio da mensagem privada.")
                    continue

                with usuarios_lock:
                    if destino not in usuarios_ativos:
                        enviar(socket_cliente, f"NOTIFY|Usuário {destino} não encontrado.")
                        continue

                    destinatario = usuarios_ativos[destino]
                    remetente_nome = usuarios_ativos[numero]['nome']

                    # Armazena nos históricos
                    usuarios_ativos[numero]['historico_privado'].setdefault(destino, []).append((remetente_nome, texto, timestamp()))
                    usuarios_ativos[destino]['historico_privado'].setdefault(numero, []).append((remetente_nome, texto, timestamp()))

                    enviar(destinatario['socket'], f"MSG_PRIV|{numero}|{remetente_nome}|{texto}")
                    enviar(socket_cliente, f"MSG_PRIV|{destino}|{remetente_nome}|{texto}")

            elif mensagem.startswith("CMD_LIST_USERS"):
                enviar_lista_usuarios(socket_cliente)

            elif mensagem.startswith("CMD_LIST_CONTACTS"):
                with usuarios_lock:
                    contatos = usuarios_ativos[numero]['historico_privado'].keys()
                    contatos_info = [
                        f"{nro},{usuarios_ativos[nro]['nome']}"
                        for nro in contatos if nro in usuarios_ativos
                    ]
                    enviar(socket_cliente, f"LIST_CONTACTS|{';'.join(contatos_info)}")

            else:
                enviar(socket_cliente, "NOTIFY|Comando não reconhecido.")

    except Exception as e:
        print(f"[ERRO] Cliente {endereco} causou exceção: {e}")

    finally:
        with usuarios_lock:
            usuario = usuarios_ativos.pop(numero, None)
            if usuario:
                broadcast(f"NOTIFY|{usuario['nome']} saiu do chat", ignorar_numero=numero)
                print(f"[{timestamp()}] {usuario['nome']} ({numero}) desconectado")

        socket_cliente.close()

def iniciar_servidor(host='0.0.0.0', porta=12345):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind((host, porta))
    servidor.listen()

    print(f"Servidor iniciado em {host}:{porta}")

    while True:
        cliente_socket, endereco = servidor.accept()
        thread = threading.Thread(target=tratar_cliente, args=(cliente_socket, endereco))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    iniciar_servidor()

