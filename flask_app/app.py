from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask

from flask_app.models.database import init_db
from flask_app.routes.live_routes import live_bp
from flask_app.routes.main_routes import main_bp
from flask_app.routes.predict_routes import predict_bp
from flask_app.routes.report_routes import report_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    base_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    app.config["SECRET_KEY"] = "oa-screening-secret-key"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    app.config["LANGUAGE_DEFAULT"] = "en"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str((base_dir.parent / "data" / "oa_screening.db").resolve())
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    init_db(app)
    app.register_blueprint(main_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(live_bp)

    @app.route("/health")
    def health():
        return {"status": "ok", "message": "OA Screening API is running."}, 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
