from flask import Blueprint, render_template, request, url_for, redirect, session, flash, send_file
from flask_login import current_user, login_required
from mysql.connector.errors import DatabaseError
from authorization import can_user
from app import db_connector
from io import StringIO, BytesIO
import csv

bp = Blueprint('plans', __name__, url_prefix='/plan')
EXERCISE_FIELDS = ['reps']

def get_exercises():
    query = ("SELECT e1.exercise_id, "
             "e1.name AS exercise_name, e1.description, "
             "e1.change_id, e1.image_name, e2.name AS change_name "
             "FROM exercises e1 "
             "LEFT JOIN exercises e2 ON e1.change_id = e2.exercise_id;")
    with db_connector.connect().cursor(named_tuple=True) as cursor:
        cursor.execute(query)
        exercises = cursor.fetchall()
    return exercises

@bp.route('/<int:trainer_id>/<int:client_id>/add_exercise_page', methods=["GET"])
@login_required
@can_user('add_exercise')
def add_exercise_page(trainer_id, client_id):
    exercises = get_exercises()
    added_exercises = session.get('added_exercises', [])
    return render_template("exercises.html", exercises=exercises, added_exercises=added_exercises, trainer_id=trainer_id, client_id=client_id)

@bp.route('/<int:trainer_id>/<int:client_id>/<int:exercise_id>/add_exercise', methods=["GET","POST"])
@login_required
@can_user('add_exercise')
def add_exercise(trainer_id, client_id, exercise_id):
    reps = request.form.get('reps')
    if reps is None or not reps.isdigit() or int(reps) <= 0 :
        flash('Введите корректное количество повторений', category='danger')
        return redirect(url_for('plans.add_exercise_page', trainer_id=trainer_id, client_id=client_id))

    exercises = get_exercises()
    exercise = None 
    for ex in exercises:
         if ex.exercise_id == int(exercise_id):
              exercise = ex
              break
    
    if exercise:
        exercise_data = {
            'exercise_id': exercise.exercise_id,
            'exercise_name': exercise.exercise_name,
            'reps': reps,
            'description': exercise.description,
            'change_name': exercise.change_name,
            'image_name': exercise.image_name
        }

        added_exercises = session.get('added_exercises', [])
        added_exercises.append(exercise_data)
        session['added_exercises'] = added_exercises

    return redirect(url_for('plans.create_plan', trainer_id=trainer_id, client_id=client_id))

@bp.route('/<int:trainer_id>/<int:client_id>/remove_exercise/<int:exercise_id>', methods=["GET", "POST"])
@login_required
@can_user('add_exercise')
def remove_exercise(trainer_id, client_id, exercise_id):
    added_exercises = session.get('added_exercises', [])
    
    added_exercises = [exercise for exercise in added_exercises if exercise['exercise_id'] != exercise_id]
    
    session['added_exercises'] = added_exercises
    
    flash('Упражнение успешно удалено', 'success')
    return redirect(url_for('plans.create_plan', trainer_id=trainer_id, client_id=client_id))


@bp.route('/<int:trainer_id>/<int:client_id>/create_plan', methods=["GET", "POST"])
@login_required
@can_user('create_plan')
def create_plan(trainer_id, client_id):
    exercises = get_exercises()
    added_exercises = session.get('added_exercises', [])

    if request.method == 'POST':
        training_name = request.form.get('name')

        if not training_name:
            flash('Введите название тренировки!', category='danger')
            return redirect(url_for('plans.create_plan', trainer_id=trainer_id, client_id=client_id))
        
        if added_exercises == []:
            flash('Добавьте упражнения!', category='danger')
            return render_template("create_plan.html", exercises=exercises, added_exercises=added_exercises, trainer_id=trainer_id, client_id=client_id, training_name=training_name)
        
        query = ("INSERT INTO trainings (training_name, trainer_id, client_id) "
                 "VALUES (%s, %s, %s) ")
        
        try:
            connection = db_connector.connect()
            with connection.cursor(named_tuple=True) as cursor:
                cursor.execute(query, (training_name, trainer_id, client_id))
                training_id = cursor.lastrowid

                if insert_plan_info(added_exercises, training_id, connection):
                    connection.commit()
                    session.pop('added_exercises', None)
                    flash('План тренировки сохранен успешно!', category='success')
                    return redirect(url_for('trainer.show_clients', user_id=current_user.id))
                else:
                    connection.rollback()
                    flash('Ошибка добавления информации об упражнениях!', category="danger")

        except DatabaseError as error:
            flash(f'Ошибка сохранения плана! {error}', category="danger")    
            connection.rollback()
    
    return render_template("create_plan.html", exercises=exercises, added_exercises=added_exercises, trainer_id=trainer_id, client_id=client_id)

