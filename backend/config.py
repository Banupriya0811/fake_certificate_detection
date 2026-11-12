"""Central configuration for the DocVerify AI backend API."""

import os
import secrets

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Application configuration loaded from environment variables with safe defaults."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    TOKEN_EXPIRY_SECONDS = int(os.environ.get("TOKEN_EXPIRY_SECONDS", 60 * 60 * 24 * 7))  # 7 days

    # Database
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'docverify.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File storage
    STORAGE_DIR = os.path.join(BASE_DIR, "storage")
    UPLOAD_FOLDER = os.path.join(STORAGE_DIR, "uploads")
    AVATAR_FOLDER = os.path.join(STORAGE_DIR, "avatars")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff", "webp"}

    # ML model artifacts
    MODEL_DIR = os.path.join(BASE_DIR, "model")
    MODEL_PATH = os.path.join(MODEL_DIR, "model.keras")
    CLASS_INFO_PATH = os.path.join(MODEL_DIR, "class_info.json")
    IMAGE_SIZE = (224, 224)

    # CORS origins for separate frontend
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
