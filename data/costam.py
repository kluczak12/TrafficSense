# manager bazy danych

import os
from db import init_db
 
DB_DIR = os.environ.get("DB_DIR", "/data/db")

db_path = os.path.join(DB_DIR, "db.sqlite")
 
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

init_db(db_path)

# wymagania wstępne:
# zbiór filmów w data/videos
# zbiór adnotacji w data/videos/annotations

from os.path import join, exists

if exists("/data/.done"):
    print("Data extraction already done, skipping.")
    exit(0)

import cv2
import xml.etree.ElementTree as ET


VIDEO_DIR = os.environ.get("VIDEO_DIR", "/data/videos")
ANNOTATIONS_DIR = os.environ.get("ANNOTATIONS_DIR", "/data/videos/annotations")
FRAMES_DIR = os.environ.get("FRAMES_DIR", "/data/frames")

videos = [f[:-4] for f in sorted(os.listdir(VIDEO_DIR)) if f.endswith('.mp4')]

for vid in videos[:2]: # na razie 2 pierwsze filmy, do ostatecznego całość
    path_to_file = join(ANNOTATIONS_DIR, vid + '.xml')
    tree = ET.parse(path_to_file)
    num_frames = int(tree.find("./meta/task/size").text)

    video_clip_path = join(VIDEO_DIR, vid + '.mp4')

    save_images_path = join(FRAMES_DIR, vid)
    if not exists(save_images_path):
        os.makedirs(save_images_path)

    vidcap = cv2.VideoCapture(video_clip_path)
    success, image = vidcap.read()
    frame_num = 0
    img_count = 0
    if not success:
        print(f"Failed to open the video {vid}")
    while success:
        img_count += 1
        img_path = join(save_images_path, "{:05d}.jpg".format(frame_num))
        if not exists(img_path):
            cv2.imwrite(img_path, image, [cv2.IMWRITE_JPEG_QUALITY, 10])
        success, image = vidcap.read()
        frame_num += 1
    if num_frames != img_count:
        print(f"Did not extract all frames ({img_count} / {num_frames})")
    print('\n')

open("/data/frames/.done", "w").close()
