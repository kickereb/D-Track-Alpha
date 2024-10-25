import sqlite3

conn = sqlite3.connect("points.sqlite")

cursor = conn.cursor()
sql_query = """ CREATE TABLE location (
    id integer PRIMARY KEY,
    target text NOT NULL,
    seq integer NOT NULL,
    x text NOT NULL,
    y text NOT NULL
)"""

cursor.execute(sql_query)