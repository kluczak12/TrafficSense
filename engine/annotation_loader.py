import xml.etree.ElementTree as ET
from os.path import join, exists

WEATHER_MULT = {'clear': 1.0, 'cloudy': 1.1, 'rain': 1.3, 'snow': 1.4}
TIME_MULT = {'daytime': 1.0, 'nighttime': 1.3}
VEHICLE_MULT = {
    'stopped': 0.2, 'moving_slow': 0.4, 'moving_fast': 0.8,
    'accelerating': 0.9, 'decelerating': 0.3,
}


class AnnotationManager:
    def __init__(self, base_path):
        self._main = join(base_path, 'annotations')
        self._vehicle = join(base_path, 'annotations_vehicle')
        self._traffic = join(base_path, 'annotations_traffic')
        self._cache = {}

    def load(self, video_id):
        if video_id in self._cache:
            return self._cache[video_id]

        data = {'vehicle': {}, 'traffic': {}, 'env_mult': 1.0}

        veh_path = join(self._vehicle, f'{video_id}_vehicle.xml')
        if exists(veh_path):
            try:
                for f in ET.parse(veh_path).getroot().findall('frame'):
                    data['vehicle'][int(f.get('id'))] = f.get('action', 'unknown')
            except Exception as e:
                print(f"Vehicle annotation error {video_id}: {e}")

        trf_path = join(self._traffic, f'{video_id}_traffic.xml')
        if exists(trf_path):
            try:
                root = ET.parse(trf_path).getroot()
                for f in root.findall('frame'):
                    data['traffic'][int(f.get('id'))] = {
                        'ped_crossing': int(f.get('ped_crossing', 0)),
                        'ped_sign': int(f.get('ped_sign', 0)),
                        'stop_sign': int(f.get('stop_sign', 0)),
                        'traffic_light': f.get('traffic_light', 'n/a'),
                    }
            except Exception as e:
                print(f"Traffic annotation error {video_id}: {e}")

        main_path = join(self._main, f'{video_id}.xml')
        if exists(main_path):
            try:
                attrs = ET.parse(main_path).getroot().find('./meta/task/video_attributes')
                if attrs is not None:
                    w = attrs.findtext('weather', 'clear').lower()
                    t = attrs.findtext('time_of_day', 'daytime').lower()
                    data['env_mult'] = WEATHER_MULT.get(w, 1.0) * TIME_MULT.get(t, 1.0)
            except Exception as e:
                print(f"Env annotation error {video_id}: {e}")

        self._cache[video_id] = data
        return data

    def frame_risk_mult(self, video_id, frame_id):
        # Łączny mnożnik ryzyka dla klatki: pogoda i pora dnia * ruch auta * otoczenie
        data = self.load(video_id)
        mult = data['env_mult']

        action = data['vehicle'].get(frame_id, 'unknown')
        # nie wiem czy to ma sens, na razie zakomentowane
        # mult *= VEHICLE_MULT.get(action, 0.5)

        tr = data['traffic'].get(frame_id, {})
        if tr.get('traffic_light') == 'red':
            mult *= 0.7
        if tr.get('stop_sign'):
            mult *= 0.8
        if tr.get('ped_crossing'):
            mult *= 1.2

        return mult
