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


class Banka(db.Model):
    __tablename__ = "bankalar"

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(120), unique=True, nullable=False)  # "Garanti", "YKB"...
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Banka {self.ad}>"


class PosCihazi(db.Model):
    __tablename__ = "pos_cihazlari"

    id = db.Column(db.Integer, primary_key=True)

    # POS cihazının slip üzerinde yazan gerçek numarası (ZORUNLU olacak; formda zorunlu)
    pos_no = db.Column(db.String(60), unique=True, nullable=True)  # sqlite alter için nullable; uygulama seviyesinde zorunlu

    ad = db.Column(db.String(120), unique=True, nullable=False)  # "Garanti POS-3" vb.
    komisyon_orani = db.Column(db.Numeric(6, 4), default=Decimal("0.0000"), nullable=False)  # 0.0250
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    banka_id = db.Column(db.Integer, db.ForeignKey("bankalar.id"), nullable=True)
    banka = db.relationship("Banka")

    def __repr__(self):
        return f"<POS {self.pos_no or '-'} {self.ad}>"


class ZRaporu(db.Model):
    __tablename__ = "z_raporlari"

    id = db.Column(db.Integer, primary_key=True)
    tarih = db.Column(db.Date, nullable=False)

    kasa_id = db.Column(db.Integer, db.ForeignKey("kasalar.id"), nullable=False)
    kasa = db.relationship("Kasa")

    kasiyer_id = db.Column(db.Integer, db.ForeignKey("kasiyerler.id"), nullable=True)
    kasiyer = db.relationship("Kasiyer")

    status = db.Column(db.String(20), nullable=False, default="draft")

    fis_ciro = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    fatura_ciro = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    iade_tutar = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    created_by = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime)
    updated_by = db.Column(db.String(255))

    pos_satirlari = db.relationship(
        "ZPosSatiri",
        back_populates="z_raporu",
        cascade="all, delete-orphan",
        lazy="select"
    )

    kdv_satirlari = db.relationship(
        "ZKdvSatiri",
        back_populates="z_raporu",
        cascade="all, delete-orphan",
        lazy="select"
    )


class ZKdvSatiri(db.Model):
    __tablename__ = "z_kdv_satirlari"

    id = db.Column(db.Integer, primary_key=True)

    z_raporu_id = db.Column(db.Integer, db.ForeignKey("z_raporlari.id"), nullable=False)
    z_raporu = db.relationship("ZRaporu", back_populates="kdv_satirlari")

    oran_kodu = db.Column(db.String(20), nullable=False)
    matrah = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    def __repr__(self):
        return f"<ZKDV {self.oran_kodu} {self.matrah}>"


class ZPosSatiri(db.Model):
    __tablename__ = "z_pos_satirlari"

    id = db.Column(db.Integer, primary_key=True)

    z_raporu_id = db.Column(db.Integer, db.ForeignKey("z_raporlari.id"), nullable=False)
    z_raporu = db.relationship("ZRaporu", back_populates="pos_satirlari")

    # ✅ ROUTE ile uyumlu isim:
    pos_cihaz_id = db.Column(db.Integer, db.ForeignKey("pos_cihazlari.id"), nullable=False)
    pos_cihaz = db.relationship("PosCihazi")

    brut_tutar = db.Column(db.Numeric(14, 2), default=Decimal("0.00"), nullable=False)

    def __repr__(self):
        return f"<ZPOS {self.pos_cihaz_id} {self.brut_tutar}>"

class Kasiyer(db.Model):
    __tablename__ = "kasiyerler"

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(120), unique=True, nullable=False)
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Kasiyer {self.ad}>"
