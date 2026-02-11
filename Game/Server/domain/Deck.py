class Deck:
    def __init__(self):
        self.cards = []
        self.init_cards_blackjack()

    def init_cards_blackjack(self):
        suits = ['h', 'd', 'c', 's']  # Hearts, Diamonds, Clubs, Spades
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'j', 'q', 'k', 'a']
        single_deck = [f"{suit}-{rank}" for suit in suits for rank in ranks]
        self.cards = single_deck * 4 # Standard 52-card deck multiplied by 4 for blackjack
        self.shuffle()

    def shuffle(self):
        import random
        random.shuffle(self.cards)

    def draw_card(self):
        if self.cards:
            return self.cards.pop()
        else:
            return None

    def __len__(self):
        return len(self.cards)