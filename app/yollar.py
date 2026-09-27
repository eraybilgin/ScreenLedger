"""Kurulum kökünü ve kişisel dosyaların konumlarını tek yerde tanımlar."""

from pathlib import Path


KOK = Path(__file__).resolve().parent.parent
VERI_KLASORU = KOK / "data"
GUNLUK_KLASORU = KOK / "logs"


def veri_dosyasi(ad):
    """Eski kurulumlarda kökteki kayıtları da kayıpsız kullan."""
    yeni = VERI_KLASORU / ad
    eski = KOK / ad
    if yeni.is_file() or not eski.is_file():
        return str(yeni)
    return str(eski)


VERITABANI = veri_dosyasi("veri.db")
KIMLIK_DOSYASI = veri_dosyasi("kimlik.json")
DURDUR_ISARETI = str(KOK / "durdur.isaret")
EKLENTI_AYARI = str(KOK / "sekme-eklentisi" / "ayar.json")
