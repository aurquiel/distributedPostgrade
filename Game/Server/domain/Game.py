import threading
import time
from .Player import Player

class Game:
    def __init__(self, deck, connection, MAX_PLAYERS, server_events):
        self.deck = deck
        self.deck.shuffle()
        self.players = []
        self.MAX_PLAYERS = MAX_PLAYERS
        self.connection = connection
        self.HOST_PORT = connection.get_host_port()
        self.server_events = server_events

        #Variables del juego
        self.gameready = False
        self.round_in_progress = False
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
                player_name = command.split(" ")[1] # se obtiene todos los jugadores del comando, es unico un uuid
                # si está lleno, responder partida completa
                if len(self.players) >= self.MAX_PLAYERS:
                    sock = self.connection.get_player_socket_by_name(player_name)
                    if sock:
                        self.connection.send_message_to_player(sock, f"\\f")
                        self.connection.remove_player_socket_and_name(sock, player_name)
                    self.server_events.append(f"{player_name} no pudo unirse: partida llena.")
                    continue

                result = self.add_player(player_name)
                players_names = " ".join([player.name for player in self.players])
                if result:
                    self.connection.broadcast_message(f"\\n " + players_names) # se envia todos los jugadores el nuevo jugador que se ha unido al juego para actualizar el tablero
                    self.server_events.append(f"{players_names} se ha unido al juego.")

                    # si el juego aún no había iniciado y ahora está completo, arrancar
                    if not self.gameready and len(self.players) == self.MAX_PLAYERS:
                        self.gameready = True
                        self.connection.broadcast_message(f"\\y") # indica a los jugadores que el juego ha comenzado
                        self.server_events.append("El juego está listo para iniciar.")
                        self.connection.broadcast_message(f"\\x " + self.players[0].name) # Dale el turno al que se unio primero
                    else:
                        # juego ya iniciado: jugador entra esperando siguiente ronda
                        new_player = self.get_player_by_name(player_name)
                        if new_player and self.round_in_progress:
                            new_player.set_finished_turn(True) # saltar la ronda actual
                            new_player.set_has_turn(False)
                        # asegurar que el nuevo jugador sabe que la partida está activa
                        sock = self.connection.get_player_socket_by_name(player_name)
                        if sock:
                            self.connection.send_message_to_player(sock, f"\\y")

            elif command.startswith("\\m"): #jugador envia monto de saldo para agregar a su balance
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                message = command.split(" ")[2] # se obtiene el monto de la apuesta del comando
                player = self.get_player_by_name(player_name)
                if player:
                    player.add_balance(int(message)) # se agrega el monto de la apuesta al balance del jugador
                    self.connection.broadcast_message(f"\\m {player_name} {player.get_balance()}") # se actualiza el tablero indicando el balance del jugador
                    self.server_events.append(f"{player_name} agregó saldo {message}.")

            elif command.startswith("\\a"): #jugador realiza una apuesta
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                message = command.split(" ")[2] # se obtiene el monto de la apuesta del comando
                player = self.get_player_by_name(player_name)
                if player:
                    if player.set_bet_balance(int(message)): # se realiza el retiro del monto de la apuesta al balance del jugador, si el jugador no tiene suficiente balance para realizar la apuesta se envia un mensaje al jugador indicando que no tiene suficiente balance para realizar la apuesta
                        self.connection.broadcast_message(f"\\a {player_name} {player.get_bet_balance()} {player.get_balance()}") # se actualiza el tablero indicando la apuesta del jugador
                        self.server_events.append(f"{player_name} realizó una apuesta de {message}.")

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
                    self.connection.broadcast_message(f"\\l {player_name} {player.get_balance()}") # se actualiza el tablero indicando que el jugador ha perdido
                    self.server_events.append(f"{player_name} tiene más de 21 y pierde.")
                    for player in self.players:
                        if player.name == player_name:
                            player.set_lose_game(True) # se actualiza el estado de derrota del jugador para que el cliente pueda manejarlo y evitar que pueda realizar acciones en su turno
                            player.set_has_turn(False)
                            player.set_finished_turn(True)
                            break
                    # pasar turno inmediato al siguiente jugador o al crupier si no hay más
                    self._advance_turn(player_name)

            elif command.startswith("\\c"): #jugador dobal su apuesta si tiene el saldo suficiente para hacerlo
                player_name = command.split(" ")[1] # se obtiene el nombre del jugador del comando es unico un uuid
                player = self.get_player_by_name(player_name)
                if player:
                    if player.set_bet_balance(player.get_bet_balance()): # se realiza el retiro del monto de la apuesta al balance del jugador, si el jugador no tiene suficiente balance para realizar la apuesta se envia un mensaje al jugador indicando que no tiene suficiente balance para realizar la apuesta
                        self.connection.broadcast_message(f"\\c {player_name} {player.get_bet_balance()} {player.get_balance()}") # se actualiza el tablero indicando la nueva apuesta del jugador
                        self.server_events.append(f"{player_name} dobla su apuesta a {player.get_bet_balance()}.")
                    else:
                        self.connection.send_message_to_player(self.connection.get_player_socket_by_name(player_name), f"\\t") # se envia un mensaje al jugador indicando que no tiene suficiente balance para doblar su apuesta

            elif command.startswith("\\z"): #jugador finaliza turno
                parts = command.split(" ")
                player_name = parts[1].strip() if len(parts) > 1 else ""
                player = self.get_player_by_name(player_name)

                self.connection.broadcast_message(f"\\z {player_name}") # se actualiza el tablero indicando que el jugador ha finalizado su turno
                self.server_events.append(f"{player_name} termina su turno.")

                if player and self.round_in_progress:
                    player.set_finished_turn(True)

                # si no hay ronda en curso y todos apostaron, se inicia; si no, se pasa el turno
                if self.start_round_if_ready():
                    continue
                self._advance_turn(player_name)

            elif command.startswith("\\u"): #jugador se desconecta del juego
                player_name = command.split(" ")[1] if len(command.split(" ")) > 1 else ""
                self.players = [player for player in self.players if player.name != player_name] # se elimina al jugador de la lista de jugadores del juego
                self.connection.broadcast_message(f"\\u {player_name}") # se actualiza el tablero indicando que el jugador se ha desconectado
                self.server_events.append(f"{player_name} ha salido del juego.")

                # liberar socket y nombre para permitir reingresos
                player_sock = self.connection.get_player_socket_by_name(player_name)
                if player_sock:
                    self.connection.remove_player_socket_and_name(player_sock, player_name)
                    try:
                        player_sock.close()
                    except Exception:
                        pass

                # Si la ronda está en curso, pasar el turno o finalizar si no quedan activos
                if self.round_in_progress:
                    active_left = [p for p in self.players if not p.lose_game and not p.get_finished_turn()]
                    if not active_left:
                        self.finish_round()
                    else:
                        self._advance_turn(player_name)
                else:
                    # Fuera de ronda: asegurar que alguien tenga el turno para apostar
                    if self.players and not any(p.get_has_turn() for p in self.players):
                        self.players[0].set_has_turn(True)
                        self.connection.broadcast_message(f"\\x {self.players[0].name}")

    def end_game(self):
        self.game_started = False
        pass

    def add_player(self, player_name):
        if player_name in [player.name for player in self.players]: # se verifica que el jugador no exista en la lista de jugadores del juego
            return False
        if len(self.players) < self.MAX_PLAYERS:
            self.players.append(Player(player_name))
            return True
        else:
            return False

    def start_round_if_ready(self):
        if self.round_in_progress:
            return False
        if len(self.players) >= 1 and all(player.get_bet_balance() > 0 for player in self.players):
            self.round_in_progress = True
            self.server_events.append("Todos los jugadores han realizado su apuesta. La ronda comienza.")

            for p in self.players:
                p.set_finished_turn(False)

            card_init = self.server_hit_initial_card()
            self.connection.broadcast_message(f"\\s {card_init}")
            self.server_events.append(f"El crupier recibe su carta inicial. Carta del crupier: {card_init}.")
            self.connection.broadcast_message(f"\\v {self.server_value}")
            self.server_events.append(f"Valor de la mano del crupier: {self.server_value}.")

            for player in self.players:
                card1 = self.deck.draw_card()
                card2 = self.deck.draw_card()
                player.receive_card(card1)
                player.receive_card(card2)
                player.set_has_turn(False)
                self.connection.broadcast_message(f"\\k {player.name} {card1} {card2}")

            self.players[0].set_has_turn(True)
            self.connection.broadcast_message(f"\\x {self.players[0].name}")
            return True
        return False

    def _advance_turn(self, current_player_name):
        if not self.players:
            return
        # apagar turno actual
        for p in self.players:
            if p.name == current_player_name:
                p.set_has_turn(False)
                break

        # buscar siguiente jugador activo
        active_indices = [i for i, p in enumerate(self.players) if not p.lose_game and not p.get_finished_turn()]
        if not active_indices:
            if self.round_in_progress:
                self.finish_round()
            return

        # buscar el siguiente activo respecto al jugador actual; si no se encuentra, tomar el primero activo
        idx = next((i for i, p in enumerate(self.players) if p.name == current_player_name), -1)
        ordered = active_indices
        if idx >= 0 and idx in active_indices:
            ordered = [i for i in active_indices if i > idx] + [i for i in active_indices if i <= idx]

        next_idx = ordered[0]
        candidate = self.players[next_idx]
        candidate.set_has_turn(True)
        self.connection.broadcast_message(f"\\x {candidate.name}")
        self.server_events.append(f"{candidate.name} inicia su turno.")
        return

    def finish_round(self):
        self.server_hits()

        cards_on_table_string = " ".join(self.cards_on_table)
        self.connection.broadcast_message(f"\\s {cards_on_table_string}")
        self.server_events.append(f"Cartas del crupier en la mesa: {cards_on_table_string}.")
        self.connection.broadcast_message(f"\\v {self.server_value}")
        self.server_events.append(f"El turno del crupier termina con un valor de {self.server_value}.")

        time.sleep(4) # esperar unos segundos para que los jugadores puedan ver las cartas del crupier antes de mostrar el resultado

        for player in self.players:
            bust = player.has_more_than_21()
            if bust:
                self.connection.broadcast_message(f"\\l {player.name} {player.get_balance()}")
                self.server_events.append(f"{player.name} tiene más de 21 y pierde.")
            elif self.server_value > 21:
                player.add_balance(player.get_bet_balance() * 2)
                self.connection.broadcast_message(f"\\w {player.name} {player.get_balance()}")
                self.server_events.append(f"{player.name} gana porque el crupier tiene más de 21. Nuevo saldo: {player.get_balance()}.")
            elif player.player_value > self.server_value:
                player.add_balance(player.get_bet_balance() * 2)
                self.connection.broadcast_message(f"\\w {player.name} {player.get_balance()}")
                self.server_events.append(f"{player.name} gana con un valor de {player.player_value} contra el {self.server_value} del crupier. Nuevo saldo: {player.get_balance()}.")
            elif player.player_value == self.server_value:
                player.add_balance(player.get_bet_balance())
                self.connection.broadcast_message(f"\\g {player.name} {player.get_balance()}")
                self.server_events.append(f"{player.name} empata con el crupier con un valor de {player.player_value}. Nuevo saldo: {player.get_balance()}.")
            else:
                self.connection.broadcast_message(f"\\l {player.name} {player.get_balance()}")
                self.server_events.append(f"{player.name} pierde con un valor de {player.player_value} contra el {self.server_value} del crupier.")

        time.sleep(6) # esperar unos segundos para que los jugadores puedan ver el resultado antes de limpiar el tablero
        self.round_in_progress = False
        self.clear_round_game()
        self.connection.broadcast_message(f"\\b")

        # iniciar siguiente ronda: token al primer jugador disponible
        if self.players:
            self.players[0].set_has_turn(True)
            self.connection.broadcast_message(f"\\x {self.players[0].name}")

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
            player.set_lose_game(False)
            player.set_win_game(False)
            player.set_tide_game(False)
            player.set_finished_turn(False)

        self.deck.init_cards_blackjack()
        self.deck.shuffle()
        self.cards_on_table = []
        self.server_value = 0

    def server_hit_initial_card(self):
        card = self.deck.draw_card()
        if card:
            self.cards_on_table.append(card)
            self.server_value = self.calculate_first_card_value(self.cards_on_table)
        return card

    def calculate_first_card_value(self, cards):
        """Calcula el valor de las cartas del crupier (uso inicial)."""
        if not cards:
            return 0

        card = cards[0]
        try:
            rank = card.split("-")[1]
        except IndexError:
            return 0

        if "a" in rank:
            return 11
        if rank in ("j", "q", "k"):
            return 10
        try:
            return int(rank)
        except ValueError:
            return 0
    

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