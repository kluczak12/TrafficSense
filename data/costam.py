import cv2
import os
from db import init_db
 
# test zmiennych środowiskowych z composa
VIDEO_DIR = os.environ.get("VIDEO_DIR", "data/videos")
FRAMES_DIR = os.environ.get("FRAMES_DIR", "data/frames")
DB_DIR = os.environ.get("DB_DIR", "data/db")

video_path = os.path.join(VIDEO_DIR, "test.mp4")
output_dir = os.path.join(FRAMES_DIR, "test")
db_path = os.path.join(DB_DIR, "db.sqlite")
 
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

init_db(db_path)

vidcap = cv2.VideoCapture(video_path)
frame_num = 0
success, image = vidcap.read()
while success:
    img_path = os.path.join(output_dir, f"{frame_num:05d}.png")
    cv2.imwrite(img_path, image)
    success, image = vidcap.read()
    frame_num += 1
vidcap.release()

