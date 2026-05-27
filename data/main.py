# inicjalizacja, przed engine i frontendem
# tworzy bazę sqlite, przetwarza i zapisuje w niej informacje z adnotacji dla engine
import os
import sqlite3
import sys
import xml.etree.ElementTree as ET
from os.path import join, exists

from db import init_db

ANNOTATIONS_DIR = os.environ.get("ANNOTATIONS_DIR", "/data/annotations")
ANNOTATIONS_VEHICLE_DIR = os.environ.get("ANNOTATIONS_VEHICLE_DIR", "/data/annotations_vehicle")
ANNOTATIONS_TRAFFIC_DIR = os.environ.get("ANNOTATIONS_TRAFFIC_DIR", "/data/annotations_traffic")
DB_DIR = os.environ.get("DB_DIR", "/data/db")

WEATHER_MULT = {"clear": 1.0, "cloudy": 1.1, "rain": 1.3, "snow": 1.4}
TIME_MULT = {"daytime": 1.0, "nighttime": 1.3}


def _video_ids():
    if not os.path.isdir(ANNOTATIONS_DIR):
        return []
    return sorted(
        f[:-4] for f in os.listdir(ANNOTATIONS_DIR) if f.endswith(".xml")
    )


def _env_mult(video_id):
    path = join(ANNOTATIONS_DIR, f"{video_id}.xml")
    if not exists(path):
        return 1.0
    try:
        attrs = ET.parse(path).getroot().find("./meta/task/video_attributes")
        if attrs is None:
            return 1.0
        w = (attrs.findtext("weather", "clear") or "clear").lower()
        t = (attrs.findtext("time_of_day", "daytime") or "daytime").lower()
        return WEATHER_MULT.get(w, 1.0) * TIME_MULT.get(t, 1.0)
    except ET.ParseError as e:
        print(f" błąd przy przetwarzaniu adnotacji: {e}", file=sys.stderr)
        return 1.0


def _vehicle_actions(video_id):
    path = join(ANNOTATIONS_VEHICLE_DIR, f"{video_id}_vehicle.xml")
    if not exists(path):
        return {}
    try:
        return {
            int(f.get("id")): f.get("action", "unknown")
            for f in ET.parse(path).getroot().findall("frame")
        }
    except ET.ParseError as e:
        print(f" błąd przy przetwarzaniu adnotacji: {e}", file=sys.stderr)
        return {}


def _traffic_frames(video_id):
    path = join(ANNOTATIONS_TRAFFIC_DIR, f"{video_id}_traffic.xml")
    if not exists(path):
        return {}
    try:
        out = {}
        for f in ET.parse(path).getroot().findall("frame"):
            out[int(f.get("id"))] = {
                "traffic_light": f.get("traffic_light", "n/a"),
                "ped_crossing": int(f.get("ped_crossing", 0)),
                "ped_sign": int(f.get("ped_sign", 0)),
                "stop_sign": int(f.get("stop_sign", 0)),
            }
        return out
    except ET.ParseError as e:
        print(f" błąd przy przetwarzaniu adnotacji: {e}", file=sys.stderr)
        return {}


def index(db_path):
    videos = _video_ids()

    with sqlite3.connect(db_path) as conn:
        for vid in videos:
            env = _env_mult(vid)
            veh = _vehicle_actions(vid)
            trf = _traffic_frames(vid)

            conn.execute(
                "INSERT OR REPLACE INTO video_env (video_id, env_mult) VALUES (?, ?)",
                (vid, env),
            )
            conn.execute("DELETE FROM frame_annotations WHERE video_id = ?", (vid,))

            frame_ids = set(veh) | set(trf)
            rows = []
            for fid in sorted(frame_ids):
                t = trf.get(fid, {})
                rows.append((
                    vid, fid,
                    veh.get(fid),
                    t.get("traffic_light"),
                    t.get("ped_crossing", 0),
                    t.get("ped_sign", 0),
                    t.get("stop_sign", 0),
                ))
            if rows:
                conn.executemany(
                    "INSERT INTO frame_annotations "
                    "(video_id, frame_id, vehicle_action, traffic_light, "
                    " ped_crossing, ped_sign, stop_sign) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )


def main():
    os.makedirs(DB_DIR, exist_ok=True)
    db_path = join(DB_DIR, "db.sqlite")
    print(f"Inicjalizacja bazy danych w {db_path}")
    init_db(db_path)
    index(db_path)
    print("Zakończona")


if __name__ == "__main__":
    main()
