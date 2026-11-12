"""REST API endpoints for authentication, scanning, history, and profile."""

import base64
import os
import re
from datetime import datetime, timezone
from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from auth import create_auth_token, hash_password, token_required, verify_password
from models import ScanHistory, User, db

api = Blueprint("api", __name__, url_prefix="/api")


def _allowed_file(filename: str) -> bool:
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _save_scan_record(user_id: int, filename: str, prediction: dict) -> ScanHistory:
    scan = ScanHistory(
        user_id=user_id,
        filename=filename,
        result=prediction["result"],
        confidence=prediction["confidence"],
    )
    db.session.add(scan)
    db.session.commit()
    return scan


# ── HEALTH ────────────────────────────────────────────────────────────────────
@api.route("/health", methods=["GET"])
def health():
    predictor = current_app.predictor
    return jsonify({
        "status": "ok",
        "model_loaded": predictor.is_loaded,
        "mode": "model" if predictor.is_loaded else "demo",
    })


# ── AUTHENTICATION ────────────────────────────────────────────────────────────
@api.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username:
        return jsonify({"error": "Username is required."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "A valid email address is required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username is already taken."}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email is already registered."}), 409

    user = User(username=username, email=email, password=hash_password(password))
    db.session.add(user)
    db.session.commit()

    token = create_auth_token(user.id)
    return jsonify({"token": token, "user": user.to_dict()}), 201


@api.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not verify_password(user.password, password):
        return jsonify({"error": "Invalid username or password."}), 401

    token = create_auth_token(user.id)
    return jsonify({"token": token, "user": user.to_dict()})


@api.route("/auth/me", methods=["GET"])
@token_required
def me():
    return jsonify({"user": g.current_user.to_dict()})


# ── DOCUMENT SCANNING ─────────────────────────────────────────────────────────
@api.route("/scan/upload", methods=["POST"])
@token_required
def scan_upload():
    user = g.current_user
    file = request.files.get("file")

    if not file or not file.filename:
        return jsonify({"error": "Please select an image file to scan."}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type. Allowed: PNG, JPG, JPEG, BMP, TIFF, WEBP."}), 400

    safe_name = secure_filename(file.filename)
    filename = f"{user.id}_{_timestamp()}_{safe_name}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    prediction = current_app.predictor.predict(filepath)
    scan = _save_scan_record(user.id, filename, prediction)

    return jsonify({
        "scan": scan.to_dict(),
        "prediction": prediction,
        "image_url": f"/api/files/uploads/{filename}",
    }), 201


@api.route("/scan/camera", methods=["POST"])
@token_required
def scan_camera():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    data_url = data.get("image_data") or ""

    if not data_url:
        return jsonify({"error": "No captured image data received."}), 400

    encoded = re.sub(r"^data:image/\w+;base64,", "", data_url)
    filename = f"{user.id}_{_timestamp()}_camera.jpg"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

    try:
        raw_bytes = base64.b64decode(encoded)
        with open(filepath, "wb") as f:
            f.write(raw_bytes)
    except Exception:
        return jsonify({"error": "Invalid camera image data."}), 400

    prediction = current_app.predictor.predict(filepath)
    scan = _save_scan_record(user.id, filename, prediction)

    return jsonify({
        "scan": scan.to_dict(),
        "prediction": prediction,
        "image_url": f"/api/files/uploads/{filename}",
    }), 201


# ── HISTORY & STATS ───────────────────────────────────────────────────────────
@api.route("/scans", methods=["GET"])
@token_required
def list_scans():
    user = g.current_user
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 10, type=int)))
    filter_type = (request.args.get("filter") or "all").lower()

    query = ScanHistory.query.filter_by(user_id=user.id)
    if filter_type == "fake":
        query = query.filter_by(result="Fake Document")
    elif filter_type == "real":
        query = query.filter_by(result="Original Document")

    pagination = query.order_by(ScanHistory.scanned_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    total = ScanHistory.query.filter_by(user_id=user.id).count()
    fakes = ScanHistory.query.filter_by(user_id=user.id, result="Fake Document").count()

    return jsonify({
        "items": [
            {**s.to_dict(), "image_url": f"/api/files/uploads/{s.filename}"}
            for s in pagination.items
        ],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
        },
        "stats": {
            "total": total,
            "fakes": fakes,
            "reals": total - fakes,
        },
    })


@api.route("/scans/<int:scan_id>", methods=["DELETE"])
@token_required
def delete_scan(scan_id: int):
    user = g.current_user
    scan = ScanHistory.query.filter_by(id=scan_id, user_id=user.id).first()
    if not scan:
        return jsonify({"error": "Scan record not found."}), 404

    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], scan.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(scan)
    db.session.commit()
    return jsonify({"success": True})


# ── PROFILE ───────────────────────────────────────────────────────────────────
@api.route("/profile", methods=["GET"])
@token_required
def get_profile():
    user = g.current_user
    total = ScanHistory.query.filter_by(user_id=user.id).count()
    fakes = ScanHistory.query.filter_by(user_id=user.id, result="Fake Document").count()
    recent = (
        ScanHistory.query.filter_by(user_id=user.id)
        .order_by(ScanHistory.scanned_at.desc())
        .limit(5)
        .all()
    )

    return jsonify({
        "user": user.to_dict(),
        "stats": {
            "total": total,
            "fakes": fakes,
            "reals": total - fakes,
        },
        "recent": [s.to_dict() for s in recent],
    })


@api.route("/profile", methods=["PUT"])
@token_required
def update_profile():
    user = g.current_user

    # Support both multipart form-data (when uploading avatar) and JSON
    if request.content_type and "multipart/form-data" in request.content_type:
        new_username = (request.form.get("username") or "").strip()
        new_email = (request.form.get("email") or "").strip().lower()
        new_password = (request.form.get("new_password") or "").strip()
        avatar_file = request.files.get("profile_pic")
    else:
        data = request.get_json(silent=True) or {}
        new_username = (data.get("username") or "").strip()
        new_email = (data.get("email") or "").strip().lower()
        new_password = (data.get("new_password") or "").strip()
        avatar_file = None

    if not new_username:
        return jsonify({"error": "Username is required."}), 400
    if not new_email or "@" not in new_email:
        return jsonify({"error": "Valid email address is required."}), 400
    if new_password and len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400

    if User.query.filter(User.username == new_username, User.id != user.id).first():
        return jsonify({"error": "Username is already taken."}), 409
    if User.query.filter(User.email == new_email, User.id != user.id).first():
        return jsonify({"error": "Email is already in use."}), 409

    user.username = new_username
    user.email = new_email
    if new_password:
        user.password = hash_password(new_password)

    if avatar_file and avatar_file.filename:
        if not _allowed_file(avatar_file.filename):
            return jsonify({"error": "Unsupported avatar image format."}), 400
        pic_name = secure_filename(f"pfp_{user.id}_{avatar_file.filename}")
        avatar_file.save(os.path.join(current_app.config["AVATAR_FOLDER"], pic_name))
        user.profile_pic = pic_name

    db.session.commit()
    return jsonify({"user": user.to_dict()})


# ── FILE SERVING ──────────────────────────────────────────────────────────────
@api.route("/files/uploads/<path:filename>", methods=["GET"])
def serve_upload(filename: str):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))


@api.route("/files/avatars/<path:filename>", methods=["GET"])
def serve_avatar(filename: str):
    return send_from_directory(current_app.config["AVATAR_FOLDER"], os.path.basename(filename))

