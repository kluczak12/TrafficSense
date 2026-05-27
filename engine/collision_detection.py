import numpy as np
import cv2
from collections import deque


class MotionAnalyzer:
    # Analiza ruchu pieszego i trajektorii
    def __init__(self, history_window=5):
        self.history_window = history_window

    def calculate_direction(self, positions):
        if len(positions) < 2:
            return None, None
        x1, y1 = positions[-2]
        x2, y2 = positions[-1]
        dx, dy = x2 - x1, y2 - y1
        magnitude = np.sqrt(dx**2 + dy**2)
        if magnitude < 0.1:
            return None, magnitude
        return np.degrees(np.arctan2(dy, dx)), magnitude

    def is_moving_toward_vehicle_zone(self, positions, vehicle_zone):
        if len(positions) < 2:
            return False, 0
        cur_x, cur_y = positions[-1]
        prev_x, prev_y = positions[-2]
        cur_dist = vehicle_zone.distance_to_zone(cur_x, cur_y)
        prev_dist = vehicle_zone.distance_to_zone(prev_x, prev_y)
        approach_rate = prev_dist - cur_dist
        return approach_rate > 0.5, approach_rate

    def calculate_direction_consistency(self, positions):
        if len(positions) < self.history_window:
            return 1.0, False
        recent = positions[-self.history_window:]
        angles = []
        for i in range(1, len(recent)):
            x1, y1 = recent[i-1]
            x2, y2 = recent[i]
            dx, dy = x2 - x1, y2 - y1
            if np.sqrt(dx**2 + dy**2) > 0.1:
                angles.append(np.degrees(np.arctan2(dy, dx)))
        if not angles or len(angles) < 2:
            return 1.0, False
        angles = np.array(angles)
        mean_angle = np.mean(angles)
        angle_diff = np.minimum(np.abs(angles - mean_angle), 360 - np.abs(angles - mean_angle))
        consistency = 1.0 - (np.mean(angle_diff) / 180.0)
        is_changing = np.max(angle_diff) > 45
        return np.clip(consistency, 0, 1), is_changing


class PerspectiveCalculator:
    # Estymacja odległości z rozmiaru bounding box
    def __init__(self, frame_height, frame_width, typical_ped_height=180):
        self.frame_height = frame_height
        self.frame_width = frame_width
        self.typical_ped_height = typical_ped_height
        self.distance_history = deque(maxlen=10)
        self.bbox_sizes = deque(maxlen=30)

    def estimate_distance_from_perspective(self, current_bbox, historical_bbox_heights=None):
        if current_bbox is None:
            return 0.5
        x1, y1, x2, y2 = current_bbox
        current_height = abs(y2 - y1)
        self.bbox_sizes.append(current_height)

        normalized_height = current_height / self.frame_height
        center_y = (y1 + y2) / 2
        vertical_weight = (center_y / self.frame_height) * 0.15

        final_estimate = np.clip(normalized_height + vertical_weight, 0, 1)
        self.distance_history.append(final_estimate)
        return final_estimate


class TrapezoidZone:
    def __init__(self, frame_height, frame_width):
        self.frame_height = frame_height
        self.frame_width = frame_width
        self.points = np.array([
            [int(frame_width * 0.05), frame_height],
            [int(frame_width * 0.95), frame_height],
            [int(frame_width * 0.7), int(frame_height * 0.65)],
            [int(frame_width * 0.3), int(frame_height * 0.65)],
        ], dtype=np.int32)

    def point_in_trapezoid(self, x, y):
        result = cv2.pointPolygonTest(self.points, (float(x), float(y)), measureDist=False)
        return result >= 0

    def bbox_overlaps_trapezoid(self, x1, y1, x2, y2):
        for px, py in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
            if self.point_in_trapezoid(px, py):
                return True
        box_poly = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        trap_poly = self.points.astype(np.float32)
        retval, _ = cv2.intersectConvexConvex(box_poly, trap_poly)
        return retval > 0

    def distance_to_zone(self, x, y):
        dist = cv2.pointPolygonTest(self.points, (float(x), float(y)), measureDist=True)
        return 0.0 if dist >= 0 else float(abs(dist))

    def get_trapezoid_points(self):
        return self.points

    def draw(self, frame, color=(100, 100, 255), alpha=0.2):
        overlay = frame.copy()
        cv2.fillPoly(overlay, [self.points], color)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        cv2.polylines(frame, [self.points], True, color, 2)


