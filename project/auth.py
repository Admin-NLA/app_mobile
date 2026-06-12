from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort, g
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps

from .models import User, Stats
from . import db

auth = Blueprint('auth', __name__)

def require_user_type(*allowed_types):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_type = current_user.user_type
            if user_type not in allowed_types:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get("username")
    password = request.form.get("password")
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(name=username).first()

    if not user or not user.check_password(password):
        flash("Error en Credenciales: Intenta de Nuevo")
        return redirect(url_for('auth.login'))

    login_user(user, remember=remember)
    return redirect(url_for('main.home'))

@auth.route('/signup')
@login_required
@require_user_type("ADMIN")
def signup():
    active_event = g.active_event
    stats = Stats.query.filter_by(event_id = active_event.event_id).first()
    companies = []
    if stats and stats.stats:
        companies = stats.stats.get('exhibitor_companies', [])
    return render_template("signup.html", companies = companies)

@auth.route('/signup', methods=['POST'])
@login_required
@require_user_type("ADMIN")
def signup_post():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    company = data.get("companySelector")
    password = data.get("password")
    user_type = data.get("typeSelector")

    user = User.query.filter_by(name=username).first()

    if user:
        return jsonify({"success": False, "message": "Usuario ya registrado"}), 400

    new_user = User(email=email, name=username, company=company, user_type=user_type)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "Usuario registrado exitosamente"}), 200

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