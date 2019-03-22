from application import db, login_manager
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
    email = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)
    password = db.Column(db.String(80), unique=False, nullable=False)
    type = db.Column(db.String(50))

    def __init__(self, email, name, password, type):
        self.email = email
        self.name = name
        self.password = password
        self.type = type

    def __repr__(self):
        return '<User\tname: %s\temail: %s\tpassword: %s\ttype: %s>' % (self.name, self.email, self.password, self.type)

@login_manager.user_loader
def user_loader(email):
    return User.query.get(email)

#
#
# @login_manager.request_loader
# def request_loader(request):
