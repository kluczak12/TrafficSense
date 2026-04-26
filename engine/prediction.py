import os
import cv2
import sys
import time
import numpy as np
from collections import defaultdict, deque
sys.path.insert(0, os.path.dirname(__file__))
from identificationOfPedestrians import detect_pedestrians


FRAMES_DIR = os.environ.get("FRAMES_DIR", "/data/frames")
TARGET_FPS = int(os.environ.get("TARGET_FPS", "30"))
PRED_HORIZON = int(os.environ.get("PRED_HORIZON", "10"))
HISTORY_LEN = int(os.environ.get("HISTORY_LEN", "10"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "output_videos")

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


video_dirs = sorted(
    d for d in os.listdir(FRAMES_DIR)
    if os.path.isdir(os.path.join(FRAMES_DIR, d))
)
if not video_dirs:
    video_dirs = [""]

track_history = defaultdict(lambda: deque(maxlen=HISTORY_LEN))

#WINDOW_NAME = "TrafficSense - Pedestrian Prediction"
#cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
#cv2.resizeWindow(WINDOW_NAME, 1280, 720)

for vid in video_dirs:
    vid_frames_dir = os.path.join(FRAMES_DIR, vid) if vid else FRAMES_DIR
    if not os.path.exists(vid_frames_dir):
        continue

    frame_files = sorted(f for f in os.listdir(vid_frames_dir) if f.endswith(('.jpg')))
    print(f"Przetwarzanie wideo: {vid} ({len(frame_files)} klatek)")

    video_writer = None
    paused = False

    for fname in frame_files:
        frame = cv2.imread(os.path.join(vid_frames_dir, fname))
        if frame is None:
            continue

        if video_writer is None:
            h, w = frame.shape[:2]
            out_path = os.path.join(OUTPUT_DIR, f"{vid}_output.mp4")
            video_writer = cv2.VideoWriter(
                out_path, cv2.VideoWriter_fourcc(*'mp4v'), TARGET_FPS, (w, h)
            )

        results = detect_pedestrians(frame)

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.int().cpu().tolist()
            confs = results[0].boxes.conf.cpu().numpy()

            for box, tid, conf in zip(boxes, ids, confs):
                x1, y1, x2, y2 = map(int, box)
                cx, cy = get_center((x1, y1, x2, y2))
                track_history[tid].append((cx, cy))

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
                
                label = f"#{tid} {conf:.0%}"
                cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)

                history = list(track_history[tid])
                if len(history) >= 2:
                    draw_trajectory(frame, history)
                    preds = predict_future_positions(history)
                    draw_prediction(frame, history[-1], preds)

        count = len(results[0].boxes) if results[0].boxes.id is not None else 0
        cv2.putText(frame, f"Pieszych: {count}", (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)

        video_writer.write(frame)
        """cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord(' '):
            paused = not paused
            while paused:
                key2 = cv2.waitKey(0) & 0xFF
                if key2 == ord(' '):
                    paused = False
                elif key2 == ord('n'):
                    paused = False
                    break
                elif key2 == ord('q'):
                    if video_writer:
                        video_writer.release()
                    cv2.destroyAllWindows()
                    sys.exit(0)

        if key == ord('q'):
            print("Przerwano przez użytkownika.")
            if video_writer: video_writer.release()
            cv2.destroyAllWindows()
            sys.exit(0)
            
        elif key == ord('n'):
            print("Pomijam do następnego filmu...")
            break """

    if video_writer:
        video_writer.release()
    track_history.clear()

#cv2.destroyAllWindows()
print(f"\nPrzetwarzanie zakończone. Wyniki w: '{OUTPUT_DIR}'.")