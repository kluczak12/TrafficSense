import os
import re
import cv2
import sys
import time
import numpy as np
from collections import defaultdict, deque
sys.path.insert(0, os.path.dirname(__file__))
from pedestrian_detection import detect_pedestrians
from collision_detection import CollisionDetector
from annotation_loader import AnnotationManager


FRAMES_DIR = os.environ.get("FRAMES_DIR", "/data/frames")
TARGET_FPS = int(os.environ.get("TARGET_FPS", "30"))
PRED_HORIZON = int(os.environ.get("PRED_HORIZON", "10"))
HISTORY_LEN = int(os.environ.get("HISTORY_LEN", "10"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output_videos")
ANNOTATIONS_BASE = os.environ.get(
    "ANNOTATIONS_BASE",
    os.path.join(os.path.dirname(__file__), '..', 'data')
)

# zamiast logiki healthcheckowej w docker compose
DONE_FILE = os.path.join(FRAMES_DIR, ".done")
while not os.path.exists(DONE_FILE):
    time.sleep(2)
print("Zaczynam przetwarzanie")


def get_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def predict_future_positions(history, horizon=PRED_HORIZON):
    if len(history) < 2:
        return [history[-1]] * horizon
    vx = np.mean(np.diff([p[0] for p in history]))
    vy = np.mean(np.diff([p[1] for p in history]))
    last = history[-1]
    return [(last[0] + vx * i, last[1] + vy * i) for i in range(1, horizon + 1)]


def draw_trajectory(frame, history, color=(0, 165, 255), thickness=2):
    pts = [(int(p[0]), int(p[1])) for p in history]
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i - 1], pts[i], color, thickness)


def draw_prediction(frame, last_pos, predictions, color=(0, 0, 255), thickness=1):
    pts = [(int(last_pos[0]), int(last_pos[1]))] + [(int(p[0]), int(p[1])) for p in predictions]
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i - 1], pts[i], color, thickness, cv2.LINE_AA)
    if pts:
        cv2.circle(frame, pts[-1], 5, color, -1)


def determine_pedestrian_action(history, movement_threshold=2.0):
    if len(history) < 3:
        return 'unknown'
    movements = []
    for i in range(1, len(history)):
        x1, y1 = history[i-1]
        x2, y2 = history[i]
        movements.append(np.sqrt((x2-x1)**2 + (y2-y1)**2))
    avg = np.mean(movements) if movements else 0
    return 'walking' if avg > movement_threshold else 'standing'


def parse_frame_id(fname):
    m = re.search(r'(\d+)', os.path.splitext(fname)[0])
    return int(m.group(1)) if m else 0


video_dirs = sorted(
    d for d in os.listdir(FRAMES_DIR)
    if os.path.isdir(os.path.join(FRAMES_DIR, d))
)
if not video_dirs:
    video_dirs = [""]

track_history = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
annotation_manager = AnnotationManager(ANNOTATIONS_BASE)
collision_detector = None

for vid in video_dirs:
    vid_frames_dir = os.path.join(FRAMES_DIR, vid) if vid else FRAMES_DIR
    if not os.path.exists(vid_frames_dir):
        continue

    frame_files = sorted(f for f in os.listdir(vid_frames_dir) if f.endswith('.jpg'))
    print(f"Przetwarzanie wideo: {vid} ({len(frame_files)} klatek)")

    annotation_manager.load(vid)

    video_writer = None

    for fname in frame_files:
        frame = cv2.imread(os.path.join(vid_frames_dir, fname))
        if frame is None:
            continue

        # Inicjalizacja przy pierwszej klatce
        if video_writer is None:
            h, w = frame.shape[:2]
            out_path = os.path.join(OUTPUT_DIR, f"{vid}_output.mp4")
            video_writer = cv2.VideoWriter(
                out_path, cv2.VideoWriter_fourcc(*'mp4v'), TARGET_FPS, (w, h)
            )
            collision_detector = CollisionDetector(
                h, w, warning_distance=350, collision_threshold=0.3
            )

        # Mnożnik ryzyka dla bieżącej klatki
        frame_id = parse_frame_id(fname)
        collision_detector.set_risk_multiplier(
            annotation_manager.frame_risk_mult(vid, frame_id)
        )

        # Trapez strefy pojazdu
        collision_detector.draw_vehicle_zone(frame, alpha=0.1)

        results = detect_pedestrians(frame)

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().tolist()

            for box, tid in zip(boxes, ids):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = get_center((x1, y1, x2, y2))
                track_history[tid].append((cx, cy))

                # Bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)

                history = list(track_history[tid])
                if len(history) >= 2:
                    draw_trajectory(frame, history)
                    preds = predict_future_positions(history)
                    draw_prediction(frame, history[-1], preds)

                    ped_action = determine_pedestrian_action(history)
                    collision_info = collision_detector.detect_collision(
                        pedestrian_id=tid,
                        current_pos=(cx, cy),
                        bbox=(x1, y1, x2, y2),
                        predicted_positions=preds,
                        movement_history=history,
                        pedestrian_action=ped_action,
                        frame=frame,
                    )
                    if collision_info:
                        collision_detector.draw_collision_alert(frame, collision_info)

        count = len(results[0].boxes) if results[0].boxes.id is not None else 0
        cv2.putText(frame, f"Pieszych: {count}", (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)

        video_writer.write(frame)

    if video_writer:
        video_writer.release()
    track_history.clear()
    if collision_detector is not None:
        collision_detector.pedestrian_history.clear()

print(f"\nPrzetwarzanie zakończone. Wyniki w: '{OUTPUT_DIR}'.")
