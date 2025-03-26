import cv2
import mediapipe as mp
import pyautogui
import pygame
import numpy as np
import json
import random
import time
import ctypes
import subprocess
from core.gaze_estimator import GazeEstimator  # Blink detection

# Disable PyAutoGUI fail-safe (we use 'q' as manual escape key)
pyautogui.FAILSAFE = False

# Load calibration settings
CALIBRATION_FILE = "calibration_settings.json"

def load_calibration_settings():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            settings = json.load(f)
            print("\u2705 Loaded Calibration Settings:", settings)
            return settings["dead_zone"], settings["smoothing"], settings["sensitivity"]
    except FileNotFoundError:
        print("\u26a0\ufe0f No calibration file found! Using default settings.")
        return 0.02, 0.8, 3.5

# Apply calibration settings
DEAD_ZONE, SMOOTHING_FACTOR, SENSITIVITY = load_calibration_settings()

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Map musical notes to each column
note_sounds = {
    0: pygame.mixer.Sound("assets/piano/c.wav"),
    1: pygame.mixer.Sound("assets/piano/e.wav"),
    2: pygame.mixer.Sound("assets/piano/g.wav"),
}

# Initialize FaceMesh for nose tracking
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Initialize EyePy's GazeEstimator
gaze_estimator = GazeEstimator()

# Screen settings
screen_width, screen_height = pyautogui.size()

# Rhythm game settings
num_columns = 3
column_width = screen_width // num_columns
notes = []
note_speed = 5
spawn_interval = 1.0
last_spawn_time = time.time()
score = 0
game_start_time = time.time()
game_duration = 40  # seconds

timer_displayed = False
game_end_time = None

# Nose cursor
cursor_x = screen_width // 2
cursor_y = screen_height - 100
selected_column = 0

# Open webcam
cap = cv2.VideoCapture(0)
blink_counter = 0
blink_threshold = 2

cv2.namedWindow("Rhythm Game", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Rhythm Game", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# Always hide system cursor
ctypes.windll.user32.ShowCursor(False)

game_active = True

CENTER_X, CENTER_Y = screen_width // 2, screen_height // 2
history_x, history_y = CENTER_X, CENTER_Y

# Clamp settings
MIN_CURSOR_X = 0
MAX_CURSOR_X = screen_width - 1

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if game_active and time.time() - game_start_time >= game_duration:
        game_active = False
        timer_displayed = True
        game_end_time = time.time()

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            nose_tip = face_landmarks.landmark[1]
            nose_x_norm = nose_tip.x - 0.5
            nose_y_norm = nose_tip.y - 0.5

            if abs(nose_x_norm) < DEAD_ZONE:
                nose_x_norm = 0
            if abs(nose_y_norm) < DEAD_ZONE:
                nose_y_norm = 0

            cursor_x = int((1 - SMOOTHING_FACTOR) * (CENTER_X + (nose_x_norm * screen_width * SENSITIVITY)) + SMOOTHING_FACTOR * history_x)
            cursor_y = int((1 - SMOOTHING_FACTOR) * (CENTER_Y + (nose_y_norm * screen_height * SENSITIVITY)) + SMOOTHING_FACTOR * history_y)

            # Clamp X position to prevent overshooting
            cursor_x = max(MIN_CURSOR_X, min(MAX_CURSOR_X, cursor_x))

            pyautogui.moveTo(cursor_x, cursor_y, _pause=False)
            history_x, history_y = cursor_x, cursor_y

            selected_column = cursor_x // column_width

    # Blink detection
    _, blink_detected = gaze_estimator.extract_features(frame)
    if blink_detected:
        blink_counter += 1
    else:
        if blink_counter >= blink_threshold:
            if game_active:
                for note in notes:
                    if note["column"] == selected_column and screen_height - 150 <= note["y"] <= screen_height - 50:
                        notes.remove(note)
                        score += 1
                        note_sounds[selected_column].play()
                        break
            elif timer_displayed and game_end_time and time.time() - game_end_time > 2:
                if selected_column == 0:
                    print("\U0001f7e2 RETRY selected")
                    notes = []
                    score = 0
                    game_start_time = time.time()
                    last_spawn_time = time.time()
                    game_active = True
                    timer_displayed = False
                    blink_counter = 0
                    continue
                elif selected_column == 2:
                    print("\U0001f3e0 MENU selected")
                    cap.release()
                    cv2.destroyAllWindows()
                    ctypes.windll.user32.ShowCursor(True)
                    subprocess.Popen(["python", "main_menu.py"])
                    exit()
        blink_counter = 0

    # Update game state
    if game_active:
        if time.time() - last_spawn_time > spawn_interval:
            new_column = random.randint(0, num_columns - 1)
            notes.append({"column": new_column, "y": 0})
            last_spawn_time = time.time()

        for note in notes:
            note["y"] += note_speed
        notes = [note for note in notes if note["y"] < screen_height]

    # Draw screen
    game_canvas = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

    for i in range(num_columns):
        x = i * column_width
        cv2.rectangle(game_canvas, (x, 0), (x + column_width, screen_height), (50, 50, 50), 2)

    for note in notes:
        x = note["column"] * column_width + column_width // 2
        cv2.circle(game_canvas, (x, note["y"]), 20, (0, 255, 0), -1)

    # Target zone
    cv2.rectangle(game_canvas, (0, screen_height - 150), (screen_width, screen_height - 50), (255, 255, 255), 2)
    cv2.circle(game_canvas, (selected_column * column_width + column_width // 2, screen_height - 75), 15, (0, 0, 255), -1)

    if not timer_displayed:
        cv2.putText(game_canvas, f"Score: {score}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(game_canvas, "Blink to Hit, Move Nose to Select Column", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    else:
        cv2.putText(game_canvas, f"Final Score: {score}", (screen_width//2 - 200, screen_height//2 - 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

        for i in range(num_columns):
            label = ""
            if i == 0:
                label = "Retry"
            elif i == 2:
                label = "Menu"
            if label:
                x = i * column_width + 40
                y = screen_height - 60
                cv2.putText(game_canvas, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)

        highlight_x = selected_column * column_width + column_width // 2
        highlight_y = screen_height - 75
        cv2.circle(game_canvas, (highlight_x, highlight_y), 25, (0, 255, 255), 4)

        cv2.putText(game_canvas, "Blink to Retry (Left) or Menu (Right)", (screen_width//2 - 300, screen_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

        if game_end_time and time.time() - game_end_time <= 2:
            cv2.putText(game_canvas, "Get ready...", (screen_width//2 - 150, screen_height - 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 200, 255), 3)

    cv2.imshow("Rhythm Game", game_canvas)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
# Restore system cursor when done
ctypes.windll.user32.ShowCursor(True)
