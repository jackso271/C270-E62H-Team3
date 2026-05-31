# backend/server.py
# Main entry point for the Flask backend
# Run with: python server.py

from flask import Flask
from flask_cors import CORS
from routes.products import products_bp, init_db

app = Flask(__name__)
CORS(app)  # Allows the HTML frontend to call this API from a different port

# Register Oliver's product routes
app.register_blueprint(products_bp)

if __name__ == '__main__':
    init_db()           # Create tables + seed data on first run
    app.run(port=5000, debug=True)
