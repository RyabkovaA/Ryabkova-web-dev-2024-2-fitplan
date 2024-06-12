from flask import Blueprint, render_template, request, url_for, redirect, flash, current_app
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user
from app import db_connector
from functools import wraps
from users_policy import UsersPolicy


bp = Blueprint('auth', __name__, url_prefix='/auth')

class User(UserMixin):
    def __init__(self, user_id, login, role_id):
        self.id = user_id
        self.login = login
        self.role_id = role_id

    def is_trainer(self):
       return self.role_id == current_app.config['TRAINER_ROLE_ID']
    
    def can(self, action, user=None):
        self.users_policy = UsersPolicy(user)
        method = getattr(self.users_policy, action, lambda: False)
        return method()
    
def can_user(action):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = None
            user_id = kwargs.get('user_id')
            if user_id:
                with db_connector.connect().cursor(named_tuple=True) as cursor:
                    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
                    user = cursor.fetchone()

            if not current_user.can(action, user):
                flash("У вас недостаточно прав для просмотра этой страницы", category='warning')
                return redirect(url_for("index"))
            return func(*args, **kwargs)
        return wrapper
    return decorator


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Войдите для просмотра содержимого этой страницы"
    login_manager.login_message_category = 'warning'
    login_manager.user_loader(load_user)

def load_user(user_id):
    query = "SELECT id, login, role_id FROM users WHERE id=%s"

    with db_connector.connect().cursor(named_tuple=True) as cursor:

        cursor.execute(query, (user_id,))

        user = cursor.fetchone()

    if user:
        return User(user_id, user.login, user.role_id)

    return None


@bp.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('auth.html')
    
    login = request.form.get("login", "")
    password = request.form.get("pass", "")
    remember = request.form.get("remember") == "on"

    query = 'SELECT id, login, role_id FROM users WHERE login=%s AND password_hash=SHA2(%s, 256)'
    
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        
        cursor.execute(query, (login, password))

        user = cursor.fetchone()

    if user is not None:
        login_user(User(user.id, user.login, user.role_id), remember=remember)
        flash("Авторизация прошла успешно", category='success')
        target_page = request.args.get("next", url_for('index'))
        return redirect(target_page)
                  
    flash("Введены некорректные учётные данные пользователя", category='danger')
    return render_template("auth.html")

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

def logout():
    logout_user()
    return redirect(url_for('index'))