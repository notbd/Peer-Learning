from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from application import db
from flask_socketio import SocketIO, emit, join_room, leave_room
from application.models import *
from application.forms import *
import flask_login
import query_parser
import os
import json
import datetime
import json

# Elastic Beanstalk initalization
application = Flask(__name__)
db.init_app(application)

application.debug = True
# change this to your own value
application.secret_key = 'cC1YCIWOj9GgWspgNEo2'
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

login_manager = flask_login.LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'login'

INSTRUCTOR = 'instructor'
STUDENT = 'student'


@application.route('/')
@application.route('/index')
def index():
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


# page where instructor can view the list of courses and add new course
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


# page where instructor can view the list of sessions in a course and add new questions
@application.route('/dashboard/instructor/course/<CRN>', methods=['GET'])
def instructor_course_dashboard(CRN):
    try:
        course_CRN, course_title = db.session.execute(
            'SELECT CRN, title FROM course '
            'WHERE CRN="%s"' % CRN).fetchone()
        session_info = db.session.execute(
            'SELECT date, COUNT(*) FROM question WHERE CRN="%s" GROUP BY date ORDER BY date DESC' % CRN
        ).fetchall()
        db.session.close()
        return render_template("instructor_course_dashboard.html", current_user=flask_login.current_user,
                               course_title=course_title, course_CRN=course_CRN, session_info=session_info)
    except Exception as e:
        db.session.rollback()
        # TODO: render form with error msg
        return str(e)


# backend-only function for an instructor to delete a course
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


# backend-only function for an instructor to set a question as the "active" question of a course
@application.route('/set-active-question', methods=['POST'])
def set_active_question():
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


# page where instructor can manage a specific question (and view its responses)
@application.route('/dashboard/instructor/question/', methods=['POST'])
@application.route('/dashboard/instructor/question/<qid>', methods=['GET'])
def instructor_question(qid=None):
    if request.method == 'GET':
        try:
            q = db.session.execute(
                'SELECT question, schemas, crn FROM Question WHERE id=%s' % (qid)).fetchone()
            question, schemas, crn = q
            active_question = db.session.execute(
                'SELECT active_question FROM course '
                'WHERE CRN="%s"' % crn).fetchone()[0]
            responses = db.session.execute(
                'SELECT student, response FROM response WHERE question_id =' + qid
            ).fetchall()
            db.session.close()
            q = Question(qid, question, schemas, crn)
            is_active = str(qid) == str(active_question)
            return render_template("instructor_question_dashboard.html", q=q, is_active=is_active, responses=responses)
        except Exception as e:
            return str(e)
    else:
        add_question_form = AddQuestionForm(request.form)
        if not add_question_form.validate():
            return str(add_question_form.errors)
        crn = add_question_form.CRN.data
        schemas = add_question_form.schemas.data
        question = add_question_form.question.data
        date = add_question_form.question_date.data
        try:
            db.session.execute('INSERT INTO Question (crn,date,schemas,question) '
                               'VALUES (:crn,:qdate,:schemas, :question)',
                               {'crn': crn, 'qdate': date, 'schemas': schemas, 'question': question})
            db.session.commit()
            db.session.close()
        except Exception as e:
            db.session.rollback()
            # TODO: render form with error msg
            return str(e)
        return redirect(url_for('instructor_session', CRN=crn, date=date))


@application.route('/dashboard/instructor/edit-question/<qid>', methods=['POST'])
def instructor_edit_question(qid):
    db.session.execute('UPDATE Question '
                       'SET schemas = :schemas, question = :question '
                       'WHERE id = :qid',
                       {'qid': qid, 'schemas': request.form["schemas"], 'question': request.form["question"]})
    db.session.commit()
    db.session.close()
    return "updated question"


