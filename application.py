from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from application import db
from application.models import *
from application.forms import *
import flask_login
import query_parser
import datetime

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


@application.route('/')
@application.route('/index')
def index():
    # form1 = EnterDBInfo(request.form)
    # form2 = RetrieveDBInfo(request.form)

    # if request.method == 'POST' and form1.validate():
    #     data_entered = Data(notes=form1.dbNotes.data)
    #     try:
    #         db.session.add(data_entered)
    #         db.session.commit()
    #         db.session.close()
    #     except:
    #         db.session.rollback()
    #     return render_template('thanks.html', notes=form1.dbNotes.data)

    # if request.method == 'POST' and form2.validate():
    #     try:
    #         num_return = int(form2.numRetrieve.data)
    #         query_db = Data.query.order_by(Data.id.desc()).limit(num_return)
    #         for q in query_db:
    #             print(q.notes)
    #         db.session.close()
    #     except:
    #         db.session.rollback()
    #     return render_template('results.html', results=query_db, num_return=num_return)

    # return render_template('index.html', form1=form1, form2=form2)
    return render_template('index.html')


@application.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm(request.form)

    if request.method == 'POST':
        if not form.validate():
            return str(form.errors)
        user = User(email=form.email.data, password=form.password.data, user_type=form.user_type.data,
                    name=form.name.data)
        user_repr = str(user)
        print("user to sign up: ", user_repr)
        try:
            # db.session.add(user)
            db.session.execute(
                'INSERT INTO user '
                '(email, password, name, user_type) '
                'VALUES ("%s", "%s", "%s", "%s")' %
                (user.email, user.password, user.name, user.user_type))
            db.session.commit()
            db.session.close()
            return redirect(url_for('login', data=request.form.get('data')), code=307)
        except Exception as e:
            db.session.rollback()
            # TODO: render form with error msg
            return str(e)

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


@application.route('/logout', methods=['GET'])
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

        c = course_from_form(add_course_form)
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


@application.route('/dashboard/instructor/course/<CRN>', methods=['GET'])
def course_dashboard(CRN):
    try:
        fetched_course = db.session.execute(
            'SELECT * FROM course '
            'WHERE CRN="%s"' % CRN).fetchone()
        if fetched_course is None:
            db.session.close()
            return redirect("instructor_dashboard")
        else:
            course = Course(CRN=fetched_course.CRN, title=fetched_course.title, year=fetched_course.year,
                            term=fetched_course.term, instructor=fetched_course.instructor)
            db.session.close()
            return render_template("instructor_course_dashboard.html", current_user=flask_login.current_user,
                                   course=course)
    except Exception as e:
        db.session.rollback()
        # TODO: render form with error msg
        return str(e)


@application.route('/course/delete/<CRN>', methods=['POST'])
def delete_course(CRN):
    # TODO: authenticate user permission
    try:
        db.session.execute(
            'DELETE FROM course '
            'WHERE CRN="%s"' % CRN)
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        # TODO: render form with error msg
        return str(e)
    return redirect(url_for('instructor_dashboard'))

@application.route('/set-active-question', methods=['POST'])
def set_active_question():
    print(request.form)
    try:
        db.session.execute(
            'UPDATE course '
            'SET active_question = %s '
            'WHERE CRN = %s' % (request.form['qid'], request.form['crn'])
        )
        db.session.commit()
        db.session.close()
        return "set active question successful"
    except Exception as e:
        db.session.rollback()
        # TODO: render form with error msg
        return "data: " + str(request.form['qid']) + " " + str(e)




