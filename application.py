'''
Simple Flask application to test deployment to Amazon Web Services
Uses Elastic Beanstalk and RDS

Author: Scott Rodkey - rodkeyscott@gmail.com

Step-by-step tutorial: https://medium.com/@rodkey/deploying-a-flask-application-on-aws-a72daba6bb80
'''

from flask import Flask, render_template, request, redirect, url_for
from application import db
from application.models import *
from application.forms import *
import flask_login

# Elastic Beanstalk initalization
application = Flask(__name__)
application.debug = True
# change this to your own value
application.secret_key = 'cC1YCIWOj9GgWspgNEo2'

login_manager = flask_login.LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'login'

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
        user = User(email=form.email.data, password=form.password.data, user_type=form.user_type.data,
                    name=form.name.data)
        user_repr = str(user)
        try:
            # db.session.add(user)
            db.session.execute(
                'INSERT INTO user '
                '(email, password, name, user_type) '
                'VALUES ("%s", "%s", "%s", "%s")' %
                (user.email, user.password, user.name, user.user_type))
            db.session.commit()
            db.session.close()
        except Exception as e:
            db.session.rollback()
            # TODO: render form with error msg
            return str(e)
        return render_template('thanks.html', notes=user_repr)

    else:  # GET
        return render_template("signup.html", form=form)


@application.route('/login', methods=['GET', 'POST'])
def login():
    form = LogInForm(request.form)

    if request.method == 'POST':
        if not form.validate():
            return form.errors
        user = User(email=form.email.data, password=form.password.data)
        try:
            # queried_user = User.query.filter_by(email=user.email).first()
            queried_user = db.session.execute('SELECT * FROM user WHERE email = "%s"' % user.email).fetchone()
            if queried_user is None:
                return "No account is registered with this email."
            if queried_user.password != user.password:
                return "Wrong password."
            flask_login.login_user(
                user_from_query_result(queried_user))  # conversion is needed for flask_login functions
            redirect_endpoint = "instructor_dashboard" if queried_user.user_type == INSTRUCTOR else "student_dashboard"
            db.session.close()
            return redirect(url_for(redirect_endpoint))
        except Exception as e:
            return str(e)
    else:
        return render_template("login.html", form=form)


@application.route('/logout', methods=['POST'])
def logout():
    flask_login.logout_user()
    return redirect(url_for("login"))


@application.route('/dashboard/instructor/courses', methods=['GET', 'POST'])
def instructor_dashboard():
    if flask_login.current_user is None or flask_login.current_user.is_anonymous:
        return redirect(url_for('login'))

    if flask_login.current_user.user_type == STUDENT:
        return redirect(url_for('student_dashboard'))

    add_course_form = CourseInfoForm(request.form)

    if request.method == 'POST':
        if not add_course_form.validate():
            return str(add_course_form.errors)

        c = Course(CRN=add_course_form.CRN.data, title=add_course_form.title.data, year=add_course_form.year.data,
                   term=add_course_form.term.data,
                   instructor=flask_login.current_user.email)
        try:
            db.session.execute(
                'INSERT INTO course '
                '(CRN, title, year, term, instructor) '
                'VALUES ("%s", "%s", "%s", "%s", "%s")' %
                (c.CRN, c.title, c.year, c.term, c.instructor))
            db.session.commit()
            db.session.close()
        except Exception as e:
            db.session.rollback()
            # TODO: render form with error msg
            return str(e)
        return redirect(url_for('instructor_dashboard'))
    elif request.method == 'GET':
        try:
            courses = Course.query.filter_by(instructor=flask_login.current_user.email)
            return render_template("instructor_dashboard.html", current_user=flask_login.current_user, courses=courses,
                                   add_course_form=add_course_form)
        except Exception as e:
            db.session.rollback()
            return str(e)

    return render_template("instructor_dashboard.html", current_user=flask_login.current_user,
                           add_course_form=add_course_form)


@application.route('/dashboard/student', methods=['GET'])
def student_dashboard():
    if flask_login.current_user is None or flask_login.current_user.is_anonymous:
        return redirect(url_for('login'))

    if flask_login.current_user.user_type == INSTRUCTOR:
        return redirect(url_for('instructor_dashboard'))

    return render_template("student_dashboard.html", current_user=flask_login.current_user)

@application.route('/update/')
def update():
    name = request.args.get('name')
    return render_template('update.html')

@application.route('/updateaction/', methods=['POST'])
def updateaction():
    params = request.args if request.method == 'GET' else request.form
    newname = params.get('name')
    try:
        db.session.execute('UPDATE user SET name = "%s" WHERE email = "%s"' % (newname, flask_login.current_user.email))
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return redirect(url_for('student_dashboard'))

@login_manager.user_loader
def user_loader(email):
    return User.query.get(email)


if __name__ == '__main__':
    application.run(host='0.0.0.0')
