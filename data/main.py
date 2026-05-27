# inicjalizacja, przed engine i frontendem
# tworzy bazę sqlite, przetwarza i zapisuje w niej informacje z adnotacji dla engine
import os
import sqlite3
import sys
import xml.etree.ElementTree as ET
from os.path import join, exists

from db import init_db

ANNOTATIONS_DIR = os.environ.get("ANNOTATIONS_DIR", "/data/videos/annotations")
ANNOTATIONS_VEHICLE_DIR = os.environ.get("ANNOTATIONS_VEHICLE_DIR", "/data/annotations_vehicle")
ANNOTATIONS_TRAFFIC_DIR = os.environ.get("ANNOTATIONS_TRAFFIC_DIR", "/data/annotations_traffic")
DB_DIR = os.environ.get("DB_DIR", "/data/db")

WEATHER_MULT = {"clear": 1.0, "cloudy": 1.1, "rain": 1.3, "snow": 1.4}
TIME_MULT = {"daytime": 1.0, "nighttime": 1.3}


def _read_attr(attrs, key, default="unknown"):
    if attrs is None:
        return default

    # Format 1: <weather>clear</weather>
    text_val = attrs.findtext(key)
    if text_val:
        return text_val.strip().lower()

    # Format 2: <weather val="clear"/>
    node = attrs.find(key)
    if node is not None:
        node_val = node.get("val")
        if node_val:
            return node_val.strip().lower()

    # Format 3: misspelled key in source data
    if key == "location":
        typo_text_val = attrs.findtext("loaction")
        if typo_text_val:
            return typo_text_val.strip().lower()
        typo_node = attrs.find("loaction")
        if typo_node is not None:
            typo_node_val = typo_node.get("val")
            if typo_node_val:
                return typo_node_val.strip().lower()

    return default


def _detect_annotations_dir():
    if os.path.isdir(ANNOTATIONS_DIR):
        return ANNOTATIONS_DIR
    fallback = "/data/annotations"
    if os.path.isdir(fallback):
        return fallback
    return ANNOTATIONS_DIR


def _video_ids():
    annotations_dir = _detect_annotations_dir()
    if not os.path.isdir(annotations_dir):
        return []
    return sorted(
        f[:-4] for f in os.listdir(annotations_dir) if f.endswith(".xml")
    )


def _video_env(video_id):
    path = join(_detect_annotations_dir(), f"{video_id}.xml")
    if not exists(path):
        return 1.0, "unknown", "unknown"
    try:
        attrs = ET.parse(path).getroot().find("./meta/task/video_attributes")
        if attrs is None:
            return 1.0, "unknown", "unknown"
        weather = _read_attr(attrs, "weather", "clear")
        location = _read_attr(attrs, "location", "unknown")
        time_of_day = _read_attr(attrs, "time_of_day", "daytime")
        env_mult = WEATHER_MULT.get(weather, 1.0) * TIME_MULT.get(time_of_day, 1.0)
        return env_mult, weather, location
    except ET.ParseError as e:
        print(f" błąd przy przetwarzaniu adnotacji: {e}", file=sys.stderr)
        return 1.0, "unknown", "unknown"


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
            env, weather, location = _video_env(vid)
            veh = _vehicle_actions(vid)
            trf = _traffic_frames(vid)

            conn.execute(
                "INSERT OR REPLACE INTO video_env (video_id, env_mult, weather, location) "
                "VALUES (?, ?, ?, ?)",
                (vid, env, weather, location),
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