# page where instructor can manage the questions for a single session
@application.route('/dashboard/instructor/session/<CRN>/<date>', methods=['GET', 'POST'])
def instructor_session(CRN, date):
    if flask_login.current_user is None or flask_login.current_user.is_anonymous:
        return redirect(url_for('login'))

    if flask_login.current_user.user_type == STUDENT:
        return redirect(url_for('student_dashboard'))

    add_question_form = AddQuestionForm(request.form)
    if request.method == 'GET':
        try:
            fetched_questions = db.session.execute('SELECT id, question, schemas FROM Question WHERE CRN="%s" '
                                                   'AND date = "%s"' % (CRN, date)).fetchall()
            print(fetched_questions)
            questions = []
            for id, question, schemas in fetched_questions:
                questions.append(Question(id, question, schemas))
            db.session.close()
            return render_template("instructor_session_dashboard.html", questions=questions,
                                   add_question_form=add_question_form, date=date, CRN=CRN)
        except Exception as e:
            return str(e)
    else:
        return "Not yet implemented"


# backend-only function for student to search for existing courses
@application.route('/search-course', methods=['GET'])
def search_course():
    search_query = request.args.get('q')
    if search_query == "":
        return ""

    search_query_list = search_query.split(" ")

    try:
        # find all courses that match the query
        all_results = set()
        for q in search_query_list:
            sql_query = 'SELECT crn, title, year, term, user.name ' \
                        'FROM course JOIN user ON course.instructor = user.email ' \
                        'WHERE (CRN LIKE "%{0}%" OR title LIKE "%{0}%" OR user.name LIKE "%{0}%" ' \
                        'OR year LIKE "%{0}%")'.format(q)
            # filter out courses already registered
            if flask_login.current_user is not None and not flask_login.current_user.is_anonymous:
                sql_query += ' AND crn NOT IN (SELECT crn FROM take WHERE student = "{}")'.format(
                    flask_login.current_user.email)

            results = db.session.execute(sql_query).fetchall()
            results = [tuple([val for val in r]) for r in results]
            if len(all_results) == 0:
                all_results.update(results)
            else:
                all_results.intersection_update(results)

        db.session.close()
        courses = []
        for r in all_results:
            crn, title, year, term, instructor = r
            courses.append({
                "CRN": crn,
                "title": title,
                "year": year,
                "term": term,
                "instructor": instructor
            })
        return json.dumps(courses)
    except Exception as e:
        return str(e)  # page for student to search and register a new course


@application.route('/dashboard/student/add-course', methods=['GET', 'POST'])
def search_and_register_course():
    if request.method == 'GET':
        return render_template("student_search_dashboard.html")
    elif request.method == 'POST':
        CRN = request.form['CRN']
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


# TODO: move frontend of dropping course to registered course page
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
def student_dashboard():
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


# @application.route('/dashboard/student', methods=['GET', 'POST'])
# def student_dashboard():
#     if flask_login.current_user is None or flask_login.current_user.is_anonymous:
#         return redirect(url_for('login'))
#     if flask_login.current_user.user_type == INSTRUCTOR:
#         return redirect(url_for('instructor_dashboard'))
#
#     form2 = StudentSearchForm(request.form)
#     if request.method == 'POST' and form2.validate():
#         try:
#             CRN = int(form2.CRN.data)
#             fetched_course = db.session.execute(
#                 'SELECT * FROM course '
#                 'WHERE CRN="%s"' % CRN).fetchone()
#             if fetched_course is None:
#                 db.session.close()
#                 # output error message
#                 return "<h1>The CRN you entered does not exist. Please go back to previous page and re-enter the CRN.</h1>"
#             else:
#                 course = Course(CRN=fetched_course.CRN, title=fetched_course.title, year=fetched_course.year,
#                                 term=fetched_course.term, instructor=fetched_course.instructor)
#                 db.session.close()
#                 registered_flag = False
#                 # registered_flag: True if a student has already registered certain course
#                 try:
#                     possible_redundancy = db.session.execute(
#                         'SELECT * '
#                         'FROM Take '
#                         'WHERE student="%s" AND CRN = "%s"' %
#                         (flask_login.current_user.email, CRN)).fetchone()
#                     db.session.close()
#                     if possible_redundancy is not None:
#                         registered_flag = True
#                 except Exception as e:
#                     db.session.rollback()
#                     return str(e)
#                 return render_template("student_search_dashboard.html", current_user=flask_login.current_user,
#                                        course=course, registered_flag=registered_flag)
#         except Exception as e:
#             db.session.rollback()
#             return str(e)
#     return render_template('student_dashboard.html', current_user=flask_login.current_user, form2=form2)


