import cv2
from cv2 import imshow
import numpy as np
from models.TrainRanks import Train_ranks
from src.models.Coin import Coin
from src.models.QueryCard import Query_card
from src.models.TrainSuits import Train_suits
from config import *


def load_ranks(filepath):
    """Loads rank images from directory specified by filepath. Stores
    them in a list of Train_ranks objects."""

    train_ranks = []
    i = 0

    for Rank in ['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                 'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King', 'Queen2', 'Six2']:
        train_ranks.append(Train_ranks())
        if Rank != 'Queen2' and Rank != 'Six2':
            train_ranks[i].name = Rank
        else:
            train_ranks[i].name = Rank[:-1]
        filename = Rank + '.jpg'
        # print(filepath+filename)
        train_ranks[i].img = cv2.imread(filepath + filename, cv2.IMREAD_GRAYSCALE)
        i = i + 1

    return train_ranks


def load_suits(filepath):
    """Loads suit images from directory specified by filepath. Stores
    them in a list of Train_suits objects."""

    train_suits = []
    i = 0

    for Suit in ['Spades', 'Diamonds', 'Clubs', 'Hearts', 'Clubs2']:
        train_suits.append(Train_suits())
        if Suit != 'Clubs2':
            train_suits[i].name = Suit
        else:
            train_suits[i].name = 'Clubs'
        filename = Suit + '.jpg'
        train_suits[i].img = cv2.imread(filepath + filename, cv2.IMREAD_GRAYSCALE)
        i = i + 1

    return train_suits


def preprocess_image(image):
    """Returns a grayed, blurred, and adaptively thresholded camera image."""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)

    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 91, 8)

    return thresh


def find_cards(thresh_image):
    """Finds all card-sized contours in a thresholded camera image.
    Returns the number of cards, and a list of card contours sorted
    from largest to smallest."""

    # Find contours and sort their indices by contour size
    cnts, hier = cv2.findContours(thresh_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    index_sort = sorted(range(len(cnts)), key=lambda i: cv2.contourArea(cnts[i]), reverse=True)

    # If there are no contours, do nothing
    if len(cnts) == 0:
        return [], []

    # Determine which of the contours are cards by applying the
    # following criteria: 1) Smaller area than the maximum card size,
    # 2), bigger area than the minimum card size, 3) have no parents,
    # and 4) have four corners
    finnal_cnts = []
    for i in range(len(cnts)):
        size = cv2.contourArea(cnts[i])
        peri = cv2.arcLength(cnts[i], True)
        approx = cv2.approxPolyDP(cnts[i], 0.01 * peri, True)
        # print(size, len(approx), hier[0][i][3])
        if ((size < CARD_MAX_AREA) and (size > CARD_MIN_AREA) and (len(approx) == 4)):  # and (hier[0][i][3] == -1 )):
            finnal_cnts.append(cnts[i])
    return finnal_cnts


def preprocess_card(contour, image, show=True):
    """Uses contour to find information about the query card. Isolates rank
        and suit images from the card."""

    # Initialize new Query_card object
    qCard = Query_card()
    qCard.contour = contour

    # save size for future
    size = cv2.contourArea(contour)
    qCard.size = size

    # Find perimeter of card and use it to approximate corner points
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.01 * peri, True)
    pts = np.float32(approx)
    qCard.corner_pts = pts

    # Find width and height of card's bounding rectangle
    x, y, w, h = cv2.boundingRect(contour)
    ##########################################################
    if show: image_copy = image.copy()
    if show: cv2.rectangle(image_copy, (x, y), (x + w, y + h), (0, 255, 0), 2)
    if show: imshow(image_copy)

    qCard.width, qCard.height = w, h

    # Find center point of card by taking x and y average of the four corners.
    average = np.sum(pts, axis=0) / len(pts)
    cent_x = int(average[0][0])
    cent_y = int(average[0][1])
    qCard.center = [cent_x, cent_y]

    if cent_y > IM_HEIGHT / 2:
        qCard.half = 'bottom'
    else:
        qCard.half = 'top'

    if cent_x > IM_WIDTH / 2:
        qCard.side = 'right'
    else:
        qCard.side = 'left'

    # Warp card into 200x300 flattened image using perspective transform
    # testa = (image.copy(), pts, w, h)
    qCard.warp = flattener(image, pts, w, h)
    if show: imshow(qCard.warp)

    # Grab corner of warped card image and do a 4x zoom
    Qcorner = qCard.warp[0:CORNER_HEIGHT, 0:CORNER_WIDTH]
    Qcorner_zoom = cv2.resize(Qcorner, (0, 0), fx=4, fy=4)
    if show: imshow(Qcorner_zoom)
    # Sample known white pixel intensity to determine good threshold level

    # this adaptiveThreshold may need some tunning
    query_thresh = cv2.adaptiveThreshold(Qcorner_zoom, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 91,
                                         8)

    if show: imshow(query_thresh)

    # Split in to top and bottom half (top shows rank, bottom shows suit)
    Qrank = query_thresh[20:195, 0:128]
    Qsuit = query_thresh[195:336, 0:128]

    if show: print('##########################################################')
    if show: imshow(Qrank)
    if show: print('##########################################################')
    if show: imshow(Qsuit)

    qCard.rank_img = find_bounds(Qrank, RANK_WIDTH, RANK_HEIGHT)  # Qrank_sized
    qCard.suit_img = find_bounds(Qsuit, SUIT_WIDTH, SUIT_HEIGHT)

    if show: print('##########################################################')
    if show: imshow(qCard.rank_img)
    if show: print('##########################################################')
    if show: imshow(qCard.suit_img)
    return qCard


