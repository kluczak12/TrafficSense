# frontend - wystawia gui, czyta z /data/videos i przesyła klatki
# do engine, otrzymuje przerobione.
# przeglądarka <-> ten serwer: JSON + klatki JPEG zakodowane w base64
# ten serwer <-> engine: JSON + klatki JPEG w postaci binarnej

import asyncio
import json
import os
import sqlite3
import time

import cv2
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

VIDEO_DIR = os.environ.get("VIDEO_DIR", "/data/videos")
ENGINE_WS = os.environ.get("ENGINE_WS", "ws://engine:8000/ws")
ANNOTATIONS_DB = os.environ.get("ANNOTATIONS_DB", "/data/db/db.sqlite")
FRAME_MAX_WIDTH = int(os.environ.get("FRAME_MAX_WIDTH", "1600"))
FRONTEND_JPEG_QUALITY = int(os.environ.get("FRONTEND_JPEG_QUALITY", "80"))
MAX_IN_FLIGHT = int(os.environ.get("MAX_IN_FLIGHT", "2"))
FRAME_SKIP_COEFF = float(os.environ.get("FRAME_SKIP_COEFF", "0.5"))

app = FastAPI()


@app.get("/")
def index():
    return FileResponse(
        os.path.join(os.path.dirname(__file__), "index.html"),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/videos")
def list_videos():
    if not os.path.isdir(VIDEO_DIR):
        return {"videos": []}
    return {"videos": sorted(f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4"))}


@app.get("/logs")
def list_logs():
    if not os.path.isfile(ANNOTATIONS_DB):
        return {"logs": []}
    with sqlite3.connect(ANNOTATIONS_DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, date, type, description FROM critical_events_logs ORDER BY id DESC"
        ).fetchall()
    return {"logs": [dict(row) for row in rows]}


async def _stream_video(video_name, browser_ws, engine_ws, stop_event):
    path = os.path.join(VIDEO_DIR, video_name)
    if not os.path.isfile(path):
        await browser_ws.send_json({"type": "error", "message": f"Video not found: {video_name}"})
        return

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        await browser_ws.send_json({"type": "error", "message": f"Cannot open: {video_name}"})
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    interval = 1.0 / fps

    await engine_ws.send(json.dumps({"action": "start", "video": video_name}))
    ready = await engine_ws.recv()

    await browser_ws.send_json({"type": "started", "video": video_name, "fps": fps, "width": orig_w, "height": orig_h})

    skip_every = 0
    if FRAME_SKIP_COEFF > 0:
        skip_every = max(2, int(round(1.0 / FRAME_SKIP_COEFF)))

    in_flight_sem = asyncio.Semaphore(max(1, MAX_IN_FLIGHT))
    in_flight = 0
    in_flight_lock = asyncio.Lock()

    async def _receiver():
        nonlocal in_flight
        try:
            while not stop_event.is_set():
                msg = await engine_ws.recv()
                if isinstance(msg, (bytes, bytearray)):
                    async with in_flight_lock:
                        if in_flight > 0:
                            in_flight -= 1
                            in_flight_sem.release()
                    try:
                        await browser_ws.send_bytes(msg)
                    except Exception:
                        pass
                else:
                    try:
                        await browser_ws.send_text(msg)
                    except Exception:
                        pass
        except (asyncio.CancelledError, Exception):
            pass

    async def _sender():
        nonlocal in_flight
        frame_idx = 0
        while not stop_event.is_set():
            t0 = time.perf_counter()
            ok, frame = cap.read()
            if not ok:
                await browser_ws.send_json({"type": "ended", "video": video_name})
                break

            if skip_every and (frame_idx % skip_every) == (skip_every - 1):
                frame_idx += 1
                elapsed = time.perf_counter() - t0
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)
                continue

            if FRAME_MAX_WIDTH:
                scale = FRAME_MAX_WIDTH / float(frame.shape[1])
                new_h = int(frame.shape[0] * scale)

                interpolation = (
                    cv2.INTER_AREA
                    if scale < 1.0
                    else cv2.INTER_LINEAR
                )

                frame = cv2.resize(
                    frame,
                    (FRAME_MAX_WIDTH, new_h),
                    interpolation=interpolation,
                )

            ok_enc, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, FRONTEND_JPEG_QUALITY])
            if not ok_enc:
                frame_idx += 1
                continue

            await in_flight_sem.acquire()
            async with in_flight_lock:
                in_flight += 1
            await engine_ws.send(buf.tobytes())
            frame_idx += 1

            elapsed = time.perf_counter() - t0
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)

    try:
        recv_task = asyncio.create_task(_receiver())
        send_task = asyncio.create_task(_sender())
        await send_task

        t_flush_start = time.perf_counter()
        while True:
            async with in_flight_lock:
                pending = in_flight
            if pending == 0:
                break
            if time.perf_counter() - t_flush_start > 0.75:
                break
            await asyncio.sleep(0.01)

        if not recv_task.done():
            recv_task.cancel()
            try:
                await recv_task
            except (asyncio.CancelledError, Exception):
                pass
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
                        try:
                            await play_task
                        except asyncio.CancelledError:
                            pass
                    stop_event = asyncio.Event()
                    play_task = asyncio.create_task(
                        _play(video, autoplay, browser_ws, engine_ws, stop_event)
                    )
                elif action == "stop":
                    stop_event.set()
                    if play_task:
                        try:
                            await play_task
                        except asyncio.CancelledError:
                            pass
                    play_task = None
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        if play_task:
            try:
                await play_task
            except (asyncio.CancelledError, Exception):
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