def insert_plan_info(added_exercises, training_id, connection):
    try:
        with connection.cursor(named_tuple=True) as cursor:
            query = ("INSERT INTO plans (training_id, exercise_id, reps) "
                    "VALUES (%s, %s, %s)")
            for exercise in added_exercises:
                cursor.execute(query, (training_id, exercise['exercise_id'], exercise['reps'] ))
            return True          
            
    except DatabaseError as error:
        flash(f'Ошибка добавления информации об упражнениях!{error}', category="danger")   
 
    return False


@bp.route('/<int:user_id>/show_plans', methods=["GET","POST"]) 
@login_required
def show_plans(user_id):
    plans = {}
    try:
        with db_connector.connect().cursor(named_tuple=True, buffered=True) as cursor:
            query = ("SELECT trainings.*, clients.user_id FROM trainings "
                    "LEFT JOIN clients ON clients.client_id = trainings.client_id WHERE clients.user_id=%s")
            cursor.execute(query, (user_id, ))
            plans = cursor.fetchall()
            print(plans)

    except DatabaseError as error:
        flash(f'Ошибка получения планов пользователя! {error}', category="danger")
    return render_template("show_plans.html", plans=plans)

@bp.route('/<int:training_id>/show_plan', methods=["GET","POST"]) 
@login_required
def show_training_plan(training_id):
    training = {}
    exercises = []
    print(training_id)
    try:
        with db_connector.connect().cursor(named_tuple=True) as cursor:
            query = ("SELECT plans.*, trainings.training_name FROM plans JOIN trainings "
                    "ON trainings.training_id=plans.training_id WHERE plans.training_id=%s")
            cursor.execute(query, (training_id, ))
            training = cursor.fetchall()
            exercises_id = [exercise.exercise_id for exercise in training]
            print(training)
            print(exercises_id)
            query2 = ("SELECT e1.exercise_id, "
             "e1.name AS exercise_name, e1.description, "
             "e1.change_id, e1.image_name, e2.name AS change_name "
             "FROM exercises e1 "
             "LEFT JOIN exercises e2 ON e1.change_id = e2.exercise_id WHERE e1.exercise_id=%s")
            counter = -1
            for exercise_id in exercises_id:
                counter += 1
                cursor.execute(query2, (exercise_id, ))
                exercise = cursor.fetchone()
                if exercise:
                    exercise = exercise._asdict() 
                    exercise['reps'] = training[counter].reps
                    print(exercise_id)
                    (print(exercise))
                    exercises.append(exercise)
                print(exercises)

            if request.args.get('download'):
                data = prepare_data(training, exercises)
                file = generate_file(data)
                print(data)
                return send_file(file, mimetype='text/csv', as_attachment=True, download_name='trainig_plan.csv')


    except DatabaseError as error:
        flash(f'Ошибка получения плана тренировки! {error}', category="danger")
    return render_template("plan.html", training=training, exercises=exercises)

def prepare_data(training, exercises):
    data = {"training_name": training[0].training_name, "exercises": exercises}
    return data

def generate_file(data):
    result = StringIO()
    writer = csv.writer(result, quotechar='"', quoting=csv.QUOTE_ALL)

    writer.writerow(['Название тренировки', data['training_name']])
    writer.writerow([])

    writer.writerow(['Название упражнения', 'Описание', 'Количество повторений', 'Упражнение для замены'])
    for exercise in data['exercises']:
            writer.writerow([exercise['exercise_name'], exercise['description'], exercise['reps'], exercise['change_name']])   

    result.seek(0)
    return BytesIO(result.getvalue().encode('utf-8'))
