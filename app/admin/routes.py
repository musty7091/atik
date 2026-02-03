from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Kasa, PosCihazi

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def _is_admin():
    return getattr(current_user, "role", "") == "admin"

def _require_admin():
    if not _is_admin():
        flash("Bu sayfaya erişim yetkin yok.", "danger")
        return False
    return True

def parse_decimal(text: str, scale: str = "0.00") -> Decimal:
    """
    TR girişleri için güvenli Decimal parse:
    - boş -> 0
    - virgül -> nokta
    """
    if text is None:
        return Decimal(scale)
    s = str(text).strip()
    if s == "":
        return Decimal(scale)
    s = s.replace(".", "").replace(",", ".")  # 1.234,56 -> 1234.56
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal(scale)

@admin_bp.get("/")
@login_required
def admin_home():
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))
    return redirect(url_for("admin.kasa_list"))

# ----------------- KASA -----------------

@admin_bp.get("/kasalar")
@login_required
def kasa_list():
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))
    kasalar = Kasa.query.order_by(Kasa.kasa_no.asc()).all()
    return render_template(
        "admin_kasa.html",
        app_title=current_app.config["APP_TITLE"],
        kasalar=kasalar
    )

@admin_bp.post("/kasalar/add")
@login_required
def kasa_add():
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    kasa_no = request.form.get("kasa_no", "").strip()
    fm_no = (request.form.get("fm_no") or "").strip() or None

    if not kasa_no.isdigit():
        flash("Kasa no sayısal olmalı.", "danger")
        return redirect(url_for("admin.kasa_list"))

    kasa_no_int = int(kasa_no)
    if kasa_no_int <= 0:
        flash("Kasa no 1 ve üzeri olmalı.", "danger")
        return redirect(url_for("admin.kasa_list"))

    if Kasa.query.filter_by(kasa_no=kasa_no_int).first():
        flash("Bu kasa no zaten var.", "danger")
        return redirect(url_for("admin.kasa_list"))

    db.session.add(Kasa(kasa_no=kasa_no_int, fm_no=fm_no, aktif=True))
    db.session.commit()
    flash("Kasa eklendi.", "success")
    return redirect(url_for("admin.kasa_list"))

@admin_bp.post("/kasalar/toggle/<int:kasa_id>")
@login_required
def kasa_toggle(kasa_id):
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    kasa = db.session.get(Kasa, kasa_id)
    if not kasa:
        flash("Kasa bulunamadı.", "danger")
        return redirect(url_for("admin.kasa_list"))

    kasa.aktif = not kasa.aktif
    db.session.commit()
    flash("Kasa durumu güncellendi.", "success")
    return redirect(url_for("admin.kasa_list"))

@admin_bp.post("/kasalar/delete/<int:kasa_id>")
@login_required
def kasa_delete(kasa_id):
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    kasa = db.session.get(Kasa, kasa_id)
    if not kasa:
        flash("Kasa bulunamadı.", "danger")
        return redirect(url_for("admin.kasa_list"))

    db.session.delete(kasa)
    db.session.commit()
    flash("Kasa silindi.", "success")
    return redirect(url_for("admin.kasa_list"))

# ----------------- POS -----------------

@admin_bp.get("/pos")
@login_required
def pos_list():
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    poslar = PosCihazi.query.order_by(PosCihazi.ad.asc()).all()
    return render_template(
        "admin_pos.html",
        app_title=current_app.config["APP_TITLE"],
        poslar=poslar
    )

@admin_bp.post("/pos/add")
@login_required
def pos_add():
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    ad = (request.form.get("ad") or "").strip()
    banka_adi = (request.form.get("banka_adi") or "").strip() or None
    komisyon_raw = request.form.get("komisyon_orani", "").strip()

    if not ad:
        flash("POS adı boş olamaz.", "danger")
        return redirect(url_for("admin.pos_list"))

    if PosCihazi.query.filter_by(ad=ad).first():
        flash("Bu POS adı zaten var.", "danger")
        return redirect(url_for("admin.pos_list"))

    # Komisyon: kullanıcı 2.5 veya 0.025 girebilir.
    # 2.5 => %2.5 kabul edip 0.0250'a çeviriyoruz.
    komisyon = parse_decimal(komisyon_raw, "0.0000")
    if komisyon > Decimal("1.0"):
        komisyon = (komisyon / Decimal("100")).quantize(Decimal("0.0000"))
    else:
        komisyon = komisyon.quantize(Decimal("0.0000"))

    db.session.add(PosCihazi(ad=ad, banka_adi=banka_adi, komisyon_orani=komisyon, aktif=True))
    db.session.commit()
    flash("POS eklendi.", "success")
    return redirect(url_for("admin.pos_list"))

@admin_bp.post("/pos/toggle/<int:pos_id>")
@login_required
def pos_toggle(pos_id):
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    pos = db.session.get(PosCihazi, pos_id)
    if not pos:
        flash("POS bulunamadı.", "danger")
        return redirect(url_for("admin.pos_list"))

    pos.aktif = not pos.aktif
    db.session.commit()
    flash("POS durumu güncellendi.", "success")
    return redirect(url_for("admin.pos_list"))

@admin_bp.post("/pos/delete/<int:pos_id>")
@login_required
def pos_delete(pos_id):
    if not _require_admin():
        return redirect(url_for("zrapor.dashboard"))

    pos = db.session.get(PosCihazi, pos_id)
    if not pos:
        flash("POS bulunamadı.", "danger")
        return redirect(url_for("admin.pos_list"))

    db.session.delete(pos)
    db.session.commit()
    flash("POS silindi.", "success")
    return redirect(url_for("admin.pos_list"))