@application.route('/dashboard/student/course/<CRN>', methods=['GET', 'POST'])
def student_question_page(CRN):
    # TODO: verify that this student is registered for this class

    if request.method == 'GET':
        try:
            active_question = db.session.execute(
                'SELECT q.id, q.question, q.schemas FROM question q WHERE id in '
                '(SELECT active_question FROM course '
                'WHERE CRN="%s")' % CRN).fetchone()
            db.session.close()
            return render_template("student_question_page.html", question=active_question)
        except Exception as e:
            return str(e)
    elif request.method == 'POST':
        # TODO: implement student submitting question response
        response = request.form.get("response").strip()
        if len(response) < 0:
            return redirect(url_for(student_question_page))

        qid = request.form.get('qid')

        user_id = flask_login.current_user.email

        try:
            question = db.session.execute(
                'SELECT q.id, q.question, q.schemas FROM question q WHERE id = %s ' % qid).fetchone()
            db.session.execute(
                'INSERT INTO response (question_id, student, response) VALUES ("%s", "%s", "%s")' % (
                    qid, user_id, response)
            )
            db.session.commit()
            db.session.close()
            return render_template("student_question_page.html", question=question, response=response,
                                   msg="Response submitted!")
        except Exception as e:
            return str(e)


@application.route('/dashboard/student/profile', methods=['GET', 'POST'])
@application.route('/dashboard/instructor/profile', methods=['GET', 'POST'])
def profile():
    update_profile_form = UserProfileForm(request.form)

    if request.method == 'POST':
        if not update_profile_form.validate():
            return str(update_profile_form.errors)
        try:
            db.session.execute('UPDATE user SET name = "%s",email = "%s" WHERE email = "%s"' %
                               (update_profile_form.name.data, update_profile_form.email.data,
                                flask_login.current_user.email))
            db.session.commit()
            db.session.close()
        except Exception as e:
            db.session.rollback()
            return str(e)

        try:
            queried_user = db.session.execute(
                'SELECT * FROM user WHERE email = "%s"' % update_profile_form.email.data).fetchone()
            flask_login.login_user(
                user_from_query_result(queried_user))
            redirect_endpoint = "instructor_dashboard" if queried_user.user_type == INSTRUCTOR else "student_dashboard"
            db.session.close()
            return redirect(url_for(redirect_endpoint))
        except Exception as e:
            return str(e)
    return render_template('profile.html', user=flask_login.current_user, update_profile_form=update_profile_form)


@login_manager.user_loader
def user_loader(email):
    return User.query.get(email)


def course_from_form(course_form):
    return Course(CRN=course_form.CRN.data, title=course_form.title.data, year=course_form.year.data,
                  term=course_form.term.data,
                  instructor=flask_login.current_user.email)


@application.route("/analyze-responses/<qid>", methods=['GET'])
def analyze_responses(qid):
    try:
        question, schemas = db.session.execute('SELECT question, schemas FROM question WHERE id=' + qid).fetchone()
        responses = db.session.execute('SELECT response FROM response WHERE question_id=' + qid).fetchall()
        db.session.close()
        analysis = query_parser.concise_report(
            *query_parser.parse_multiple_query(responses, schemas)
        )
        return render_template("query_analysis.html", analysis=analysis)
    except Exception as e:
        return str(e)


