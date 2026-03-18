import cv2
import mediapipe as mp
import random
import math
import numpy as np

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

window_name = "Finger Coordination Trainer"
cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# -------- LEVEL CONFIG (unchanged) --------
levels = {
    1: {"type": "single",           "goal": 5,  "frames": 15, "label": "NOVICE",  "color": (180, 220, 0)},
    2: {"type": "combo_single_hand","goal": 6,  "frames": 15, "label": "SKILLED",  "color": (255, 160, 0)},
    3: {"type": "two_hand_single",  "goal": 8,  "frames": 12, "label": "EXPERT",   "color": (255, 60,  180)},
    4: {"type": "two_hand_combo",   "goal": 10, "frames": 10, "label": "MASTER",   "color": (60,  60,  255)},
}

fingers = ["INDEX", "MIDDLE", "RING", "PINKY", "THUMB"]

current_level   = 1
score           = 0
gesture_counter = 0
last_match      = False

# ── UI state ──
flash_timer  = 0
flash_bgr    = (0, 255, 120)
particles    = []
match_pulse  = 0.0

# -------- PARTICLE SYSTEM --------
def spawn_particles(cx, cy, bgr, n=22):
    for _ in range(n):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 10)
        life  = random.randint(18, 38)
        particles.append({
            "x": float(cx), "y": float(cy),
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed,
            "life": life, "max_life": life,
            "bgr": bgr,
            "size": random.randint(3, 7),
        })

def update_draw_particles(frame):
    dead = []
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.35
        p["life"] -= 1
        a  = p["life"] / p["max_life"]
        c  = tuple(int(ch * a) for ch in p["bgr"])
        sz = max(1, int(p["size"] * a))
        ix, iy = int(p["x"]), int(p["y"])
        H, W = frame.shape[:2]
        if 0 < ix < W and 0 < iy < H:
            cv2.circle(frame, (ix, iy), sz, c, -1)
        if p["life"] <= 0:
            dead.append(p)
    for d in dead:
        particles.remove(d)

# -------- DRAWING HELPERS --------
def blend_rect(frame, x, y, w, h, bgr, alpha=0.55):
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(frame.shape[1], x+w), min(frame.shape[0], y+h)
    if x2 <= x1 or y2 <= y1:
        return
    roi = frame[y1:y2, x1:x2]
    overlay = np.full_like(roi, bgr)
    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)
    frame[y1:y2, x1:x2] = roi

def glow_text(frame, text, pos, font, scale, bgr, thick, spread=3):
    x, y = pos
    for s in range(spread, 0, -1):
        a = 0.4 * (1 - s / spread)
        gc = tuple(int(c * a) for c in bgr)
        cv2.putText(frame, text, (x - s, y), font, scale, gc, thick + s * 2)
    cv2.putText(frame, text, pos, font, scale, bgr, thick)

