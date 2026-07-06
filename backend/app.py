from pathlib import Path

from flask import Flask

from backend.routes.admin_routes import admin_bp
from backend.routes.auth_routes import auth_bp
from backend.routes.chat_routes import chat_bp
from backend.routes.marketplace_routes import marketplace_bp
from backend.routes.seller_dashboard_routes import seller_dashboard_bp
from backend.services.auth_service import create_admin
from backend.utils.json_storage import ensure_data_files


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "frontend" / "templates"
STATIC_DIR = BASE_DIR / "frontend" / "static"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(TEMPLATE_DIR),
        static_folder=str(STATIC_DIR),
    )

    app.config.from_mapping(
        SECRET_KEY="rp_marketplace_secret_key",
        DATA_DIR=str(DEFAULT_DATA_DIR),
    )

    if test_config:
        app.config.update(test_config)

    with app.app_context():
        ensure_data_files(app.config["DATA_DIR"])
        create_admin()

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(seller_dashboard_bp)
    app.register_blueprint(chat_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
