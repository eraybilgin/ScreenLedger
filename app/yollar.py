"""Kurulum kökünü ve kişisel dosyaların konumlarını tek yerde tanımlar."""

import os
import sys
from pathlib import Path


PAKETLI = bool(getattr(sys, "frozen", False))
KOK = (Path(sys.executable).resolve().parent if PAKETLI
       else Path(__file__).resolve().parent.parent)
if PAKETLI:
    kullanici_klasoru = Path(os.environ.get("LOCALAPPDATA") or
                            (Path.home() / "AppData" / "Local")) / "ScreenLedger"
    VERI_KLASORU = kullanici_klasoru / "data"
    GUNLUK_KLASORU = kullanici_klasoru / "logs"
else:
    VERI_KLASORU = KOK / "data"
    GUNLUK_KLASORU = KOK / "logs"


def veri_dosyasi(ad):
    """Eski kurulumlarda kökteki kayıtları da kayıpsız kullan."""
    yeni = VERI_KLASORU / ad
    eski = KOK / ad
    if PAKETLI:
        return str(yeni)
    if yeni.is_file() or not eski.is_file():
        return str(yeni)
    return str(eski)


VERITABANI = veri_dosyasi("veri.db")
KIMLIK_DOSYASI = veri_dosyasi("kimlik.json")
DURDUR_ISARETI = str((VERI_KLASORU if PAKETLI else KOK) / "durdur.isaret")
EKLENTI_AYARI = str((kullanici_klasoru if PAKETLI else KOK) /
                   "sekme-eklentisi" / "ayar.json")
