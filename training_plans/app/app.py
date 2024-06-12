from flask import Flask, render_template, session, request, flash
from flask_login import login_required, current_user
from mysqldb import DBConnector
from mysql.connector.errors import DatabaseError


app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')

db_connector = DBConnector(app)

from authorization import bp as authorization_bp, init_login_manager
app.register_blueprint(authorization_bp)
init_login_manager(app)

from users import bp as users_bp
app.register_blueprint(users_bp)

from trainer import bp as trainer_bp
app.register_blueprint(trainer_bp)

from client import bp as client_bp
app.register_blueprint(client_bp)

from plans import bp as plan_bp
app.register_blueprint(plan_bp)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == 'main':
    app.run(debug=True)
   
