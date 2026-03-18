"""
PHYSIO REHAB AI - MediaPipe 0.10+ Tasks API Version
====================================================
SETUP:
  pip install mediapipe opencv-python numpy

  The script auto-downloads the pose model on first run (~3MB).

CONTROLS:
  S   → Shoulder Raise exercise
  Q   → Sit-to-Stand (squat) exercise
  R   → Reset reps & score
  ESC → Quit
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import time
import math
import urllib.request
import os

# ─── Auto-download model ───────────────────────────────────────────────────────
MODEL_PATH = "pose_landmarker_lite.task"
MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading pose model (first run only, ~3MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("✓ Model downloaded!")

# ─── Pose skeleton connections ────────────────────────────────────────────────
POSE_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,7),(0,4),(4,5),(5,6),(6,8),
    (9,10),(11,12),(11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
    (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    (11,23),(12,24),(23,24),(23,25),(24,26),(25,27),(26,28),
    (27,29),(28,30),(29,31),(30,32),(27,31),(28,32),
]

# ─── Color Palette (BGR) ──────────────────────────────────────────────────────
C = {
    "bg":           (10, 8, 20),
    "panel":        (20, 16, 40),
    "panel2":       (28, 22, 55),
    "cyan":         (255, 220, 0),
    "neon":         (0, 255, 180),
    "purple":       (200, 80, 180),
    "white":        (255, 255, 255),
    "gray":         (120, 110, 140),
    "red":          (60, 60, 220),
    "orange":       (30, 160, 255),
    "shoulder_col": (0, 220, 255),
    "squat_col":    (0, 255, 140),
}

FONT      = cv2.FONT_HERSHEY_DUPLEX
FONT_BOLD = cv2.FONT_HERSHEY_SIMPLEX
WIN_W, WIN_H = 1280, 720

# ─── App state ────────────────────────────────────────────────────────────────
state = {
    "exercise":      "shoulder",
    "reps":          0,
    "stage":         None,
    "angle":         0.0,
    "session_start": time.time(),
    "particles":     [],
    "feedback":      "",
    "feedback_timer":0.0,
    "angle_history": [],
    "rep_flash":     0.0,
    "score":         0,
    "combo":         0,
}

# ─── Landmark indices ─────────────────────────────────────────────────────────
R_SHOULDER, R_ELBOW, R_WRIST = 12, 14, 16
L_HIP, L_KNEE, L_ANKLE       = 23, 25, 27

# ─── Particles ────────────────────────────────────────────────────────────────
def spawn_particles(cx, cy, color, n=18):
    for _ in range(n):
        a = np.random.uniform(0, 2 * math.pi)
        s = np.random.uniform(2, 8)
        state["particles"].append({
            "x": cx, "y": cy,
            "vx": math.cos(a)*s, "vy": math.sin(a)*s,
            "life": 1.0, "color": color,
            "size": np.random.randint(3, 8),
        })

def update_particles(frame):
    alive = []
    for p in state["particles"]:
        p["x"] += p["vx"]; p["y"] += p["vy"]; p["vy"] += 0.2
        p["life"] -= 0.035
        if p["life"] > 0:
            col = tuple(int(c * p["life"]) for c in p["color"])
            cv2.circle(frame, (int(p["x"]), int(p["y"])), p["size"], col, -1)
            alive.append(p)
    state["particles"] = alive

# ─── Drawing helpers ──────────────────────────────────────────────────────────
def draw_rounded_rect(img, pt1, pt2, color, radius=12, thickness=-1, alpha=1.0):
    overlay = img.copy()
    x1, y1 = pt1; x2, y2 = pt2; r = radius
    cv2.rectangle(overlay, (x1+r, y1), (x2-r, y2), color, thickness)
    cv2.rectangle(overlay, (x1, y1+r), (x2, y2-r), color, thickness)
    for cx, cy in [(x1+r,y1+r),(x2-r,y1+r),(x1+r,y2-r),(x2-r,y2-r)]:
        cv2.circle(overlay, (cx,cy), r, color, thickness)
    cv2.addWeighted(overlay, alpha, img, 1-alpha, 0, img)

def draw_text_centered(img, text, cx, cy, font, scale, color, thickness=1):
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    cv2.putText(img, text, (cx-tw//2, cy+th//2), font, scale, color, thickness, cv2.LINE_AA)

def draw_glow_circle(img, center, radius, color, thickness=2, glow_layers=3):
    for i in range(glow_layers, 0, -1):
        col = tuple(max(0, min(255, int(c*(i/glow_layers)*0.4))) for c in color)
        cv2.circle(img, center, radius+i*3, col, thickness+i*2)
    cv2.circle(img, center, radius, color, thickness, cv2.LINE_AA)

def draw_arc_progress(img, center, radius, value, max_val, color, bg_color, thickness=14):
    cx, cy = center
    start_angle, end_angle = 135, 405
    span     = end_angle - start_angle
    progress = min(value / max_val, 1.0)
    for angle in range(0, int(span), 2):
        a_rad = math.radians(start_angle + angle)
        x = int(cx + radius * math.cos(a_rad))
        y = int(cy + radius * math.sin(a_rad))
        cv2.circle(img, (x,y), thickness//2, bg_color, -1)
    filled = int(span * progress)
    for angle in range(0, filled, 2):
        a_rad = math.radians(start_angle + angle)
        x = int(cx + radius * math.cos(a_rad))
        y = int(cy + radius * math.sin(a_rad))
        t = angle / span
        r = int(color[0]*(1-t) + C["neon"][0]*t)
        g = int(color[1]*(1-t) + C["neon"][1]*t)
        b = int(color[2]*(1-t) + C["neon"][2]*t)
        cv2.circle(img, (x,y), thickness//2, (r,g,b), -1)
    if filled > 0:
        tip_rad = math.radians(start_angle + filled)
        tx = int(cx + radius * math.cos(tip_rad))
        ty = int(cy + radius * math.sin(tip_rad))
        draw_glow_circle(img, (tx,ty), thickness//2+2, color, -1, 2)

# ─── Math ─────────────────────────────────────────────────────────────────────
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b; bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))

def lm_xy(landmarks, idx, w, h):
    lm = landmarks[idx]
    return [lm.x * w, lm.y * h]

# ─── Exercise logic ───────────────────────────────────────────────────────────
def process_shoulder(landmarks, w, h):
    shoulder = lm_xy(landmarks, R_SHOULDER, w, h)
    elbow    = lm_xy(landmarks, R_ELBOW,    w, h)
    wrist    = lm_xy(landmarks, R_WRIST,    w, h)
    angle    = calculate_angle(shoulder, elbow, wrist)
    state["angle"] = angle
    state["angle_history"].append(angle)
    if len(state["angle_history"]) > 60: state["angle_history"].pop(0)

    if angle < 35:
        if state["stage"] == "up":
            state["reps"]  += 1
            state["combo"] += 1
            state["score"] += 10 + state["combo"] * 2
            state["rep_flash"] = 1.0
            spawn_particles(int(elbow[0]), int(elbow[1]), C["shoulder_col"])
            state["feedback"] = "GREAT REP!"; state["feedback_timer"] = time.time()
        state["stage"] = "down"
    elif angle > 155:
        state["stage"] = "up"
        state["feedback"] = "HOLD STEADY"; state["feedback_timer"] = time.time()
    return elbow, angle

def process_squat(landmarks, w, h):
    hip   = lm_xy(landmarks, L_HIP,   w, h)
    knee  = lm_xy(landmarks, L_KNEE,  w, h)
    ankle = lm_xy(landmarks, L_ANKLE, w, h)
    angle = calculate_angle(hip, knee, ankle)
    state["angle"] = angle
    state["angle_history"].append(angle)
    if len(state["angle_history"]) > 60: state["angle_history"].pop(0)

    if angle > 160:
        if state["stage"] == "down":
            state["reps"]  += 1
            state["combo"] += 1
            state["score"] += 10 + state["combo"] * 2
            state["rep_flash"] = 1.0
            spawn_particles(int(knee[0]), int(knee[1]), C["squat_col"])
            state["feedback"] = "PERFECT SQUAT!"; state["feedback_timer"] = time.time()
        state["stage"] = "up"
    elif angle < 90:
        state["stage"] = "down"
        state["feedback"] = "LOWER! GOOD DEPTH"; state["feedback_timer"] = time.time()
    return knee, angle

# ─── Skeleton drawing ─────────────────────────────────────────────────────────
def draw_skeleton(canvas, landmarks, w, h, color, ox, oy, sx, sy):
    pts = [(int(lm.x*w*sx+ox), int(lm.y*h*sy+oy)) for lm in landmarks]
    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(canvas, pts[a], pts[b], (100,80,160), 2, cv2.LINE_AA)
    for px, py in pts:
        cv2.circle(canvas, (px,py), 5, color, -1, cv2.LINE_AA)
        cv2.circle(canvas, (px,py), 5, C["white"], 1, cv2.LINE_AA)

# ─── UI panels ────────────────────────────────────────────────────────────────
def draw_grid(frame):
    for x in range(0, WIN_W, 80): cv2.line(frame, (x,0), (x,WIN_H), (30,25,55), 1)
    for y in range(0, WIN_H, 80): cv2.line(frame, (0,y), (WIN_W,y), (30,25,55), 1)

def draw_scanlines(frame):
    overlay = frame.copy()
    for y in range(0, WIN_H, 4): cv2.line(overlay, (0,y), (WIN_W,y), (0,0,0), 1)
    cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)

def draw_left_panel(frame, ex_color):
    draw_rounded_rect(frame, (10,10), (300,WIN_H-10), C["panel"], radius=16, alpha=0.85)
    draw_text_centered(frame, "PHYSIO",   155, 55, FONT_BOLD, 1.1, ex_color, 2)
    draw_text_centered(frame, "REHAB AI", 155, 85, FONT_BOLD, 0.9, C["gray"],  1)
    cv2.line(frame, (30,105), (280,105), C["panel2"], 2)

    for btn_y, ex_key, label, sublabel, btn_color, active_bg in [
        (120, "shoulder", "[ S ]  SHOULDER RAISE", "Arm Raise Exercise",  C["shoulder_col"], (40,35,70)),
        (195, "squat",    "[ Q ]  SIT-TO-STAND",   "Knee Rehab Exercise", C["squat_col"],    (25,50,35)),
    ]:
        active = state["exercise"] == ex_key
        col    = btn_color if active else C["gray"]
        bg     = active_bg if active else (25,20,45)
        draw_rounded_rect(frame, (20,btn_y), (290,btn_y+65), bg, radius=10, alpha=0.95 if active else 0.6)
        if active: cv2.rectangle(frame, (20,btn_y), (25,btn_y+65), btn_color, -1)
        draw_text_centered(frame, label,    155, btn_y+25, FONT, 0.5,  col, 1)
        draw_text_centered(frame, sublabel, 155, btn_y+48, FONT, 0.38, C["white"] if active else C["gray"], 1)

    cv2.line(frame, (30,278), (280,278), C["panel2"], 2)

    # Angle arc
    draw_arc_progress(frame, (155,378), 70, state["angle"], 180.0, ex_color, C["panel2"], thickness=12)
    draw_text_centered(frame, f"{int(state['angle'])}", 155, 370, FONT_BOLD, 1.5, ex_color, 2)
    draw_text_centered(frame, "DEGREES", 155, 400, FONT, 0.4, C["gray"], 1)

    stage_txt = (state["stage"] or "READY").upper()
    stage_col = C["neon"] if state["stage"] == "up" else C["orange"] if state["stage"] == "down" else C["gray"]
    draw_rounded_rect(frame, (50,425), (260,458), (30,28,60), radius=8, alpha=0.8)
    draw_text_centered(frame, f"STAGE: {stage_txt}", 155, 441, FONT, 0.5, stage_col, 1)

    cv2.line(frame, (30,472), (280,472), C["panel2"], 2)

    flash   = state["rep_flash"]
    rep_col = ex_color if flash < 0.1 else C["white"]
    if flash > 0:
        draw_rounded_rect(frame, (50,482), (260,550), ex_color, radius=10, alpha=min(0.4, flash*0.4))
        state["rep_flash"] = max(0.0, flash - 0.05)
    draw_text_centered(frame, "REPS",              155, 502, FONT,      0.5,  C["gray"],  1)
    draw_text_centered(frame, str(state["reps"]),  155, 542, FONT_BOLD, 2.2,  rep_col,   3)
    draw_text_centered(frame, f"SCORE: {state['score']}", 155, 576, FONT, 0.5, C["cyan"], 1)

    if state["combo"] > 1:
        draw_text_centered(frame, f"COMBO x{state['combo']}", 155, 600, FONT, 0.5,
                           C["orange"] if state["combo"] < 5 else C["red"], 1)

    elapsed = int(time.time() - state["session_start"])
    mins, secs = divmod(elapsed, 60)
    cv2.line(frame, (30,618), (280,618), C["panel2"], 2)
    draw_text_centered(frame, f"{mins:02d}:{secs:02d}", 155, 645, FONT_BOLD, 1.1, C["gray"], 2)
    draw_text_centered(frame, "[ R ] Reset   [ ESC ] Quit", 155, 682, FONT, 0.36, (70,60,90), 1)

def draw_mini_graph(frame, x, y, gw, gh, data, color):
    if len(data) < 2: return
    draw_rounded_rect(frame, (x,y), (x+gw,y+gh), C["panel"], radius=8, alpha=0.7)
    cv2.putText(frame, "ANGLE GRAPH", (x+8,y+16), FONT, 0.32, C["gray"], 1, cv2.LINE_AA)
    pts = [(x + int(i/len(data)*gw),
            y + gh - int((v/180)*(gh-20)) - 5)
           for i, v in enumerate(data)]
    for i in range(1, len(pts)):
        t = i / len(pts)
        r = int(color[0]*t + C["purple"][0]*(1-t))
        g = int(color[1]*t + C["purple"][1]*(1-t))
        b = int(color[2]*t + C["purple"][2]*(1-t))
        cv2.line(frame, pts[i-1], pts[i], (r,g,b), 2, cv2.LINE_AA)
    if pts: draw_glow_circle(frame, pts[-1], 4, color, -1, 2)

def draw_feedback(frame):
    if not state["feedback"]: return
    elapsed = time.time() - state["feedback_timer"]
    if elapsed > 2.0: return
    alpha = max(0.0, 1.0 - elapsed / 2.0)
    y_off = int(elapsed * 30)
    txt   = state["feedback"]
    cx, cy = WIN_W//2 + 160, WIN_H//2 - 120 - y_off
    (tw, th), _ = cv2.getTextSize(txt, FONT_BOLD, 1.0, 2)
    draw_rounded_rect(frame, (cx-tw//2-20,cy-th-10), (cx+tw//2+20,cy+10),
                      C["panel2"], radius=10, alpha=alpha*0.85)
    col = tuple(int(c*alpha) for c in C["neon"])
    cv2.putText(frame, txt, (cx-tw//2, cy), FONT_BOLD, 1.0, col, 2, cv2.LINE_AA)

def draw_corner_deco(frame, color):
    L, T = 40, 3
    pts = [(315,10),(WIN_W-15,10),(315,WIN_H-10),(WIN_W-15,WIN_H-10)]
    dirs = [(1,1),(-1,1),(1,-1),(-1,-1)]
    for (px,py),(dx,dy) in zip(pts, dirs):
        cv2.line(frame, (px,py), (px+dx*L,py), color, T)
        cv2.line(frame, (px,py), (px,py+dy*L), color, T)

def draw_exercise_label(frame, ex_color, ex_name):
    draw_rounded_rect(frame, (WIN_W-340,10), (WIN_W-10,60), C["panel"], radius=12, alpha=0.85)
    cv2.rectangle(frame, (WIN_W-340,10), (WIN_W-335,60), ex_color, -1)
    draw_text_centered(frame, f"● {ex_name}", WIN_W-175, 38, FONT_BOLD, 0.7, ex_color, 2)

# ─── Reset ────────────────────────────────────────────────────────────────────
def reset_exercise():
    for k in ("reps","score","combo"): state[k] = 0
    for k in ("stage","feedback"): state[k] = None if k == "stage" else ""
    state["angle"] = 0.0
    state["angle_history"] = []
    state["rep_flash"] = 0.0
    state["particles"] = []
    state["session_start"] = time.time()

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIN_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, WIN_H)

    cv2.namedWindow("PHYSIO REHAB AI", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("PHYSIO REHAB AI", WIN_W, WIN_H)

    options = mp_vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=mp_vision.RunningMode.VIDEO,
        min_pose_detection_confidence=0.6,
        min_pose_presence_confidence=0.6,
        min_tracking_confidence=0.6,
    )

    with mp_vision.PoseLandmarker.create_from_options(options) as landmarker:
        frame_idx = 0

        while cap.isOpened():
            ret, raw_frame = cap.read()
            if not ret: break

            raw_frame = cv2.flip(raw_frame, 1)
            raw_frame = cv2.resize(raw_frame, (WIN_W, WIN_H))
            h, w = raw_frame.shape[:2]

            # Run pose detection
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB,
                                 data=cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB))
            timestamp = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            if timestamp == 0: timestamp = frame_idx * 33
            result    = landmarker.detect_for_video(mp_image, timestamp)
            frame_idx += 1

            # Build canvas
            canvas = np.full((WIN_H, WIN_W, 3), C["bg"], dtype=np.uint8)
            draw_grid(canvas)

            # Camera region
            cam_x1, cam_y1, cam_x2, cam_y2 = 310, 10, WIN_W-10, WIN_H-10
            cam_w, cam_h = cam_x2-cam_x1, cam_y2-cam_y1
            cam_crop = cv2.resize(raw_frame, (cam_w, cam_h))
            cv2.addWeighted(cam_crop, 0.85, np.zeros_like(cam_crop), 0.15, 0, cam_crop)
            canvas[cam_y1:cam_y2, cam_x1:cam_x2] = cam_crop

            ex_color = C["shoulder_col"] if state["exercise"] == "shoulder" else C["squat_col"]
            ex_name  = "SHOULDER RAISE"  if state["exercise"] == "shoulder" else "SIT-TO-STAND"

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                sx, sy    = cam_w / w, cam_h / h
                draw_skeleton(canvas, landmarks, w, h, ex_color, cam_x1, cam_y1, sx, sy)

                try:
                    if state["exercise"] == "shoulder":
                        joint, angle = process_shoulder(landmarks, w, h)
                    else:
                        joint, angle = process_squat(landmarks, w, h)

                    jx = int(joint[0] * sx + cam_x1)
                    jy = int(joint[1] * sy + cam_y1)
                    draw_glow_circle(canvas, (jx, jy), 28, ex_color, 2, 3)
                    draw_text_centered(canvas, f"{int(angle)}", jx, jy, FONT_BOLD, 0.7, C["white"], 2)
                except Exception:
                    pass
            else:
                state["feedback"] = "Stand in camera view"
                state["feedback_timer"] = time.time()

            update_particles(canvas)
            draw_left_panel(canvas, ex_color)
            draw_corner_deco(canvas, ex_color)
            draw_exercise_label(canvas, ex_color, ex_name)
            draw_mini_graph(canvas, WIN_W-340, WIN_H-130, 325, 120,
                            state["angle_history"], ex_color)
            draw_feedback(canvas)
            draw_scanlines(canvas)

            cv2.imshow("PHYSIO REHAB AI", canvas)

            key = cv2.waitKey(1) & 0xFF
            if   key == 27:        break
            elif key == ord('s'):  state["exercise"] = "shoulder"; reset_exercise()
            elif key == ord('q'):  state["exercise"] = "squat";    reset_exercise()
            elif key == ord('r'):  reset_exercise()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
