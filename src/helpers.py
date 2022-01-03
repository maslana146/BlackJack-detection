from typing import List, Tuple

import cv2
from cv2 import imshow
import numpy as np
from numpy import ndarray

from models.TrainRanks import TrainRanks
from src.models.Coin import Coin
from src.models.QueryCard import QueryCard
from src.models.TrainSuits import TrainSuits
from config import *


def load_ranks(filepath: str) -> List[TrainRanks]:
    """Loads rank images from directory specified by filepath. Stores
    them in a list of TrainRanks objects."""

    train_ranks = []
    for i, rank in enumerate(['Ace', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
                              'Eight', 'Nine', 'Ten', 'Jack', 'Queen', 'King', 'Queen2', 'Six2']):
        train_ranks.append(TrainRanks())
        if rank != 'Queen2' and rank != 'Six2':
            train_ranks[i].name = rank
        else:
            train_ranks[i].name = rank[:-1]
        filename = rank + '.jpg'
        train_ranks[i].img = cv2.imread(filepath + filename, cv2.IMREAD_GRAYSCALE)

    return train_ranks


def load_suits(filepath: str) -> TrainSuits:
    """Loads suit images from directory specified by filepath. Stores
    them in a list of TrainSuits objects."""

    train_suits = []
    for i, suit in enumerate(['Spades', 'Diamonds', 'Clubs', 'Hearts', 'Clubs2']):
        train_suits.append(TrainSuits())
        if suit != 'Clubs2':
            train_suits[i].name = suit
        else:
            train_suits[i].name = 'Clubs'
        filename = suit + '.jpg'
        train_suits[i].img = cv2.imread(filepath + filename, cv2.IMREAD_GRAYSCALE)
    return train_suits


def preprocess_image(image: ndarray) -> ndarray:
    """Returns a grayed, blurred, and adaptively thresholded camera image."""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # TODO
    # blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 91, 8)

    return thresh


def find_cards(thresh_image: ndarray) -> List[ndarray]:
    """Finds all card-sized contours in a thresholded camera image.
    Returns the number of cards, and a list of card contours sorted
    from largest to smallest."""

    # Find contours and sort their indices by contour size
    cnts, hier = cv2.findContours(thresh_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

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
        if (size < CARD_MAX_AREA) and (size > CARD_MIN_AREA) and (len(approx) == 4):  # and (hier[0][i][3] == -1 )):
            finnal_cnts.append(cnts[i])
    return finnal_cnts


def preprocess_card(contour: ndarray, image: ndarray, show: bool = True) -> QueryCard:
    """Uses contour to find information about the query card. Isolates rank
        and suit images from the card."""

    # Initialize new QueryCard object
    q_card = QueryCard()
    q_card.contour = contour

    # save size for future
    size = cv2.contourArea(contour)
    q_card.size = size

    # Find perimeter of card and use it to approximate corner points
    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.01 * peri, True)
    pts = np.float32(approx)
    q_card.corner_pts = pts

    # Find width and height of card's bounding rectangle
    x, y, w, h = cv2.boundingRect(contour)
    q_card.width, q_card.height = w, h

    # Find center point of card by taking x and y average of the four corners.
    average = np.sum(pts, axis=0) / len(pts)
    cent_x = int(average[0][0])
    cent_y = int(average[0][1])
    q_card.center = [cent_x, cent_y]

    if cent_y > IM_HEIGHT / 2:
        q_card.half = 'bottom'
    else:
        q_card.half = 'top'

    if cent_x > IM_WIDTH / 2:
        q_card.side = 'right'
    else:
        q_card.side = 'left'

    # Warp card into 200x300 flattened image using perspective transform
    q_card.warp = flattener(image, pts, w, h)

    # Grab corner of warped card image and do a 4x zoom
    q_corner = q_card.warp[0:CORNER_HEIGHT, 0:CORNER_WIDTH]
    q_corner_zoom = cv2.resize(q_corner, (0, 0), fx=4, fy=4)

    # Sample known white pixel intensity to determine good threshold level
    # this adaptiveThreshold may need some tunning
    query_thresh = cv2.adaptiveThreshold(q_corner_zoom, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 91,
                                         8)
    # Split in to top and bottom half (top shows rank, bottom shows suit)
    q_rank = query_thresh[20:195, 0:128]
    q_suit = query_thresh[195:336, 0:128]

    q_card.rank_img = find_bounds(q_rank, RANK_WIDTH, RANK_HEIGHT)  # Qrank_sized
    q_card.suit_img = find_bounds(q_suit, SUIT_WIDTH, SUIT_HEIGHT)
    return q_card


def find_bounds(q: ndarray, width: int, height: int) -> ndarray:
    """Find contour and bounding rectangle, isolate and find largest contour and use
        it to resize image to match dimensions. If no contours is find, return empty list"""

    cnts, hier = cv2.findContours(q, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    if len(cnts) != 0:
        x, y, w, h = cv2.boundingRect(cnts[0])
        roi = q[y:y + h, x:x + w]
        sized = cv2.resize(roi, (width, height), 0, 0)
        return sized
    return []


def match_card(q_card: QueryCard, train_ranks: List[TrainRanks], train_suits: List[TrainSuits]) -> \
        Tuple[str, str, int, int]:
    """Finds best rank and suit matches for the query card. Differences
    the query card rank and suit images with the train rank and suit images.
    The best match is the rank or suit image that has the least difference."""

    best_rank_match_diff = 10000
    best_suit_match_diff = 10000
    best_rank_match_name = "Unknown"
    best_suit_match_name = "Unknown"

    # If no contours were found in query card in preprocess_card function,
    # the img size is zero, so skip the differencing process
    # (card will be left as Unknown)

    if (len(q_card.rank_img) != 0) and (len(q_card.suit_img) != 0):
        best_rank_name, best_rank_match_diff = find_most_simmilar(q_card.rank_img, train_ranks)
        best_suit_name, best_suit_match_diff = find_most_simmilar(q_card.suit_img, train_suits)

    # Combine best rank match and best suit match to get query card's identity.
    # If the best matches have too high of a difference value, card identity
    # is still Unknown
    if best_rank_match_diff < RANK_DIFF_MAX:
        best_rank_match_name = best_rank_name

    if best_suit_match_diff < SUIT_DIFF_MAX:
        best_suit_match_name = best_suit_name

    # Return the identiy of the card and the quality of the suit and rank match
    return best_rank_match_name, best_suit_match_name, best_rank_match_diff, best_suit_match_diff


def find_most_simmilar(image: ndarray, train_set: List[TrainRanks]) -> Tuple[str, int]:
    """ Difference the query card image from each of the train images,
        and return the result with the least difference """
    best_match_diff = 10000
    best_name = "Unknown"

    for element in train_set:

        diff_img = cv2.absdiff(image, element.img)
        diff = int(np.sum(diff_img) / 255)

        if diff < best_match_diff:
            best_match_diff = diff
            best_name = element.name
    return best_name, best_match_diff


def find_coins(image: ndarray) -> List[List[Coin]]:
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
                    coins[1].append(Coin((x, y, r), 'right'))
                else:
                    coins[0].append(Coin((x, y, r), 'left'))

    return coins


def find_corners(pts: ndarray, w: int, h: int) -> ndarray:
    """ From un ordered cornner points, return order cornner points """

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


def flattener(image: ndarray, pts: ndarray, w: int, h: int) -> ndarray:
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
