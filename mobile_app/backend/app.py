from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import sqlite3


app = Flask(__name__)
CORS(app)

def db_connection():
    conn = None
    try:
        conn = sqlite3.connect("points.sqlite")
    except sqlite3.error as e:
        print(e)
    return conn



@app.route('/', methods=['GET','POST', 'DELETE', 'WIPE'])
def get_articles():
    conn = db_connection()
    cursor = conn.cursor()
    
    if request.method == "GET":
        cursor = conn.execute("SELECT * FROM location")
        locs = [
            dict(id=r[0],target=r[1], seq=r[2], x=r[3], y=r[4])
            for r in cursor.fetchall()
        ]
        return jsonify(locs)
    
    if request.method == "WIPE":
        cursor = conn.executescript("""DELETE FROM location""")
        conn.commit()
        return "Locations Deleted"
    
    if request.method == "POST":
        n_seq = request.form['seq']
        n_target = request.form['target']
        n_x = request.form['x']
        n_y = request.form['y']
        
        sql = """INSERT INTO location (target, seq, x, y) VALUES (?, ?, ?, ?)"""
        
        cursor = cursor.execute(sql, (n_target, n_seq, n_x, n_y))
        conn.commit()
        return f"Entry with id {cursor.lastrowid} created successfully"
    
    if request.method == "DELETE":
        n_seq = request.form['seq']
        n_target = request.form['target']
        
        sql = """DELETE FROM location WHERE seq=? AND target=?"""
        conn.execute(sql,(n_seq, n_target))
        conn.commit()
        return "Target entry from {} has been deleted".format(n_target)
    
    if request.method == "DTARGET":
        n_target = request.form['target']
        
        sql = """DELETE FROM location WHERE target=?"""
        conn.execute(sql,(n_seq, n_target))
        conn.commit()
        return "Target {} has been deleted".format(n_target)
    
if __name__ == "__main__":
    app.run('10.0.0.169', port = 3000, debug = True)