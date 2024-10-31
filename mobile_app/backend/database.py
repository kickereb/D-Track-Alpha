import sqlite3
import bcrypt
import jwt
import os

from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

class TokenManager:
    def __init__(self):
        load_dotenv()
        self.accessTokenSecret = os.getenv('JWT_ACCESS_S', 'accessSecretKey')
        self.accessTokenExpiry = timedelta(minutes=15)
        
        self.refreshTokenSecret = os.getenv('JWT_REFRESH_S', 'refreshSecretKey')
        self.refreshTokenExpiry = timedelta(days=1)
    
    def generateTokens(self, userID: int, username: str):
        """Generates access and refresh tokens for a user"""
        
        # Generate access token
        accessTokenPayload = {
            'userid': userID,
            'username': username,
            'exp': datetime.now(timezone.utc) + self.accessTokenExpiry,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }
        accessToken = jwt.encode(
            accessTokenPayload,
            self.accessTokenSecret,
            algorithm='HS256'
        )

        # Generate refresh token
        refreshTokenPayload = {
            'userid': userID,
            'exp': datetime.now(timezone.utc) + self.refreshTokenExpiry,
            'iat': datetime.now(timezone.utc),
            'type': 'refresh'
        }
        refreshToken = jwt.encode(
            refreshTokenPayload,
            self.refreshTokenSecret,
            algorithm='HS256'
        )

        return accessToken, refreshToken

    def verifyAccessToken(self, token: str):
        """Verify an access token and return the contained payload if token is valid"""
        try:
            payload = jwt.decode(
                token,
                self.accessTokenSecret,
                algorithms=['HS256']
            )
            
            if payload['type'] != 'access':
                return None
            return payload
        
        except jwt.ExpiredSignatureError:
            return None
        
        except jwt.InvalidTokenError:
            return None
        
    def verifyRefreshToken(self, token: str):
        """Verify a refresh token and return the contained payload if token is valid"""
        try:
            payload = jwt.decode(
                token,
                self.refreshTokenSecret,
                algorithms=['HS256']
            )
            if payload['type'] != 'refresh':
                return None
            return payload
        
        except jwt.ExpiredSignatureError:
            return None
        
        except jwt.InvalidTokenError:
            return None

class DTrackDB:
    def __init__(self, dbPath: str="points.sqlite"):
        self.dbPath = dbPath
        self.initDB()

    def initDB(self):
        """Initialize the database with neccesary tables"""
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        queryLoc = """ CREATE TABLE IF NOT EXISTS location (
            id integer PRIMARY KEY AUTOINCREMENT,
            target text NOT NULL,
            seq integer NOT NULL,
            x text NOT NULL,
            y text NOT NULL
        )"""
        
        queryAuth = """ CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            pwdhash TEXT NOT NULL,
            userlevel TEXT NOT NULL
        )"""
        
        queryToken = """ CREATE TABLE IF NOT EXISTS refreshtokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expiry TIMESTAMP NOT NULL,
            FOREIGN KEY (userid) REFERENCES users (id)
        )"""
        
        cursor.execute(queryLoc)
        conn.commit()
        cursor.execute(queryAuth)
        conn.commit()
        cursor.execute(queryToken)
        
        conn.commit()
        conn.close()
        
    def hashPwd(self, password: str):
        pwdBytes = password.encode('utf-8')
        pwdHash = bcrypt.hashpw(pwdBytes, bcrypt.gensalt())
        return pwdHash
            

    def createUser(self, username: str, password: str):
        """Create a new user with the given username and password"""
        try:
            conn = sqlite3.connect(self.dbPath)
            cursor = conn.cursor()
            
            pwdhash = self.hashPwd(password)
            
            queryInsert = """
                INSERT INTO users (username, pwdhash, userlevel)
                VALUES (?, ?, ?)
            """
            
            cursor.execute(queryInsert, (username, pwdhash,1,))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            # Username already exists
            return False
        
    

    def verifyUser(self, username: str, password: str):
        """Verify a user's credentials"""
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        queryCompare = """ SELECT pwdhash FROM users WHERE username = ? """
        
        # Get user's stored password hash
        cursor.execute(queryCompare, (username,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result is None:
            return False
            
        stored_hash = result[0]
        # Verify the password using bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)

    def getUserByName(self, username: str):
        """Get user data by username"""
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        queryGet = """ SELECT id, username, userlevel FROM users WHERE username = ? """
        
        cursor.execute(queryGet, (username,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'username': result[1],
                'userlevel': result[2]
            }
        return None
    
    def getUserByID(self, id: int):
        """Get user data by username"""
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        queryGet = """ SELECT id, username, userlevel FROM users WHERE id = ? """
        
        cursor.execute(queryGet, (id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'username': result[1],
                'userlevel': result[2]
            }
        return None
    
    def storeRefreshToken(self, userID: int, token: str, expiry: datetime):
        """Store a refresh token"""
        try:
            conn = sqlite3.connect(self.dbPath)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO refreshtokens (userid, token, expiry)
                VALUES (?, ?, ?)
            ''', (userID, token, expiry,))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
        
    def revokeRefreshToken(self, token: str):
        """Revoke a refresh token"""
        try:
            conn = sqlite3.connect(self.dbPath)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM refreshtokens WHERE token = ?', (token,))
            
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
        
    def validateRefreshToken(self, token: str):
        """Check if refresh token is valid and not expired"""
        conn = sqlite3.connect(self.dbPath)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT expiry
            FROM refreshtokens
            WHERE token = ?
            AND expiry > datetime('now')
        ''', (token,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None