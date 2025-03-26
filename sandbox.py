import cv2
import mediapipe as mp
import pyautogui
import pygame
import numpy as np
import json
import random
import subprocess  # <-- added
from core.gaze_estimator import GazeEstimator
from config import DEAD_ZONE, SMOOTHING_FACTOR, SENSITIVITY

pyautogui.FAILSAFE = False

UI_MARGIN = 60
QUIT_BTN_WIDTH = 120
QUIT_BTN_HEIGHT = 50

pygame.init()
pygame.mixer.init()

screen_width, screen_height = pyautogui.size()
cv2.namedWindow("Sandbox", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Sandbox", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

note_order = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
white_notes = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
black_notes_map = {'C': 'C#', 'D': 'D#', 'F': 'F#', 'G': 'G#', 'A': 'A#'}

white_key_width = screen_width // 14
white_key_height = int(screen_height * 0.35)
black_key_width = white_key_width // 2
black_key_height = int(white_key_height * 0.6)

slider_value = 50
knob_angle = 135
radio_selected = False
slider_selected = False
knob_selected = False
note_rects = []
pressed_notes = set()

CENTER_X, CENTER_Y = screen_width // 2, screen_height // 2
history_x, history_y = CENTER_X, CENTER_Y
blink_counter = 0
blink_threshold = 2

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)
gaze_estimator = GazeEstimator()
cap = cv2.VideoCapture(0)

def load_piano_sounds():
    sounds = {}
    for note in note_order:
        try:
            sounds[note] = pygame.mixer.Sound(f"assets/piano/{note}.wav")
        except:
            print(f"Missing sound for {note}")
    return sounds

piano_sounds = load_piano_sounds()

def get_sustain_duration_from_angle(angle):
    return np.interp(angle, [135, 405], [100, 1000])

def apply_effect(note, volume, angle):
    sound = piano_sounds.get(note)
    if sound:
        adjusted_volume = max(0.0, min(1.0, volume / 100))
        sound.set_volume(adjusted_volume)
        if radio_selected:
            sustain_ms = int(get_sustain_duration_from_angle(angle))
            channel = sound.play()
            if channel:
                channel.fadeout(sustain_ms)
        else:
            sound.play()
        pressed_notes.add(note)

locked_slider_y = None
locked_knob_x = None

quit_button = (
    screen_width - UI_MARGIN - QUIT_BTN_WIDTH,
    screen_height - UI_MARGIN - QUIT_BTN_HEIGHT,
    QUIT_BTN_WIDTH,
    QUIT_BTN_HEIGHT
)

