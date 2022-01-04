from typing import List, Optional, Tuple

import cv2
from config import *
from src.helpers import load_ranks, load_suits, preprocess_image, find_cards, preprocess_card, find_coins, match_card
from src.models.Game import Game
from src.models.Player import Player
from numpy import ndarray

from src.models.QueryCard import QueryCard

FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_results(image: ndarray, q_card: QueryCard) -> ndarray:
    """Draw the card name, center point, and contour on the camera image."""

    x = q_card.center[0]
    y = q_card.center[1]
    rank_name = q_card.best_rank_match
    suit_name = q_card.best_suit_match

    if rank_name != "Unknown" or suit_name != "Unknown":
        if suit_name != 'reverse' and suit_name != 'deck':
            cv2.circle(image, (x, y), 5, (255, 0, 0), -1)

            cv2.putText(image, (rank_name + ' of'), (x - 60, y - 10), FONT, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(image, (rank_name + ' of'), (x - 60, y - 10), FONT, 1, (0, 246, 147), 2, cv2.LINE_AA)

            cv2.putText(image, suit_name, (x - 60, y + 25), FONT, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(image, suit_name, (x - 60, y + 25), FONT, 1, (0, 246, 147), 2, cv2.LINE_AA)
        else:
            cv2.putText(image, suit_name, (x - 60, y), FONT, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(image, suit_name, (x - 60, y), FONT, 1, (0, 246, 147), 2, cv2.LINE_AA)

    return image


def draw_points(image: ndarray, game: Game) -> ndarray:
    pos = [(IM_WIDTH // 2, IM_HEIGHT // 2 + 20), (30, 60), (IM_WIDTH // 2, 60)]
    for player, (x, y) in zip(game.players, pos):
        cv2.putText(image, (player.name + ' points ' + str(player.points)), (x, y), FONT, 1, (147, 246, 200), 3,
                    cv2.LINE_AA)
        cv2.putText(image, (player.name + ' cards ' + str(player.total_cards)), (x, y + 50), FONT, 1, (147, 246, 200),
                    3, cv2.LINE_AA)

    cv2.putText(image, ('Player1 coins ' + str(game.players[1].coins)), (30, 160), FONT, 1, (147, 246, 200), 3,
                cv2.LINE_AA)
    cv2.putText(image, ('Player2 coins ' + str(game.players[2].coins)), (IM_WIDTH // 2, 160), FONT, 1, (147, 246, 200),
                3, cv2.LINE_AA)

    return image


def draw_actions(image: ndarray, game: Game) -> ndarray:
    if len(game.actions_to_print) > 0:
        height = IM_HEIGHT // 2 + 100
        for action in game.actions_to_print:
            cv2.putText(image, (action), (50, height), FONT, 1, (0, 0, 0), 3, cv2.LINE_AA)
            height += 50
    return image


def draw_coins(image: ndarray, game: Game) -> ndarray:
    if len(game.coins) > 0:
        for player in game.coins:
            for coin in player:
                x, y, r = coin.pos
                cv2.circle(image, (x, y), r, (0, 255, 0), 4)
    return image


def draw_winners(image: ndarray, new_winners: List[str]) -> ndarray:
    if len(new_winners) > 0:
        cv2.putText(image, 'The winners are(is):', (200, IM_HEIGHT // 2 - 100), FONT, 5, (0, 0, 0), 6, cv2.LINE_AA)
        cv2.putText(image, 'The winners are(is):', (200, IM_HEIGHT // 2 - 100), FONT, 5, (0, 255, 255), 4, cv2.LINE_AA)
        h = 0
        for winner in new_winners:
            cv2.putText(image, (winner), (200, IM_HEIGHT // 2 + h), FONT, 5, (0, 0, 0), 6, cv2.LINE_AA)
            cv2.putText(image, (winner), (200, IM_HEIGHT // 2 + h), FONT, 5, (0, 255, 255), 4, cv2.LINE_AA)
            h += 100
    return image


def main_logic(new_frame: ndarray, search: bool, new_game: Optional[Game], new_winners: dict, debug=False) -> \
        Tuple[ndarray, List, bool, dict]:
    global game
    if new_game:  # at the begging, or when is nessesery, create  new game
        players = [Player('Dealer'), Player('Player1'), Player('Player2')]
        game = Game(players)
        new_game = False

    if search:  # only every 15 frame do this part
        cards = []
        pre_proc = preprocess_image(new_frame)
        card_cnts = find_cards(pre_proc)

        if len(card_cnts) != 0:
            for i in range(len(card_cnts)):
                cards.append(preprocess_card(card_cnts[i], new_frame, debug))
                cards[i].best_rank_match, cards[i].best_suit_match, cards[i].rank_diff, cards[i].suit_diff = match_card(
                    cards[i], train_ranks, train_suits)

        game.coins = find_coins(pre_proc)
        game.cards = cards

        game.search_deck()  # find deck and reverse
        game.clean_cards()  # deleate all non card from cards
        game.restore_cards()  # restore cards from prev iter
        game.restore_coins()  # restore coins from prev iter
        game.add_deck()  # add deck and reverse

        game.count_cards()
        game.search_action()  # search for basic actions

        game.set_prev()  # set current state of the game as previosuly for next iter

        game.set_coins()  # cet number of coins and points for print
        game.set_points()

    if len(game.cards) != 0:
        for card in game.cards:
            new_frame = draw_results(new_frame, card)
        temp_cnts = []
        for i in range(len(game.cards)):
            temp_cnts.append(game.cards[i].contour)
        cv2.drawContours(new_frame, temp_cnts, -1, (255, 0, 0), 2)

        new_frame = draw_coins(new_frame, game)
        new_frame = draw_actions(new_frame, game)
        new_frame = draw_points(new_frame, game)
        if new_winners['time'] > 0:
            new_frame = draw_winners(new_frame, new_winners['who'])

    if search:
        new_game = game.new_game()
        if len(new_winners['who']) == 0:
            if game.has_game_concluded() and new_game is False:
                new_winners['who'] = game.who_win()
                new_winners['time'] = 12
        else:
            if new_winners['time'] > 0:
                new_winners['time'] -= 1
            else:
                new_winners['who'] = []

    return new_frame, game.cards, new_game, new_winners


if __name__ == "__main__":
    train_ranks = load_ranks('Card_Imgs/')
    train_suits = load_suits('Card_Imgs/')
    cap = cv2.VideoCapture('video/idk3.mp4')
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total == 0:
        print('Video was not found')
    else:
    # print(total)
        fourcc = cv2.VideoWriter_fourcc(*'MP4V')
        out = cv2.VideoWriter('output/idk3.mp4', fourcc, 30.0, (1920, 1080))

        frames_count = 0
        last_frame = None
        new_game = True
        game = None
        winners = {'who': [], 'time': 0}
        print('Program is running...')
        while cap.isOpened():
            ret, frame = cap.read()
            frames_count += 1
            # if frame is read correctly ret is True
            if not ret:
                print("Can't receive frame (stream end?). \nExiting ...")
                break
            last_frame = frame
            if frames_count % 15 == 0:  # search for cards only on every 15's frame
                frame, cards, new_game, winners = main_logic(frame, True, new_game, winners)
            else:
                frame, cards, new_game, winners = main_logic(frame, False, new_game, winners)
            out.write(frame)
            if cv2.waitKey(1) == ord('q'):
                break
        cap.release()
        out.release()
