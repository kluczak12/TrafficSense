import cv2
import os
 
# test zmiennych środowiskowych z composa
VIDEO_DIR = os.environ.get("VIDEO_DIR", "data/videos")
FRAMES_DIR = os.environ.get("FRAMES_DIR", "data/frames")

# te pliki muszą tam być!
video_path = os.path.join(VIDEO_DIR, "test.mp4")
output_dir = os.path.join(FRAMES_DIR, "test")
 
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

vidcap = cv2.VideoCapture(video_path)
frame_num = 0
success, image = vidcap.read()
while success:
    img_path = os.path.join(output_dir, f"{frame_num:05d}.png")
    cv2.imwrite(img_path, image)
    success, image = vidcap.read()
    frame_num += 1
vidcap.release()