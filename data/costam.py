import os
from db import init_db
 
DB_DIR = os.environ.get("DB_DIR", "data/db")

db_path = os.path.join(DB_DIR, "db.sqlite")
 
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

init_db(db_path)

