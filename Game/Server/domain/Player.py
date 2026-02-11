class Player:
    def __init__(self, name):
        self.name = name
        self.balance = 0
        self.bet_balance = 0
        self.hand = []
        self.player_value = 0
        self.has_turn = False

    def receive_card(self, card):
        self.hand.append(card)  

    def empty_hand(self):
        self.hand = []
    
    def add_balance(self, amount):
        self.balance += amount

    def get_balance(self):
        return self.balance
    
    def get_bet_balance(self):
        return self.bet_balance
    
    def bet_balance(self, amount):
        if amount > self.balance:
            return False
        self.bet_balance += amount
        self.balance -= amount
        return True
    
    def clear_bet(self):
        self.bet_balance = 0

    def set_has_turn(self, has_turn):
        self.has_turn = has_turn

    def get_has_turn(self):
        return self.has_turn
    
    def has_more_than_21(self):
        value = 0
        aces = 0

        for card in self.hand:
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

        self.player_value = value
        return value > 21
    