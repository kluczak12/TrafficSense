# manager bazy danych

import os
import time
from db import init_db
 
VIDEO_DIR = os.environ.get("VIDEO_DIR", "/data/videos")
ANNOTATIONS_DIR = os.environ.get("ANNOTATIONS_DIR", "/data/annotations")
FRAMES_DIR = os.environ.get("FRAMES_DIR", "/data/frames")
DB_DIR = os.environ.get("DB_DIR", "/data/db")

db_path = os.path.join(DB_DIR, "db.sqlite")
 
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

init_db(db_path)

# wymagania wstępne:
# zbiór filmów w data/videos
# zbiór adnotacji w data/annotations

from os.path import join, exists

# if exists(join(FRAMES_DIR, ".done")):
#     print("Data extraction already done, skipping.")
#     exit(0)

# niech klatkuje zawsze, tego docelowo nie będzie i tak
from shutil import rmtree
for filename in os.listdir(FRAMES_DIR):
    file_path = os.path.join(FRAMES_DIR, filename)
    
    if os.path.isfile(file_path) or os.path.islink(file_path):
        os.remove(file_path)
    elif os.path.isdir(file_path):
        rmtree(file_path)

import cv2
import xml.etree.ElementTree as ET

videos = [f[:-4] for f in sorted(os.listdir(VIDEO_DIR)) if f.endswith('.mp4')]

# docelowo nie będzie klatkowania wstępnego, tutaj wybrane filmy do demonstracji
# z jakiegoś powodu brane są index + 2, na razie nie chce mi się szukać dlaczego
# pewnie coś z sortowaniem
for i in [33, 75, 204, 319]:
    path_to_file = join(ANNOTATIONS_DIR, videos[i] + '.xml')
    tree = ET.parse(path_to_file)
    num_frames = int(tree.find("./meta/task/size").text)

    video_clip_path = join(VIDEO_DIR, videos[i] + '.mp4')

    save_images_path = join(FRAMES_DIR, videos[i])
    if not exists(save_images_path):
        os.makedirs(save_images_path)

    vidcap = cv2.VideoCapture(video_clip_path)
    success, image = vidcap.read()
    frame_num = 0
    img_count = 0
    if not success:
        print(f"Failed to open the video {videos[i]}")
    while success:
        img_count += 1
        img_path = join(save_images_path, "{:05d}.jpg".format(frame_num))
        if not exists(img_path):
            cv2.imwrite(img_path, image, [cv2.IMWRITE_JPEG_QUALITY, 80])
        success, image = vidcap.read()
        frame_num += 1
    if num_frames != img_count:
        print(f"Did not extract all frames ({img_count} / {num_frames})")
    print('\n')

open("/data/frames/.done", "w").close()
