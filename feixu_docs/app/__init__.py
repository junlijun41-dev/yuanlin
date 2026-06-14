# -*- coding: utf-8 -*-
import os

from flask import Flask
from flask_login import LoginManager

from .models import db, User

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录"


@login_manager.user_loader
def load_user(uid):
    return db.session.get(User, int(uid))


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    for d in (app.config["UPLOAD_DIR"], app.config["TEMPLATE_DIR"],
              app.config["EXPORT_DIR"], os.path.dirname(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))):
        os.makedirs(d, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import auth_bp
    from .views import main_bp
    from .ai_views import ai_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(ai_bp)

    from .constants import PHASE_MAP, PROCESS_MAP, VOLUME_MAP, WORKFLOW_MAP, WORKFLOW_STEPS
    app.jinja_env.globals.update(
        PHASE_MAP=PHASE_MAP, PROCESS_MAP=PROCESS_MAP, VOLUME_MAP=VOLUME_MAP,
        WORKFLOW_MAP=WORKFLOW_MAP, WORKFLOW_STEPS=WORKFLOW_STEPS,
    )

    with app.app_context():
        db.create_all()
        from .seed import seed_all
        seed_all()

    return app
