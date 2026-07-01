from flask import Flask

from backend.routes.sell_items_routes import sell_items_bp


def create_app():
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static"
    )

    app.secret_key = "dev-secret-key"

    app.register_blueprint(sell_items_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)