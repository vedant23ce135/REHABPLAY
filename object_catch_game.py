import cv2
import mediapipe as mp
import pygame
import random
import math
import numpy as np
import sys

# ---------------- INIT ----------------
pygame.init()
WIDTH, HEIGHT = 960, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Advanced Rehab Pinch Catch")

font = pygame.font.Font(None, 36)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    # Try DirectShow backend on Windows which can resolve some camera access issues
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    except Exception:
        pass

if not cap.isOpened():
    print("Error: Could not open webcam. Close other apps using the camera or try a different camera index.")
    sys.exit(1)

# -------------- GAME STATE --------------
level = 1
score = 0
objects_caught_in_level = 0
objects_per_level = 5

cursor_radius = 15
clock = pygame.time.Clock()

objects = []

# -------------- FUNCTIONS --------------

def create_object():
    return {
        "x": random.randint(100, WIDTH - 100),
        "y": 0,
        "dx": random.choice([-3, 3]),
        "speed": 3 + level,
        "radius": max(12, 25 - level)
    }

def setup_level():
    global objects
    object_count = 1

    if level >= 5:
        object_count = 2
    if level >= 7:
        object_count = 3

    objects = [create_object() for _ in range(object_count)]

def check_catch(cursor_x, cursor_y, pinch_distance):
    global score, objects_caught_in_level

    if pinch_distance < 40:
        for obj in objects:
            distance = math.sqrt(
                (cursor_x - obj["x"])**2 +
                (cursor_y - obj["y"])**2
            )

            if distance < obj["radius"] + cursor_radius:
                score += 1
                objects_caught_in_level += 1
                obj["x"] = random.randint(100, WIDTH - 100)
                obj["y"] = 0

# -------------- INITIAL SETUP --------------
setup_level()

# -------------- MAIN LOOP --------------

running = True
while running:
    clock.tick(30)

    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (WIDTH, HEIGHT))

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    cursor_x, cursor_y = None, None
    pinch_distance = 1000

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:

            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            lm = hand_landmarks.landmark

            thumb = lm[4]
            index = lm[8]

            thumb_x = int(thumb.x * WIDTH)
            thumb_y = int(thumb.y * HEIGHT)

            index_x = int(index.x * WIDTH)
            index_y = int(index.y * HEIGHT)

            pinch_distance = math.sqrt(
                (thumb_x - index_x)**2 +
                (thumb_y - index_y)**2
            )

            cursor_x = (thumb_x + index_x) // 2
            cursor_y = (thumb_y + index_y) // 2

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0,1))
    screen.blit(frame_surface, (0, 0))

    # -------- Object Updates --------
    for obj in objects:
        obj["y"] += obj["speed"]
        
        if level >= 3:
            obj["x"] += obj["dx"]

        if obj["x"] <= 50 or obj["x"] >= WIDTH - 50:
            obj["dx"] *= -1

        if obj["y"] > HEIGHT:
            obj["y"] = 0
            obj["x"] = random.randint(100, WIDTH - 100)

        pygame.draw.circle(screen, (255, 0, 0), (int(obj["x"]), int(obj["y"])), obj["radius"])

    # -------- Cursor --------
    if cursor_x is not None and cursor_y is not None:
        pygame.draw.circle(screen, (0, 255, 0), (cursor_x, cursor_y), cursor_radius)
        check_catch(cursor_x, cursor_y, pinch_distance)

    # -------- Level Progression --------
    if objects_caught_in_level >= objects_per_level:
        level += 1
        objects_caught_in_level = 0
        setup_level()

    # -------- UI --------
    pygame.draw.rect(screen, (0, 0, 0), (0, 0, WIDTH, 60))
    screen.blit(font.render(f"Level: {level}", True, (255,255,255)), (20,15))
    screen.blit(font.render(f"Score: {score}", True, (255,255,255)), (150,15))
    screen.blit(font.render(f"Progress: {objects_caught_in_level}/5", True, (255,255,255)), (300,15))

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

cap.release()
pygame.quit()