# -*- coding: utf-8 -*-
"""
adres.py -- Tarayicinin adres cubugundaki internet adresini (URL) okur.

NASIL: Windows'un "UI Automation" (= ekran okuyucu programlarin
kullandigi, pencerelerin icindeki kutulari okuyabilen Windows servisi)
ozelligini kullanir. Chrome'un adres cubugunu bulup icindeki yaziyi alir.

MALIYET: Bir okuma ~13 milisaniye suruyor. Bu yuzden HER OLCUMDE DEGIL,
sadece sayfa degistiginde (pencere basligi degistiginde) okunur.
Gunde birkac yuz kez calisir, toplam maliyeti saniyeler mertebesindedir.

Bir sey ters giderse kendini kapatir; takip URL olmadan calismaya devam eder.
"""

# Adres cubugu okunacak tarayicilar
TARAYICILAR = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe",
    "opera.exe", "vivaldi.exe", "yandex.exe", "thorium.exe",
}

# UI Automation sabitleri (Windows'un kendi numaralari)
UIA_ControlTypePropertyId = 30003
UIA_ValueValuePropertyId = 30045
UIA_EditControlTypeId = 50004
TreeScope_Descendants = 4

ARDISIK_HATA_SINIRI = 5   # bu kadar ust uste hata olursa ozelligi kapat


class AdresOkuyucu:
    def __init__(self, acik=True):
        self.acik = acik
        self._uia = None
        self._kosul = None
        self._hazirlandi = False
        self._hata_sayaci = 0
        self.calisiyor = False   # disaridan bakip durumu ogrenmek icin

    def _hazirla(self):
        """UI Automation servisini ilk kullanimda baslatir (~250 ms, tek sefer)."""
        if self._hazirlandi:
            return self._uia is not None
        self._hazirlandi = True
        try:
            import comtypes.client
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as U
            self._uia = comtypes.client.CreateObject(
                U.CUIAutomation, interface=U.IUIAutomation)
            self._kosul = self._uia.CreatePropertyCondition(
                UIA_ControlTypePropertyId, UIA_EditControlTypeId)
            self.calisiyor = True
            return True
        except Exception:
            self._uia = None
            self.calisiyor = False
            return False

    def tarayici_mi(self, exe):
        return exe.lower() in TARAYICILAR

    def oku(self, hwnd):
        """
        Pencerenin adres cubugundaki adresi dondurur.
        Okunamazsa bos metin ("") doner -- program yine de calismaya devam eder.
        """
        if not self.acik:
            return ""
        if not self._hazirla():
            return ""
        try:
            eleman = self._uia.ElementFromHandle(hwnd)
            if not eleman:
                return ""
            kutu = eleman.FindFirst(TreeScope_Descendants, self._kosul)
            if not kutu:
                return ""
            deger = kutu.GetCurrentPropertyValue(UIA_ValueValuePropertyId)
            self._hata_sayaci = 0
            return temizle(deger)
        except Exception:
            self._hata_sayaci += 1
            if self._hata_sayaci >= ARDISIK_HATA_SINIRI:
                self.acik = False        # surekli hata veriyorsa vazgec
                self.calisiyor = False
            return ""


def temizle(adres):
    """
    Adresi sadelestirir:
      - basindaki https:// ve www. atilir (yer kaplamasin)
      - arama kutusuna yazilmis duz metinler (adres olmayanlar) elenir
      - cok uzun adresler kisaltilir
    """
    if not adres:
        return ""
    a = str(adres).strip()
    if not a:
        return ""
    # Kullanici adres cubuguna arama yazmissa bu bir adres degildir
    if " " in a and "://" not in a:
        return ""
    for on_ek in ("https://", "http://"):
        if a.lower().startswith(on_ek):
            a = a[len(on_ek):]
            break
    if a.lower().startswith("www."):
        a = a[4:]
    # Nokta icermeyen sey adres olamaz (localhost haric)
    alan = a.split("/")[0].split("?")[0]
    if "." not in alan and not alan.lower().startswith("localhost"):
        return ""
    return a[:300]


def alan_adi(adres):
    """'youtube.com/watch?v=abc' -> 'youtube.com'"""
    if not adres:
        return ""
    return adres.split("/")[0].split("?")[0].split(":")[0]
