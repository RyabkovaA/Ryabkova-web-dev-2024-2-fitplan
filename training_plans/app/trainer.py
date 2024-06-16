from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import current_user, login_required
from mysql.connector.errors import DatabaseError
from app import db_connector
from users import get_form_data
from authorization import can_user


bp = Blueprint('trainer', __name__, url_prefix='/trainer')
EDIT_TRAINER_FIELDS = ['about_trainer', 'age', 'experience_years', 'speciality']

def get_clients(trainer_id):
    print(trainer_id)
    query = ("SELECT clients.client_id, personal_data.user_id, CONCAT(personal_data.last_name, ' ', "
                "personal_data.first_name, ' ', "
                "COALESCE(personal_data.middle_name, '')) AS full_name "
                "FROM clients, personal_data WHERE "
                "clients.user_id=personal_data.user_id AND clients.trainer_id=%s")
    with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (trainer_id, ))
            clients = cursor.fetchall()
    return clients

@bp.route('/<int:user_id>/show', methods=["GET","POST"])
@login_required
def show(user_id):
    user = {}
    personal_data = {}
    trainer_info = {}
    clients = {}
    query = 'SELECT users.*, roles.role_name as role_name FROM users LEFT JOIN roles ON users.role_id = roles.role_id WHERE users.id=%s'
    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            cursor.execute(query, (user_id, ))
            user = cursor.fetchone()
            print(user)

            query2 = ("SELECT CONCAT(personal_data.last_name, ' ', "
                    "personal_data.first_name, ' ', "
                    "COALESCE(personal_data.middle_name, '')) AS full_name, "
                    "personal_data.email, personal_data.phone "
                    "FROM personal_data WHERE personal_data.user_id=%s")

            cursor.execute(query2, (user_id, ))
            personal_data = cursor.fetchone()

            query3 = ("SELECT * FROM trainers WHERE trainers.user_id=%s")
            cursor.execute(query3, (user_id, ))
            trainer_info = cursor.fetchone()
            clients = get_clients(trainer_info.trainer_id)
        
    except DatabaseError as error:
        flash(f'Ошибка просмотра пользователя! {error}', category="danger")
        db_connector.connect().rollback()    
    
    return render_template("trainer_profile.html", user=user, personal_data=personal_data, trainer_info=trainer_info, clients=clients)


@bp.route('/<int:user_id>/edit', methods=["GET","POST"]) 
@login_required
@can_user('edit')
def edit(user_id):
    query = "SELECT * FROM trainers WHERE user_id=%s"
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id, ))
        user = cursor.fetchone() 
    print(user)
    if request.method == "POST":
        user = get_form_data(EDIT_TRAINER_FIELDS)

        columns = ','.join([f'{key}=%({key})s' for key in user])
        user['user_id'] = user_id

        query = (f"UPDATE trainers SET {columns} WHERE user_id=%(user_id)s ")

        try:
            with db_connector.connect().cursor(named_tuple=True) as cursor:
                cursor.execute(query, user)
                db_connector.connect().commit()
            
            flash("Запись пользователя успешно обновлена", category="success")
            return redirect(url_for('trainer.show', user_id=user_id))
        except DatabaseError as error:
            flash(f'Ошибка редактирования пользователя! {error}', category="danger")
            db_connector.connect().rollback()    

    return render_template("edit_trainer.html", user=user)

@bp.route('/<int:user_id>/clients', methods=["GET","POST"])
@login_required
@can_user('see_clients')
def show_clients(user_id):
    clients = {}
    query = "SELECT * FROM trainers WHERE user_id=%s"

    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query, (user_id, ))
        user = cursor.fetchone() 
    
    clients = get_clients(user.trainer_id)
    return render_template("trainer_clients.html", clients=clients, user=user)
    


