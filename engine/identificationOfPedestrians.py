import hashlib
import os

import urllib
import cv2
import time
from ultralytics import YOLO

# ===== SPRWADZENIE YOLO =====
FRAMES_DIR = os.environ.get("FRAMES_DIR", "/data/frames")
EXPECTED_MODEL_HASH = os.environ.get("EXPECTED_MODEL_HASH")

_model = None

def get_model():
    global _model
    if _model is None:
        _model = YOLO("yolov8n.pt")
        verify_model("yolov8n.pt")
    return _model

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1_048_576): # 1 MiB
            h.update(chunk)
    return h.hexdigest()

def verify_model(path):
    expected = str(EXPECTED_MODEL_HASH)
    if expected is None:
        raise ValueError(f"Hash variable for model not found.")
    # @TODO exception handling
    actual = compute_sha256(path)
    if actual is None:
        raise RuntimeError(f"Could not find YOLO model file. Aborting.")
    if actual != expected:
        raise RuntimeError(
            f"Hash mismatch for YOLO model. The file may have been replaced. Aborting."
        )
    print(f"YOLO model verified correctly.")

def detect_pedestrians(frame, conf=0.45):
    model = get_model()
    results = model.track(frame, classes=[0], conf=conf, persist=True, verbose=False)
    return results


