from application import db
from application.models import Data, User, Course


Course.__table__.drop(db.engine)
User.__table__.drop(db.engine)

print("Tables removed.")
