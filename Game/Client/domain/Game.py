import threading
import time
from .Player import Player 

class Game:
    def __init__(self, connection, MAX_PLAYERS):
        self.players = []
        self.connection = connection
        self.MAX_PLAYERS = MAX_PLAYERS

        #Variables del juego
        self.acepted_in_game = False
        self.need_to_draw = False
        self.server_full = False
        self.is_my_turn = False
        self.not_engough_balance = False
        self.lose_game = False
        self.win_game = False
        self.tide_game = False
        self.gameready = False
        self.cards_on_table = []
        self.server_value = 0
        self.lost_connection = False
        self.connection_error = False
        self.error_message = ""
        self.info_message = ""
        self.blocked_from_rejoin = False

    def set_host_ip(self, host_ip):
        self.connection.set_host_ip(host_ip)

    def set_host_port(self, host_port):
        self.connection.set_host_port(host_port)

    def start_game(self):
        # Resetear estados de error previos para reintentos de conexión.
        self.connection_error = False
        self.lost_connection = False
        self.error_message = ""
        self.info_message = ""
        self.server_full = False
        self.acepted_in_game = False
        self.blocked_from_rejoin = False
        self.reset_game_data()

        process_command_thread = threading.Thread(target=self.process_command, daemon=True)
        process_command_thread.start()

        self.connection.start_connect_client()


    def process_command(self):
        while True:
            #Consumir mensajes de la cola de comandos del servidor y procesarlos
            command = self.connection.commands_consume()

            if command is None: #no hay comandos para procesar
                continue
            elif command.startswith("\\n"): #jugador pide unirse al juego
                player_names = command.split(" ")[1:] # se obtiene los nombre de todos los jugadores
                
                for player_name in player_names:
                    self.add_player(player_name)
                
                self.server_full = False
                
                if player_name == self.connection.unique_name:
                    self.acepted_in_game = True
                self.need_to_draw = True

                if len(self.players) == self.MAX_PLAYERS:
                    self.server_full = True
                    self.gameready = True
                    self.need_to_draw = True

            elif command.startswith("\\f"): #recibe el servidor esta lleno
                self.acepted_in_game = False
                self.server_full = True
                self.need_to_draw = True
                self.error_message = "Servidor Full"
                self.connection_error = False

            elif command.startswith("\\k"): #dar dos cartas a un jugador
                array_command = command.split(" ")
                player_name = array_command[1] # se obtiene el nombre del jugador del comando es unico un uuid
                card1 = array_command[2]
                card2 = array_command[3]
                for player in self.players:
                    if player.name == player_name:
                        player.receive_card(card1)
                        player.receive_card(card2)
                        break
                self.need_to_draw = True

            elif command.startswith("\\y"):
                # señal de que la partida está activa
                self.gameready = True
                self.need_to_draw = True

            elif command.startswith("\\x"): #indica que es el turno de un jugador
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                for player in self.players:
                    if player.name == player_name:
                        player.set_has_turn(True)
                        if player.name == self.connection.unique_name and not self.lose_game: # se verifica que el jugador que tiene el turno activo es el cliente actual y que el cliente no ha perdido la ronda para activar su turno en el cliente
                            self.is_my_turn = True
                        elif player.name == self.connection.unique_name and self.lose_game: # si el cliente actual tiene el turno activo pero ha perdido la ronda se le indica que su turno ha finalizado para evitar que pueda realizar acciones en su turno
                            self.connection.send_message(f"\\z {self.connection.unique_name}") # pierde turno 
                            self.is_my_turn = False
                        break
                self.need_to_draw = True

            elif command.startswith("\\z"): #indica que un jugador termino turno
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                for player in self.players:
                    if player.name == player_name:
                        player.set_has_turn(False)
                        if player.name == self.connection.unique_name:
                            self.is_my_turn = False
                            # limpiar mensaje de saldo insuficiente al cerrar turno
                            self.info_message = ""
                        break
                self.need_to_draw = True

            elif command.startswith("\\m"): #indica carga de monto al balance del jugador no la apuesta
                array_command = command.split(" ")
                player_name = array_command[1] # se obtiene el nombre del jugador del comando es unico un uuid
                amount = float(array_command[2])
                for player in self.players:
                    if player.name == player_name:
                        player.add_balance(amount)
                        break
                self.need_to_draw = True

            elif command.startswith("\\a"): #indica que un jugador realizo una apuesta
                array_command = command.split(" ")
                player_name = array_command[1] # se obtiene el nombre del jugador del comando es unico un uuid
                amount = float(array_command[2]) # monto de la apuesta
                balance = float(array_command[3])  #monto del balance del jugador despues de realizar la apuesta
                for player in self.players:
                    if player.name == player_name:
                        player.set_bet_balance(amount)
                        player.set_balance(balance)
                        break
                # limpiar mensajes previos de saldo insuficiente al apostar con éxito
                self.info_message = ""
                self.need_to_draw = True

            elif command.startswith("\\h"): #el jugador pide hit
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                card = command.split(" ")[2:] # se obtiene todas las cartas de la mano del jugador
                for player in self.players:
                    if player.name == player_name:
                        player.empty_hand() # se vacia la mano del jugador para actualizarla con las nuevas cartas
                        for c in card:
                            player.receive_card(c)
                        break
                self.need_to_draw = True

            elif command.startswith("\\c"): #el jugador pide doblar su apuesta
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                amount = float(command.split(" ")[2]) # monto de la nueva apuesta del jugador despues de doblar
                balance = float(command.split(" ")[3]) # monto del balance del jugador despues de doblar su apuesta
                for player in self.players:
                    if player.name == player_name:
                        player.set_bet_balance(amount)
                        player.set_balance(balance)
                        break
                # limpiar mensajes previos de saldo insuficiente al doblar con éxito
                self.info_message = ""
                self.need_to_draw = True

            elif command.startswith("\\l"): #indica que un jugador perdió
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                balance = float(command.split(" ")[2]) # se obtiene el balance del jugador despues de perder la ronda
                for player in self.players:
                    if player.name == player_name:
                        player.set_lose_game(True)
                        player.set_balance(balance)
                        player.set_has_turn(False)
                        break
                if player_name == self.connection.unique_name:
                    self.lose_game = True
                    self.win_game = False
                    self.tide_game = False
                    self.connection.send_message(f"\\z {self.connection.unique_name}") # pierde turno 
                    self.is_my_turn = False
                self.need_to_draw = True

            elif command.startswith("\\s"): #cartas del crupier en la mesa
                cards = command.split(" ")[1:] # se obtiene todas las cartas del crupier en la mesa
                self.cards_on_table = [] # se vacia la lista de cartas en la mesa para actualizarla con las nuevas cartas
                for card in cards:
                    self.cards_on_table.append(card)
                self.need_to_draw = True

            elif command.startswith("\\v"): #indica el numero del crupier en la mesa
                value = command.split(" ")[1] # se obtiene el valor del crupier en la mesa
                self.server_value = value
                self.need_to_draw = True

            elif command.startswith("\\w"): #indica cuale jugador gano en la ronda
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                balance = float(command.split(" ")[2]) # se obtiene el balance del jugador despues de ganar la ronda
                for player in self.players:
                    if player.name == player_name:
                        player.set_win_game(True)
                        player.set_balance(balance)
                        break
                if player_name == self.connection.unique_name:
                    self.lose_game = False
                    self.tide_game = False
                    self.win_game = True
                self.need_to_draw = True

            elif command.startswith("\\g"): #indica que un jugador empató en la ronda
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                balance = float(command.split(" ")[2]) # se obtiene el balance del jugador despues de empatar la ronda
                for player in self.players:
                    if player.name == player_name:
                        player.set_balance(balance)
                        break
                if player_name == self.connection.unique_name:
                    self.lose_game = False
                    self.win_game = False
                    self.tide_game = True
                self.need_to_draw = True

            elif command.startswith("\\b"): #mensaje de reinicio para la siguiente ronda
                self.lose_game = False
                self.win_game = False
                self.tide_game = False
                self.need_to_draw = True
                self.cards_on_table = [] # se vacia la lista de cartas en la mesa para la siguiente ronda
                self.server_value = 0 # se reinicia el valor del crupier para la siguiente ronda
                self.info_message = ""
                for player in self.players:
                    player.clear_bet() # se reinicia la apuesta de cada jugador para la siguiente ronda
                    player.empty_hand() # se vacia la mano de cada jugador para la siguiente ronda
                    player.set_has_turn(False) # se reinicia el turno de cada jugador para la siguiente ronda
                    player.set_win_game(False) # se reinicia el estado de victoria de cada jugador para la siguiente ronda
                    player.set_lose_game(False) # se reinicia el estado de derrota de cada jugador para la siguiente ronda
                    player.set_tide_game(False) # se reinicia el estado de empate de cada jugador para la siguiente ronda
                    player.set_balance(player.get_balance()) # se actualiza el balance de cada jugador para la siguiente ronda
                self.need_to_draw = True

            elif command.startswith("\\u"): #jugador se desconecta del juego
                parts = command.split(" ")
                player_name = parts[1].strip().strip(".") if len(parts) > 1 else ""

                # Si el jugador actual se desconecta, marcar error y bloquear reingreso mientras la partida siga activa.
                if player_name == self.connection.unique_name:
                    self.lost_connection = True
                    self.connection_error = True
                    self.error_message = "Error de conexión. Fuiste desconectado."
                    if self.gameready:
                        self.blocked_from_rejoin = True
                    self.acepted_in_game = False
                    self.is_my_turn = False
                    self.reset_game_data()

                # Eliminar jugador de la lista y registrar mensaje informativo.
                self.players = [player for player in self.players if player.name != player_name]
                # No mostrar mensaje en cliente al eliminar jugador
                self.info_message = ""
                # Mantener la partida activa si ya había iniciado; solo se desactiva al quedar sin jugadores.
                if len(self.players) == 0:
                    self.gameready = False

                self.need_to_draw = True

    def reset_game_data(self):
        # Reiniciar estado de partida en el cliente tras fallo de conexión o reintento
        self.players = []
        self.cards_on_table = []
        self.gameready = False
        self.is_my_turn = False
        self.need_to_draw = True
        self.lose_game = False
        self.win_game = False
        self.tide_game = False
        self.server_value = 0
        self.info_message = ""

    def send_command(self, command):
        self.connection.send_message(command)

    def end_game(self):
        self.game_started = False
        pass
    
    def add_player(self, player_name):
        if player_name not in [player.name for player in self.players]: # se verifica que el jugador no exista en la lista de jugadores del juego
            self.players.append(Player(player_name))

        
    def get_player_by_name(self, player_name):
        for player in self.players:
            if player.name == player_name:
                return player
        return None
    
    def get_player_name(self):
        return self.connection.unique_name
    
    def get_player_hand_value_by_name(self, player_name):
        player = self.get_player_by_name(player_name)
        if player:
            return player.calculate_hand_value()
        return None
    
    def calculate_hand_value(self):
        return self.server_value
