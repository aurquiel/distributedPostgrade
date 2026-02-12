import threading
import time
from .Player import Player 

class Game:
    def __init__(self, deck, connection, MAX_PLAYERS, server_events):
        self.deck = deck
        self.deck = deck.shuffle()
        self.players = []
        self.MAX_PLAYERS = MAX_PLAYERS
        self.connection = connection
        self.HOST_PORT = connection.get_host_port()
        self.server_events = server_events 

        #Variables del juego
        self.gameready = False
        self.cards_on_table = []
        self.server_value = 0

    def start_game(self):

        process_command_thread = threading.Thread(target=self.process_command, daemon=True)
        process_command_thread.start()

        self.connection.start_server(self.HOST_PORT)

    def process_command(self):
        while True:
            #Si el juego comenzo y se fueron todos los jugadores, entonces reinicio el juego para que puedan unirse nuevos jugadores
            if self.gameready and len(self.players) == 0:
                self.gameready = False
                self.clear_round_game()

                self.server_events.append("Todos los jugadores se han desconectado. El juego se ha reiniciado.")
                continue
            
            #Consumir mensajes de la cola de comandos del servidor y procesarlos
            command = self.connection.commands_consume()

            if command is None: #no hay comandos para procesar
                continue
            if command.startswith("\\i"):
                message = " ".join(command.split(" ")[1:])
                self.server_events.append(message)
            elif command.startswith("\\n"): #jugador pide unirse al juego
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                result = self.add_player(player_name)
                if result:
                    #self.connection.send_message_to_player(self.connection.get_player_socket_by_name(player_name), f"\\a") # se envia un mensaje al jugador indicando que se ha unido al juego
                    self.connection.broadcast_message(f"\\n {player_name}") # se actuliza el tablero indicando que un nuevo jugador se ha unido al juego
                    self.server_events.append(f"{player_name} se ha unido al juego.")

                    if self.gameready:
                        self.connection.send_message_to_player(self.connection.get_player_socket_by_name(player_name), f"\\i") # se envia un mensaje al jugador indicando que el juego ya ha comenzado y no puede unirse
                        self.connection.remove_player_socket_and_name(self.connection.get_player_socket_by_name(player_name), player_name) # se elimina al jugador de la lista de sockets y nombres del servidor
                        self.server_events.append(f"{player_name} intentó unirse al juego pero ya había comenzado.")
                    elif len(self.players) == self.MAX_PLAYERS:
                        self.gameready = True
                        self.server_events.append("El juego está listo para iniciar.")

                        #primero saco la carta inicial del servidor
                        card_init = self.server_hit_initial_card()

                        #broadcast carta inicial del servidor
                        self.connection.broadcast_message(f"\\s {card_init}")

                        #broadcast de dos cartas a todos los jugadores
                        for player in self.players:
                            card1 = self.deck.draw_card()
                            card2 = self.deck.draw_card()
                            player.receive_card(card1)
                            player.receive_card(card2)
                            self.connection.broadcast_message(f"\\k {player.name} {card1} {card2}")

                        #envio token de turno al primer jugador
                        self.connection.broadcast_message(f"\\x {self.players[0].name}")
                        self.players[0].set_has_turn(True)

            elif command.startswith("\\m"): #jugador envia monto de saldo para agregar a su balance
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                message = " ".join(command.split(" ")[2]) # se obtiene el monto de la apuesta del comando
                player = self.get_player_by_name(player_name)
                if player:
                    player.add_balance(int(message)) # se agrega el monto de la apuesta al balance del jugador
                    self.connection.broadcast_message(f"\\m {player_name} {player.get_balance()}") # se actualiza el tablero indicando el balance del jugador
                    self.server_events.append(f"{player_name} agregó saldo {message}.")

            elif command.startswith("\\a"): #jugador realiza una apuesta
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                message = " ".join(command.split(" ")[2]) # se obtiene el monto de la apuesta del comando
                player = self.get_player_by_name(player_name)
                if player:
                    if player.bet_balance(int(message)): # se realiza el retiro del monto de la apuesta al balance del jugador, si el jugador no tiene suficiente balance para realizar la apuesta se envia un mensaje al jugador indicando que no tiene suficiente balance para realizar la apuesta
                        self.connection.broadcast_message(f"\\a {player_name} {player.get_bet_balance()} {player.get_balance()}") # se actualiza el tablero indicando la apuesta del jugador
                        self.server_events.append(f"{player_name} realizó una apuesta de {message}.")
                    else:
                        self.connection.send_message_to_player(self.connection.get_player_socket_by_name(player_name), f"\\f") # se envia un mensaje al jugador indicando que no tiene suficiente balance para realizar la apuesta

            elif command.startswith("\\h"): #jugador pide hit
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                player = self.get_player_by_name(player_name)
                card = self.deck.draw_card()
                if card:
                    player.receive_card(card)

                    cards_of_the_player_string = ""
                    for card in player.hand:
                        cards_of_the_player_string += f"{card} "
                    cards_of_the_player_string = cards_of_the_player_string.strip()

                    self.connection.broadcast_message(f"\\h {player_name} {cards_of_the_player_string}") # se actualiza el tablero indicando la carta que ha recibido el jugador
                    self.server_events.append(f"{player_name} pide carta y recibe {card}.")

                if player.has_more_than_21():
                    self.connection.broadcast_message(f"\\l {player_name}") # se actualiza el tablero indicando que el jugador ha perdido
                    self.server_events.append(f"{player_name} tiene más de 21 y pierde.")

            elif command.startswith("\\z"): #jugador finaliza turno
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                player = self.get_player_by_name(player_name)
                if player:
                    self.connection.broadcast_message(f"\\z {player_name}") # se actualiza el tablero indicando que el jugador ha finalizado su turno
                    self.server_events.append(f"{player_name} termina su turno.")

                    player_next_trun = None

                    for p in self.players:
                        if p.get_has_turn():
                            player_next_trun = p
                            break
                    
                    if player_next_trun:
                        player_next_trun.set_has_turn(True)
                        self.connection.broadcast_message(f"\\x {player_next_trun.name}") # se actualiza el tablero indicando que el siguiente jugador tiene su turno
                        self.server_events.append(f"{player_next_trun.name} inicia su turno.")      
                    else:
                        self.server_hits() # el servidor realiza sus jugadas

                        cards_on_table_string = ""
                        for card in self.cards_on_table:
                            cards_on_table_string += f"{card} "
                        cards_on_table_string = cards_on_table_string.strip()

                        self.connection.broadcast_message(f"\\s {cards_on_table_string}") # se actualiza el tablero indicando el valor del servidor
                        self.connection.broadcast_message(f"\\v {self.server_value}") # se actualiza el tablero indicando el valor del servidor
                        self.server_events.append(f"El turno del crupier termina con un valor de {self.server_value}.")

                        #ahora tengo que saber quienes son los ganadores de la ronda y actualizar el balance de cada jugador
                        for player in self.players:
                            if player.has_more_than_21():
                                continue
                            elif self.server_value > 21:
                                player.add_balance(player.get_bet_balance() * 2) # el jugador gana el doble de su apuesta si el servidor se pasa de 21
                                self.connection.broadcast_message(f"\\w {player.name} {player.get_balance()}") # se actualiza el tablero indicando que el jugador ha ganado y su nuevo balance
                                self.server_events.append(f"{player.name} gana porque el crupier tiene más de 21. Nuevo saldo: {player.get_balance()}.")
                            elif player.player_value > self.server_value:
                                player.add_balance(player.get_bet_balance() * 2) # el jugador gana el doble de su apuesta si su valor es mayor al del servidor
                                self.connection.broadcast_message(f"\\w {player.name} {player.get_balance()}") # se actualiza el tablero indicando que el jugador ha ganado y su nuevo balance
                                self.server_events.append(f"{player.name} gana con un valor de {player.player_value} contra el {self.server_value} del crupier. Nuevo saldo: {player.get_balance()}.")
                            elif player.player_value == self.server_value:
                                player.add_balance(player.get_bet_balance()) # el jugador recupera su apuesta si su valor es igual al del servidor
                                self.connection.broadcast_message(f"\\t {player.name} {player.get_balance()}") # se actualiza el tablero indicando que el jugador ha empatado y su nuevo balance
                                self.server_events.append(f"{player.name} empata con el crupier con un valor de {player.player_value}. Nuevo saldo: {player.get_balance()}.")
                            else:
                                self.connection.broadcast_message(f"\\l {player.name}") # se actualiza el tablero indicando que el jugador ha perdido
                                self.server_events.append(f"{player.name} pierde con un valor de {player.player_value} contra el {self.server_value} del crupier.")

                    #DELAY PARA VER LOS MENSAJES EN EL CLIENTE ANTES DE INICIAR LA SIGUIENTE RONDA
                    time.sleep(3)

                    #necesito reiniciar todos los valores del juego para la siguiente ronda
                    self.clear_round_game()

                    self.connection.broadcast_message(f"\\x") #comando de reinicio para la siguiente ronda

                    time.sleep(1)

                    #primero saco la carta inicial del servidor
                    card_init = self.server_hit_initial_card()

                    #broadcast carta inicial del servidor
                    self.connection.broadcast_message(f"\\s {card_init}")

                    #broadcast de dos cartas a todos los jugadores
                    for player in self.players:
                        card1 = self.deck.draw_card()
                        card2 = self.deck.draw_card()
                        player.receive_card(card1)
                        player.receive_card(card2)
                        self.connection.broadcast_message(f"\\k {player.name} {card1} {card2}")

                    #envio token de turno al primer jugador
                    self.connection.broadcast_message(f"\\x {self.players[0].name}")
                    self.players[0].set_has_turn(True)

            elif command.startswith("\\u"): #jugador se desconecta del juego
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                self.players = [player for player in self.players if player.name != player_name] # se elimina al jugador de la lista de jugadores del juego
                self.connection.broadcast_message(f"\\u {player_name}") # se actualiza el tablero indicando que el jugador se ha desconectado
                self.server_events.append(f"{player_name} ha salido del juego.")

    def end_game(self):
        self.game_started = False
        pass
    
    def add_player(self, player_name):
        if len(self.players) < self.MAX_PLAYERS:
            self.players.append(Player(player_name))
            return True
        else:
            return False
        
    def get_player_by_name(self, player_name):
        for player in self.players:
            if player.name == player_name:
                return player
        return None

    def clear_round_game(self):
        for player in self.players:
            player.clear_bet()
            player.empty_hand()
            player.set_has_turn(False)

        self.deck.init_cards_blackjack()
        self.deck.shuffle()
        self.cards_on_table = []

    def server_hit_initial_card(self):
        card = self.deck.draw_card()
        if card:
            self.cards_on_table.append(card)
        return card

    def server_has_between_17_and_21(self):
        value = 0
        aces = 0

        for card in self.cards_on_table:
            rank = card.split("-")[1]  # asumiendo formato "suit-rank"
            if "a" in rank:
                aces += 1
                value += 11
            elif rank in ("j", "q", "k"):
                value += 10
            else:
                value += int(rank)

        # Ajustar Ases de 11 a 1 si se pasa de 21
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        self.server_value = value
        return 17 <= value <= 21
    
    def server_hits(self):
        while self.server_value < 17:
            card = self.deck.draw_card()
            if card:
                self.cards_on_table.append(card)
                if self.server_has_between_17_and_21():
                    break
                elif self.server_value > 21:
                    break