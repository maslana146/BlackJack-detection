import math
from src.config import *


class Game:
    def __init__(self, players):
        self.players = players  # [dealer, player1, player2]
        self.cards = []
        self.coins = [[], []]
        self.prev_cards = []
        self.prev_coins = [[], []]
        self.was_all_zeros = []
        self.actions = [[] for i in range(10)]  # x= 5 is for how long (x*15 frames)
        self.actions_to_print = []
        self.deck = None
        self.rewers = None

        # Now some fun with flags
        self.was_rewers_puted = False
        self.was_rewers_inverted = False
        self.temp = False  # something for rewerse
        self.game_ended = False
        self.end_of_dealing = False

    def set_points(self):
        ''' Set new number of points in game for each player, only if this number is greater than prev score'''
        dealer_p = self.count_points(self.cards, 'bottom', ['left', 'right'])
        p1_p = self.count_points(self.cards, 'top', ['left'])
        p2_p = self.count_points(self.cards, 'top', ['right'])

        if dealer_p == 0 and p1_p == 0 and p2_p == 0:
            self.was_all_zeros.append(True)
        else:
            self.was_all_zeros.append(False)

        self.players[0].points = dealer_p
        self.players[1].points = p1_p
        self.players[2].points = p2_p

    def set_coins(self):
        player1_coins = len(self.coins[0])
        player2_coins = len(self.coins[1])
        if self.players[1].coins < player1_coins:
            self.players[1].coins = player1_coins
        if self.players[2].coins < player2_coins:
            self.players[2].coins = player2_coins

    def count_points(self, cards, half, side):
        total = 0
        for card in cards:
            if card.half == half and card.side in side:
                if card.best_rank_match == 'Two':
                    total += 2
                elif card.best_rank_match == 'Three':
                    total += 3
                elif card.best_rank_match == 'Four':
                    total += 4
                elif card.best_rank_match == 'Five':
                    total += 5
                elif card.best_rank_match == 'Six':
                    total += 6
                elif card.best_rank_match == 'Seven':
                    total += 7
                elif card.best_rank_match == 'Eight':
                    total += 8
                elif card.best_rank_match == 'Nine':
                    total += 9
                elif (card.best_rank_match == 'Jack' or card.best_rank_match == 'Queen'
                      or card.best_rank_match == 'King' or card.best_rank_match == 'Ten'):
                    total += 10
                elif card.best_rank_match == 'Ace':
                    if total + 11 > 21:
                        total += 1
                    else:
                        total += 11
        return total

    def clean_cards(self):
        ''' Remove all cards thats have unknown rank and suit and add deck and rewers'''
        too_remove = []
        for card in self.cards:
            if card.best_rank_match == "Unknown" and (
                    card.best_suit_match == "Unknown" or card.best_suit_match == 'rewers'):
                too_remove.append(card)
        self.cards = [card for card in self.cards if card not in too_remove]

    def add_deck(self):
        if self.deck != None:
            self.cards.append(self.deck)
        if self.rewers != None:
            dist, clost_card = self.shortes_distance(self.rewers, self.cards)
            if dist > 20:

                self.cards.append(self.rewers)
            else:
                self.rewers = None

    def shortes_distance(self, card, cards):
        min_d = 10000
        closted = None
        for cardx in cards:
            dist = math.sqrt((cardx.center[0] - card.center[0]) ** 2 + (cardx.center[1] - card.center[1]) ** 2)
            if dist < min_d:
                min_d = dist
                closted = cardx
        return min_d, closted

    def restore_cards(self):
        '''if some card was found prevoisly, but is not found currently, restore it'''
        curr_set = []

        if len(self.cards) > 0:  # do it only when find any card
            for card in self.cards:
                curr_set.append((card.best_rank_match, card.best_suit_match))
            if len(self.cards) > 1:
                for card in self.prev_cards:
                    if (card.best_rank_match, card.best_suit_match) not in curr_set:
                        if card.best_suit_match != 'rewers':
                            dist, clost_card = self.shortes_distance(card, self.cards)
                            if dist > 10:
                                self.cards.append(card)
                            else:
                                if dist < 2:
                                    # in worst case scen. 'Unknown' will change into 'Unknown'
                                    if clost_card.best_rank_match == 'Unknown' and clost_card.best_suit_match != 'deck':
                                        clost_card.best_rank_match = card.best_rank_match

                                    if clost_card.best_suit_match == 'Unknown':
                                        clost_card.best_suit_match = card.best_suit_match

    def restore_coins(self):
        '''restore coins that are not found, but was found early'''
        for i in range(2):
            for coin in self.prev_coins[i]:
                dist, clost_coin = self.shortes_distance_coins(coin, self.coins[i])
                if dist > 50:
                    self.coins[i].append(coin)

    def shortes_distance_coins(self, coin, coins):
        min_d = 10000
        closted = None
        for coinx in coins:
            dist = math.sqrt((coinx.pos[0] - coin.pos[0]) ** 2 + (coinx.pos[1] - coin.pos[1]) ** 2)
            if dist < min_d:
                min_d = dist
                closted = coinx
        return min_d, closted

    def set_prev(self):
        '''at the end, set current state of the game as previous'''

        for player in self.players:
            player.prev_points = player.points
            player.prev_total_cards = player.total_cards
        self.prev_cards = self.cards
        self.prev_coins = self.coins

    def search_action(self):

        for player in self.players:
            if player.prev_total_cards != player.total_cards and player.total_cards != 0 and (
                    self.was_rewers_inverted == False or self.temp == True):
                # print('dealing')
                self.actions = [x + ['dealer deals ' + str(player.name)] for x in self.actions[:5]]

            if self.was_rewers_inverted == True:
                self.temp = True

            if player.points > 21 and player.busted == False:
                player.busted = True
                self.actions = [x + [str(player.name) + ' busted'] for x in self.actions[:5]]

            if player.points == 21 and player.total_cards == 2:
                self.actions = [x + [str(player.name) + ' hit BLACKJACK'] for x in self.actions]

        if self.players[0].points > 17:
            self.game_ended = True

        if self.players[1].coins > 1 and self.players[
            1].raised == False and self.was_rewers_inverted == False and self.was_rewers_puted == True:
            self.players[1].raised = True
            self.actions = [x + [str(self.players[1].name) + ' double his bet'] for x in self.actions[:5]]

        if self.players[2].coins > 1 and self.players[
            2].raised == False and self.was_rewers_inverted == False and self.was_rewers_puted == True:
            self.players[2].raised = True
            self.actions = [x + [str(self.players[2].name) + ' double his bet'] for x in self.actions[:5]]

        self.actions_to_print = self.actions.pop(0)
        self.actions.append([])

    def search_deck(self):
        deck = []
        rewers = []
        for card in self.cards:
            if card.side == 'left' and card.half == 'bottom':
                if card.center[0] < IM_WIDTH / 4:
                    deck.append(card)
                else:
                    rewers.append(card)
        if len(deck) > 0:
            max_size = 0
            display_deck = None
            for card in deck:
                if card.size > max_size:
                    max_size = card.size
                    display_deck = card
                    display_deck.best_suit_match = 'deck'
            self.deck = display_deck
        else:
            self.deck = None

        if len(rewers) > 0:
            max_size = 0
            display_rewers = None
            for card in rewers:
                if card.best_suit_match != 'Unknown' or card.best_rank_match != 'Unknown':
                    self.rewers = None
                    break
                if card.size > max_size:
                    max_size = card.size
                    display_rewers = card
                    display_rewers.best_suit_match = 'rewers'
            # rewers = random.choice(rewers)
            # if rewers.best_suit_match == 'Unknown':
            if display_rewers != None and self.was_rewers_puted == False:
                self.was_rewers_puted = True
            if display_rewers == None and self.was_rewers_puted == True and self.was_rewers_inverted == False:
                self.was_rewers_inverted = True
                self.actions = [x + ['secret card inverted'] for x in self.actions]
            self.rewers = display_rewers
        else:
            self.rewers = None

    def count_cards(self):
        dealer = []
        player1 = []
        player2 = []
        for card in self.cards:
            if card.side == 'left' and card.half == 'top':
                player1.append(card)
            if card.side == 'right' and card.half == 'top':
                player2.append(card)
            else:
                if card.side == 'right' and card.half == 'bottom':
                    dealer.append(card)

        self.players[0].total_cards = len(dealer) + self.was_rewers_puted
        self.players[1].total_cards = len(player1)
        self.players[2].total_cards = len(player2)

        if self.players[0].total_cards == 2:
            self.end_of_dealing = True

    def new_game(self):
        aa = sum([1 for x in self.was_all_zeros[-10:] if x is True])
        if aa == 10:  # if during  10 checks(150 frames) noone have any points, its mean it is new game
            return True
        return False

    def player_vs_dealer(self, player, dealer):
        ''' return player, dealer, or tie, for each player'''
        if player.points > 21: return 'dealer'  # if both dealer and player busted, dealer wins
        if dealer.points > 21: return 'player'
        if dealer.points == player.points: return 'tie'
        if player.points > dealer.points:
            return 'player'
        else:
            return 'dealer'

    def who_win(self):
        dealer, player1, player2 = self.players
        winners = []
        for player in [player1, player2]:
            if self.player_vs_dealer(player, dealer) == 'player':
                winners.append(player)
        if len(winners) < 2:
            winners.append(dealer)

        return [player.name for player in winners]

    def has_game_concluded(self):
        if self.players[0].points > 16:
            return True
        return False
