import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # SQLite'a KİLİTLE (bu projede Postgres istemiyoruz)
    default_db_path = BASE_DIR / "instance" / "atik.db"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{default_db_path}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APP_TITLE = "Atik Muhasebe | Ertan Market - Z Rapor Akışı"
    APP_SUBTITLE = "Ertan Market günlük Z raporlarını girer, Atik Muhasebe her yerden anlık erişir."
