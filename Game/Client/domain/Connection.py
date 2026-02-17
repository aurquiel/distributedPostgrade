import socket
import uuid
import threading

class Connection:
    def __init__(self, HOST_IP, HOST_PORT):
        self.HOST_IP = HOST_IP
        self.HOST_PORT = HOST_PORT
        self.ENCODER = "utf-8"
        self.client_socket = None
        self.commands = []
        self.commands_lock = threading.Lock()
        self.unique_name = str(uuid.uuid4()) #nombre unico del cliente

    def commands_add(self, command):
        with self.commands_lock:
            self.commands.append(command)
    
    def commands_consume(self):
        with self.commands_lock:
            if self.commands:
                return self.commands.pop(0) # lamport no importa mucho en blackjack porque es el turno del jugador y los otros no pueden realizar acciones hasta su turno.
            else:
                return None

    def set_host_ip(self, host_ip):
        self.HOST_IP = host_ip

    def set_host_port(self, host_port):
        self.HOST_PORT = host_port

    def send_message(self, message):
        try:
            header = str(len(message))
            while(len(header) < 10):
                header += " "
            self.client_socket.send(header.encode(self.ENCODER))
            self.client_socket.send(message.encode(self.ENCODER))
        except Exception as e:
            print(f"Error sending message: {e}")

    def recieve_message(self):
         while True:
            try:
                header = self.client_socket.recv(10)
                command = self.client_socket.recv(int(header.decode(self.ENCODER)))
                self.commands_add(command.decode(self.ENCODER)) # se reciben los comandos del servidor y se guardan en una lista para ser procesados por el cliente
            except Exception as ex:
                print(f"Socket error: {ex}")
                if self.client_socket:
                    self.client_socket.close()
                    self.commands_add(f"\\u {self.unique_name}.")
                break

    def start_connect_client(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.HOST_IP, int(self.HOST_PORT)))

            self.commands_add(f"\\y {self.unique_name}") # se agrega un mensaje a la lista de comandos para ser proceso en el cliente
            self.send_message(f"\\n {self.unique_name}") # se envia un mensaje al servidor con el nombre unico del cliente para que el servidor lo registre como un nuevo jugador
            recieve_thread = threading.Thread(target=self.recieve_message, daemon=True)
            recieve_thread.start()
        except Exception as ex:
            print(f"Socket error: {ex}")
            if self.client_socket:
                self.client_socket.close()
                self.commands_add(f"\\u {self.unique_name}.")
            return


    