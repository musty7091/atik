from decimal import Decimal, InvalidOperation

KDV_KODLARI = ["KDV0", "KDV5", "KDV10", "KDV16", "KDV20", "OZEL"]

def parse_try(text: str) -> Decimal:
    """
    TRY tutar parse:
    - "" / None -> 0.00
    - "1.234,56" -> 1234.56
    - "1234.56" -> 1234.56
    """
    if text is None:
        return Decimal("0.00")
    s = str(text).strip()
    if s == "":
        return Decimal("0.00")

    # TR format: 1.234,56
    s = s.replace(".", "").replace(",", ".")
    try:
        val = Decimal(s)
    except InvalidOperation:
        return Decimal("0.00")

    # negatifleri istemiyoruz
    if val < 0:
        return Decimal("0.00")

    return val.quantize(Decimal("0.00"))

def komisyon_hesapla(brut: Decimal, oran: Decimal) -> Decimal:
    """
    oran: 0.0250 gibi
    """
    if brut <= 0:
        return Decimal("0.00")
    if oran <= 0:
        return Decimal("0.00")
    return (brut * oran).quantize(Decimal("0.00"))

KDV_ORAN_MAP = {
    "KDV0": Decimal("0.00"),
    "KDV5": Decimal("0.05"),
    "KDV10": Decimal("0.10"),
    "KDV16": Decimal("0.16"),
    "KDV20": Decimal("0.20"),
    # OZEL: oran sabit değil, şimdilik hesap yok
}

def kdv_dahil_ayir(brut_kdv_dahil: Decimal, oran: Decimal) -> tuple[Decimal, Decimal]:
    """
    brut_kdv_dahil: KDV DAHİL tutar
    oran: 0.05 gibi
    dönüş: (net_kdv_haric, kdv_tutari)
    """
    if brut_kdv_dahil <= 0:
        return (Decimal("0.00"), Decimal("0.00"))
    if oran <= 0:
        # %0 ise net = brut, kdv = 0
        return (brut_kdv_dahil.quantize(Decimal("0.00")), Decimal("0.00"))

    net = (brut_kdv_dahil / (Decimal("1.00") + oran)).quantize(Decimal("0.00"))
    kdv = (brut_kdv_dahil - net).quantize(Decimal("0.00"))
    return (net, kdv)