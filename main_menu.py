import cv2
import numpy as np
import pyautogui
import mediapipe as mp
import time
import ctypes
from core.gaze_estimator import GazeEstimator
from config import DEAD_ZONE, SMOOTHING_FACTOR, SENSITIVITY

pyautogui.FAILSAFE = False

screen_width, screen_height = pyautogui.size()
CENTER_X, CENTER_Y = screen_width // 2, screen_height // 2
history_x, history_y = CENTER_X, CENTER_Y

UI_MARGIN = 60
BUTTON_WIDTH = 400
BUTTON_HEIGHT = 120
blink_counter, blink_threshold = 0, 2
selected_option = None

sandbox_button = (screen_width//2 - BUTTON_WIDTH//2, screen_height//2 - 200, BUTTON_WIDTH, BUTTON_HEIGHT)
rhythm_button = (screen_width//2 - BUTTON_WIDTH//2, screen_height//2 + 50, BUTTON_WIDTH, BUTTON_HEIGHT)
quit_button = (screen_width - UI_MARGIN - 120, screen_height - UI_MARGIN - 50, 120, 50)

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
gaze_estimator = GazeEstimator()
cap = cv2.VideoCapture(0)
cv2.namedWindow("Main Menu", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Main Menu", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

ctypes.windll.user32.ShowCursor(False)

cursor_x, cursor_y = CENTER_X, CENTER_Y

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)
    menu_canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            nose_tip = face_landmarks.landmark[1]
            nose_x_norm = nose_tip.x - 0.5
            nose_y_norm = nose_tip.y - 0.5

            if abs(nose_x_norm) < DEAD_ZONE:
                nose_x_norm = 0
            if abs(nose_y_norm) < DEAD_ZONE:
                nose_y_norm = 0

            target_x = int(CENTER_X + (nose_x_norm * screen_width * SENSITIVITY))
            target_y = int(CENTER_Y + (nose_y_norm * screen_height * SENSITIVITY))

            cursor_x = int((1 - SMOOTHING_FACTOR) * target_x + SMOOTHING_FACTOR * history_x)
            cursor_y = int((1 - SMOOTHING_FACTOR) * target_y + SMOOTHING_FACTOR * history_y)

            cursor_x = max(0, min(screen_width - 1, cursor_x))
            cursor_y = max(0, min(screen_height - 1, cursor_y))

            history_x, history_y = cursor_x, cursor_y

            if sandbox_button[0] < cursor_x < sandbox_button[0] + sandbox_button[2] and sandbox_button[1] < cursor_y < sandbox_button[1] + sandbox_button[3]:
                selected_option = "sandbox"
            elif rhythm_button[0] < cursor_x < rhythm_button[0] + rhythm_button[2] and rhythm_button[1] < cursor_y < rhythm_button[1] + rhythm_button[3]:
                selected_option = "rhythm"
            elif quit_button[0] < cursor_x < quit_button[0] + quit_button[2] and quit_button[1] < cursor_y < quit_button[1] + quit_button[3]:
                selected_option = "quit"
            else:
                selected_option = None

    _, blink_detected = gaze_estimator.extract_features(frame)
    if blink_detected:
        blink_counter += 1
    else:
        if blink_counter >= blink_threshold and selected_option:
            cap.release()
            cv2.destroyAllWindows()
            ctypes.windll.user32.ShowCursor(True)

            if selected_option == "sandbox":
                import sandbox
            elif selected_option == "rhythm":
                import rhythm_game
            elif selected_option == "quit":
                exit()
            break
        blink_counter = 0

    cv2.putText(menu_canvas, "Select Mode with Nose, Blink to Start", (screen_width//2 - 300, UI_MARGIN), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    # Draw buttons
    sx, sy, sw, sh = sandbox_button
    rx, ry, rw, rh = rhythm_button
    qx, qy, qw, qh = quit_button

    sandbox_color = (0, 255, 0) if selected_option == "sandbox" else (100, 100, 100)
    rhythm_color = (0, 255, 255) if selected_option == "rhythm" else (100, 100, 100)
    quit_color = (0, 0, 255) if selected_option == "quit" else (100, 100, 100)

    cv2.rectangle(menu_canvas, (sx, sy), (sx + sw, sy + sh), sandbox_color, 3)
    cv2.rectangle(menu_canvas, (rx, ry), (rx + rw, ry + rh), rhythm_color, 3)
    cv2.rectangle(menu_canvas, (qx, qy), (qx + qw, qy + qh), quit_color, 2)

    cv2.putText(menu_canvas, "Sandbox Mode", (sx + 40, sy + 70), cv2.FONT_HERSHEY_SIMPLEX, 1.5, sandbox_color, 3)
    cv2.putText(menu_canvas, "Rhythm Game", (rx + 50, ry + 70), cv2.FONT_HERSHEY_SIMPLEX, 1.5, rhythm_color, 3)
    cv2.putText(menu_canvas, "Quit", (qx + 20, qy + 35), cv2.FONT_HERSHEY_SIMPLEX, 1, quit_color, 2)

    # Draw cursor as red circle
    cv2.circle(menu_canvas, (cursor_x, cursor_y), 15, (0, 0, 255), -1)

    cv2.imshow("Main Menu", menu_canvas)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
ctypes.windll.user32.ShowCursor(True)
