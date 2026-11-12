"""SQLAlchemy database models for users and document scan history."""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(200), default="default.png")
    created_at = db.Column(db.DateTime, default=_utcnow)

    scans = db.relationship(
        "ScanHistory",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "profile_pic": self.profile_pic or "default.png",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScanHistory(db.Model):
    __tablename__ = "scan_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    result = db.Column(db.String(50), nullable=False)  # "Fake Document" | "Original Document"
    confidence = db.Column(db.Float, nullable=False)
    scanned_at = db.Column(db.DateTime, default=_utcnow)

    @property
    def is_fake(self) -> bool:
        return self.result == "Fake Document"

    def to_dict(self) -> dict:
        display_name = (
            self.filename.split("_", 2)[-1]
            if self.filename.count("_") >= 2
            else self.filename
        )
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "display_name": display_name,
            "result": self.result,
            "is_fake": self.is_fake,
            "confidence": round(float(self.confidence), 2),
            "scanned_at": self.scanned_at.isoformat() if self.scanned_at else None,
        }