if __name__ == "__main__":
    TARGET_FPS = 30
    model = get_model()
    frames = sorted(os.listdir(FRAMES_DIR))
    print(f"Processing {len(frames)} frames from {FRAMES_DIR} at target {TARGET_FPS} FPS.")

    for filename in frames:
        print(f"Processing {filename}...")
        t = time.time()
        
        frame = cv2.imread(os.path.join(FRAMES_DIR, filename))
        results = detect_pedestrians(frame)
        
        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            tid  = int(box.id[0]) if box.id is not None else -1

            # Box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
            
            # Półprzezroczyste wypełnienie
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 220, 0), -1)
            cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
            
            # Etykieta
            label = f"#{tid} {conf:.0%}"
            cv2.putText(frame, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 0), 2)

        # Licznik pieszych
        count = len(results[0].boxes)
        cv2.putText(frame, f"Pieszych: {count}", (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3)

        cv2.imshow("Pedestrian Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        # Kontrola FPS
        sleep = (1 / TARGET_FPS) - (time.time() - t)
        if sleep > 0:
            time.sleep(sleep)

    cv2.destroyAllWindows()







# class PedestrianIdentificationAndTrajectory:
#     def __init__(self, jaad_path):
#         self._frames_path = join(jaad_path, 'images')

#     def setframes_to_analyze(self, frames_to_analyze):
#         self._frames_to_analyze = frames_to_analyze    
    

#     # ===== Pedestrian detection data generators =====
#     def get_detection_data(self, image_set, method, occlusion_type=None, file_path='data/', **params):
#         """
#         Generates data for pedestrian detection algorithms
#         :param image_set: Split set name
#         :param method: Detection algorithm: frcnn, retinanet, yolo3, ssd
#         :param occlusion_type: The types of occlusion: None: only unoccluded samples
#                                                     part: Unoccluded and partially occluded samples
#                                                     full: All samples
#         :param file_path: Where to save the script file
#         :return: Pedestrian samples
#         """
#         squarify_ratio = params['squarify_ratio']
#         frame_stride = params['fstride']
#         height_rng = params['height_rng']
#         if not exists(file_path):
#             makedirs(file_path)
#         if height_rng is None:
#             height_rng = [0, float('inf')]

#         annotations = self.generate_database() # TUTAJ TRZEBA PRZYPISYWAĆ FILMY DO KTÓRE MAJĄ BYĆ ANALZOWANE 
#         video_ids, _pids = self._get_data_ids(image_set, params)

#         ped_samples = {}
#         unique_samples = []
#         total_sample_count = 0
#         for vid in video_ids:
#             img_width = annotations[vid]['width']
#             img_height = annotations[vid]['height']
#             num_frames = annotations[vid]['num_frames']
#             for i in range(0,num_frames,frame_stride):
#                 ped_samples[join(self._jaad_path, 'images', vid, '{:05d}.png'.format(i))] = []
#             for pid in annotations[vid]['ped_annotations']:
#                 if params['data_split_type'] != 'default' and pid not in _pids:
#                     continue
#                 difficult =  0
#                 if 'p' in pid:
#                     difficult = -1
#                     if image_set in ['train', 'val']:
#                         continue
#                 imgs = [join(self._jaad_path, 'images', vid, '{:05d}.png'.format(f)) for f in \
#                         annotations[vid]['ped_annotations'][pid]['frames']]
#                 boxes = annotations[vid]['ped_annotations'][pid]['bbox']
#                 occlusion = annotations[vid]['ped_annotations'][pid]['occlusion']
#                 for i, b in enumerate(boxes):
#                     if imgs[i] not in ped_samples:
#                         continue
#                     bbox_height = abs(b[0] - b[2])
#                     if height_rng[0] <= bbox_height <= height_rng[1]:
#                         if (occlusion_type == None and occlusion[i] == 0) or \
#                                 (occlusion_type == 'part' and occlusion[i] < 2) or \
#                                 (occlusion_type == 'full'):
#                             if squarify_ratio:
#                                 b = self._squarify(b, squarify_ratio, img_width)
#                             ped_samples[imgs[i]].append(
#                                                 {'width': img_width,
#                                                 'height': img_height,
#                                                 'tag': pid,
#                                                 'box': b,
#                                                 'seg_area': (b[2] - b[0] + 1) * (b[3] - b[1] + 1),
#                                                 'occlusion': occlusion[i],
#                                                 'difficult': difficult})
#                             if pid not in unique_samples:
#                                 unique_samples.append(pid)
#                             total_sample_count += 1
#         print('Number of unique pedestrians %d ' % len(unique_samples))
#         print('Number of samples %d ' % total_sample_count)
#         if method == 'frcnn':
#             return self._get_data_frcnn(ped_samples)
#         elif method == 'retinanet':
#             return self._generate_csv_data_retinanet(image_set, file_path, ped_samples)
#         elif method == 'yolo3':
#             return self._generate_csv_data_yolo3(image_set, file_path, ped_samples)
#         elif method == 'ssd':
#             return self._generate_csv_data_ssd(image_set, file_path, ped_samples)
        



#     # ===== Pedestrian trajectory generators =====
#     def generate_data_trajectory_sequence(self, image_set, **opts):
#         """
#         Generates pedestrian tracks
#         :param image_set: the split set to produce for. Options are train, test, val.
#         :param opts:
#                 'fstride': Frequency of sampling from the data.
#                 'sample_type': Whether to use 'all' pedestrian annotations or the ones
#                                     with 'beh'avior only.
#                 'subset': The subset of data annotations to use. Options are: 'default': Includes high resolution and
#                                                                                         high visibility videos
#                                                                         'high_visibility': Only videos with high
#                                                                                             visibility (include low
#                                                                                             resolution videos)
#                                                                         'all': Uses all videos
#                 'height_rng': The height range of pedestrians to use.
#                 'squarify_ratio': The width/height ratio of bounding boxes. A value between (0,1]. 0 the original
#                                         ratio is used.
#                 'data_split_type': How to split the data. Options: 'default', predefined sets, 'random', randomly split the data,
#                                         and 'kfold', k-fold data split (NOTE: only train/test splits).
#                 'seq_type': Sequence type to generate. Options: 'trajectory', generates tracks, 'crossing', generates
#                                 tracks up to 'crossing_point', 'intention' generates tracks similar to human experiments
#                 'min_track_size': Min track length allowable.
#                 'random_params: Parameters for random data split generation. (see _get_random_pedestrian_ids)
#                 'kfold_params: Parameters for kfold split generation. (see _get_kfold_pedestrian_ids)
#         :return: Sequence data
#         """
#         params = {'fstride': 1,
#                 'sample_type': 'all',  # 'beh'
#                 'subset': 'default',
#                 'height_rng': [0, float('inf')],
#                 'squarify_ratio': 0,
#                 'data_split_type': 'default',  # kfold, random, default
#                 'seq_type': 'intention',
#                 'min_track_size': 15,
#                 'random_params': {'ratios': None,
#                                     'val_data': True,
#                                     'regen_data': False},
#                 'kfold_params': {'num_folds': 5, 'fold': 1}}
#         assert all(k in params for k in opts.keys()), "Wrong option(s)."\
#         "Choose one of the following: {}".format(list(params.keys()))
#         params.update(opts)
#         print('---------------------------------------------------------')
#         print("Generating action sequence data")
#         self._print_dict(params)
#         annot_database = self.generate_database()
#         if params['seq_type'] == 'trajectory':
#             sequence = self._get_trajectories(image_set, annot_database, **params)
#         elif params['seq_type'] == 'crossing':
#             sequence = self._get_crossing(image_set, annot_database, **params)
#         elif params['seq_type'] == 'intention':
#             sequence = self._get_intention(image_set, annot_database, **params)
#         return sequence