def find_bounds(Q, WIDTH, HEIGHT):
    """Find countour and bounding rectangle, isolate and find largest contour and use
        it to resize image to match dimensions"""

    cnts, hier = cv2.findContours(Q, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    if len(cnts) != 0:
        x, y, w, h = cv2.boundingRect(cnts[0])
        roi = Q[y:y + h, x:x + w]
        sized = cv2.resize(roi, (WIDTH, HEIGHT), 0, 0)
        return sized
    return []


def match_card(qCard, train_ranks, train_suits):
    """Finds best rank and suit matches for the query card. Differences
    the query card rank and suit images with the train rank and suit images.
    The best match is the rank or suit image that has the least difference."""

    best_rank_match_diff = 10000
    best_suit_match_diff = 10000
    best_rank_match_name = "Unknown"
    best_suit_match_name = "Unknown"
    i = 0

    # If no contours were found in query card in preprocess_card function,
    # the img size is zero, so skip the differencing process
    # (card will be left as Unknown)

    if (len(qCard.rank_img) != 0) and (len(qCard.suit_img) != 0):
        best_rank_name, best_rank_match_diff = find_most_simmilar(qCard.rank_img, train_ranks)
        best_suit_name, best_suit_match_diff = find_most_simmilar(qCard.suit_img, train_suits)

    # Combine best rank match and best suit match to get query card's identity.
    # If the best matches have too high of a difference value, card identity
    # is still Unknown
    if (best_rank_match_diff < RANK_DIFF_MAX):
        best_rank_match_name = best_rank_name

    if (best_suit_match_diff < SUIT_DIFF_MAX):
        best_suit_match_name = best_suit_name

    # Return the identiy of the card and the quality of the suit and rank match
    return best_rank_match_name, best_suit_match_name, best_rank_match_diff, best_suit_match_diff


def find_most_simmilar(image, train_set):
    """ Difference the query card image from each of the train images,
        and return the result with the least difference """
    best_match_diff = 10000
    best_name = "Unknown"

    for element in train_set:

        diff_img = cv2.absdiff(image, element.img)
        diff = int(np.sum(diff_img) / 255)

        if diff < best_match_diff:
            # best_diff_img = diff_img
            best_match_diff = diff
            best_name = element.name
    return best_name, best_match_diff


def find_coins(image):
    coins = [[], []]
    circles = cv2.HoughCircles(image, cv2.HOUGH_GRADIENT, 1, 80, param1=32, param2=32, minRadius=50, maxRadius=70)
    # ensure at least som e circles were found
    if circles is not None:
        # convert the (x, y) coordinates and radius of the circles to integers
        circles = np.round(circles[0, :]).astype("int")
        # loop over the (x, y) coordinates and radius of the circles
        for (x, y, r) in circles:
            if y < 150:
                if x > IM_WIDTH / 2:
                    # side =
                    coins[1].append(Coin((x, y, r), 'right'))
                else:
                    coins[0].append(Coin((x, y, r), 'left'))

    return coins


def find_corners(pts, w, h):
    ''' From un ordered cornner points, return order cornner points '''

    temp_rect = np.zeros((4, 2), dtype="float32")

    s = np.sum(pts, axis=2)
    # top left corner have smaller sum
    top_left = pts[np.argmin(s)]
    # bottom_left corner have smaller sum
    bottom_right = pts[np.argmax(s)]

    diff = np.diff(pts, axis=-1)
    # top right cornner have smaller diffrence
    top_right = pts[np.argmin(diff)]
    # bottom left cornner have smaller diffrence
    bottom_left = pts[np.argmax(diff)]

    if w <= 0.8 * h:  # If card is vertically oriented
        temp_rect[0] = top_left
        temp_rect[1] = top_right
        temp_rect[2] = bottom_right
        temp_rect[3] = bottom_left

    elif w >= 1.2 * h:  # If card is horizontally oriented
        temp_rect[0] = bottom_left
        temp_rect[1] = top_left
        temp_rect[2] = top_right
        temp_rect[3] = bottom_right

    else:  # If card is diamond oriented
        # If furthest left point is higher than furthest right point,
        # card is tilted to the left.
        if pts[1][0][1] <= pts[3][0][1]:
            # If card is titled to the left, approxPolyDP returns points
            # in this order: top right, top left, bottom left, bottom right
            temp_rect[0] = pts[1][0]  # Top left
            temp_rect[1] = pts[0][0]  # Top right
            temp_rect[2] = pts[3][0]  # Bottom right
            temp_rect[3] = pts[2][0]  # Bottom left

        # If furthest left point is lower than furthest right point,
        # card is tilted to the right
        else:
            # If card is titled to the right, approxPolyDP returns points
            # in this order: top left, bottom left, bottom right, top right
            temp_rect[0] = pts[0][0]  # Top left
            temp_rect[1] = pts[3][0]  # Top right
            temp_rect[2] = pts[2][0]  # Bottom right
            temp_rect[3] = pts[1][0]  # Bottom left

    return temp_rect


def flattener(image, pts, w, h):
    # print(pts)
    """Flattens an image of a card into a top-down 200x300 perspective.
    Returns the flattened, re-sized, grayed image.
    See www.pyimagesearch.com/2014/08/25/4-point-opencv-getperspective-transform-example/"""

    corrner_points = find_corners(pts, w, h)

    maxWidth = 200
    maxHeight = 300

    # Create destination array, calculate perspective transform matrix,
    # and warp card image
    dst = np.array([[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]], np.float32)
    M = cv2.getPerspectiveTransform(corrner_points, dst)
    warp = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    warp = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY)

    return warp
