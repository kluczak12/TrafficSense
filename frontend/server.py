# frontend - wystawia gui, czyta z /data/videos i przesyła klatki
# do engine, otrzymuje przerobione.
# przeglądarka <-> ten serwer: JSON + klatki JPEG zakodowane w base64
# ten serwer <-> engine: JSON + klatki JPEG w postaci binarnej

import asyncio
import base64
import json
import os
import time

import cv2
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

VIDEO_DIR = os.environ.get("VIDEO_DIR", "/data/videos")
ENGINE_WS = os.environ.get("ENGINE_WS", "ws://engine:8000/ws")

app = FastAPI()


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))


@app.get("/videos")
def list_videos():
    if not os.path.isdir(VIDEO_DIR):
        return {"videos": []}
    return {"videos": sorted(f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4"))}


async def _stream_video(video_name, browser_ws, engine_ws, stop_event):
    # czyta klatki z filmu, przesyła do engine, przerobione przekazuje do przeglądarki
    # wyjście z funkcji następuje przy zakończeniu filmu lub ustawieniu flagi stop
    path = os.path.join(VIDEO_DIR, video_name)
    if not os.path.isfile(path):
        await browser_ws.send_json({"type": "error", "message": f"Video not found: {video_name}"})
        return

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        await browser_ws.send_json({"type": "error", "message": f"Cannot open: {video_name}"})
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    interval = 1.0 / fps

    await engine_ws.send(json.dumps({"action": "start", "video": video_name}))
    # czeka na gotowość engine
    ready = await engine_ws.recv()

    await browser_ws.send_json({"type": "started", "video": video_name, "fps": fps})

    try:
        while not stop_event.is_set():
            t0 = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                await browser_ws.send_json({"type": "ended", "video": video_name})
                break

            ok_enc, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok_enc:
                continue
            await engine_ws.send(buf.tobytes())

            annotated = await engine_ws.recv()
            if isinstance(annotated, str):
                # wiadomość kontrolna z engine, skip
                continue
            await browser_ws.send_text("F" + base64.b64encode(annotated).decode("ascii"))

            elapsed = time.perf_counter() - t0
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
    finally:
        cap.release()
        await engine_ws.send(json.dumps({"action": "stop"}))


@app.websocket("/ws")
async def ws_endpoint(browser_ws: WebSocket):
    await browser_ws.accept()
    stop_event = asyncio.Event()
    play_task = None

    try:
        async with websockets.connect(ENGINE_WS, max_size=None) as engine_ws:
            while True:
                msg = await browser_ws.receive_json()
                action = msg.get("action")

                if action == "start":
                    video = msg.get("video")
                    autoplay = bool(msg.get("autoplay"))
                    if play_task and not play_task.done():
                        stop_event.set()
                        await play_task
                    stop_event = asyncio.Event()
                    play_task = asyncio.create_task(
                        _play(video, autoplay, browser_ws, engine_ws, stop_event)
                    )
                elif action == "stop":
                    stop_event.set()
                    if play_task:
                        await play_task
                    play_task = None
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        if play_task:
            try:
                await play_task
            except Exception:
                pass


async def _play(video, autoplay, browser_ws, engine_ws, stop_event):
    videos = sorted(f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4"))
    if video not in videos:
        await browser_ws.send_json({"type": "error", "message": f"Unknown video: {video}"})
        return
    idx = videos.index(video)
    while not stop_event.is_set():
        await _stream_video(videos[idx], browser_ws, engine_ws, stop_event)
        if stop_event.is_set() or not autoplay:
            break
        idx = (idx + 1) % len(videos)