def draw_prog_bar(frame, x, y, w, h, ratio, fill_bgr, track=(25, 25, 35)):
    blend_rect(frame, x, y, w, h, track, alpha=0.85)
    fw = int(w * min(1.0, max(0.0, ratio)))
    if fw > 0:
        blend_rect(frame, x, y, fw, h, fill_bgr, alpha=0.95)
    # highlight
    cv2.rectangle(frame, (x, y), (x + w, y + 2), (255, 255, 255), -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), tuple(c // 2 for c in fill_bgr), 1)

def draw_scanlines(frame, alpha=0.06):
    h, w = frame.shape[:2]
    ov = np.zeros_like(frame)
    for yy in range(0, h, 4):
        cv2.line(ov, (0, yy), (w, yy), (0, 0, 0), 1)
    cv2.addWeighted(ov, alpha, frame, 1.0, 0, frame)

def draw_vignette(frame):
    h, w = frame.shape[:2]
    Y, X = np.ogrid[:h, :w]
    mask = ((X - w/2)**2 / (w/2)**2 + (Y - h/2)**2 / (h/2)**2)
    mask = np.clip(mask, 0, 1)
    mask = (mask * 110).astype(np.uint8)
    vg   = np.stack([mask]*3, axis=-1)
    frame[:] = cv2.subtract(frame, vg)

def draw_grid(frame, alpha=0.04):
    h, w = frame.shape[:2]
    ov = np.zeros_like(frame)
    step = 55
    for xx in range(0, w, step):
        cv2.line(ov, (xx, 0), (xx, h), (0, 200, 130), 1)
    for yy in range(0, h, step):
        cv2.line(ov, (0, yy), (w, yy), (0, 200, 130), 1)
    cv2.addWeighted(ov, alpha, frame, 1.0, 0, frame)

# -------- TARGET GENERATION (unchanged) --------
def generate_target(level):
    t = levels[level]["type"]
    if t == "single":
        return random.choice(fingers)
    elif t == "combo_single_hand":
        return tuple(sorted(random.sample(fingers, 2)))
    elif t == "two_hand_single":
        return {"Left": random.choice(fingers), "Right": random.choice(fingers)}
    elif t == "two_hand_combo":
        return {"Left":  tuple(sorted(random.sample(fingers, 2))),
                "Right": tuple(sorted(random.sample(fingers, 2)))}

current_target = generate_target(current_level)

lm_style   = mp_draw.DrawingSpec(color=(0, 230, 180), thickness=2, circle_radius=4)
conn_style = mp_draw.DrawingSpec(color=(0, 120, 80),  thickness=2)

# -------- MAIN LOOP --------
with mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
) as hands:

    while True:
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        H, W, _ = frame.shape

        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)

        # Darken for cyberpunk atmosphere
        frame = (frame.astype(np.float32) * 0.5).astype(np.uint8)
        draw_grid(frame)

        detected = {"Left": [], "Right": []}

        if result.multi_hand_landmarks:
            for hand_lm, handedness in zip(result.multi_hand_landmarks, result.multi_handedness):
                mp_draw.draw_landmarks(frame, hand_lm, mp_hands.HAND_CONNECTIONS, lm_style, conn_style)

                side = handedness.classification[0].label
                lm   = hand_lm.landmark

                index_up  = lm[8].y  < lm[6].y
                middle_up = lm[12].y < lm[10].y
                ring_up   = lm[16].y < lm[14].y
                pinky_up  = lm[20].y < lm[18].y

                px = (lm[0].x + lm[5].x + lm[9].x) / 3
                py = (lm[0].y + lm[5].y + lm[9].y) / 3
                t_tip = math.sqrt((lm[4].x-px)**2 + (lm[4].y-py)**2)
                t_ip  = math.sqrt((lm[3].x-px)**2 + (lm[3].y-py)**2)
                thumb_up = t_tip > t_ip * 1.2

                finger_state = {
                    "INDEX": index_up, "MIDDLE": middle_up,
                    "RING":  ring_up,  "PINKY":  pinky_up,
                    "THUMB": thumb_up,
                }
                detected[side] = sorted([f for f, v in finger_state.items() if v])

        # -------- MATCH LOGIC (unchanged) --------
        lt    = levels[current_level]["type"]
        match = False

        if lt == "single":
            all_up = detected["Left"] + detected["Right"]
            if len(all_up) == 1 and all_up[0] == current_target:
                match = True
        elif lt == "combo_single_hand":
            for side in ["Left", "Right"]:
                if tuple(detected[side]) == current_target:
                    match = True
        elif lt == "two_hand_single":
            if (len(detected["Left"]) == 1 and len(detected["Right"]) == 1 and
                detected["Left"][0]  == current_target["Left"] and
                detected["Right"][0] == current_target["Right"]):
                match = True
        elif lt == "two_hand_combo":
            if (tuple(detected["Left"])  == current_target["Left"] and
                tuple(detected["Right"]) == current_target["Right"]):
                match = True

        # -------- STABILITY (unchanged) --------
        if match:
            gesture_counter = gesture_counter + 1 if last_match else 1
        else:
            gesture_counter = 0
        last_match = match

        scored_this_frame = False
        if gesture_counter >= levels[current_level]["frames"]:
            score += 1
            scored_this_frame = True
            lc = levels[current_level]["color"]
            spawn_particles(W // 2, H // 2, lc, n=28)
            flash_timer = 14
            flash_bgr   = lc
            current_target  = generate_target(current_level)
            gesture_counter = 0

        # -------- LEVEL PROGRESSION (unchanged) --------
        if score >= levels[current_level]["goal"]:
            current_level += 1
            if current_level > 4:
                current_level = 4
            score = 0
            lc = levels[current_level]["color"]
            spawn_particles(W // 2, H // 3, lc, n=60)
            flash_timer = 28
            flash_bgr   = lc
            current_target  = generate_target(current_level)

        # ── Match pulse animation ──
        match_pulse = min(match_pulse + 0.15, 1.0) if match else max(match_pulse - 0.08, 0.0)

        # ── Flash overlay ──
        if flash_timer > 0:
            fa = (flash_timer / 28.0) * 0.38
            ov = np.full_like(frame, flash_bgr)
            cv2.addWeighted(ov, fa, frame, 1.0, 0, frame)
            flash_timer -= 1

        update_draw_particles(frame)
        draw_scanlines(frame)
        draw_vignette(frame)

        # ====================================================
        #  UI  LAYOUT
        # ====================================================
        PAD     = 18
        PW      = 330       # panel width
        PH      = H - PAD*2

        lc_bgr  = levels[current_level]["color"]   # BGR tuple from config

        # ── Left Panel background ──
        blend_rect(frame, PAD, PAD, PW, PH, (8, 8, 18), alpha=0.72)
        cv2.rectangle(frame, (PAD, PAD), (PAD+PW, PAD+PH), lc_bgr, 1)

        cur_y = PAD + 28  # cursor for vertical layout

        # ─ Level badge ─
        badge_h = 48
        blend_rect(frame, PAD+16, cur_y-4, PW-32, badge_h, lc_bgr, alpha=0.20)
        cv2.rectangle(frame, (PAD+16, cur_y-4), (PAD+PW-16, cur_y+badge_h-4), lc_bgr, 1)
        glow_text(frame,
                  f"LVL {current_level}   {levels[current_level]['label']}",
                  (PAD+30, cur_y+28),
                  cv2.FONT_HERSHEY_DUPLEX, 0.72, lc_bgr, 2)
        cur_y += badge_h + 30

        # ─ Score ─
        cv2.putText(frame, "SCORE",
                    (PAD+26, cur_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (110, 110, 140), 1)
        cur_y += 6
        glow_text(frame,
                  f"{score}  /  {levels[current_level]['goal']}",
                  (PAD+26, cur_y+44),
                  cv2.FONT_HERSHEY_DUPLEX, 1.4, (240, 240, 255), 2, spread=2)
        cur_y += 60

        # ─ Score progress bar ─
        bar_x = PAD + 26
        bar_w = PW - 52
        draw_prog_bar(frame, bar_x, cur_y, bar_w, 12,
                      score / levels[current_level]["goal"], lc_bgr)
        cur_y += 38

        # ─ Hold progress ─
        cv2.putText(frame, "HOLD PROGRESS",
                    (bar_x, cur_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (110, 110, 140), 1)
        cur_y += 8
        hold_ratio = gesture_counter / levels[current_level]["frames"]
        hold_col   = (40, 240, 80) if match else (0, 160, 60)
        draw_prog_bar(frame, bar_x, cur_y, bar_w, 10, hold_ratio, hold_col)
        cur_y += 42

        # ─ Target gesture ─
        cv2.putText(frame, "TARGET GESTURE",
                    (bar_x, cur_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (110, 110, 140), 1)
        cur_y += 10

        tgt_h = 88
        if match_pulse > 0.05:
            glow_col = tuple(int(c * match_pulse * 0.45) for c in lc_bgr)
            blend_rect(frame, PAD+14, cur_y-2, PW-28, tgt_h+4, glow_col, alpha=0.55)
        blend_rect(frame, PAD+16, cur_y, PW-32, tgt_h, (16, 16, 28), alpha=0.88)
        cv2.rectangle(frame, (PAD+16, cur_y), (PAD+PW-16, cur_y+tgt_h),
                      lc_bgr if match else (55, 55, 70), 1)

        if isinstance(current_target, dict):
            lt_str = current_target["Left"]  if isinstance(current_target["Left"],  str) else " + ".join(current_target["Left"])
            rt_str = current_target["Right"] if isinstance(current_target["Right"], str) else " + ".join(current_target["Right"])
            cv2.putText(frame, f"L: {lt_str}", (PAD+28, cur_y+32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 210, 255), 1)
            cv2.putText(frame, f"R: {rt_str}", (PAD+28, cur_y+64),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 155, 0), 1)
        else:
            tgt_str = current_target if isinstance(current_target, str) else " + ".join(current_target)
            glow_text(frame, tgt_str,
                      (PAD+28, cur_y+54),
                      cv2.FONT_HERSHEY_DUPLEX, 0.80, (0, 230, 255), 2)
        cur_y += tgt_h + 20

        # ─ Match indicator ─
        ind_h = 34
        if match:
            blend_rect(frame, PAD+16, cur_y, PW-32, ind_h, (0, 160, 50), alpha=0.35)
            cv2.rectangle(frame, (PAD+16, cur_y), (PAD+PW-16, cur_y+ind_h), (0, 215, 80), 1)
            glow_text(frame, "  MATCHED!", (PAD+28, cur_y+22),
                      cv2.FONT_HERSHEY_SIMPLEX, 0.66, (0, 255, 100), 2)
        else:
            blend_rect(frame, PAD+16, cur_y, PW-32, ind_h, (0, 0, 0), alpha=0.40)
            cv2.rectangle(frame, (PAD+16, cur_y), (PAD+PW-16, cur_y+ind_h), (50, 50, 65), 1)
            cv2.putText(frame, "  WAITING...", (PAD+28, cur_y+22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.60, (75, 75, 95), 1)
        cur_y += ind_h + 26

        # ─ Detected fingers ─
        cv2.putText(frame, "DETECTED", (bar_x, cur_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (110, 110, 140), 1)
        cur_y += 8
        for side, col in [("Left", (0, 210, 255)), ("Right", (255, 155, 0))]:
            d = detected[side]
            d_str = "  ".join(d) if d else "—"
            cv2.putText(frame, f"{side[0]}: {d_str}", (bar_x, cur_y+20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, col, 1)
            cur_y += 26

        # ─ Bottom hint ─
        hint_y = PAD + PH - 28
        cv2.line(frame, (PAD+16, hint_y-14), (PAD+PW-16, hint_y-14), (45, 45, 60), 1)
        cv2.putText(frame, "[1] [2] [3] [4] Change Level    [Q] Quit",
                    (PAD+18, hint_y+8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 100), 1)

        # ── Top-center title ──
        tx = PAD + PW + 30
        title = "FINGER  COORDINATION  TRAINER"
        ts, tf = 0.72, cv2.FONT_HERSHEY_DUPLEX
        tw = cv2.getTextSize(title, tf, ts, 1)[0][0]
        title_x = tx + ((W - PAD - tx) - tw) // 2
        glow_text(frame, title, (title_x, PAD + 30), tf, ts, lc_bgr, 1, spread=4)
        cv2.line(frame, (tx, PAD + 42), (W - PAD, PAD + 42), lc_bgr, 1)

        cv2.imshow(window_name, frame)

        key = cv2.waitKey(1) & 0xFF
        if key in [ord('1'), ord('2'), ord('3'), ord('4')]:
            current_level  = int(chr(key))
            score          = 0
            current_target = generate_target(current_level)
        if key == ord('q') or key == 27:
            break

cap.release()
cv2.destroyAllWindows()