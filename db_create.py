from application import db
from application.models import Data, User

db.create_all()

print("DB created.")