class CollisionDetector:
    def __init__(self, frame_height, frame_width,
                 warning_distance=350, collision_threshold=0.3):
        self.frame_height = frame_height
        self.frame_width = frame_width
        self.warning_distance = warning_distance
        self.collision_threshold = collision_threshold

        self.motion_analyzer = MotionAnalyzer()
        self.perspective_calc = PerspectiveCalculator(frame_height, frame_width)
        self.vehicle_zone = TrapezoidZone(frame_height, frame_width)

        self.pedestrian_history = {}
        self.risk_mult = 1.0

    def set_risk_multiplier(self, mult):
        self.risk_mult = mult

    def draw_vehicle_zone(self, frame, alpha=0.1):
        self.vehicle_zone.draw(frame, color=(100, 100, 255), alpha=alpha)

    def detect_collision(self, pedestrian_id, current_pos, bbox, predicted_positions,
                         movement_history=None, pedestrian_action='unknown', frame=None):
        if pedestrian_id not in self.pedestrian_history:
            self.pedestrian_history[pedestrian_id] = {
                'positions': deque(maxlen=30),
                'bboxes': deque(maxlen=30),
            }

        self.pedestrian_history[pedestrian_id]['positions'].append(current_pos)
        if bbox:
            self.pedestrian_history[pedestrian_id]['bboxes'].append(bbox)

        history = list(self.pedestrian_history[pedestrian_id]['positions'])

        perspective_distance = self.perspective_calc.estimate_distance_from_perspective(bbox)

        x1, y1, x2, y2 = bbox if bbox else (0, 0, 0, 0)
        bbox_in_zone = self.vehicle_zone.bbox_overlaps_trapezoid(x1, y1, x2, y2)

        centroid_in_zone = self.vehicle_zone.point_in_trapezoid(current_pos[0], current_pos[1])

        is_approaching, approach_rate = self.motion_analyzer.is_moving_toward_vehicle_zone(
            history, self.vehicle_zone
        )
        min_distance = self.vehicle_zone.distance_to_zone(current_pos[0], current_pos[1])

        if centroid_in_zone:
            collision_prob = perspective_distance * 0.5 + 0.45
        elif bbox_in_zone:
            collision_prob = perspective_distance * 0.5 + 0.25
        elif is_approaching:
            collision_prob = perspective_distance * 0.3 + 0.05
        else:
            return None

        collision_frame = None
        collision_positions = []

        if predicted_positions and (bbox_in_zone or is_approaching):
            for i, pred_pos in enumerate(predicted_positions):
                if self.vehicle_zone.point_in_trapezoid(pred_pos[0], pred_pos[1]):
                    if collision_frame is None:
                        collision_frame = i + 1
                    collision_positions.append(pred_pos)
                    collision_prob += 0.12 * (1 - i / len(predicted_positions))

        collision_prob = np.clip(collision_prob * self.risk_mult, 0, 1)

        risk_level = self._calculate_risk_level(
            collision_prob, collision_frame,
            is_approaching, perspective_distance, min_distance,
        )

        if collision_prob >= self.collision_threshold or bbox_in_zone:
            return {
                'pedestrian_id': pedestrian_id,
                'collision_detected': centroid_in_zone or collision_prob > 0.65,
                'collision_probability': collision_prob,
                'collision_frame': collision_frame,
                'collision_positions': collision_positions,
                'min_distance': min_distance,
                'risk_level': risk_level,
                'current_pos': current_pos,
                'perspective_distance': perspective_distance,
                'is_approaching': is_approaching,
            }
        return None

    def _calculate_risk_level(self, collision_prob, collision_frame, is_approaching=False,
        perspective_distance=0.5, min_distance=9999):
        # Mapowanie prawdopodobieństwa na 4 poziomy ryzyka
        if collision_prob >= 0.6 and perspective_distance > 0.5:
            return 'critical'
        if collision_prob >= 0.4 and (collision_frame is None or collision_frame <= 8):
            return 'high'
        if collision_prob >= 0.3 or (is_approaching and perspective_distance > 0.25):
            return 'medium'
        if collision_prob >= 0.25 and min_distance < self.warning_distance:
            return 'medium'
        return 'low' 

    def draw_collision_alert(self, frame, collision_info):
        current_pos = collision_info['current_pos']
        risk_level = collision_info['risk_level']

        color_map = {
            'critical': (0, 0, 255),
            'high': (0, 165, 255),
            'medium': (0, 255, 255),
            'low': (0, 255, 0),
        }
        color = color_map.get(risk_level, (255, 255, 255))

        px, py = int(current_pos[0]), int(current_pos[1])
        cv2.circle(frame, (px, py), 15, color, 3)

        if collision_info.get('collision_detected'):
            cv2.rectangle(frame, (px - 25, py - 25), (px + 25, py + 25), color, 2)
            for cx, cy in collision_info.get('collision_positions', []):
                cv2.circle(frame, (int(cx), int(cy)), 5, color, -1)
                cv2.line(frame, (px, py), (int(cx), int(cy)), color, 1)

        label = risk_level.upper()
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), bl = cv2.getTextSize(label, font, 0.6, 2)
        cv2.rectangle(frame, (px - 30, py - 55 - th - 5),
                      (px - 30 + tw + 5, py - 55 + bl + 5), (0, 0, 0), -1)
        cv2.putText(frame, label, (px - 30, py - 55), font, 0.6, color, 2)
