from flask import Flask
from dotenv import load_dotenv

from .config import Config
from .extensions import db, login_manager, csrf
from .models import User


def _ensure_schema_sqlite():
    """
    SQLite'da create_all yeni kolon eklemez.
    Bu fonksiyon eksik kolonları ALTER TABLE ile ekler.
    """
    # sadece sqlite ise çalıştır
    uri = str(db.engine.url)
    if not uri.startswith("sqlite"):
        return

    def _has_column(table, col):
        rows = db.session.execute(db.text(f"PRAGMA table_info({table});")).fetchall()
        return any(r[1] == col for r in rows)

    table = "z_raporlari"

    if not _has_column(table, "status"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'draft'"))
    if not _has_column(table, "submitted_at"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN submitted_at DATETIME"))
    if not _has_column(table, "submitted_by"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN submitted_by VARCHAR(255)"))
    if not _has_column(table, "locked_at"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN locked_at DATETIME"))
    if not _has_column(table, "locked_by"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN locked_by VARCHAR(255)"))
    if not _has_column(table, "updated_at"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN updated_at DATETIME"))
    if not _has_column(table, "updated_by"):
        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN updated_by VARCHAR(255)"))

    db.session.commit()


def _ensure_default_users():
    # Default admin: admin@atik.local / 123
    # Default muhasebe: muhasebe@atik.local / 123
    if not User.query.filter_by(email="admin@atik.local").first():
        db.session.add(User(email="admin@atik.local", password="123", role="admin"))
    if not User.query.filter_by(email="muhasebe@atik.local").first():
        db.session.add(User(email="muhasebe@atik.local", password="123", role="muhasebe"))
    db.session.commit()


def create_app():
    load_dotenv()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from flask_wtf.csrf import generate_csrf

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Devam etmek için giriş yapmalısın."

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Blueprints
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .zrapor.routes import zrapor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(zrapor_bp)

    # İlk çalıştırmada DB oluştur + schema + default kullanıcı
    with app.app_context():
        db.create_all()
        _ensure_schema_sqlite()
        _ensure_default_users()

    return app
