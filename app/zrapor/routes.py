from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import distinct

from ..extensions import db
from ..models import Kasa, PosCihazi, ZRaporu, ZKdvSatiri, ZPosSatiri, Kasiyer
from .services import (
    parse_try,
    KDV_KODLARI,
    komisyon_hesapla,
    KDV_ORAN_MAP,
    kdv_dahil_ayir,
)

zrapor_bp = Blueprint("zrapor", __name__, url_prefix="")

@zrapor_bp.get("/")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        app_title=current_app.config["APP_TITLE"],
        app_subtitle=current_app.config["APP_SUBTITLE"],
        user=current_user
    )

@zrapor_bp.get("/z-giris")
@login_required
def z_giris():
    kasalar = Kasa.query.filter_by(aktif=True).order_by(Kasa.kasa_no.asc()).all()
    poslar = PosCihazi.query.filter_by(aktif=True).order_by(PosCihazi.ad.asc()).all()
    kasiyerler = Kasiyer.query.filter_by(aktif=True).all()

    today = date.today()
    default_tarih = today.isoformat()

    # Bu ayın ilk ve son günü
    first_day = today.replace(day=1)
    if today.month == 12:
        next_month = today.replace(year=today.year+1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month+1, day=1)
    last_day = next_month - timedelta(days=1)

    # Bu ay girilmiş tarihler
    entered_dates = {
        row[0]
        for row in db.session.query(ZRaporu.tarih)
        .filter(ZRaporu.tarih >= first_day, ZRaporu.tarih <= last_day)
        .distinct()
        .all()
    }

    # Ayın tüm günlerini üret
    calendar_days = []
    d = first_day
    while d <= last_day:
        calendar_days.append({
            "date": d.isoformat(),
            "entered": d in entered_dates
        })
        d += timedelta(days=1)

    return render_template(
        "z_giris.html",
        app_title=current_app.config["APP_TITLE"],
        kasalar=kasalar,
        poslar=poslar,
        kasiyerler=kasiyerler,
        kdv_kodlari=KDV_KODLARI,
        default_tarih=default_tarih,
        calendar_days=calendar_days,
        month_label=today.strftime("%B %Y")
    )

@zrapor_bp.post("/z-giris")
@login_required
def z_giris_post():
    tarih_raw = request.form.get("tarih")
    kasa_id_raw = request.form.get("kasa_id")

    if not tarih_raw:
        flash("Tarih zorunlu.", "danger")
        return redirect(url_for("zrapor.z_giris"))
    if not kasa_id_raw or not kasa_id_raw.isdigit():
        flash("Kasa seçmelisin.", "danger")
        return redirect(url_for("zrapor.z_giris"))

    try:
        tarih = datetime.strptime(tarih_raw, "%Y-%m-%d").date()
    except ValueError:
        flash("Tarih formatı hatalı.", "danger")
        return redirect(url_for("zrapor.z_giris"))

    kasa_id = int(kasa_id_raw)
    kasa = db.session.get(Kasa, kasa_id)
    if not kasa or not kasa.aktif:
        flash("Kasa bulunamadı.", "danger")
        return redirect(url_for("zrapor.z_giris"))
    
    kasiyer_id_raw = (request.form.get("kasiyer_id") or "").strip()
    if not kasiyer_id_raw or not kasiyer_id_raw.isdigit():
        flash("Kasiyer seçmelisin.", "danger")
        return redirect(url_for("zrapor.z_giris"))

    kasiyer_id = int(kasiyer_id_raw)
    kasiyer = db.session.get(Kasiyer, kasiyer_id)
    if not kasiyer or not kasiyer.aktif:
        flash("Kasiyer bulunamadı.", "danger")
        return redirect(url_for("zrapor.z_giris"))
    
    vardiya_raw = (request.form.get("vardiya") or "1").strip()
    vardiya = int(vardiya_raw) if vardiya_raw.isdigit() else 1
    if vardiya not in (1, 2, 3):
        vardiya = 1

    fis = parse_try(request.form.get("fis_ciro"))
    fatura = parse_try(request.form.get("fatura_ciro"))
    iade = parse_try(request.form.get("iade_tutar"))

    # Aynı gün + aynı kasa varsa güncelle
    z = ZRaporu.query.filter_by(tarih=tarih, kasa_id=kasa_id, vardiya=vardiya).first()
    if z and z.status == "locked":
        flash("Bu Z raporu kilitli. Düzenlenemez.", "danger")
        return redirect(url_for("zrapor.rapor_detay", z_id=z.id))
    if not z:
        z = ZRaporu(
            tarih=tarih,
            kasa_id=kasa_id,
            kasiyer_id=kasiyer_id,
            created_by=current_user.email,
            status="draft",
            vardiya=vardiya
        )
        db.session.add(z)
        db.session.flush()
    else:
        z.kasiyer_id = kasiyer_id


    z.fis_ciro = fis
    z.fatura_ciro = fatura
    z.iade_tutar = iade

    # Eski satırları temizle
    ZKdvSatiri.query.filter_by(z_raporu_id=z.id).delete()
    ZPosSatiri.query.filter_by(z_raporu_id=z.id).delete()

    # KDV satırları: kullanıcı KDV DAHİL tutar giriyor (senin kullanımın)
    for kod in KDV_KODLARI:
        brut_kdv_dahil = parse_try(request.form.get(f"kdv_{kod}"))
        db.session.add(ZKdvSatiri(z_raporu_id=z.id, oran_kodu=kod, matrah=brut_kdv_dahil))

    # POS satırları: input isimleri pos_{id}
    poslar = PosCihazi.query.filter_by(aktif=True).all()
    for p in poslar:
        brut = parse_try(request.form.get(f"pos_{p.id}"))
        if brut > 0:
            db.session.add(ZPosSatiri(z_raporu_id=z.id, pos_cihaz_id=p.id, brut_tutar=brut))
    
    z.updated_at = datetime.utcnow()
    z.updated_by = current_user.email

    db.session.commit()
    flash("Z raporu kaydedildi.", "success")
    return redirect(url_for("zrapor.z_giris"))

