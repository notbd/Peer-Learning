from application import db
from application.models import User, Course, Question


Course.__table__.drop(db.engine)
User.__table__.drop(db.engine)
Question.__table__.drop(db.engine)

print("Tables removed.")
