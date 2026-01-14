from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def init_db(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql://{os.environ['DB_USER']}:"
        f"{os.environ['DB_PASSWORD']}@"
        f"{os.environ['DB_HOST']}:"
        f"{os.environ['DB_PORT']}/"
        f"{os.environ['DB_NAME']}"
        "?sslmode=require"
    )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
