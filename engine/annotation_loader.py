import sqlite3


class AnnotationManager:
    def __init__(self, db_path):
        self._db_path = db_path
        self._conn = None
        self._env = {} # video_id -> env_mult
        self._frames = {} # video_id -> {frame_id -> row dict}
        self._loaded = set() # video_ids których klatki zostały już załadowane

    def _connect(self):
        if self._conn is None:
            uri = f"file:{self._db_path}?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def load(self, video_id):
        # załadowanie informacji dla filmu video_id
        if video_id in self._loaded:
            return
        conn = self._connect()

        row = conn.execute(
            "SELECT env_mult FROM video_env WHERE video_id = ?", (video_id,),
        ).fetchone()
        self._env[video_id] = row["env_mult"] if row else 1.0

        frames = {}
        for r in conn.execute(
            "SELECT frame_id, vehicle_action, traffic_light, "
            "       ped_crossing, ped_sign, stop_sign "
            "FROM frame_annotations WHERE video_id = ?",
            (video_id,),
        ):
            frames[r["frame_id"]] = {
                "vehicle_action": r["vehicle_action"],
                "traffic_light": r["traffic_light"],
                "ped_crossing": r["ped_crossing"],
                "ped_sign": r["ped_sign"],
                "stop_sign": r["stop_sign"],
            }
        self._frames[video_id] = frames
        self._loaded.add(video_id)

    def frame_risk_mult(self, video_id, frame_id):
        # mnożnik ryzyka w danej klatce
        if video_id not in self._loaded:
            self.load(video_id)

        mult = self._env.get(video_id, 1.0)
        tr = self._frames.get(video_id, {}).get(frame_id, {})

        if tr.get("traffic_light") == "red":
            mult *= 0.7
        if tr.get("stop_sign"):
            mult *= 0.8
        if tr.get("ped_crossing"):
            mult *= 1.2

        return mult