@application.route('/dashboard/instructor/course/question/<CRN>', methods=['GET', 'POST'])
def check_question(CRN):
    if flask_login.current_user is None or flask_login.current_user.is_anonymous:
        return redirect(url_for('login'))

    if flask_login.current_user.user_type == STUDENT:
        return redirect(url_for('student_dashboard'))

    add_question_form = AddQuestionForm(request.form)
    if request.method == 'GET':
        try:
            # questions = db.session.execute('SELECT * FROM Question WHERE Question.CRN=:crn',{'crn':CRN}).fetchall()
            query_results = []
            questions = db.session.execute('SELECT * FROM Question WHERE CRN="%s"' % (CRN)).fetchall()
            active_question = db.session.execute(
                'SELECT active_question FROM course '
                'WHERE CRN="%s"' % CRN).fetchone()[0]
            if questions is not None:
                for q in questions:
                    query_results.append([q.id, q.date, q.question])
            db.session.close()
            return render_template("add_question.html", current_user=flask_login.current_user,
                                   query_results=query_results, CRN=CRN, add_question_form=add_question_form,
                                   active_question=active_question)
        except Exception as e:
            db.session.rollback()
            return str(e)
    elif request.method == 'POST':
        if not add_question_form.validate():
            return str(add_question_form.errors)
        question = add_question_form.question.data
        date = add_question_form.question_date.data
        try:
            datetime.datetime.strptime(date, '%m/%d/%Y')
        except ValueError:
            return ('<h1>Incorrect data format, should be MM/DD/YYYY</h1>')

        if len(question) < 1:
            return ('<h1>Failed. The question content is empty.</h1>')
        date_object = datetime.datetime.strptime(date, '%m/%d/%Y')
        try:
            db.session.execute('INSERT INTO Question (crn,date,question) VALUES (:crn,:qdate,:question)',
                               {'crn': CRN, 'qdate': date_object, 'question': question})
            db.session.commit()
            db.session.close()
        except Exception as e:
            db.session.rollback()
            # TODO: render form with error msg
            return str(e)
        return redirect(url_for('check_question', CRN=CRN))
    # return render_template("add_question.html", current_user=flask_login.current_user, CRN=CRN,
    #                        add_question_form=add_question_form)


@application.route('/dashboard/student/<CRN>', methods=['POST'])
def register_course(CRN):
    try:
        db.session.execute(
            'INSERT INTO Take '
            '(CRN, Student) '
            'VALUES ("%s", "%s")' %
            (CRN, flask_login.current_user.email))
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return redirect(url_for('student_dashboard'))


@application.route('/dashboard/student/delete/<CRN>', methods=['POST'])
def student_drop_course(CRN):
    if flask_login.current_user is None or flask_login.current_user.is_anonymous:
        return redirect(url_for('login'))
    if flask_login.current_user.user_type == INSTRUCTOR:
        return redirect(url_for('instructor_dashboard'))
    try:
        db.session.execute(
            'DELETE FROM Take '
            'WHERE CRN="%s" AND student="%s"' %
            (CRN, flask_login.current_user.email))
        db.session.commit()
        db.session.close()
    except Exception as e:
        db.session.rollback()
        return str(e)
    return redirect(url_for('student_dashboard'))


@application.route('/dashboard/student/courses', methods=['GET'])
def find_registered_courses():
    if request.method == 'GET':
        try:
            # fetched_course = db.session.execute(
            #     'SELECT c.CRN, c.title, c.year, c.term, i.name FROM course AS c, Take AS t, user as i '
            #     'WHERE t.student="bow2@illinois.edu" AND c.CRN=t.CRN AND c.instructor=i.email').fetchall()
            fetched_courses = db.session.execute(
                'SELECT c.CRN, c.title, c.year, c.term, i.name FROM course AS c, Take AS t, user as i '
                'WHERE t.student="%s" AND c.CRN=t.CRN AND c.instructor=i.email' % flask_login.current_user.email).fetchall()
            if fetched_courses is None:
                db.session.close()
                return redirect("student_dashboard")
            else:
                courses = []
                for fetched_course in fetched_courses:
                    curr_course = Course(CRN=fetched_course.CRN, title=fetched_course.title, year=fetched_course.year,
                                         term=fetched_course.term, instructor=fetched_course.name)
                    courses.append(curr_course)
                db.session.close()
            return render_template("student_registered_courses.html", current_user=flask_login.current_user,
                                   courses=courses)
        except Exception as e:
            db.session.rollback()
            return str(e)
    return render_template('student_dashboard.html', current_user=flask_login.current_user)


