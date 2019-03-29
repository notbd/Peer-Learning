from application import db
from application.models import Data, User, Course, Question, Response

db.create_all()

print("DB created.")
