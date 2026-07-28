import os
import json
import time
import hashlib
import hmac
import threading
from functools import wraps
from flask import request, jsonify, session

TOKEN_STORE = {}
TOKEN_LOCK = threading.Lock()
TOKEN_EXPIRY = 86400


def generate_token(username):
    ts = int(time.time())
    raw = f"{username}:{ts}:{os.urandom(16).hex()}"
    token = hashlib.sha256(raw.encode()).hexdigest()
    with TOKEN_LOCK:
        TOKEN_STORE[token] = {"username": username, "created": ts, "expires": ts + TOKEN_EXPIRY}
    return token


def validate_token(token):
    with TOKEN_LOCK:
        data = TOKEN_STORE.get(token)
        if not data:
            return None
        if time.time() > data["expires"]:
            del TOKEN_STORE[token]
            return None
        return data["username"]


def revoke_token(token):
    with TOKEN_LOCK:
        TOKEN_STORE.pop(token, None)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        if not token:
            token = request.args.get("token")
        if not token:
            token = request.cookies.get("token")
        if not token or not validate_token(token):
            return jsonify({"error": "Authentication required"}), 401
        request.username = validate_token(token)
        return f(*args, **kwargs)
    return decorated


def init_auth_routes(app, db):
    @app.route("/api/auth/login", methods=["POST"])
    def auth_login():
        data = request.json or {}
        username = data.get("username", "")
        password = data.get("password", "")
        user = db.validate_user(username, password)
        if user:
            token = generate_token(username)
            resp = jsonify({
                "status": "ok",
                "token": token,
                "user": {"username": user["username"], "role": user["role"]},
            })
            resp.set_cookie("token", token, httponly=True, max_age=TOKEN_EXPIRY)
            return resp
        return jsonify({"error": "Invalid credentials"}), 401

    @app.route("/api/auth/logout", methods=["POST"])
    @login_required
    def auth_logout():
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            revoke_token(auth_header[7:])
        return jsonify({"status": "ok"})

    @app.route("/api/auth/check")
    def auth_check():
        token = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        if not token:
            token = request.cookies.get("token")
        if token and validate_token(token):
            return jsonify({"authenticated": True, "username": validate_token(token)})
        return jsonify({"authenticated": False})

    @app.route("/api/users", methods=["GET"])
    @login_required
    def api_users():
        users = db.query("SELECT id, username, role, created_at, last_login FROM users")
        return jsonify({"users": users})

    return app
