'''
Simple Flask application to test deployment to Amazon Web Services
Uses Elastic Beanstalk and RDS

Author: Scott Rodkey - rodkeyscott@gmail.com

Step-by-step tutorial: https://medium.com/@rodkey/deploying-a-flask-application-on-aws-a72daba6bb80
'''

from flask import Flask, render_template, request
from application import db
from application.models import Data, User
from application.forms import *

# Elastic Beanstalk initalization
application = Flask(__name__)
application.debug = True
# change this to your own value
application.secret_key = 'cC1YCIWOj9GgWspgNEo2'

INSTRUCTOR = 'instructor'
STUDENT = 'student'

@application.route('/', methods=['GET', 'POST'])
@application.route('/index', methods=['GET', 'POST'])
def index():
    form1 = EnterDBInfo(request.form)
    form2 = RetrieveDBInfo(request.form)

    if request.method == 'POST' and form1.validate():
        data_entered = Data(notes=form1.dbNotes.data)
        try:
            db.session.add(data_entered)
            db.session.commit()
            db.session.close()
        except:
            db.session.rollback()
        return render_template('thanks.html', notes=form1.dbNotes.data)

    if request.method == 'POST' and form2.validate():
        try:
            num_return = int(form2.numRetrieve.data)
            query_db = Data.query.order_by(Data.id.desc()).limit(num_return)
            for q in query_db:
                print(q.notes)
            db.session.close()
        except:
            db.session.rollback()
        return render_template('results.html', results=query_db, num_return=num_return)

    return render_template('index.html', form1=form1, form2=form2)


@application.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm(request.form)

    if request.method == 'POST':
        if not form.validate():
            return form.errors
        user = User(name=form.name.data, email=form.email.data, password=form.password.data, type=form.user_type.data)
        user_repr = str(user)
        try:
            db.session.add(user)
            db.session.commit()
            db.session.close()
        except Exception as e:
            db.session.rollback()
            # TODO: render form with error msg
            return str(e)
        return render_template('thanks.html', notes=user_repr)

    else: # GET
        return render_template("signup.html", form=form)


# @application.route('/signup', methods=['GET', 'POST'])
# def login():
#     form = SignUpForm(request.form)
#
#     if request.method == 'POST':
#         if not form.validate():
#             return form.errors
#         user = User(name=form.name.data, email=form.email.data, password=form.password.data, type=form.type.data)
#
#         try:
#             queried_instr = USER.query.filter_by(email=instr.email).first()
#             if queried_instr is None:
#                 return "No account is registered with this email."
#             if queried_instr.password != instr.password:
#                 return "Wrong password."
#             return


if __name__ == '__main__':

    application.run(host='0.0.0.0')

