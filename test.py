import cv2
import numpy as np
import time
import os
import Cards
# import VideoStream



if __name__=='__main__':

    IM_WIDTH = 1280
    IM_HEIGHT = 720

    path = os.path.dirname(os.path.abspath(__file__))

    train_ranks = Cards.load_ranks( path + '/Card_Imgs/')
    train_suits = Cards.load_suits( path + '/Card_Imgs/')

    image = cv2.imread('Test_Imgs/card3.jpg')
    pre_proc = Cards.preprocess_image(image)
    cnts_sort, cnt_is_card = Cards.find_cards(pre_proc)

    if len(cnts_sort) != 0:

        # Initialize a new "cards" list to assign the card objects.
        # k indexes the newly made array of cards.
        cards = []
        k = 0

        # For each contour detected:
        for i in range(len(cnts_sort)):
            if (cnt_is_card[i] == 1):

                # Create a card object from the contour and append it to the list of cards.
                # preprocess_card function takes the card contour and contour and
                # determines the cards properties (corner points, etc). It generates a
                # flattened 200x300 image of the card, and isolates the card's
                # suit and rank from the image.
                cards.append(Cards.preprocess_card(cnts_sort[i],image))

                # Find the best rank and suit match for the card.
                cards[k].best_rank_match,cards[k].best_suit_match,cards[k].rank_diff,cards[k].suit_diff = Cards.match_card(cards[k],train_ranks,train_suits)

                # Draw center point and match result on the image.
                image = Cards.draw_results(image, cards[k])
                k = k + 1

        # Draw card contours on image (have to do contours all at once or
        # they do not show up properly for some reason)
        if (len(cards) != 0):
            temp_cnts = []
            for i in range(len(cards)):
                temp_cnts.append(cards[i].contour)
            cv2.drawContours(image,temp_cnts, -1, (255,0,0), 2)


        # Draw framerate in the corner of the image. Framerate is calculated at the end of the main loop,
        # so the first time this runs, framerate will be shown as 0.
    # cv2.putText(image,"FPS: "+str(int(frame_rate_calc)),(10,26),font,0.7,(255,0,255),2,cv2.LINE_AA)

    # Finally, display the image with the identified cards!
    # print(image)
    cv2.imshow("Card Detector", image)

    cv2.waitKey(0)
    cv2.destroyAllWindows()
    # videostream.stop()

    # Calculate framerate
    # t2 = cv2.getTickCount()
    # time1 = (t2-t1)/freq
    # frame_rate_calc = 1/time1