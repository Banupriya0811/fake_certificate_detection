"""Token authentication and password hashing helpers."""

from functools import wraps
from flask import current_app, g, jsonify, request
from flask_bcrypt import Bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import User

bcrypt = Bcrypt()


def hash_password(plain_password: str) -> str:
    return bcrypt.generate_password_hash(plain_password).decode("utf-8")


def verify_password(hashed_password: str, plain_password: str) -> bool:
    return bcrypt.check_password_hash(hashed_password, plain_password)


def create_auth_token(user_id: int) -> str:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"user_id": user_id}, salt="docverify-auth")


def decode_auth_token(token: str) -> int | None:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    max_age = current_app.config["TOKEN_EXPIRY_SECONDS"]
    try:
        payload = serializer.loads(token, salt="docverify-auth", max_age=max_age)
        return payload.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def token_required(fn):
    """Protect API endpoints using Authorization: Bearer <token>."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if not token:
            return jsonify({"error": "Authentication token required."}), 401

        user_id = decode_auth_token(token)
        if not user_id:
            return jsonify({"error": "Invalid or expired token. Please log in again."}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User account not found."}), 401

        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper

