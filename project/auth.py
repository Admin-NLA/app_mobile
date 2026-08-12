from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    jsonify,
    abort,
    g,
    session,
)
from datetime import date
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps

from .models import User, Stats, Event
from .events import get_active_event
from . import db

auth = Blueprint("auth", __name__)


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


def _build_event_companies_index():
    records = (
        Stats.query.with_entities(Stats.stats, Event.location, Event.year)
        .join(Event, Event.event_id == Stats.event_id)
        .all()
    )
    index = []
    for stats_json, location, year in records:
        companies = stats_json.get("exhibitor_companies", []) if stats_json else []
        companies_upper = {c.strip().upper() for c in companies}
        index.append((f"{location} {year}", companies_upper))
    return index


def _get_sedes_for_company(company, event_companies_index):
    if not company:
        return []
    company_upper = company.strip().upper()
    return [
        name
        for name, companies_upper in event_companies_index
        if company_upper in companies_upper
    ]


@auth.route("/login")
def login():
    return render_template("login.html")


@auth.route("/login", methods=["POST"])
def login_post():
    username = request.form.get("username")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    user = User.query.filter_by(name=username).first()

    if not user or not user.check_password(password):
        flash("Error en Credenciales: Intenta de Nuevo")
        return redirect(url_for("auth.login"))

    if not user.is_active_user:
        flash("Esta cuenta está desactivada. Contacta al administrador.")
        return redirect(url_for("auth.login"))

    login_user(user, remember=remember)

    if user.user_type == "EXHIBITOR":
        if session.get("rep_selected_date") != date.today().isoformat():
            return redirect(url_for("auth.select_rep"))

    return redirect(url_for("main.home"))


@auth.route("/select-rep")
@login_required
@require_user_type("EXHIBITOR")
def select_rep():
    event = get_active_event()
    reps = []
    if event and event.stats_ev and event.stats_ev.stats:
        exhibitor_list = event.stats_ev.stats.get("exhibitor_scan_stats", [])
        own_company = (current_user.company or "").strip().upper()
        reps = sorted(
            {
                f'{row.get("Nombre(s)", "").strip()} {row.get("Apellido(s)", "").strip()}'.strip()
                for row in exhibitor_list
                if row.get("Empresa", "").strip().upper() == own_company
            }
        )
    return render_template("select_rep.html", reps=reps)


@auth.route("/select-rep", methods=["POST"])
@login_required
@require_user_type("EXHIBITOR")
def select_rep_post():
    rep_name = request.form.get("rep_name", "").strip()
    if not rep_name:
        flash("Selecciona tu nombre para continuar")
        return redirect(url_for("auth.select_rep"))
    session["scanned_by_rep_name"] = rep_name
    session["rep_selected_date"] = date.today().isoformat()
    return redirect(url_for("main.home"))


@auth.route("/signup")
@login_required
@require_user_type("ADMIN")
def signup():
    active_event = g.active_event
    stats = Stats.query.filter_by(event_id=active_event.event_id).first()
    companies = []
    if stats and stats.stats:
        companies = stats.stats.get("exhibitor_companies", [])
    sede_label = (
        f"{active_event.location} {active_event.year}"
        if active_event
        else "Sin evento activo"
    )
    return render_template("signup.html", companies=companies, sede_label=sede_label)


@auth.route("/signup", methods=["POST"])
@login_required
@require_user_type("ADMIN")
def signup_post():
    data = request.get_json()
    username = data.get("username")
    display_name = data.get("displayName")
    email = data.get("email")
    company = data.get("companySelector")
    password = data.get("password")
    user_type = data.get("typeSelector")

    user = User.query.filter_by(name=username).first()

    if user:
        return jsonify({"success": False, "message": "Usuario ya registrado"}), 400

    new_user = User(
        email=email,
        name=username,
        display_name=display_name,
        company=company,
        user_type=user_type,
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"success": True, "message": "Usuario registrado exitosamente"}), 200


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# -------- AJUSTE PARA VISUALIZACIÓN --------
@auth.route("/admin/users")
@login_required
@require_user_type("ADMIN")
def users():
    return render_template("users.html")


