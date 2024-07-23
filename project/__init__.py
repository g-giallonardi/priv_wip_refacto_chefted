import os

from flask import Flask
from flask_migrate import Migrate

from project.database.database import db

def create_app(database_uri = "sqlite:///project.db"):
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') #secrets.token_hex(20)
    db.init_app(app)
    migrate = Migrate(app, db)
    return app
