from application import db
from flask_login import LoginManager, UserMixin, \
    login_required, login_user, logout_user


class Data(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    notes = db.Column(db.String(128), index=True, unique=False)

    def __init__(self, notes):
        self.notes = notes

    def __repr__(self):
        return '<Data %r>' % self.notes


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    email = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    password = db.Column(db.String(80), unique=False, nullable=False)
    user_type = db.Column(db.String(50))

    def __init__(self, email, password, user_type="", name=""):
        self.email = email
        self.name = name
        self.password = password
        self.user_type = user_type

    def get_id(self):
        return self.email

    def is_authenticated(self):
        return True

    def __repr__(self):
        return '<User\tname: %s\temail: %s\tpassword: %s\ttype: %s>' % (
            self.name, self.email, self.password, self.user_type)


def user_from_query_result(query_result):
    return User(query_result.email, query_result.password, query_result.user_type,
                query_result.name)


class Course(db.Model):
    CRN = db.Column(db.String(120), primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    term = db.Column(db.String(10), nullable=False)
    instructor = db.Column(db.String(120), db.ForeignKey('user.email'))
    active_question = db.Column(db.Integer,
                                nullable=True)  # supposed to be a foreign key, but will cause circular dependency

    def __init__(self, CRN, title, year, term, instructor):
        self.CRN = CRN
        self.year = year
        self.title = title
        self.term = term
        self.instructor = instructor
        self.active_question = None


class Take(db.Model):
    CRN = db.Column(db.String(120), db.ForeignKey('course.CRN'), primary_key=True)
    student = db.Column(db.String(120), db.ForeignKey('user.email'), primary_key=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    CRN = db.Column(db.String(120), db.ForeignKey('course.CRN'))
    date = db.Column(db.Date())
    question = db.Column(db.String(300))
    schemas = db.Column(db.String(1000), nullable=True)

    def __init__(self, id, question, schemas, CRN=None):
        self.id = id
        self.question = question
        self.schemas = schemas
        self.CRN = CRN



class Response(db.Model):
    question_id = db.Column(db.Integer, primary_key=True)
    student = db.Column(db.String(120), db.ForeignKey('user.email'), primary_key=True)
    response = db.Column(db.String(1000))
