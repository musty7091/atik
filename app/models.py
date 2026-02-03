from .extensions import db
from flask_login import UserMixin
from decimal import Decimal
from sqlalchemy import UniqueConstraint

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # MVP: düz metin (bilerek)
    role = db.Column(db.String(50), nullable=False, default="muhasebe")  # admin / muhasebe
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def get_id(self):
        return str(self.id)

class Kasa(db.Model):
    __tablename__ = "kasalar"

    id = db.Column(db.Integer, primary_key=True)
    kasa_no = db.Column(db.Integer, unique=True, nullable=False)  # 1..6
    fm_no = db.Column(db.String(50), nullable=True)
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Kasa {self.kasa_no}>"

class PosCihazi(db.Model):
    __tablename__ = "pos_cihazlari"

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(120), unique=True, nullable=False)      # "Garanti POS-3"
    banka_adi = db.Column(db.String(120), nullable=True)             # opsiyonel
    komisyon_orani = db.Column(db.Numeric(6, 4), default=Decimal("0.0000"), nullable=False)  # 0.0250
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<POS {self.ad}>"
    
class ZRaporu(db.Model):
    __tablename__ = "z_raporlari"
    __table_args__ = (
        UniqueConstraint("tarih", "kasa_id", name="uq_z_tarih_kasa"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tarih = db.Column(db.Date, nullable=False)

    kasa_id = db.Column(db.Integer, db.ForeignKey("kasalar.id"), nullable=False)
    kasa = db.relationship("Kasa")

    fis_ciro = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    fatura_ciro = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    iade_tutar = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    created_by = db.Column(db.String(255), nullable=True)

class ZKdvSatiri(db.Model):
    __tablename__ = "z_kdv_satirlari"

    id = db.Column(db.Integer, primary_key=True)
    z_raporu_id = db.Column(db.Integer, db.ForeignKey("z_raporlari.id"), nullable=False)
    z_raporu = db.relationship("ZRaporu", backref=db.backref("kdv_satirlari", lazy=True, cascade="all,delete-orphan"))

    # "KDV0", "KDV5", "KDV10", "KDV16", "KDV20", "OZEL"
    oran_kodu = db.Column(db.String(10), nullable=False)

    matrah = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)

class ZPosSatiri(db.Model):
    __tablename__ = "z_pos_satirlari"

    id = db.Column(db.Integer, primary_key=True)
    z_raporu_id = db.Column(db.Integer, db.ForeignKey("z_raporlari.id"), nullable=False)
    z_raporu = db.relationship("ZRaporu", backref=db.backref("pos_satirlari", lazy=True, cascade="all,delete-orphan"))

    pos_cihaz_id = db.Column(db.Integer, db.ForeignKey("pos_cihazlari.id"), nullable=False)
    pos_cihaz = db.relationship("PosCihazi")

    brut_tutar = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)