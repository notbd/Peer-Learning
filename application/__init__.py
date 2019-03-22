from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_login import LoginManager

application = Flask(__name__)
application.config.from_object('config')
db = SQLAlchemy(application)