@application.route('/dashboard/student', methods=['GET', 'POST'])
def student_dashboard():
    if flask_login.current_user is None or flask_login.current_user.is_anonymous:
        return redirect(url_for('login'))
    if flask_login.current_user.user_type == INSTRUCTOR:
        return redirect(url_for('instructor_dashboard'))

    form2 = StudentSearchForm(request.form)
    if request.method == 'POST' and form2.validate():
        try:
            CRN = int(form2.CRN.data)
            fetched_course = db.session.execute(
                'SELECT * FROM course '
                'WHERE CRN="%s"' % CRN).fetchone()
            if fetched_course is None:
                db.session.close()
                # output error message
                return "<h1>The CRN you entered does not exist. Please go back to previous page and re-enter the CRN.</h1>"
            else:
                course = Course(CRN=fetched_course.CRN, title=fetched_course.title, year=fetched_course.year,
                                term=fetched_course.term, instructor=fetched_course.instructor)
                db.session.close()
                registered_flag = False
                # registered_flag: True if a student has already registered certain course
                try:
                    possible_redundancy = db.session.execute(
                        'SELECT * '
                        'FROM Take '
                        'WHERE student="%s" AND CRN = "%s"' %
                        (flask_login.current_user.email, CRN)).fetchone()
                    db.session.close()
                    if possible_redundancy is not None:
                        registered_flag = True
                except Exception as e:
                    db.session.rollback()
                    return str(e)
                return render_template("student_search_dashboard.html", current_user=flask_login.current_user,
                                       course=course, registered_flag=registered_flag)
        except Exception as e:
            db.session.rollback()
            return str(e)
    return render_template('student_dashboard.html', current_user=flask_login.current_user, form2=form2)


@application.route('/dashboard/student/course/<CRN>', methods=['GET', 'POST'])
def student_question_page(CRN):
    # TODO: verify that this student is registered for this class

    if request.method == 'GET':
        try:
            active_question = db.session.execute(
                'SELECT q.question FROM question q WHERE id in '
                '(SELECT active_question FROM course '
                'WHERE CRN="%s")' % CRN).fetchone()[0]
            db.session.close()
            return render_template("student_question_page.html", question=active_question)
        except Exception as e:
            return str(e)
    elif request.method == 'POST':
        # TODO: implement student submitting question response
        return "POST method not yet implemented"


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


def course_from_form(course_form):
    return Course(CRN=course_form.CRN.data, title=course_form.title.data, year=course_form.year.data,
                  term=course_form.term.data,
                  instructor=flask_login.current_user.email)


@application.route("/query-parser-test", methods=['GET', 'POST'])
def query_parser_test():
    if request.method == 'GET':
        return """
        <form action="/query-parser-test" method="post">
            Table 1 Name: <br>
            <input type="text" name="table1name" value="foo"> <br>
            Table 1 Columns: <br>
            <input type="text" name="table1columns" value="a,b,c"> <br>

            Table 2 Name: <br>
            <input type="text" name="table2name" value="bar"> <br>
            Table 2 Columns: <br>
            <input type="text" name="table2columns" value="d,e,f"> <br>

            Enter SQL query: (one query on each line)<br>
            <textarea type="text" name="query" rows="10" cols="300">SELECT AVG(a) FROM foo JOIN bar ON bar.d = foo.a GROUP BY bar.f </textarea> <br>
            <br><br>
            <input type="submit" value="Submit">
        </form>
        """
    else:
        try:
            table1 = request.form['table1name'] + "," + request.form['table1columns']
            table2 = request.form['table2name'] + "," + request.form['table2columns']
            sql_queries = request.form['query'].split('\n')
            analysis = query_parser.concise_report(
                *query_parser.parse_multiple_query(sql_queries, [table1, table2])
            )
            return render_template("query_analysis.html", analysis=analysis)
        except Exception as e:
            return str(e)


def test():
    return render_template('test.html')


if __name__ == '__main__':
    application.run(host='0.0.0.0')