@zrapor_bp.get("/raporlar")
@login_required
def raporlar():
    # Filtreler
    start_raw = request.args.get("start") or ""
    end_raw = request.args.get("end") or ""
    kasa_id_raw = request.args.get("kasa_id") or ""

    # default: son 7 gün
    today = date.today()
    default_start = today - timedelta(days=6)
    default_end = today

    def _parse_date(s, fallback):
        if not s:
            return fallback
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except ValueError:
            return fallback

    start_date = _parse_date(start_raw, default_start)
    end_date = _parse_date(end_raw, default_end)

    q = ZRaporu.query.filter(ZRaporu.tarih >= start_date, ZRaporu.tarih <= end_date)

    kasa_id = None
    if kasa_id_raw.isdigit():
        kasa_id = int(kasa_id_raw)
        q = q.filter(ZRaporu.kasa_id == kasa_id)

    rapor_list = q.order_by(ZRaporu.tarih.desc(), ZRaporu.kasa_id.asc()).all()

    rows = []
    toplam_fis = Decimal("0.00")
    toplam_fatura = Decimal("0.00")
    toplam_iade = Decimal("0.00")
    toplam_pos_brut = Decimal("0.00")
    toplam_komisyon = Decimal("0.00")
    toplam_pos_net = Decimal("0.00")
    toplam_kdv = Decimal("0.00")

    for z in rapor_list:
        pos_brut = Decimal("0.00")
        komisyon = Decimal("0.00")
        kdv_toplam = Decimal("0.00")

        # KDV satırlarından (KDV DAHİL girilen) tutarı KDV'ye ayırıp topla
        for ks in z.kdv_satirlari:
            brut = Decimal(ks.matrah)
            oran = KDV_ORAN_MAP.get(ks.oran_kodu, None)
            if oran is None:
                continue  # OZEL gibi sabit oranı olmayanlar
            _, kdv = kdv_dahil_ayir(brut, oran)
            kdv_toplam += kdv

        kdv_toplam = kdv_toplam.quantize(Decimal("0.00"))

        for ps in z.pos_satirlari:
            pos_brut += Decimal(ps.brut_tutar)
            oran = Decimal(ps.pos_cihaz.komisyon_orani)
            komisyon += komisyon_hesapla(Decimal(ps.brut_tutar), oran)

        pos_net = (pos_brut - komisyon).quantize(Decimal("0.00"))

        nihai_ciro = (Decimal(z.fis_ciro) + Decimal(z.fatura_ciro) - Decimal(z.iade_tutar)).quantize(Decimal("0.00"))

        rows.append({
            "id": z.id,
            "tarih": z.tarih,
            "kasa_no": z.kasa.kasa_no,
            "fis": Decimal(z.fis_ciro),
            "fatura": Decimal(z.fatura_ciro),
            "iade": Decimal(z.iade_tutar),
            "nihai": nihai_ciro,
            "kdv": kdv_toplam,
            "pos_brut": pos_brut,
            "komisyon": komisyon,
            "pos_net": pos_net,
        })

        toplam_fis += Decimal(z.fis_ciro)
        toplam_fatura += Decimal(z.fatura_ciro)
        toplam_iade += Decimal(z.iade_tutar)
        toplam_pos_brut += pos_brut
        toplam_komisyon += komisyon
        toplam_pos_net += pos_net
        toplam_kdv += kdv_toplam

    kasalar = Kasa.query.order_by(Kasa.kasa_no.asc()).all()

    return render_template(
        "raporlar.html",
        app_title=current_app.config["APP_TITLE"],
        rows=rows,
        kasalar=kasalar,
        start_date=start_date,
        end_date=end_date,
        kasa_id=kasa_id,
        totals={
            "fis": toplam_fis,
            "fatura": toplam_fatura,
            "iade": toplam_iade,
            "pos_brut": toplam_pos_brut,
            "komisyon": toplam_komisyon,
            "pos_net": toplam_pos_net,
            "kdv": toplam_kdv.quantize(Decimal("0.00")),
            "nihai": (toplam_fis + toplam_fatura - toplam_iade).quantize(Decimal("0.00"))
        }
    )

