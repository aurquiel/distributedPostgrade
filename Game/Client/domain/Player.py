class Player:
    def __init__(self, name):
        self.name = name
        self.balance = 0
        self.bet_balance = 0
        self.hand = []
        self.player_value = 0
        self.has_turn = False
        self.lose_game = False
        self.win_game = False
        self.tide_game = False

    def set_lose_game(self, lose_game):
        self.lose_game = lose_game

    def set_win_game(self, win_game):
        self.win_game = win_game

    def set_tide_game(self, tide_game):
        self.tide_game = tide_game

    def receive_card(self, card):
        self.hand.append(card)  

    def empty_hand(self):
        self.hand = []
    
    def add_balance(self, amount):
        self.balance += amount

    def set_balance(self, amount):
        self.balance = amount

    def get_balance(self):
        return self.balance
    
    def get_bet_balance(self):
        return self.bet_balance
    
    def set_bet_balance(self, amount):
        self.bet_balance += amount
    
    def clear_bet(self):
        self.bet_balance = 0

    def set_has_turn(self, has_turn):
        self.has_turn = has_turn

    def get_has_turn(self):
        return self.has_turn
    
    def calculate_hand_value(self):
        if not self.hand:
            return 0

        total = 0
        aces = 0

        for card in self.hand:
            try:
                _, value_code = card.split("-", 1)
            except ValueError:
                continue

            value_code = value_code.lower()
            if value_code == "a":
                total += 11
                aces += 1
            elif value_code in ("k", "q", "j"):
                total += 10
            else:
                try:
                    total += int(value_code)
                except ValueError:
                    continue

        while total > 21 and aces:
            total -= 10
            aces -= 1

        return total