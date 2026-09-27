# -*- coding: utf-8 -*-
"""
hareket.py -- "Ekranda bir sey oynuyor mu?" sorusunu cevaplayan katman.

Nasil calisir: Butun ekranlarin cok kucuk (96x54 piksel) bir kopyasini
alir ve bir onceki kopyayla karsilastirir. Piksellerin bir kismi degismisse
"ekranda hareket var" der. Bu sayede kullanici klavyeye dokunmasa bile,
video izliyorsa "bosta" sayilmaz.

MALIYET: Bir goruntu alma islemi bu bilgisayarda ~55 milisaniye suruyor.
Bu yuzden SUREKLI DEGIL, sadece kullanici bir suredir klavyeye/fareye
dokunmadiginda calistirilir. Normal calisma sirasinda maliyeti sifirdir.
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

SRCCOPY = 0x00CC0020
COLORONCOLOR = 3           # hizli olceklendirme yontemi
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

GENISLIK = 96              # kucultulmus ornegin genisligi (piksel)
YUKSEKLIK = 54             # kucultulmus ornegin yuksekligi (piksel)

# Bir pikselin "degisti" sayilmasi icin gereken renk farki (0-255 arasi)
PIKSEL_ESIGI = 16
# Kac piksel degisirse "ekranda hareket var" denir
DEGISEN_PIKSEL_ESIGI = 6


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", wintypes.DWORD * 3)]


def _ekran_ornegi():
    """Butun ekranlarin kucultulmus bir kopyasini bayt dizisi olarak alir."""
    sol = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    ust = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    en = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    boy = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if en <= 0 or boy <= 0:
        return None

    kaynak = user32.GetDC(0)
    if not kaynak:
        return None
    bellek = gdi32.CreateCompatibleDC(kaynak)
    resim = gdi32.CreateCompatibleBitmap(kaynak, GENISLIK, YUKSEKLIK)
    try:
        gdi32.SelectObject(bellek, resim)
        gdi32.SetStretchBltMode(bellek, COLORONCOLOR)
        gdi32.StretchBlt(bellek, 0, 0, GENISLIK, YUKSEKLIK,
                         kaynak, sol, ust, en, boy, SRCCOPY)
        bilgi = BITMAPINFO()
        bilgi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bilgi.bmiHeader.biWidth = GENISLIK
        bilgi.bmiHeader.biHeight = -YUKSEKLIK   # eksi = yukaridan asagi
        bilgi.bmiHeader.biPlanes = 1
        bilgi.bmiHeader.biBitCount = 32
        bilgi.bmiHeader.biCompression = 0
        arabellek = (ctypes.c_ubyte * (GENISLIK * YUKSEKLIK * 4))()
        gdi32.GetDIBits(bellek, resim, 0, YUKSEKLIK, arabellek,
                        ctypes.byref(bilgi), 0)
        return bytes(arabellek)
    finally:
        gdi32.DeleteObject(resim)
        gdi32.DeleteDC(bellek)
        user32.ReleaseDC(0, kaynak)


class HareketDedektoru:
    """Ekran goruntusunu hatirlar ve bir sonrakiyle karsilastirir."""

    def __init__(self):
        self._onceki = None

    def sifirla(self):
        self._onceki = None

    def hareket_var_mi(self):
        """
        True  = ekranda bir sey degisiyor (video, animasyon, ilerleyen bir islem)
        False = ekran donmus, hicbir sey degismiyor
        None  = olculemedi (ekran kilitli veya kapali olabilir)
        """
        simdiki = _ekran_ornegi()
        if simdiki is None:
            return None
        onceki = self._onceki
        self._onceki = simdiki
        if onceki is None or len(onceki) != len(simdiki):
            return None

        # Her pikselin sadece yesil kanalina bakmak yeterli ve 4 kat hizli
        degisen = 0
        for i in range(1, len(simdiki), 4):
            fark = simdiki[i] - onceki[i]
            if fark < 0:
                fark = -fark
            if fark > PIKSEL_ESIGI:
                degisen += 1
                if degisen >= DEGISEN_PIKSEL_ESIGI:
                    return True
        return False
