"""DocVerify AI — Flask REST API entry point."""

import os
from flask import Flask, jsonify
from flask_cors import CORS

from auth import bcrypt
from config import Config
from models import db
from predictor import DocumentPredictor
from routes import api


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["INSTANCE_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["AVATAR_FOLDER"], exist_ok=True)
    os.makedirs(app.config["MODEL_DIR"], exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    db.init_app(app)
    bcrypt.init_app(app)

    with app.app_context():
        db.create_all()

    app.predictor = DocumentPredictor(
        model_path=app.config["MODEL_PATH"],
        class_info_path=app.config["CLASS_INFO_PATH"],
        image_size=app.config["IMAGE_SIZE"],
    )

    app.register_blueprint(api)

    @app.errorhandler(413)
    def file_too_large(_error):
        return jsonify({"error": "File too large. Maximum allowed size is 16 MB."}), 413

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Endpoint not found."}), 404

    return app


app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 52)
    print("  DocVerify AI — Backend REST API")
    print(f"  Model Loaded : {'YES' if app.predictor.is_loaded else 'NO (Demo Mode)'}")
    print(f"  Database     : {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("  Listening on : http://127.0.0.1:5000")
    print("=" * 52 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000)