@auth.route("/admin/users/list")
@login_required
@require_user_type("ADMIN")
def users_list():
    users = User.query.all()
    event_companies_index = _build_event_companies_index()
    return jsonify(
        [
            {
                "id": u.user_id,
                "name": u.name,
                "display_name": u.display_name or "",
                "email": u.email,
                "company": u.company or "",
                "user_type": u.user_type,
                "is_active_user": u.is_active_user,
                "sedes": _get_sedes_for_company(u.company, event_companies_index),
            }
            for u in users
        ]
    )


@auth.route("/admin/users/<int:user_id>/edit", methods=["POST"])
@login_required
@require_user_type("ADMIN")
def edit_user(user_id):
    if user_id == current_user.user_id:
        return (
            jsonify({"success": False, "message": "No puedes editarte a ti mismo"}),
            400,
        )
    data = request.get_json()
    user = User.query.get_or_404(user_id)
    user.name = data.get("name", user.name)
    user.display_name = data.get("display_name", user.display_name)
    user.email = data.get("email", user.email)
    user.company = data.get("company", user.company)
    user.user_type = data.get("user_type", user.user_type)
    db.session.commit()
    return jsonify({"success": True, "message": "Usuario actualizado"})


@auth.route("/admin/users/delete", methods=["POST"])
@login_required
@require_user_type("ADMIN")
def delete_users():
    data = request.get_json()
    ids = data.get("ids", [])
    if current_user.user_id in ids:
        return (
            jsonify({"success": False, "message": "No puedes eliminarte a ti mismo"}),
            400,
        )
    User.query.filter(User.user_id.in_(ids)).delete()
    db.session.commit()
    return jsonify({"success": True, "message": f"{len(ids)} usuario(s) eliminado(s)"})


@auth.route("/admin/users/bulk-role", methods=["POST"])
@login_required
@require_user_type("ADMIN")
def bulk_role():
    data = request.get_json()
    ids = data.get("ids", [])
    role = data.get("role", "")
    if not role:
        return jsonify({"success": False, "message": "Rol no especificado"}), 400
    if current_user.user_id in ids:
        return (
            jsonify({"success": False, "message": "No puedes cambiar tu propio rol"}),
            400,
        )
    User.query.filter(User.user_id.in_(ids)).update({"user_type": role})
    db.session.commit()
    return jsonify(
        {"success": True, "message": f"Rol actualizado para {len(ids)} usuario(s)"}
    )


@auth.route("/admin/users/activate", methods=["POST"])
@login_required
@require_user_type("ADMIN")
def activate_users():
    data = request.get_json()
    ids = data.get("ids", [])
    User.query.filter(User.user_id.in_(ids)).update(
        {"is_active_user": True}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({"success": True, "message": f"{len(ids)} usuario(s) activado(s)"})


@auth.route("/admin/users/deactivate", methods=["POST"])
@login_required
@require_user_type("ADMIN")
def deactivate_users():
    data = request.get_json()
    ids = data.get("ids", [])
    if current_user.user_id in ids:
        return (
            jsonify({"success": False, "message": "No puedes desactivarte a ti mismo"}),
            400,
        )
    User.query.filter(User.user_id.in_(ids)).update(
        {"is_active_user": False}, synchronize_session=False
    )
    db.session.commit()
    return jsonify(
        {"success": True, "message": f"{len(ids)} usuario(s) desactivado(s)"}
    )


# -------- AJUSTE PARA VISUALIZACIÓN --------


def service_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Service-Token")

        if token != current_app.config["SERVICE_TOKEN"]:
            return jsonify({"error": "Acceso no Autorizado"}), 401

        return f(*args, **kwargs)

    return wrapper
