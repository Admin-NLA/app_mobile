from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from bcrypt import checkpw, gensalt, hashpw
from functools import wraps

from .models import User
from . import db


auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get("username")
    password = request.form.get("password").encode('utf-8')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(name=username).first()

    if not user or not checkpw(password, user.password.encode('utf-8')):
        flash("Error en Credenciales: Intenta de Nuevo")
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('main.home'))

@auth.route('/signup')
@login_required
def signup():
    return render_template("signup.html", username=current_user.name)

@auth.route('/signup', methods=['POST'])
@login_required
def signup_post():
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password").encode('utf-8')

    user = User.query.filter_by(name=username).first()

    if user:
        flash('Usuario ya registrado')
        return redirect(url_for('auth.signup'))
    
    salt = gensalt()
    hashed_password = hashpw(password, salt).decode('utf-8')
    
    new_user = User(email=email, name=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    flash('Usuario registrado exitosamente')
    return redirect(url_for('auth.signup'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


def service_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Service-Token")

        if token != current_app.config["SERVICE_TOKEN"]:
            return jsonify({"error": "Acceso no Autorizado"}), 401
        
        return f(*args, **kwargs)
    
    return wrapper