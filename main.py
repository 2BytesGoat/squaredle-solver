import json
import cv2
import pyautogui
import numpy as np
import time

class SquardaleBot:
    def __init__(self, letters_str):
        self.letters_str = letters_str
        self.min_word_size = 4
        self.max_word_size = 10

        self.letters = []
        self.nb_rows = 4
        self.nb_cols = 4

        self.raw_image = None
        self.roi_image = None
        self.roi_start = None
        self.roi_end = None
        self.first_letter_position = None
        self.letter_size = None

        self.word_dict = {}
        self.seen_words = set()

        self.init_letters()
        self.init_dictionary()
        self.init_roi()
        self.init_letter_buttons()
    
    def init_letters(self):
        self.letters = []
        for row in self.letters_str.split(" "):
            letters_row = [letter for letter in row]
            self.letters.append(letters_row)
        self.nb_rows = len(self.letters)
        self.nb_cols = len(letters_row)

    def init_dictionary(self):
        self.word_dict = json.load(open('wordle_dictionary.json', 'r'))

    def init_roi(self):
        self.raw_image = np.array(pyautogui.screenshot())
        self.is_selecting_roi = False
        cv2.namedWindow("Image")
        cv2.setMouseCallback("Image", self._region_select)

        cv2.imshow("Image", self.raw_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def init_letter_buttons(self):
        self.button_size = (self.roi_end - self.roi_start) / 4
        self.mouse_start_pos = self.roi_start + self.button_size / 2    

    def search_for_words(self):
        for row in range(self.nb_cols):
            for col in range(self.nb_rows):
                start = np.array([row, col])
                been_to = [self.point_to_id(start)]
                # print(self.get_letter(start))
                self.find_words(start, been_to)

    def connect_letters(self, point_list):
        travel_positions = [self.mouse_start_pos + point[::-1] * self.button_size for point in point_list]

        pyautogui.moveTo(travel_positions[0][0], travel_positions[0][1])
        pyautogui.mouseDown()
        for point in travel_positions:
            pyautogui.moveTo(point[0], point[1])
        pyautogui.mouseUp()

    def find_words(self, start, been_to):
        points = [self.id_to_point(n) for n in been_to]
        word = "".join([self.get_letter(p) for p in points]).lower()

        if len(word) > self.max_word_size:
            return

        if len(word) >= self.min_word_size:
            if word not in self.word_dict[str(len(word))]:
                return
            if word not in self.seen_words and word in self.word_dict["words"]:
                self.connect_letters(points)
                self.seen_words.add(word)
                time.sleep(0.2)
                pyautogui.press("escape")

        for neighbour in self.get_neighbours(start):
            n_id = self.point_to_id(neighbour)
            if n_id not in been_to:
                n_been_to = been_to + [n_id]
                self.find_words(neighbour, n_been_to)
        return

    def is_valid_point(self, point):
        # it's not outside the interval
        return (
            (point[0] >= 0 and point[0] < self.nb_cols) and 
            (point[1] >= 0 and point[1] < self.nb_rows)
        )

    def get_neighbours(self, point):
        neighbours = []
        for y in [-1, 0, 1]:
            for x in [-1, 0, 1]:
                neighbour = point + np.array([x, y])
                if x == 0 and y == 0:
                    continue
                if self.is_valid_point(neighbour):
                    neighbours.append(neighbour)
        return neighbours
    
    def get_letter(self, point):
        return self.letters[point[0]][point[1]]

    def point_to_id(self, point):
        return point[0] * self.nb_cols + point[1]

    def id_to_point(self, id_):
        return np.array([id_ // self.nb_cols, id_ % self.nb_cols])

    def _region_select(self, event, x, y, flags, params):
        if event == cv2.EVENT_LBUTTONDOWN:
            # if mousedown, store the x,y position of the mous
            self.is_selecting_roi = True
            self.roi_start = np.array([x, y])
        elif event == cv2.EVENT_MOUSEMOVE and self.is_selecting_roi:
                # when dragging pressed, draw rectangle in image
                img_copy = self.raw_image.copy()
                cv2.rectangle(img_copy, self.roi_start, (x, y), (0,0,255), 2)
                cv2.imshow("Image", img_copy)
        elif event == cv2.EVENT_LBUTTONUP:
                # on mouseUp, create subimage
                self.is_selecting_roi = False
                self.roi_end = np.array([x, y])
                # You can display the ROI if you show this image
                self.roi_image = self.raw_image[self.roi_start[1]:y, self.roi_start[0]:x]
                # cv2.imshow("subimg", sub_img)
                cv2.destroyAllWindows()
    
    def _find_letters_using_tesseract(self):
        # Yeah ... we're not using this
        import pytesseract

        letters = []
        for row in range(self.nb_rows):
            letters_row = []
            for col in range(self.nb_cols):
                shift = self.button_size * np.array([col, row])
                src_point = (self.roi_start + shift).astype(int)
                dst_point = (src_point + self.button_size).astype(int)
                
                img_slice = self.roi_image[src_point[1]:dst_point[1],src_point[0]:dst_point[0]].copy()

                img_slice = cv2.cvtColor(img_slice, cv2.COLOR_BGR2GRAY)
                img_slice = cv2.threshold(img_slice, 100, 255, cv2.THRESH_BINARY)[1]

                custom_config = r'--oem 3 --psm 10'
                raw_text = pytesseract.image_to_string(img_slice, lang="eng", config=custom_config).strip()
                
                if raw_text.isnumeric():
                    match raw_text:
                        case "0":
                            raw_text = "O"
                        case "1":
                            raw_text = "I"

                letters_row.append(raw_text)

            letters.append(letters_row)

if __name__ == "__main__":
    letters_str = input("Input today's Squaredle: ")
    bot = SquardaleBot(letters_str)
    bot.search_for_words()
