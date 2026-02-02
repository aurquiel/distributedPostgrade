#Chat client side
import socket
import threading

class ChatClient:

    def __init__(self, host_ip, host_port=12345):
        self.client_socket = None  
        self.client_name = None  

        self.HOST_IP = host_ip
        self.HOST_PORT = host_port
        self.ENCODER = "utf-8"
        self.BUFFER_SIZE = 1024

        
    def start(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.HOST_IP, self.HOST_PORT))

            # Handshake de nombre antes de lanzar hilos
            first_msg = self.client_socket.recv(self.BUFFER_SIZE).decode(self.ENCODER)
            if first_msg == "NAME":
                self.client_name = input("Enter your name: ")
                self.client_socket.send(self.client_name.encode(self.ENCODER))

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

    def send_message(self):
        while True:
            message = input()
            try:
                self.client_socket.send(message.encode(self.ENCODER))
            except Exception as ex:
                print(f"Socket error: {ex}")
                if self.client_socket:
                    self.client_socket.close()
                break

    def recieve_message(self):
         while True:
            try:
                data = self.client_socket.recv(self.BUFFER_SIZE)
                if not data:
                    print("Servidor cerró la conexión.")
                    break
                message = data.decode(self.ENCODER)
                if message != "NAME":  # ya manejado en start()
                    print(message)
            except Exception as ex:
                print(f"Socket error: {ex}")
                if self.client_socket:
                    self.client_socket.close()
                break

if __name__ == "__main__":
    host_ip = input("Enter server IP address: ")
    host_port = int(input("Enter server port: "))
    chat_client = ChatClient(host_ip, host_port)
    chat_client.start()            