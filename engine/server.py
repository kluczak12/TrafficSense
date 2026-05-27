# stale działający engine, przyjmuje klatki przez websocket,
# robi detekcję i predykcję kolizji, zwraca przerobione klatki
"""
Protokół:
  klient -> serwer (JSON):    {"action": "start", "video": "<name>"}
  klient -> serwer (binary):  klatka JPEG w postaci binarnej
  klient -> serwer (JSON):    {"action": "stop"}
  serwer -> klient (JSON):    {"type": "ready"} po starcie
  serwer -> klient (binary):  przerobiona klatka
  serwer -> klient (JSON):    {"type": "error", "message": "..."} w razie błędu
"""
import json
import os
from collections import defaultdict, deque

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from pedestrian_detection import detect_pedestrians
from collision_detection import CollisionDetector
from annotation_loader import AnnotationManager

ANNOTATIONS_DB = os.environ.get("ANNOTATIONS_DB", "/data/db/db.sqlite")
PRED_HORIZON = int(os.environ.get("PRED_HORIZON", "10"))
HISTORY_LEN = int(os.environ.get("HISTORY_LEN", "10"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "75"))

app = FastAPI()
annotation_manager = AnnotationManager(ANNOTATIONS_DB)


@app.on_event("startup")
def _warmup():
    # ładowanie modelu ze sprawdzeniem hasha
    # on startup, aby nie generować opóźnień
    from pedestrian_detection import get_model
    get_model()
    try:
        from pedestrian_detection import detect_pedestrians
        import numpy as _np
        dummy = _np.zeros((640, 640, 3), dtype=_np.uint8)
        detect_pedestrians(dummy)
    except Exception:
        pass


def _center(b):
    x1, y1, x2, y2 = b
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _predict(history, horizon=PRED_HORIZON):
    if len(history) < 2:
        return [history[-1]] * horizon
    vx = float(np.mean(np.diff([p[0] for p in history])))
    vy = float(np.mean(np.diff([p[1] for p in history])))
    last = history[-1]
    return [(last[0] + vx * i, last[1] + vy * i) for i in range(1, horizon + 1)]


def _draw_traj(frame, history, color=(0, 165, 255)):
    pts = [(int(p[0]), int(p[1])) for p in history]
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i - 1], pts[i], color, 2)


def _draw_pred(frame, last, preds, color=(0, 0, 255)):
    pts = [(int(last[0]), int(last[1]))] + [(int(p[0]), int(p[1])) for p in preds]
    for i in range(1, len(pts)):
        cv2.line(frame, pts[i - 1], pts[i], color, 1, cv2.LINE_AA)
    if pts:
        cv2.circle(frame, pts[-1], 5, color, -1)


def _action(history, thr=2.0):
    if len(history) < 3:
        return "unknown"
    d = [np.hypot(history[i][0] - history[i - 1][0], history[i][1] - history[i - 1][1])
         for i in range(1, len(history))]
    return "walking" if float(np.mean(d)) > thr else "standing"


def _annotate(frame, frame_id, video_id, track_history, collision_detector):
    collision_detector.set_risk_multiplier(
        annotation_manager.frame_risk_mult(video_id, frame_id)
    )
    collision_detector.draw_vehicle_zone(frame, alpha=0.1)

    results = detect_pedestrians(frame)
    risk_levels = {}
    count = 0
    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.int().cpu().tolist()
        count = len(ids)
        for box, tid in zip(boxes, ids):
            x1, y1, x2, y2 = map(int, box)
            cx, cy = _center((x1, y1, x2, y2))
            track_history[tid].append((cx, cy))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
            history = list(track_history[tid])
            if len(history) >= 2:
                _draw_traj(frame, history)
                preds = _predict(history)
                _draw_pred(frame, history[-1], preds)
                info = collision_detector.detect_collision(
                    pedestrian_id=tid, current_pos=(cx, cy), bbox=(x1, y1, x2, y2),
                    predicted_positions=preds, movement_history=history,
                    pedestrian_action=_action(history), frame=frame,
                )
                if info:
                    collision_detector.draw_collision_alert(frame, info)
                    risk_levels[tid] = info.get("risk_level")

    return frame, risk_levels


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    video_id = None
    frame_id = 0
    track_history = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
    collision_detector = None # inicjalizowany przy każdej klatce
    last_risk_levels = {}

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break

            # wiadomości kontrolne przychodzą jako text JSON (patrz protokół)
            if "text" in msg and msg["text"] is not None:
                try:
                    data = json.loads(msg["text"])
                except ValueError:
                    continue
                action = data.get("action")
                if action == "start":
                    video_id = os.path.splitext(data.get("video", ""))[0]
                    frame_id = 0
                    track_history.clear()
                    collision_detector = None
                    last_risk_levels.clear()
                    await ws.send_json({"type": "ready"})
                elif action == "stop":
                    video_id = None
                    collision_detector = None
                    last_risk_levels.clear()
                continue

            # a binary oznacza klatkę
            if "bytes" not in msg or msg["bytes"] is None:
                continue
            if video_id is None:
                continue

            arr = np.frombuffer(msg["bytes"], dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            if collision_detector is None:
                h, w = frame.shape[:2]
                collision_detector = CollisionDetector(
                    h, w, warning_distance=350, collision_threshold=0.3
                )

            annotated, current_risk_levels = _annotate(
                frame, frame_id, video_id, track_history, collision_detector
            )
            for pedestrian_id, current_risk in current_risk_levels.items():
                previous_risk = last_risk_levels.get(pedestrian_id)
                if previous_risk and previous_risk != "critical" and current_risk == "critical":
                    await ws.send_json(
                        {
                            "type": "pedestrian_state_alert",
                            "pedestrian_id": pedestrian_id,
                            "from": previous_risk,
                            "to": current_risk,
                            "frame_id": frame_id,
                        }
                    )
                last_risk_levels[pedestrian_id] = current_risk
            frame_id += 1

            ok, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if ok:
                await ws.send_bytes(buf.tobytes())

    except WebSocketDisconnect:
        pass