# debug use only, to test query parser
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
            table1 = request.form['table1name'] + "(" + request.form['table1columns'] + ")"
            table2 = request.form['table2name'] + "(" + request.form['table2columns'] + ")"
            sql_queries = request.form['query'].split('\n')
            analysis = query_parser.concise_report(
                *query_parser.parse_multiple_query(sql_queries, table1 + "|" + table2)
            )
            return render_template("query_analysis.html", analysis=analysis)
        except Exception as e:
            return str(e)


# development use only
@application.route("/any-query", methods=['GET', 'POST'])
def any_query():
    if request.method == 'GET':
        return """
        <form action="/any-query" method="post">
            <textarea type="text" name="query" rows="10" cols="300"></textarea>
            <br><br>
            <input type="submit" value="Submit">
        </form>
        """
    else:
        try:
            results = db.session.execute(request.form['query']).fetchall()
            db.session.commit()
            db.session.close()
            return "success: " + str(results)
        except Exception as e:
            return str(e)


socketio = SocketIO(application)
channel_list = {"general": []}
present_channel = {"initial": "general"}


@application.route('/chatroom', methods=["POST", "GET"])
def index1():
    if request.method == "GET":
        # Pass channel list to, and use jinja to display already created channels
        return render_template("index1.html", channel_list=channel_list, user=flask_login.current_user.name)

    elif request.method == "POST":
        print "[INFO] POST request on /chatroom", request.form
        channel = request.form.get("channel_name")
        user = flask_login.current_user.email

        # Adding a new channel
        if channel and (channel not in channel_list):
            channel_list[channel] = []
            print "[INFO] channel {} created: {}".format(channel, channel_list)
            return jsonify({"success": True})
        # Switching to a different channel
        elif channel in channel_list:
            # send channel specific data to client i.e. messages, who sent them, and when they were sent
            # send via JSON response and then render with JS
            print("Switch to {channel}")
            present_channel[user] = channel
            channel_data = channel_list[present_channel[user]]
            print("channel data:", channel_data)
            return json.dumps(channel_data)
        else:
            print "[INFO] channel {} already existed: {}".format(channel, channel_list)
            return jsonify({"success": False})


@socketio.on("create channel")
def create_channel(new_channel):
    emit("new channel", new_channel, broadcast=True)

@socketio.on("send message")
def send_message(message_data):
    message_data["user"] = "{} ({})".format(flask_login.current_user.name, flask_login.current_user.email)
    # print "[message_data]", message_data    #  e.g. {u'message_content': u'hello', u'timestamp': u'4/18/2019, 7:39:26 AM', u'current_channel': u'general', u'user': 'Abdu (abdu@illinois.edu)'}
    channel = message_data["current_channel"]
    channel_message_count = len(channel_list[channel])
    del message_data["current_channel"]
    channel_list[channel].append(message_data)
    message_data["deleted_message"] = False
    if (channel_message_count >= 100):
        del channel_list[channel][0]
        message_data["deleted_message"] = True
    emit("recieve message", message_data, broadcast=True, room=channel)


@socketio.on("delete channel")
def delete_channel(message_data):
    channel = message_data["current_channel"]
    user = message_data["user"]
    present_channel[user] = "general"
    del message_data["current_channel"]
    del channel_list[channel]
    channel_list["general"].append(message_data)
    message_data = {"data": channel_list["general"], "deleted_channel": channel}
    emit("announce channel deletion", message_data, broadcast=True)


@socketio.on("leave")
def on_leave(room_to_leave):
    print("leaving room")
    leave_room(room_to_leave)
    emit("leave channel ack", room=room_to_leave)


@socketio.on("join")
def on_join(room_to_join):
    print("joining room")
    join_room(room_to_join)
    emit("join channel ack", room=room_to_join)


if __name__ == '__main__':
    socketio.run(application, debug=True)
