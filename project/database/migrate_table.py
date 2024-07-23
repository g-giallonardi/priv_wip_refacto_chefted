from flask import Flask
from flask_migrate import Migrate

from database import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://u4s9q1f8hduon1:p0d45e96fed4eeac5c304366ebd0990df453fd527a5c4f101efd2fd6999c73d29@c9tiftt16dc3eo.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/db33h38lta4put'
migrate = Migrate(app, db)