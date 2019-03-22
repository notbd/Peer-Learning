from application import db
from application.models import Data, User, Course

db.create_all()

print("DB created.")
