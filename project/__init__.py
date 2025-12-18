from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()
conn_string = os.getenv("DATABASE_URL")

db = SQLAlchemy()

def create_app():

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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

    return app