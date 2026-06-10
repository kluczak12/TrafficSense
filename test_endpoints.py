import asyncio
import json
import urllib.request
import urllib.error
import sys
import time

time.sleep(30)

host = sys.argv[1] if len(sys.argv) > 1 else "localhost:3000"

http_url = f"http://{host}"
ws_url = f"ws://{host}/ws"

print("Checking GET / ...")
try:
    with urllib.request.urlopen(http_url, timeout=5) as response:
        status = response.getcode()
        html = response.read().decode('utf-8')
        print(f"  [PASS] Status: {status}")
        assert status == 200
        assert "<html" in html.lower() or "<!doctype html" in html.lower()
        print("  [PASS] Returned index.html correctly.")
except Exception as e:
    print(f"  [FAIL] GET / failed: {e}")
    sys.exit(1)

print("\nChecking GET /videos ...")
videos = []
try:
    with urllib.request.urlopen(f"{http_url}/videos", timeout=5) as response:
        status = response.getcode()
        data = json.loads(response.read().decode('utf-8'))
        print(f"  [PASS] Status: {status}")
        assert status == 200
        assert "videos" in data
        videos = data["videos"]
        print(f"  [PASS] Found videos list: {videos}")
except Exception as e:
    print(f"  [FAIL] GET /videos failed: {e}")
    sys.exit(1)

async def check_websocket():
    try:
        import websockets
    except ImportError:
        print("\n  [SKIP] 'websockets' package not found locally. Skipping WebSocket live check.")
        print("  Install it via: pip install websockets")
        return

    print(f"\nChecking WS {ws_url} ...")
    if not videos:
        print("  [SKIP] No videos found in /data/videos to test streaming.")
        return
    
    video_to_test = videos[0]
    print(f"  Attempting to stream video: {video_to_test}")
    
    try:
        async with websockets.connect(ws_url) as ws:
            start_payload = {"action": "start", "video": video_to_test, "autoplay": False}
            await ws.send(json.dumps(start_payload))
            print("  [PASS] Sent start action payload.")
            
            resp = await ws.recv()
            resp_data = json.loads(resp)
            print(f"  [PASS] Received response: {resp_data}")
            assert resp_data.get("type") == "started"
            assert resp_data.get("video") == video_to_test
            assert "fps" in resp_data
            
            print("  Waiting for annotated binary frames from the engine...")
            frame_count = 0
            for _ in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                if isinstance(msg, bytes):
                    frame_count += 1
                    print(
                        f"Received processed binary frame #{frame_count} "
                        f"({len(msg)} bytes)"
                    )
                else:
                    print(f"Received text message: {msg}")
                frame_count += 1
                
            await ws.send(json.dumps({"action": "stop"}))
            print("  [PASS] Sent stop action payload.")
            print("  [PASS] WebSocket integration test completed successfully!")
            
    except Exception as e:
        print(f"  [FAIL] WebSocket live check failed: {e}")
        sys.exit(1)

asyncio.run(check_websocket())

print("\nAll tests completed successfully")
