from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import current_user, login_required, login_user
from mysql.connector.errors import DatabaseError
from authorization import User
from app import db_connector
import re
from config import TRAINER_ROLE_ID

bp = Blueprint('users', __name__, url_prefix='/users')

CREATE_USER_FIELDS = ['login', 'password', 'email', 'phone', 'last_name', 'first_name', 'middle_name', 'role_id']
CHECK_USER_FIELDS = ['login', 'password', 'email', 'phone', 'last_name', 'last_name', 'first_name', 'role_id']
EDIT_USER_FIELDS = ['last_name', 'first_name','email', 'phone']

def get_roles():
    query = "SELECT * FROM roles"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        roles = cursor.fetchall()
    return roles

def check_user_data(user):
    errors = {}
    
    for field in CHECK_USER_FIELDS:
        if not user.get(field):
            errors[field] = "Поле не может быть пустым"

    if 'login' not in errors:
        logins = get_logins()

        if user['login'] in logins:
            errors['login'] = "Пользователь с таким логином уже существует"
        elif len(user['login']) < 5:
            errors['login'] = "Логин должен содержать не менее 5 символов"
        elif not user['login'].isalnum():
            errors['login'] = "Логин должен состоять только из латинских букв и цифр"
    
    if 'password' not in errors:
        errors['password'] = check_password(user['password'])  

    if 'phone' not in errors:
        errors['phone'] = check_phone(user['phone'])  
    
    if 'email' not in errors:
        errors['email'] = check_email(user['email'])  

    return errors

def check_user_edit(user, same_phone, same_email):
    errors = {}
    
    for field in EDIT_USER_FIELDS:
        if not user.get(field):
            errors[field] = "Поле не может быть пустым"
    
    if 'phone' not in errors:
        errors['phone'] = check_phone(user['phone'], same_phone)  
    
    if 'email' not in errors:
        errors['email'] = check_email(user['email'], same_email)  
    
    return errors

def check_phone(phone, same_phone=None):
    phones = get_phones()
    if same_phone != 1:
        if phone in phones:
            return "Пользователь с таким номером уже существует"
    digs = sum(1 for i in phone if i.isdigit())
    if ((phone[0] == '+' and phone[1] == '7') or (phone[0] == '8')) == 0: 
        return "Неверный формат"
    
    if digs != 11 :
        return "Неверное количество символов"
    
    symbols ='( ).-'

    for i in range(1,len(phone)):
        if i == 1 and phone[i] == '7':
            continue
        if not phone[i].isdigit() and phone[i] not in symbols:
            return "Встречаются недопустимые символы"
    return None 


def check_email(email, same_email=None):
    emails = get_emails()
    if same_email != 1:
        if email in emails:
            return "Пользователь с таким адресом уже существует"
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if '@' not in email:
        return "Email должен содержать '@'"

    if not re.match(email_regex, email):
        return "Некорректный формат"

    return None


def format_phone(phone):
    start = 1
    result = ''
    if phone[0] == '+':
        start = 2
    phone = phone[start:]
    for i in range(len(phone)):
        if phone[i].isdigit():
            result += phone[i]
    result = '8-{}{}{}-{}{}{}-{}{}-{}{}'.format(*result)
    return result


def check_password(password):
    if len(password) < 8 or len(password) > 128:
        return "Пароль должен содержать от 8 до 128 символов"
    
    if not any(c.isupper() for c in password) or not any(c.islower() for c in password):
        return "Пароль должен содержать как минимум одну заглавную и одну строчную букву"
    
    if not any(c.isdigit() for c in password):
        return "Пароль должен содержать как минимум одну цифру"
    
    if any(c.isspace() for c in password):
        return "Пароль не должен содержать пробелы"
    
    valid_chars = set("~!?@#$%^&*_-+()[]{}></\\|\"'.,:;")
    for c in password:
        if not (c.isalpha() or c.isdigit() or c in valid_chars): 
            return "Пароль содержит недопустимые символы"

    return None


def get_form_data(required_fields):
    user = {}
    for field in required_fields:
        user[field] = request.form.get(field) or None

    return user

