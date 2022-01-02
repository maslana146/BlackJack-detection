class Player:
    def __init__(self, name):
        self.name = name
        self.prev_points = 0
        self.points = 0
        self.busted = False
        self.coins = 0
        self.total_cards = 0
        self.prev_total_cards = 0
        self.raised = False