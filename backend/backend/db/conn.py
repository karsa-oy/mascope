import sqlite3

from backend.db import db_path

conn = sqlite3.connect(database=db_path)
