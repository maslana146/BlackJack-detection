import cv2
from config import *
from src.helpers import load_ranks, load_suits, preprocess_image, find_cards, preprocess_card, find_coins, match_card
from src.models.Game import Game
from src.models.Player import Player

font = cv2.FONT_HERSHEY_SIMPLEX


def draw_results(image, qCard):
    """Draw the card name, center point, and contour on the camera image."""

    x = qCard.center[0]
    y = qCard.center[1]
    rank_name = qCard.best_rank_match
    suit_name = qCard.best_suit_match

    if rank_name != "Unknown" or suit_name != "Unknown":

        if suit_name != 'rewers' and suit_name != 'deck':
            cv2.circle(image, (x, y), 5, (255, 0, 0), -1)

            # Draw card name twice, so letters have black outline
            cv2.putText(image, (rank_name + ' of'), (x - 60, y - 10), font, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(image, (rank_name + ' of'), (x - 60, y - 10), font, 1, (0, 246, 147), 2, cv2.LINE_AA)

            cv2.putText(image, suit_name, (x - 60, y + 25), font, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(image, suit_name, (x - 60, y + 25), font, 1, (0, 246, 147), 2, cv2.LINE_AA)
        else:
            # print('here')
            cv2.putText(image, suit_name, (x - 60, y), font, 1, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(image, suit_name, (x - 60, y), font, 1, (0, 246, 147), 2, cv2.LINE_AA)

    return image


def draw_points(image, game):
    pos = [(IM_WIDTH // 2, IM_HEIGHT // 2 + 20), (30, 60), (IM_WIDTH // 2, 60)]
    for player, (x, y) in zip(game.players, pos):
        cv2.putText(image, (player.name + ' points ' + str(player.points)), (x, y), font, 1, (147, 246, 200), 3,
                    cv2.LINE_AA)
        cv2.putText(image, (player.name + ' cards ' + str(player.total_cards)), (x, y + 50), font, 1, (147, 246, 200),
                    3, cv2.LINE_AA)

    cv2.putText(image, ('Player1 coins ' + str(game.players[1].coins)), (30, 160), font, 1, (147, 246, 200), 3,
                cv2.LINE_AA)
    cv2.putText(image, ('Player2 coins ' + str(game.players[2].coins)), (IM_WIDTH // 2, 160), font, 1, (147, 246, 200),
                3, cv2.LINE_AA)

    return image


def draw_actions(image, game):
    if len(game.actions_to_print) > 0:
        height = IM_HEIGHT // 2 + 100
        for action in game.actions_to_print:
            cv2.putText(image, (action), (50, height), font, 1, (0, 0, 0), 3, cv2.LINE_AA)
            height += 50
    return image


def draw_coins(image, game):
    if len(game.coins) > 0:
        for player in game.coins:
            for coin in player:
                x, y, r = coin.pos
                cv2.circle(image, (x, y), r, (0, 255, 0), 4)
    return image


def draw_winners(image, winners):
    if len(winners) > 0:
        cv2.putText(image, 'The winners are(is):', (200, IM_HEIGHT // 2 - 100), font, 5, (0, 0, 0), 6, cv2.LINE_AA)
        cv2.putText(image, 'The winners are(is):', (200, IM_HEIGHT // 2 - 100), font, 5, (0, 255, 255), 4, cv2.LINE_AA)
        h = 0
        for winner in winners:
            cv2.putText(image, (winner), (200, IM_HEIGHT // 2 + h), font, 5, (0, 0, 0), 6, cv2.LINE_AA)
            cv2.putText(image, (winner), (200, IM_HEIGHT // 2 + h), font, 5, (0, 255, 255), 4, cv2.LINE_AA)
            # cv2.putText( image, (winner), (200, IM_HEIGHT//2+h), font, 5, (0, 0, 0), 6, cv2.LINE_AA)

            h += 100
    return image


def f(frame, search, new_game, winners, debug=False, ):
    global game
    if new_game:  # at the begging, or when is nessesery, create  new game
        players = [Player('dealer'), Player('player1'), Player('player2')]
        game = Game(players)
        new_game = False

    if search:  # only every 15 frame do this part
        cards = []
        pre_proc = preprocess_image(frame)
        card_cnts = find_cards(pre_proc)

        if len(card_cnts) != 0:

            for i in range(len(card_cnts)):
                cards.append(preprocess_card(card_cnts[i], frame, debug))

                cards[i].best_rank_match, cards[i].best_suit_match, cards[i].rank_diff, cards[i].suit_diff = match_card(
                    cards[i], train_ranks, train_suits)

        game.coins = find_coins(pre_proc)
        game.cards = cards

        game.search_deck()  # find deck and rewers
        game.clean_cards()  # deleate all non card from cards
        game.restore_cards()  # restore cards from prev iter
        game.restore_coins()  # restore coins from prev iter
        game.add_deck()  # add deck and rewers

        game.count_cards()
        game.search_action()  # search for basic actions

        game.set_prev()  # set current state of the game as previosuly for next iter

        game.set_coins()  # cet number of coins and points for print
        game.set_points()

    if (len(game.cards) != 0):
        for card in game.cards:
            frame = draw_results(frame, card)

        temp_cnts = []
        for i in range(len(game.cards)):
            temp_cnts.append(game.cards[i].contour)
        cv2.drawContours(frame, temp_cnts, -1, (255, 0, 0), 2)

        frame = draw_coins(frame, game)
        frame = draw_actions(frame, game)
        frame = draw_points(frame, game)
        if winners['time'] > 0:
            frame = draw_winners(frame, winners['who'])

    if search:

        new_game = game.new_game()

        if len(winners['who']) == 0:

            if game.has_game_concluded() and new_game == False:
                winners['who'] = game.who_win()
                winners['time'] = 12
                print(winners)
        else:
            if winners['time'] > 0:
                winners['time'] -= 1
            else:
                winners['who'] = []

    return frame, game.cards, new_game, winners


if __name__ == "__main__":
    train_ranks = load_ranks('../Card_Imgs/')
    train_suits = load_suits('../Card_Imgs/')
    cap = cv2.VideoCapture('easy1 (1).mp4')
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(total)
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    out = cv2.VideoWriter('easy1.mp4', fourcc, 30.0, (1920, 1080))
    frames_count = 0
    last_frame = None
    new_game = True
    game = None
    winners = {'who': [], 'time': 0}
    # players = [Player('dealer'), Player('player1'), Player('player2')]
    # game = Game(players)
    while cap.isOpened():
        ret, frame = cap.read()
        frames_count += 1
        # if frame is read correctly ret is True
        if not ret:
            print("Can't receive frame (stream end?). Exiting ...")
            break
        # if frames_count == 1300: # TODO: chcek coins
        last_frame = frame
        #     break

        if frames_count % 15 == 0:  # search for cards only on every 15's frame
            frame, cards, new_game, winners = f(frame, True, new_game, winners)
        else:
            frame, cards, new_game, winners = f(frame, False, new_game, winners)

        out.write(frame)

        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    out.release()
