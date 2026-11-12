from datetime import date

from flask_wtf import FlaskForm
from wtforms import (BooleanField, DateField, PasswordField, SelectField,
                     StringField, SubmitField, TextAreaField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length, Optional,
                                ValidationError)

from .extensions import db
from .models import (PRIORITY_LABELS, PRIORITY_VALUES, ROLE_LABELS, ROLE_VALUES,
                     STATUS_LABELS, STATUS_VALUES, User)


class LoginForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(3, 50)])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(3, 50)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(6, 128)])
    confirm = PasswordField(
        "Повторите пароль",
        validators=[DataRequired(), EqualTo("password", "Пароли не совпадают")],
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_username(self, field):
        if db.session.scalar(db.select(User).where(User.username == field.data.strip())):
            raise ValidationError("Такой логин уже занят.")

    def validate_email(self, field):
        if db.session.scalar(db.select(User).where(User.email == field.data.strip().lower())):
            raise ValidationError("Такой e-mail уже зарегистрирован.")


class TaskForm(FlaskForm):
    title = StringField("Название",
                        validators=[DataRequired("Название обязательно"), Length(max=200)])
    description = TextAreaField("Описание", validators=[Optional(), Length(max=5000)])
    status = SelectField("Статус", choices=[(v, STATUS_LABELS[v]) for v in STATUS_VALUES])
    priority = SelectField("Приоритет", choices=[(v, PRIORITY_LABELS[v]) for v in PRIORITY_VALUES])
    assignee_id = SelectField("Исполнитель", coerce=int, choices=[])
    due_date = DateField("Срок", format="%Y-%m-%d", validators=[Optional()],
                         render_kw={"type": "date"})
    submit = SubmitField("Сохранить")

    def __init__(self, *args, original_due_date=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_due_date = original_due_date

    def validate_due_date(self, field):
        if field.data and field.data < date.today() and field.data != self.original_due_date:
            raise ValidationError("Срок не может быть в прошлом.")


class StatusForm(FlaskForm):
    status = SelectField("Статус", choices=[(v, STATUS_LABELS[v]) for v in STATUS_VALUES])
    submit = SubmitField("Обновить статус")


class UserForm(FlaskForm):
    username = StringField("Логин", validators=[DataRequired(), Length(3, 50)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField("Роль", choices=[(v, ROLE_LABELS[v]) for v in ROLE_VALUES])
    manager_id = SelectField("Руководитель", coerce=int, choices=[])
    is_active = BooleanField("Активен", default=True)
    password = PasswordField("Пароль", validators=[Optional(), Length(6, 128)],
                             description="При редактировании оставьте пустым, чтобы не менять.")
    submit = SubmitField("Сохранить")