@zrapor_bp.get("/raporlar/<int:z_id>")
@login_required
def rapor_detay(z_id):
    z = db.session.get(ZRaporu, z_id)
    if not z:
        flash("Kayıt bulunamadı.", "danger")
        return redirect(url_for("zrapor.raporlar"))

    # ---- KDV: KDV DAHİL tutarı içinden ayır ----
    kdv_map = {s.oran_kodu: Decimal(s.matrah) for s in z.kdv_satirlari}

    order = ["KDV0", "KDV5", "KDV10", "KDV16", "KDV20", "OZEL"]
    kdv_rows = []

    toplam_brut = Decimal("0.00")
    toplam_net = Decimal("0.00")
    toplam_kdv = Decimal("0.00")

    for kod in order:
        brut = kdv_map.get(kod, Decimal("0.00"))  # kullanıcı girişi: KDV dahil
        oran = KDV_ORAN_MAP.get(kod, None)

        if oran is None:
            # OZEL: oran sabit değil -> hesap yapmıyoruz
            net = brut
            kdv = Decimal("0.00")
            oran_yuzde = None
        else:
            net, kdv = kdv_dahil_ayir(brut, oran)
            oran_yuzde = (oran * Decimal("100")).quantize(Decimal("0.00"))

        kdv_rows.append({
            "kod": kod,
            "oran_yuzde": oran_yuzde,
            "brut": brut,
            "net": net,
            "kdv": kdv,
        })

        toplam_brut += brut
        toplam_net += net
        toplam_kdv += kdv

    # ---- POS detay hesap ----
    pos_detay = []
    pos_brut = Decimal("0.00")
    komisyon = Decimal("0.00")

    for ps in z.pos_satirlari:
        brut = Decimal(ps.brut_tutar)
        oran = Decimal(ps.pos_cihaz.komisyon_orani)
        kom = komisyon_hesapla(brut, oran)
        net = (brut - kom).quantize(Decimal("0.00"))
        pos_detay.append({
            "ad": ps.pos_cihaz.ad,
            "banka": (ps.pos_cihaz.banka.ad if ps.pos_cihaz and ps.pos_cihaz.banka else "-"),
            "oran": oran,
            "brut": brut,
            "kom": kom,
            "net": net
        })
        pos_brut += brut
        komisyon += kom

    pos_net = (pos_brut - komisyon).quantize(Decimal("0.00"))
    nihai_ciro = (Decimal(z.fis_ciro) + Decimal(z.fatura_ciro) - Decimal(z.iade_tutar)).quantize(Decimal("0.00"))

    return render_template(
        "rapor_detay.html",
        app_title=current_app.config["APP_TITLE"],
        z=z,
        nihai=nihai_ciro,
        kdv_rows=kdv_rows,
        kdv_totals={"brut": toplam_brut, "net": toplam_net, "kdv": toplam_kdv},
        pos_detay=pos_detay,
        pos_brut=pos_brut,
        komisyon=komisyon,
        pos_net=pos_net
    )
