import socket
import uuid
import threading

class Connection:
    def __init__(self):
        self.HOST_IP = ""
        self.PORT = 0
        self.ENCODER = "utf-8"
        self.client_socket = None
        self.commands = []

    def server_settings(self, host_ip, port):
        self.HOST_IP = host_ip
        self.PORT = port
        self.PLAYER_NAME = str(uuid.uuid4()) #nombre unico del cliente

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
                self.commands.append(command.decode(self.ENCODER)) # se reciben los comandos del servidor y se guardan en una lista para ser procesados por el cliente
            except Exception as ex:
                print(f"Socket error: {ex}")
                if self.client_socket:
                    self.client_socket.close()
                break

    def start(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.HOST_IP, self.HOST_PORT))

            self.send_message(self, f"\\n {self.PLAYER_NAME}")
            self.recieve_message() # se espera a recibir un mensaje del servidor para confirmar la conexion

            recieve_thread = threading.Thread(target=self.recieve_message, daemon=True)
            send_thread = threading.Thread(target=self.send_message, daemon=True)
            recieve_thread.start()
            send_thread.start()

            recieve_thread.join()
            send_thread.join()

        except Exception as ex:
            print(f"Socket error: {ex}")
            if self.client_socket:
                self.client_socket.close()
            return


    