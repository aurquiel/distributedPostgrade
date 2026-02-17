import socket
import threading

class Connection:
    def __init__(self, MAX_PLAYERS, HOST_PORT=12345):
        self.HOST_IP = socket.gethostbyname(socket.gethostname())
        self.PORT = HOST_PORT
        self.ENCODER = "utf-8"
        self.server_socket = None
        self.players_lock = threading.Lock()
        self.player_sockets = [] # lista de sockets de los clientes conectados para enviar mensajes a todos los clientes
        self.player_names = [] #numbre unico de los clientes uuid
        self.commands = [] # lista de comandos recibidos del cliente para ser procesados por el juego
        self.commands_lock = threading.Lock()
        self.MAX_PLAYERS = MAX_PLAYERS

    def _drop_player(self, player_socket, reason=""):
        """Remove player safely and emit disconnect command."""
        try:
            player_name = self.get_player_name_by_socket(player_socket)
        except Exception:
            player_name = None

        self.remove_player_socket_and_name(player_socket, player_name)
        try:
            player_socket.close()
        except Exception:
            pass

        if player_name:
            self.commands_add(f"\\i {reason}" if reason else f"\\i Jugador '{player_name}' desconectado.")
            self.commands_add(f"\\u {player_name}")
        elif reason:
            self.commands_add(f"\\i {reason}")

    def commands_add(self, command):
        with self.commands_lock:
            self.commands.append(command)
    
    def commands_consume(self):
        with self.commands_lock:
            if self.commands:
                return self.commands.pop(0) # lamport no importa mucho en blackjack porque es el turno del jugador y los otros no pueden realizar acciones hasta su turno.
            else:
                return None
    
    def add_player_socket_and_name(self, player_socket, player_name):
        with self.players_lock:
            self.player_sockets.append(player_socket)
            self.player_names.append(player_name)

    def remove_player_socket_and_name(self, player_socket, player_name):
        with self.players_lock:
            if player_socket in self.player_sockets:
                self.player_sockets.remove(player_socket)
            if player_name in self.player_names:
                self.player_names.remove(player_name)

    def get_sockets_for_broadcast_message(self):
        with self.players_lock:
            return list(self.player_sockets)
        
    def get_player_socket_by_name(self, player_name):
        with self.players_lock:
            if player_name in self.player_names:
                index = self.player_names.index(player_name)
                return self.player_sockets[index]
            else:
                return None
            
    def get_player_name_by_socket(self, player_socket):
        with self.players_lock:
            if player_socket in self.player_sockets:
                index = self.player_sockets.index(player_socket)
                return self.player_names[index]
            else:
                return None

    def start_server(self, port):
        try:    
            self.PORT = port
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.HOST_IP, self.PORT))
            self.server_socket.listen(self.MAX_PLAYERS)
            self.commands_add(f"\\i Servidor escuchando en {self.HOST_IP}:{self.PORT}")
            recieve_message_thread = threading.Thread(target=self.connect_client, daemon=True)
            recieve_message_thread.start()
            return True
        except Exception as ex:
            self.commands_add(f"\\i Error al iniciar servidor: {ex}")
            if self.server_socket:
                self.server_socket.close()
            return False

    def connect_client(self):
       while True:
            #Accept an incoming connection
            player_socket, player_address = self.server_socket.accept()
            self.commands_add(f"\\i Conexión establecida con {player_address}...")

            if len(self.player_sockets) >= self.MAX_PLAYERS:
                self.commands_add(f"\\i Conexión rechazada desde {player_address}: el servidor está lleno.")
                player_socket.send("\\f".encode(self.ENCODER))
                player_socket.close()
                continue
        
            #Receive the client's name
            header = player_socket.recv(10)
            message = player_socket.recv(int(header.decode(self.ENCODER))).decode(self.ENCODER)

            if message.startswith("\\n"):   
                player_name = message.split()[1] # se elimina el caracter de nueva linea para obtener el nombre real del cliente
                self.add_player_socket_and_name(player_socket, player_name)

                #Update the server, indiviudal client, and all other clients about the new connection
                self.commands_add(f"\\n {player_name}")
                self.commands_add(f"\\i Jugador '{player_name}' conectado\n.")
                
                recieve_message_thread = threading.Thread(target=self.recieve_message, args=(player_socket,))
                recieve_message_thread.start()

    def send_message_to_player(self, player_socket, message):
        if player_socket is None:
            self.commands_add("\\i No se pudo enviar mensaje: socket inexistente.")
            return
        try:
            header = str(len(message))
            while(len(header) < 10):
                header += " "
            player_socket.send(header.encode(self.ENCODER))
            player_socket.send(message.encode(self.ENCODER))
        except Exception as e:
            self.commands_add(f"\\i Error al enviar mensaje al jugador: {e}")
            self._drop_player(player_socket, reason="Error de envío; jugador desconectado")


    def recieve_message(self, player_socket):
        while True:
            try:
                header = player_socket.recv(10)
                command = player_socket.recv(int(header.decode(self.ENCODER)))
                self.commands_add(command.decode(self.ENCODER)) # se reciben los comandos del servidor y se guardan en una lista para ser procesados por el cliente
            except Exception as ex:
                self.commands_add(f"\\i Error de socket: {ex}")
                self._drop_player(player_socket, reason="Error de socket; jugador desconectado")
                break

    def broadcast_message(self, message):
        for player_socket in self.get_sockets_for_broadcast_message():
            try:
                header = str(len(message))
                while(len(header) < 10):
                    header += " "
                player_socket.send(header.encode(self.ENCODER))
                player_socket.send(message.encode(self.ENCODER))
            except Exception as ex:
                self.commands_add(f"\\i Error de socket: {ex}")
                self._drop_player(player_socket, reason="Error al difundir; jugador desconectado")
    
    def get_host_ip(self):
        return self.HOST_IP
    
    def get_host_port(self):
        return self.PORT
