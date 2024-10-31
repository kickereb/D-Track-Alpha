from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re
from functools import wraps

from datetime import datetime, timedelta, timezone
from database import DTrackDB
from database import TokenManager

app = Flask(__name__)
CORS(app)
db = DTrackDB()
tokenManager = TokenManager()


def requireAuth(f):
    """Decoration to require valid JWT access token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        authHeader = request.headers.get('Authorization')
        
        if not authHeader or not authHeader.startswith('Bearer '):
            return jsonify({'err': 'No token provided'}), 401
            
        token = authHeader.split(' ')[1]
        payload = tokenManager.verifyAccessToken(token)
        
        if not payload:
            return jsonify({'err': 'Invalid or expired token'}), 401
            
        request.user = payload
        return f(*args, **kwargs)
    return decorated


def db_connection():
    conn = None
    try:
        conn = sqlite3.connect("points.sqlite")
    except sqlite3.error as e:
        print(e)
    return conn

def validatePassword(password: str) -> bool:
    """
    Validate password strength:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'err': 'Missing username or password'}), 400
    
    # Validate username
    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        return jsonify({
            'err': 'Username must be 3-20 characters long and contain only letters, numbers, and underscores'
        }), 400
    
    # Validate password strength
    if not validatePassword(password):
        return jsonify({
            'err': 'Password must be at least 8 characters long and contain uppercase, lowercase, and numbers'
        }), 400
    
    if db.createUser(username, password):
        user = db.getUserByName(username)
        accessToken, refreshToken = tokenManager.generateTokens(
            user['id'],
            username
        )
        
        db.storeRefreshToken(
            user['id'],
            refreshToken,
            datetime.now(timezone.utc) + tokenManager.refreshTokenExpiry
        )
        
        return jsonify({
            'message': 'User created successfully',
            'accessToken': accessToken,
            'refreshToken': refreshToken,
            'user': {
                'id': user['id'],
                'username': username
            }
        }), 201
    else:
        return jsonify({'err': 'Username already exists'}), 409
    
@app.route('/refresh', methods=['POST'])
def renewRefreshToken():
    data = request.get_json()
    refreshToken = data.get('refreshToken')
    
    if not refreshToken:
        return jsonify({'err': 'Refresh token is required'}), 400
    
    # Verify the refresh token
    payload = tokenManager.verifyRefreshToken(refreshToken)
    if not payload:
        return jsonify({'err': 'Invalid refresh token'}), 401
    
    # Check if token exists in database
    if not db.validateRefreshToken(refreshToken):
        return jsonify({'err': 'Refresh token has been revoked'}), 401
    
    # Get user information
    user = db.getUserByID(payload['userid'])
    if not user:
        return jsonify({'err': 'User not found'}), 404
    
    # Generate new tokens
    newAccessToken, newRefreshToken = tokenManager.generateTokens(
        user['id'],
        user['username']
    )
    
    # Revoke old refresh token and store new one
    db.revokeRefreshToken(refreshToken)
    db.storeRefreshToken(
        user['id'],
        newRefreshToken,
        datetime.now(timezone.utc) + tokenManager.refreshTokenExpiry
    )
    
    return jsonify({
        'accessToken': newAccessToken,
        'refreshToken': newRefreshToken
    }), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        response = jsonify({'err': 'Missing username or password'})
        response.status_code = 400
        return response
    
    if db.verifyUser(username, password):
        user = db.getUserByName(username)
        
        accessToken, refreshToken = tokenManager.generateTokens(
            user['id'],
            username
        )
        
         # Store refresh token
        db.storeRefreshToken(
            user['id'],
            refreshToken,
            datetime.now(timezone.utc) + tokenManager.refreshTokenExpiry
        )
        
        return jsonify({
            'message': 'Login successful',
            'accessToken': accessToken,
            'refreshToken': refreshToken,
            'user': {
                'id': user['id'],
                'username': username
            }
        }), 200
    else:
        return jsonify({'err': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    data = request.get_json()
    refreshToken = data.get('refreshToken')
    
    if refreshToken:
        db.revokeRefreshToken(refreshToken)
    
    return jsonify({'message': 'Logged out successfully'}), 200

# @app.route('/profile', methods=['GET'])
# @requireAuth
# def getUserProfile():
#     user = db.getUserByID(request.user['userid'])
#     if not user:
#         return jsonify({'err': 'User not found'}), 404
        
#     return jsonify({
#         'user': {
#             'id': user['id'],
#             'username': user['username']
#         }
#     }), 200
    
@app.route('/', methods=['GET','POST', 'DELETE', 'WIPE'])
@requireAuth
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
    conn.close()
    


ipv4 = '10.0.0.169'

if __name__ == "__main__":
    app.run(ipv4, port = 3000, debug = True)