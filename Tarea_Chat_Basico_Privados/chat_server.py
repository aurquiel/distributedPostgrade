#Chat server side
import socket
import threading

class ChatServer:

    def __init__(self, host_ip=socket.gethostbyname(socket.gethostname()), host_port=12345):
        self.clients_sockets_list= []
        self.clients_names_list= []
        self.clients_lock = threading.Lock()
        self.server_socket = None

        self.HOST_IP = host_ip
        self.HOST_PORT = host_port
        self.ENCODER = "utf-8"
        self.BUFFER_SIZE = 1024

    def startSocketServer(self):
        try:
            #Create a server side socket using IPV4 (AF_INET) and TCP (SOCK_STREAM) protocols
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            #Bind the socket to the defined IP and port
            
            self.server_socket.bind((self.HOST_IP, self.HOST_PORT))
            
            #Listen for incoming connections
            self.server_socket.listen(10) 
            print(f"Server listening on {self.HOST_IP}:{self.HOST_PORT}")
            
        except Exception as ex:
            print(f"Socket error: {ex}")
            if self.server_socket:
                self.server_socket.close()
            self.server_socket = None
            return
        
    def is_private_message(self, message):
        return message.startswith("\\w");

    def send_private_message(self, from_client, to_client, message):
        with self.clients_lock:
            if to_client in self.clients_names_list:
                to_index = self.clients_names_list.index(to_client)
                to_socket = self.clients_sockets_list[to_index]
            else:
                to_index = None
                to_socket = None

            if from_client in self.clients_names_list:
                from_index = self.clients_names_list.index(from_client)
                from_socket = self.clients_sockets_list[from_index]
            else:
                from_index = None
                from_socket = None

        if to_socket:
            private_message = f"priv({from_client}): {message}"
            try:
                to_socket.send(private_message.encode(self.ENCODER))
                print(f"Private message from '{from_client}' to '{to_client}': {message}")
            except Exception as ex:
                print(f"Socket error: {ex}")
        elif from_socket:
            error_message = f"User '{to_client}' not found."
            try:
                from_socket.send(error_message.encode(self.ENCODER))
                print(f"Private message error: User '{to_client}' not found for '{from_client}'")
            except Exception as ex:
                print(f"Socket error: {ex}")
        
    
    def broadcast_message(self, message):
        with self.clients_lock:
            sockets_snapshot = list(self.clients_sockets_list)
        for client_socket in sockets_snapshot:
            try:
                client_socket.send(message.encode(self.ENCODER))
            except Exception as ex:
                print(f"Socket error: {ex}")
                with self.clients_lock:
                    if client_socket in self.clients_sockets_list:
                        client_index = self.clients_sockets_list.index(client_socket)
                        client_name = self.clients_names_list[client_index]
                        self.clients_sockets_list.remove(client_socket)
                        self.clients_names_list.remove(client_name)
                client_socket.close()
                self.broadcast_message(f"{client_name} has left the chat.\n")

    def recieve_message(self, client_socket):
        while True:
            try:
                message = client_socket.recv(self.BUFFER_SIZE).decode(self.ENCODER)
                if message == "QUIT":
                    with self.clients_lock:
                        client_index = self.clients_sockets_list.index(client_socket)
                        client_name = self.clients_names_list[client_index]
                        self.clients_sockets_list.remove(client_socket)
                        self.clients_names_list.remove(client_name)
                    client_socket.close()
                    self.broadcast_message(f"{client_name} has left the chat.\n")
                elif self.is_private_message(message):
                    parts = message.split(' ', 2)
                    if len(parts) >= 3:
                        to_client = parts[1]
                        private_message = parts[2]
                        with self.clients_lock:
                            client_index = self.clients_sockets_list.index(client_socket)
                            from_client = self.clients_names_list[client_index]
                        self.send_private_message(from_client, to_client, private_message)
                else:
                    with self.clients_lock:
                        client_index = self.clients_sockets_list.index(client_socket)
                        client_name = self.clients_names_list[client_index]
                    full_message = f"{client_name}: {message}"
                    print(full_message)
                    self.broadcast_message(full_message)
            except Exception as ex:
                print(f"Socket error: {ex}")
                with self.clients_lock:
                    if client_socket in self.clients_sockets_list:
                        client_index = self.clients_sockets_list.index(client_socket)
                        client_name = self.clients_names_list[client_index]
                        self.clients_sockets_list.remove(client_socket)
                        self.clients_names_list.remove(client_name)
                    else:
                        client_name = "Unknown"
                client_socket.close()
                self.broadcast_message(f"{client_name} has left the chat.\n")
                break

    def connect_client(self):
       while True:
            #Accept an incoming connection
            client_socket, client_address = self.server_socket.accept()
            print(f"Connection established with {client_address}...")

            #Send a NAME flag t promot the client to send their name
            name_flag = "NAME"
            client_socket.send(name_flag.encode(self.ENCODER))
            client_name = client_socket.recv(self.BUFFER_SIZE).decode(self.ENCODER)

            #Add new client socket and name to respective lists
            with self.clients_lock:
                self.clients_sockets_list.append(client_socket)
                self.clients_names_list.append(client_name)

            #Update the server, indiviudal client, and all other clients about the new connection
            print(f"Client '{client_name}' connected\n.")
            welcome_message = f"Welcome to the chat, {client_name}°\n"
            client_socket.send(welcome_message.encode(self.ENCODER))
            self.broadcast_message(f"{client_name} has joined the chat.\n")

            recieve_message_thread = threading.Thread(target=self.recieve_message, args=(client_socket,))
            recieve_message_thread.start()

    def close(self):
        if self.server_socket:
            self.server_socket.close()
            print("Server socket closed.")

if __name__ == "__main__":
    chat_server = ChatServer()
    chat_server.startSocketServer()
    try:
        chat_server.connect_client()
    finally:
        chat_server.close()