import threading
from .Player import Player 

class Game:
    def __init__(self, deck, connection, MAX_PLAYERS, server_events):
        self.deck = deck
        self.deck = deck.shuffle()
        self.players = []
        self.MAX_PLAYERS = MAX_PLAYERS
        self.connection = connection
        self.HOST_PORT = connection.get_host_port()
        self.game_started  = False
        self.server_events = server_events 

        #Variables del juego
        self.gameready = False
        self.pot = 0
        self.cards_on_table = []
        self.server_value = 0


    def start_game(self):
        self.game_started = True

        process_command_thread = threading.Thread(target=self.process_command, daemon=True)
        process_command_thread.start()

        self.connection.start_server(self.HOST_PORT)

    def process_command(self):
        while True:
            command = self.connection.commands_consume()
            if command is None:
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
                    self.server_events.append(f"{player_name} has joined the game.")

                    if len(self.players) == self.MAX_PLAYERS:
                        self.gameready = True
                        self.server_events.append("Game is ready to start.")

                        #primero saco la carta inicial del servidor
                        card_init = self.server_hit_initial_card()

                        #broadcast carta inicial del servidor
                        self.connection.broadcast_message(f"\\h {card_init}")

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

            elif command.startswith("\\m"): #jugador envia monto inicial
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                message = " ".join(command.split(" ")[2]) # se obtiene el monto de la apuesta del comando
                player = self.get_player_by_name(player_name)
                if player:
                    player.add_balance(int(message)) # se agrega el monto de la apuesta al balance del jugador
                    self.connection.broadcast_message(f"\\m {player_name} {player.get_balance()}") # se actualiza el tablero indicando el balance del jugador
                    self.server_events.append(f"{player_name} add balance {message}.")

            elif command.startswith("\\a"): #jugador realiza una apuesta
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                message = " ".join(command.split(" ")[2]) # se obtiene el monto de la apuesta del comando
                player = self.get_player_by_name(player_name)
                if player:
                    if player.bet_balance(int(message)): # se realiza el retiro del monto de la apuesta al balance del jugador, si el jugador no tiene suficiente balance para realizar la apuesta se envia un mensaje al jugador indicando que no tiene suficiente balance para realizar la apuesta
                        self.connection.broadcast_message(f"\\a {player_name} {player.get_bet_balance()} {player.get_balance()}") # se actualiza el tablero indicando la apuesta del jugador
                        self.server_events.append(f"{player_name} placed a bet of {message}.")
                    else:
                        self.connection.send_message_to_player(self.connection.get_player_socket_by_name(player_name), f"\\f") # se envia un mensaje al jugador indicando que no tiene suficiente balance para realizar la apuesta

            elif command.startswith("\\h"): #jugador pide hit
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                player = self.get_player_by_name(player_name)
                card = self.deck.draw_card()
                if card:
                    player.receive_card(card)
                    self.connection.broadcast_message(f"\\h {player_name} {card}") # se actualiza el tablero indicando la carta que ha recibido el jugador
                    self.server_events.append(f"{player_name} hits and receives {card}.")

                if player.has_more_than_21():
                    self.connection.broadcast_message(f"\\l {player_name}") # se actualiza el tablero indicando que el jugador ha perdido
                    self.server_events.append(f"{player_name} has more than 21 and loses.")

                    #darle el turno a alguien mas o dar los hits del servidor
                    has_any_waiting_turn = False
                    for p in self.players:
                        if p.get_has_turn():
                            has_any_waiting_turn = True
                            p.set_has_turn(True)
                            self.connection.broadcast_message(f"\\x {p.name}") # se actualiza el tablero indicando el nuevo jugador que tiene el turno
                            break 
                    
                    if has_any_waiting_turn == False:
                        self.server_hits() # se realizan los hits del servidor

                        #broadcast resultado del servidor
                        self.connection.broadcast_message(f"\\s {self.server_value}")

                        #broadcast resultado de cada jugador
                        for p in self.players:
                            if p.get_bet_balance() > 0:
                                if p.has_more_than_21():
                                    result = "lose"
                                elif self.server_value > 21 or p.player_value > self.server_value:
                                    result = "win"
                                    p.add_balance(p.get_bet_balance() * 2) # se le da al jugador el doble de su apuesta si gana
                                elif p.player_value == self.server_value:
                                    result = "tie"
                                    p.add_balance(p.get_bet_balance()) # se le devuelve al jugador su apuesta si empata
                                else:
                                    result = "lose"

                                self.connection.broadcast_message(f"\\r {p.name} {result} {p.get_balance()}") # se actualiza el tablero indicando el resultado del jugador
                

                    


            if self.game_started == False:
                break

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

        self.deck.init_cards_blackjack()
        self.deck.shuffle()
        self.cards_on_table = []
        self.pot = 0

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
                self.server_has_between_17_and_21()
            else:
                break