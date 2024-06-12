from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import login_required
from mysql.connector.errors import DatabaseError
from app import db_connector
from authorization import can_user
from users import get_form_data

bp = Blueprint('client', __name__, url_prefix='/client')

EDIT_CLIENT_FIELDS = ['about_client', 'age', 'height', 'weight', 'trainer_id']


@bp.route('/<int:user_id>/show', methods=["GET","POST"])
@login_required
def show(user_id):
    user = {}
    personal_data = {}
    client_info = {}
    trainer = {}
    query = 'SELECT users.*, roles.role_name as role_name FROM users LEFT JOIN roles ON users.role_id = roles.role_id WHERE users.id=%s'
    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, ))
            user = cursor.fetchone()
            # print(user)

            query2 = ("SELECT CONCAT(personal_data.last_name, ' ', "
                    "personal_data.first_name, ' ', "
                    "COALESCE(personal_data.middle_name, '')) AS full_name, "
                    "personal_data.email, personal_data.phone "
                    "FROM personal_data WHERE personal_data.user_id=%s")

            cursor.execute(query2, (user_id, ))
            personal_data = cursor.fetchone()
            # print(personal_data)

            query3 = ("SELECT * FROM clients WHERE clients.user_id=%s")
            cursor.execute(query3, (user_id, ))
            client_info = cursor.fetchone()
            trainer_id = client_info.trainer_id
            trainer = get_trainer(trainer_id)
            # print(trainer)

        
    except DatabaseError as error:
        flash(f'Ошибка просмотра пользователя! {error}', category="danger")
        db_connector.connect().rollback()    
    
    return render_template("client_profile.html", user=user, personal_data=personal_data, client_info=client_info, trainer=trainer)


def get_trainer(trainer_id):
    query = ("SELECT trainers.user_id, trainers.trainer_id, CONCAT(personal_data.last_name, ' ', "
                "personal_data.first_name, ' ', "
                "COALESCE(personal_data.middle_name, '')) AS full_name "
                "FROM trainers, personal_data WHERE "
                "trainers.user_id=personal_data.user_id AND trainers.trainer_id=%s")
    with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (trainer_id, ))
            trainer = cursor.fetchone()
            # print("got trainer", trainer)
    return trainer
    
def get_trainers():        
    query = ("SELECT trainers.user_id, trainers.trainer_id, "
            "CONCAT(personal_data.last_name, ' ', personal_data.first_name, ' ', "
            "COALESCE(personal_data.middle_name, '')) AS full_name "
            "FROM trainers, personal_data WHERE trainers.user_id = personal_data.user_id")

    with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query)
            trainers = cursor.fetchall()
    return trainers


def is_valid_weight(weight):
    try:
        float(weight)
        return True
    except ValueError:
        return False

@bp.route('/<int:user_id>/edit', methods=["GET","POST"]) 
@login_required
@can_user('edit')
def edit(user_id):
    trainers=get_trainers()
    # print("Тренеры", trainers)
    query = "SELECT * FROM clients WHERE user_id=%s"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id, ))
        user = cursor.fetchone() 
    if request.method == "POST":
        user = get_form_data(EDIT_CLIENT_FIELDS)
        if not is_valid_weight(user["weight"]) or float(user["weight"]) <= 0:
            flash(f'Введите корректный вес!', category="danger")
            return render_template("edit_client.html", user=user, trainers=trainers)


        columns = ','.join([f'{key}=%({key})s' for key in user])
        user['user_id'] = user_id
        user['trainer_id'] = int(user['trainer_id']) if user['trainer_id'] else None
        # print("Данные для обновления", columns)
        # print("user:", user)

        query = (f"UPDATE clients SET {columns} WHERE clients.user_id=%(user_id)s ")

        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, user)
                # print("Запрос на обновление бд", cursor.statement)
                db_connector.connect().commit()
            
            flash("Запись пользователя успешно обновлена", category="success")
            return redirect(url_for('client.show', user_id=user_id))
        except DatabaseError as error:
            flash(f'Ошибка редактирования пользователя! {error}', category="danger")
            db_connector.connect().rollback()    

    return render_template("edit_client.html", user=user, trainers=trainers)

