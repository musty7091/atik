from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from ..models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("zrapor.dashboard"))
    return render_template("login.html")

@auth_bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or user.password != password:
        flash("E-posta veya şifre hatalı.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user)
    return redirect(url_for("zrapor.dashboard"))

@auth_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