def get_logins():
    logins = []
    query = "SELECT login FROM users"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        logins = cursor.fetchall()
    return [login.login for login in logins]

def get_emails():
    emails = []
    query = "SELECT email FROM personal_data"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        emails = cursor.fetchall()
    return [email.email for email in emails]

def get_phones():
    phones = []
    query = "SELECT phone FROM personal_data"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        phones = cursor.fetchall()
    return [phone.phone for phone in phones]

@bp.route('/register', methods=["GET", "POST"])
def register():
    user = {}
    roles = get_roles()
    errors = {}
    user = get_form_data(CREATE_USER_FIELDS)

    if request.method == "POST":
        user = get_form_data(CREATE_USER_FIELDS)
        errors = check_user_data(user)
        if all(value is None for value in errors.values()):
            user['phone'] = format_phone(user['phone'])
            query = ("INSERT INTO users "
                    "(login, password_hash, role_id) "
                    "VALUES (%(login)s, SHA2(%(password)s, 256), %(role_id)s)")

            try:
                connection = db_connector.connect()
                with connection.cursor(named_tuple=True) as cursor:
                    cursor.execute(query, user)
                    user_id = cursor.lastrowid
                    user['id'] = user_id

                    print(user_id)

                    if insert_user_data(user, user_id, connection):
                        connection.commit()
                        flash('Пользователь успешно добавлен!', category="success")
                        login_user(User(user['id'], user['login'], user['role_id']))
                        target_page = request.args.get("next", url_for('index'))
                        return redirect(target_page)
                    else:
                        connection.rollback()
                        flash('Ошибка добавления данных пользователя!', category="danger")

            except DatabaseError as error:
                flash(f'Ошибка создания пользователя! {error}', category="danger")    
                connection.rollback()

    return render_template("register.html", user=user, roles=roles, errors=errors)

def insert_user_data(user, user_id, connection):
    try:
        with connection.cursor(named_tuple=True) as cursor:
            user['user_id'] = user_id
            query = ("INSERT INTO personal_data (user_id, email, last_name, first_name, middle_name, phone) "
                      "VALUES (%(user_id)s, %(email)s, %(last_name)s, %(first_name)s, %(middle_name)s, %(phone)s)")
            
            cursor.execute(query, user)
            print(user['role_id'])
            if user['role_id'] == str(TRAINER_ROLE_ID):
                query2 = ("INSERT INTO trainers (user_id) VALUES (%s)")
            else:
                query2 = ("INSERT INTO clients (user_id) VALUES (%s)")
            cursor.execute(query2, (user_id, ))
            return True          
        
    except DatabaseError as error:
        flash(f'Ошибка создания пользователя! {error}', category="danger")    
    return False

@bp.route('/<int:user_id>/edit', methods=["GET","POST"]) 
@login_required
def edit(user_id):
    same_email = 0
    same_phone = 0
    errors = {}
    query = "SELECT * FROM personal_data WHERE user_id=%s"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id, ))
        user = cursor.fetchone() 

    if request.method == "POST":
        user_before = user
        print(user_before)
        user = get_form_data(EDIT_USER_FIELDS)
        if user_before.phone == user['phone']:
            same_phone = 1
        if user_before.email == user['email']:
            same_email = 1

        print("deleted data", user)

        errors = check_user_edit(user, same_phone, same_email)

        if all(value is None for value in errors.values()):
            print(user)
            columns = ','.join([f'{key}=%({key})s' for key in user])
            user['user_id'] = user_id

            query = (f"UPDATE personal_data SET {columns} WHERE user_id=%(user_id)s ")

            try:
                with db_connector.connect().cursor(named_tuple=True) as cursor:
                    cursor.execute(query, user)
                    print(cursor.statement)
                    db_connector.connect().commit()
                
                flash("Запись пользователя успешно обновлена", category="success")
                if current_user.is_trainer():
                    return redirect(url_for('trainer.show', user_id=user_id))
                else:
                    return redirect(url_for('client.show', user_id=user_id))

            except DatabaseError as error:
                flash(f'Ошибка редактирования пользователя! {error}', category="danger")
                db_connector.connect().rollback()    

    return render_template("edit_user.html", user=user, errors=errors)