clock = pygame.time.Clock()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    sandbox = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            nose_tip = face_landmarks.landmark[1]
            nose_x_norm = nose_tip.x - 0.5
            nose_y_norm = nose_tip.y - 0.5

            if abs(nose_x_norm) < DEAD_ZONE:
                nose_x_norm = 0
            if abs(nose_y_norm) < DEAD_ZONE:
                nose_y_norm = 0

            if slider_selected and locked_slider_y is not None:
                cursor_x = screen_width - UI_MARGIN - 80
                cursor_y = int((1 - SMOOTHING_FACTOR) * (CENTER_Y + (nose_y_norm * screen_height * SENSITIVITY)) + SMOOTHING_FACTOR * locked_slider_y)
                history_y = cursor_y
            elif knob_selected and locked_knob_x is not None:
                cursor_y = UI_MARGIN + 140
                cursor_x = int((1 - SMOOTHING_FACTOR) * (CENTER_X + (nose_x_norm * screen_width * SENSITIVITY)) + SMOOTHING_FACTOR * locked_knob_x)
                history_x = cursor_x
            else:
                cursor_x = int((1 - SMOOTHING_FACTOR) * (CENTER_X + (nose_x_norm * screen_width * SENSITIVITY)) + SMOOTHING_FACTOR * history_x)
                cursor_y = int((1 - SMOOTHING_FACTOR) * (CENTER_Y + (nose_y_norm * screen_height * SENSITIVITY)) + SMOOTHING_FACTOR * history_y)
                history_x, history_y = cursor_x, cursor_y

            pyautogui.moveTo(cursor_x, cursor_y, duration=0.05)

    _, blink_detected = gaze_estimator.extract_features(frame)
    if blink_detected:
        blink_counter += 1
    else:
        if blink_counter >= blink_threshold:
            cursor_x, cursor_y = pyautogui.position()
            if slider_selected:
                slider_selected = False
                locked_slider_y = None
            elif knob_selected:
                knob_selected = False
                locked_knob_x = None
            elif UI_MARGIN < cursor_x < UI_MARGIN + 80 and UI_MARGIN + 40 < cursor_y < UI_MARGIN + 120:
                radio_selected = not radio_selected
            elif screen_width - UI_MARGIN - 80 < cursor_x < screen_width - UI_MARGIN and UI_MARGIN + 40 < cursor_y < UI_MARGIN + 290:
                slider_selected = True
                locked_slider_y = cursor_y
            elif CENTER_X - 80 < cursor_x < CENTER_X + 80 and UI_MARGIN + 60 < cursor_y < UI_MARGIN + 220:
                knob_selected = True
                locked_knob_x = cursor_x
            elif quit_button[0] < cursor_x < quit_button[0] + quit_button[2] and quit_button[1] < cursor_y < quit_button[1] + quit_button[3]:
                subprocess.Popen(["python", "main_menu.py"])
                cap.release()
                cv2.destroyAllWindows()
                exit()
            else:
                for rect in note_rects:
                    if rect[5] == 'black' and rect[0] < cursor_x < rect[2] and rect[1] < cursor_y < rect[3]:
                        note = rect[4]
                        apply_effect(note, slider_value, knob_angle)
                        break
                else:
                    for rect in note_rects:
                        if rect[5] == 'white' and rect[0] < cursor_x < rect[2] and rect[1] < cursor_y < rect[3]:
                            note = rect[4]
                            apply_effect(note, slider_value, knob_angle)
                            break
            blink_counter = 0

    cursor_x, cursor_y = pyautogui.position()
    if slider_selected:
        if UI_MARGIN + 40 < cursor_y < UI_MARGIN + 290:
            slider_value = max(0, min(100, int((UI_MARGIN + 290 - cursor_y) / 2.5)))
    if knob_selected:
        knob_center_x = CENTER_X
        dx = cursor_x - knob_center_x
        knob_angle = max(135, min(405, int(135 + dx / 2)))

    cv2.putText(sandbox, "Sandbox DAW Controls", (screen_width//2 - 250, UI_MARGIN), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
    cv2.circle(sandbox, (UI_MARGIN + 30, UI_MARGIN + 80), 40, (255, 255, 255), 3)
    if radio_selected:
        cv2.circle(sandbox, (UI_MARGIN + 30, UI_MARGIN + 80), 20, (255, 255, 255), -1)
    cv2.putText(sandbox, "Sustain On/Off", (UI_MARGIN + 90, UI_MARGIN + 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.rectangle(sandbox, (screen_width - UI_MARGIN - 80, UI_MARGIN + 40), (screen_width - UI_MARGIN, UI_MARGIN + 290), (255, 255, 255), 3)
    slider_y = UI_MARGIN + 290 - int(slider_value * 2.5)
    cv2.rectangle(sandbox, (screen_width - UI_MARGIN - 80, slider_y), (screen_width - UI_MARGIN, slider_y + 30), (0, 255, 0), -1)
    cv2.putText(sandbox, f"Volume", (screen_width - UI_MARGIN - 180, UI_MARGIN + 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    knob_x, knob_y = CENTER_X, UI_MARGIN + 140
    knob_color = (0, 255, 0) if knob_selected else (100, 100, 100)
    cv2.circle(sandbox, (knob_x, knob_y), 80, knob_color, -1)
    angle_radians = np.radians(knob_angle - 135)
    line_x = int(knob_x + 55 * np.cos(angle_radians))
    line_y = int(knob_y + 55 * np.sin(angle_radians))
    cv2.line(sandbox, (knob_x, knob_y), (line_x, line_y), (255, 255, 255), 5)
    cv2.putText(sandbox, "Sustain", (knob_x + 90, knob_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(sandbox, f"{int(get_sustain_duration_from_angle(knob_angle))} ms", (knob_x + 90, knob_y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 180, 180), 2)

    note_rects.clear()
    piano_width = white_key_width * len(white_notes)
    white_start_x = (screen_width - piano_width) // 2
    white_positions = []
    for i, note in enumerate(white_notes):
        x1 = white_start_x + i * white_key_width
        x2 = x1 + white_key_width
        y1 = screen_height - white_key_height - UI_MARGIN
        y2 = screen_height - UI_MARGIN
        color = (200, 200, 200) if note in pressed_notes else (255, 255, 255)
        cv2.rectangle(sandbox, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(sandbox, (x1, y1), (x2, y2), (0, 0, 0), 2)
        cv2.putText(sandbox, note, (x1 + 10, y2 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        note_rects.append((x1, y1, x2, y2, note, 'white'))
        white_positions.append(x1)

    for i in range(len(white_positions) - 1):
        note = white_notes[i % len(white_notes)]
        if note in black_notes_map:
            black_note = black_notes_map[note]
            base_x = white_positions[i]
            x1 = base_x + white_key_width - black_key_width // 2
            x2 = x1 + black_key_width
            y1 = screen_height - white_key_height - UI_MARGIN
            y2 = int(y1 + black_key_height)
            color = (80, 80, 80) if black_note in pressed_notes else (0, 0, 0)
            cv2.rectangle(sandbox, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(sandbox, (x1, y1), (x2, y2), (255, 255, 255), 1)
            note_rects.append((x1, y1, x2, y2, black_note, 'black'))

    pressed_notes.clear()

    # Draw Menu button
    x, y, w, h = quit_button
    cv2.rectangle(sandbox, (x, y), (x + w, y + h), (0, 255, 255), 2)
    cv2.putText(sandbox, "Menu", (x + 20, y + 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    cv2.imshow("Sandbox", sandbox)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    clock.tick(60)

cap.release()
cv2.destroyAllWindows()
