from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()

def create_app():

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SERVICE_TOKEN'] = os.getenv("SERVICE_TOKEN")
    CORS(app)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from .auth import auth as auth_bp
    app.register_blueprint(auth_bp)

    from .main import main as main_bp
    app.register_blueprint(main_bp)

    from .scan import scan as scan_bp
    app.register_blueprint(scan_bp)

    # Evento activo disponible en toda la app (caché por día, una consulta por fecha)
    from flask import g
    from .events import set_active_event_for_request

    @app.before_request
    def inject_active_event():
        set_active_event_for_request()

    @app.context_processor
    def inject_active_event_into_templates():
        return {"active_event": g.get("active_event")}

    return app