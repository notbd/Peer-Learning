from flask.ext.wtf import Form
from wtforms import StringField, RadioField, PasswordField, validators
from wtforms.fields.html5 import EmailField


INSTRUCTOR = 'instructor'
STUDENT = 'student'

class EnterDBInfo(Form):
    dbNotes = StringField(label='Items to add to DB', description="db_enter", validators=[validators.required(),
                                                                                          validators.Length(min=0,
                                                                                                            max=128,
                                                                                                            message=u'Enter 128 characters or less')])


class RetrieveDBInfo(Form):
    numRetrieve = StringField(label='Number of DB Items to Get', description="db_get",
                              validators=[validators.required(),
                                          validators.Regexp(
                                              '^\d{1}$',
                                              message=u'Enter a number between 1 and 10')])


class SignUpForm(Form):
    user_type = RadioField(label="User Type", choices=[(STUDENT, STUDENT), (INSTRUCTOR, INSTRUCTOR)])
    name = StringField(label='Name', description="name", validators=[validators.Length(min=1, max=80,
                                                                                                  message=u'Name needs to be 1-80 character(s) long')])
    email = EmailField(label='Email address', validators=[validators.DataRequired(), validators.Email()])
    password = PasswordField(label='Password')

class LogInForm(Form):
    email = EmailField(label='Email address', validators=[validators.DataRequired(), validators.Email()])
    password = PasswordField(label='Password')
