# -*- coding: utf-8 -*-
"""
takip.py -- Uygulamanin kalbi. Arka planda surekli calisir.

Her 2 saniyede bir sunlari yapar:
  1. Ekrandaki butun pencereleri, en usttekinden en alttakine dogru listeler.
  2. Her pencerenin ne kadarinin gorundugunu hesaplar (ustu kapali mi?).
  3. Gecen sureyi uygulama basina biriktirir.
  4. Dakikada bir kez biriken sureleri veritabanina yazar.

Kullanicinin basinda olup olmadigini iki yoldan anlar:
  - Klavye/fareye dokunma zamani (bedava, sistemi hic yormaz)
  - Ekranda goruntu degisiyor mu (sadece klavye sessizken olculur)
Boylece video izlerken "bosta" sayilmaz.
"""
import ctypes
import os
import sys
import time
import threading
import traceback
from datetime import datetime

BURASI = os.path.dirname(os.path.abspath(__file__))
if BURASI not in sys.path:
    sys.path.insert(0, BURASI)

import pencere
import hareket
import adres
import sekme_windows
from zaman import Zaman
from depo import Depo, DURUM_GORUNUR, DURUM_USTU_KAPALI, DURUM_SIMGE

# =====================================================================
#  AYARLAR -- istersen bu sayilari degistirebilirsin
# =====================================================================
VERITABANI = os.path.join(BURASI, "veri.db")
DURDUR_ISARETI = os.path.join(BURASI, "durdur.isaret")

ORNEK_ARALIGI = 2.0        # kac saniyede bir olcum yapilsin
YAZMA_ARALIGI = 60.0       # kac saniyede bir diske yazilsin
GIRDI_SESSIZLIK = 60.0     # klavye/fare bu kadar saniye sessiz kalirsa ekrana bakmaya basla
HAREKET_ARALIGI = 10.0     # ekran hareket kontrolu kac saniyede bir yapilsin
BOSTA_ESIGI = 600.0        # 10 dakika hicbir hareket yoksa "bosta" say
GORUNUR_ESIGI = 5.0        # pencerenin %5'inden azi gorunuyorsa "ustu kapali" say
BASLIK_SINIRI = 180        # pencere basliginin kaydedilecek en fazla karakter sayisi

URL_KAYDET = True          # tarayicidaki sayfa adresi de kaydedilsin mi
URL_ONBELLEK_SINIRI = 400  # adres hafizasinda tutulacak en fazla pencere sayisi

WEB_PORTU = 8777           # tarayicidan bakarken kullanilacak kapi numarasi

# =====================================================================

user32 = ctypes.WinDLL("user32", use_last_error=True)
DESKTOP_SWITCHDESKTOP = 0x0100


def ekran_kilitli_mi():
    """Bilgisayar kilitliyse (veya oturum kapaliysa) True doner."""
    masaustu = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if masaustu:
        user32.CloseDesktop(masaustu)
        return False
    return True


def baslik_temizle(baslik, uygulama_adi):
    """
    Pencere basligini sadelestirir:
      "(36) Video adi - YouTube - Google Chrome"  ->  "Video adi - YouTube"
    Bastaki (36) bildirim sayisi ve sondaki program adi surekli degistigi
    icin cikarilir; yoksa ayni sayfa icin yuzlerce ayri satir olusur.
    """
    b = (baslik or "").strip()
    # Bastaki bildirim sayisini at:  "(36) ..." veya "(2) ..."
    if b.startswith("(") and ")" in b[:8]:
        kapanis = b.index(")")
        if b[1:kapanis].isdigit():
            b = b[kapanis + 1:].strip()
    # Sondaki program adini at:  "... - Google Chrome"
    for son in (" - " + uygulama_adi, " — " + uygulama_adi):
        if uygulama_adi and b.endswith(son) and len(b) > len(son):
            b = b[: -len(son)].strip()
            break
    if not b:
        b = "(basliksiz)"
    return b[:BASLIK_SINIRI]


class Takipci:
    def __init__(self):
        self.depo = Depo(VERITABANI)
        self.zaman = Zaman(VERITABANI, os.path.join(BURASI, 'sekme-eklentisi', 'ayar.json'))
        self.dedektor = hareket.HareketDedektoru()
        self.okuyucu = adres.AdresOkuyucu(acik=URL_KAYDET)
        if URL_KAYDET:
            self.okuyucu._hazirla()
        self.sekme_okuyucu = sekme_windows.SekmeOkuyucu()
        self.sekme_kilit = threading.Lock()
        self.sekme_uyari = threading.Event()
        self.sekme_girdi = []
        self.sekme_sonuc = None
        self.sekme_sira = 0
        self.sekme_islenen = 0
        # hwnd -> (baslik, url, alan). Baslik degismedikce adres yeniden okunmaz.
        self.url_onbellek = {}
        self.url_okuma_sayaci = 0
        self.tampon = {}          # anahtar -> [saniye, aktif]
        self.gun_tamponu = {}     # gun -> [acik, etkin, bosta]
        self.kilit = threading.Lock()
        self.calisiyor = True
        threading.Thread(target=self._sekme_dongusu, daemon=True).start()

        simdi = time.monotonic()
        self.son_tik = simdi
        self.son_yazma = simdi
        self.son_hareket_kontrolu = 0.0
        self.son_etkinlik = simdi     # kullanicinin en son "var" oldugu an
        self.son_temizlik = simdi

        # Arayuzun gosterecegi anlik durum
        self.durum_bilgisi = {"bosta": False, "kilitli": False,
                              "pencere_sayisi": 0, "son_olcum": "",
                              "url_okuma": False, "url_okuma_sayisi": 0}

    # ---------------- olcum dongusu ----------------
    def dongu(self):
        while self.calisiyor:
            try:
                self._bir_tik()
                if os.path.exists(DURDUR_ISARETI):
                    os.remove(DURDUR_ISARETI)
                    self.calisiyor = False
            except Exception as hata:
                self._hata_yaz(hata)
            time.sleep(ORNEK_ARALIGI)

    def _sekme_dongusu(self):
        # Tarayıcının erişilebilirlik ağacı takılırsa ana süre sayacı durmasın.
        try:
            import comtypes
            comtypes.CoInitialize()
            while self.calisiyor:
                self.sekme_uyari.wait(2)
                self.sekme_uyari.clear()
                with self.sekme_kilit:
                    windows = self.sekme_girdi
                    sira = self.sekme_sira
                if not windows:
                    continue
                tabs, checked = self.sekme_okuyucu.tara(windows)
                with self.sekme_kilit:
                    self.sekme_sonuc = (sira, tabs, checked)
        except Exception as hata:
            self._hata_yaz(hata)
        finally:
            try:
                comtypes.CoUninitialize()
            except Exception:
                pass

    def _bir_tik(self):
        simdi = time.monotonic()
        gecen = simdi - self.son_tik
        self.son_tik = simdi

        # Bilgisayar uyudu / islem donduysa aradaki sureyi kimseye yazma
        if gecen <= 0 or gecen > ORNEK_ARALIGI * 4:
            self.dedektor.sifirla()
            self.son_etkinlik = simdi
            return

        zaman = datetime.now()
        gun = zaman.strftime("%Y-%m-%d")
        saat = zaman.hour

        kilitli = ekran_kilitli_mi()
        if kilitli:
            bosta = True
            self.dedektor.sifirla()
        else:
            bosta = self._bosta_mi(simdi)

        # Gunluk ozet her halukarda islenir
        ozet = self.gun_tamponu.setdefault(gun, [0.0, 0.0, 0.0])
        ozet[0] += gecen
        if bosta:
            ozet[2] += gecen
        else:
            ozet[1] += gecen

        pencere_sayisi = self._pencereleri_isle(gun, saat, gecen, bosta, kilitli)

        self.durum_bilgisi = {
            "bosta": bosta, "kilitli": kilitli,
            "pencere_sayisi": pencere_sayisi,
            "son_olcum": zaman.strftime("%H:%M:%S"),
            "url_okuma": self.okuyucu.calisiyor,
            "url_okuma_sayisi": self.url_okuma_sayaci,
            "sekme_baglantisi": self.zaman.status(),
        }

        # Dakikada bir diske yaz
        if simdi - self.son_yazma >= YAZMA_ARALIGI:
            self.diske_yaz()
            self.son_yazma = simdi

        # 10 dakikada bir kapanmis programlarin kayitlarini temizle
        if simdi - self.son_temizlik >= 600:
            pencere.onbellek_temizle()
            self.son_temizlik = simdi

    def _bosta_mi(self, simdi):
        """
        Once klavye/fareye bakar (bedava). Sessizse ekrana bakmaya baslar.
        Ekranda hareket varsa (video vs.) kullanici 'var' sayilir.
        """
        girdi_sessizligi = pencere.bosta_gecen_saniye()

        if girdi_sessizligi < GIRDI_SESSIZLIK:
            self.son_etkinlik = simdi
            self.dedektor.sifirla()
            return False

        # Klavye sessiz -> ekranda hareket var mi diye bak
        if simdi - self.son_hareket_kontrolu >= HAREKET_ARALIGI:
            self.son_hareket_kontrolu = simdi
            sonuc = self.dedektor.hareket_var_mi()
            if sonuc is True:
                self.son_etkinlik = simdi

        return (simdi - self.son_etkinlik) >= BOSTA_ESIGI

    def _pencereleri_isle(self, gun, saat, gecen, bosta=False, kilitli=False):
        ekranlar = pencere.ekranlari_getir()
        acik, simge = pencere.pencereleri_getir()

        ustundekiler = []
        gozlem = []
        for p in acik:
            kutu = p["kutu"]
            yuzde = pencere.gorunur_yuzde(kutu, ustundekiler, ekranlar)
            ustundekiler.append(kutu)
            durum = DURUM_GORUNUR if yuzde >= GORUNUR_ESIGI else DURUM_USTU_KAPALI
            aktif = gecen if p["on_planda"] else 0.0
            p['state'] = 'Ekranda görünür' if yuzde >= GORUNUR_ESIGI else 'Arka planda — üstü kapalı veya ekran dışında'
            gozlem.append(p)
            if not bosta:
                self._ekle(gun, saat, p, durum, gecen, aktif)

        for p in simge:
            p['state'] = 'Arka planda — pencere küçültülmüş'
            gozlem.append(p)
            if not bosta:
                self._ekle(gun, saat, p, DURUM_SIMGE, gecen, 0.0)

        self.zaman.observe(gozlem, kilitli, bosta, is_window=pencere.user32.IsWindow)
        # UIA adresi yalnızca seçili sekme için verir. Geçmişte seçilmemiş
        # arka plan sekmelerinin tam adresini uydurmayız.
        with self.sekme_kilit:
            self.sekme_girdi = list(gozlem)
            self.sekme_sira += 1
            sonuc = self.sekme_sonuc
        self.sekme_uyari.set()
        if sonuc and sonuc[0] > self.sekme_islenen:
            self.sekme_islenen = sonuc[0]
            _, tabs, checked = sonuc
            try:
                if checked:
                    selected = {t['hwnd']: t for t in tabs if t['selected']}
                    current = {p['hwnd']: p for p in gozlem}
                    # Okuma ayrı iş parçacığından gelir. Bu arada sekme
                    # değiştiyse eski seçimi yeni adresle eşleştirmeyiz.
                    checked = {hwnd for hwnd in checked
                               if hwnd in current and hwnd in selected
                               and baslik_temizle(current[hwnd]['baslik'], current[hwnd]['ad'])
                                   == baslik_temizle(selected[hwnd]['title'], current[hwnd]['ad'])}
                    tabs = [t for t in tabs if t['hwnd'] in checked]
                    for p in gozlem:
                        if p['hwnd'] in selected:
                            if p['hwnd'] in checked:
                                p['url'], _ = self._adres_al(p)
                self.zaman.observe_native_tabs(tabs, checked, gozlem,
                                               is_window=pencere.user32.IsWindow)
            except Exception as hata:
                self._hata_yaz(hata)

        return len(acik)

    def _adres_al(self, p):
        """
        Pencerenin adres cubugundaki adresi dondurur.
        Adres SADECE pencere basligi degistiginde yeniden okunur; ayni
        sayfada durdugun surece hafizadan verilir, hicbir maliyeti olmaz.
        """
        if not self.okuyucu.acik or not self.okuyucu.tarayici_mi(p["exe"]):
            return "", ""
        tutamac = p["hwnd"]
        onceki = self.url_onbellek.get(tutamac)
        if onceki is not None and onceki[0] == p["baslik"]:
            return onceki[1], onceki[2]

        url = self.okuyucu.oku(tutamac)
        alan = adres.alan_adi(url)
        self.url_okuma_sayaci += 1
        if len(self.url_onbellek) > URL_ONBELLEK_SINIRI:
            self.url_onbellek.clear()
        self.url_onbellek[tutamac] = (p["baslik"], url, alan)
        return url, alan

    def _ekle(self, gun, saat, p, durum, saniye, aktif):
        baslik = baslik_temizle(p["baslik"], p["ad"])
        url, alan = self._adres_al(p)
        anahtar = (gun, saat, p["exe"], p["ad"], baslik, url, alan, durum)
        with self.kilit:
            hucre = self.tampon.get(anahtar)
            if hucre is None:
                self.tampon[anahtar] = [saniye, aktif]
            else:
                hucre[0] += saniye
                hucre[1] += aktif

    # ---------------- diske yazma ----------------
    def diske_yaz(self):
        self.zaman.flush()
        with self.kilit:
            if not self.tampon and not self.gun_tamponu:
                return
            satirlar = [(g, s, e, a, b, u, al, d, v[0], v[1])
                        for (g, s, e, a, b, u, al, d), v in self.tampon.items()]
            gunler = list(self.gun_tamponu.items())
            self.tampon = {}
            self.gun_tamponu = {}
        # Once uygulama satirlari, sonra her gunun ozeti
        if satirlar:
            self.depo.yaz(satirlar, None)
        for gun, (acik, etkin, bosta) in gunler:
            self.depo.yaz([], (gun, acik, etkin, bosta))

    def _hata_yaz(self, hata):
        try:
            with open(os.path.join(BURASI, "hatalar.log"), "a",
                      encoding="utf-8") as dosya:
                dosya.write("%s  %r\n%s\n" % (
                    datetime.now().isoformat(" ", "seconds"),
                    hata,
                    traceback.format_exc(),
                ))
        except Exception:
            pass

    def kapat(self):
        self.calisiyor = False
        self.sekme_uyari.set()
        try:
            self.diske_yaz()
        finally:
            self.zaman.close()
            self.depo.kapat()


def tek_kopya_mi():
    """
    Ayni anda iki takip programi calismasin diye Windows'a bir isaret birakir
    (mutex = 'bu is zaten yapiliyor' bayragi). Ikinci kopya acilirsa False doner.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW(None, False, "Global\\EkranTakip_TekKopya")
    ERROR_ALREADY_EXISTS = 183
    return ctypes.get_last_error() != ERROR_ALREADY_EXISTS


def main():
    if not tek_kopya_mi():
        return   # zaten calisiyor, sessizce cik

    # Önceki kapanıştan kalmış işaret yeni açılışı hemen durdurmasın.
    if os.path.exists(DURDUR_ISARETI):
        os.remove(DURDUR_ISARETI)

    takipci = Takipci()

    # Web arayuzunu ayri bir is parcaciginda baslat (cok hafif, stdlib)
    def sunucuyu_calistir():
        try:
            import arayuz
            arayuz.baslat(takipci, WEB_PORTU)
        except Exception as hata:
            takipci._hata_yaz(hata)

    sunucu_ip = threading.Thread(target=sunucuyu_calistir, daemon=True)
    sunucu_ip.start()

    try:
        takipci.dongu()
    except KeyboardInterrupt:
        pass
    finally:
        takipci.kapat()


def _calisma_kaydi(mesaj):
    try:
        with open(os.path.join(BURASI, "calisma.log"), "a",
                  encoding="utf-8") as dosya:
            dosya.write("%s  %s\n" % (
                datetime.now().isoformat(" ", "seconds"), mesaj))
    except Exception:
        pass


if __name__ == "__main__":
    _calisma_kaydi("BASLADI pid=%s" % os.getpid())
    try:
        main()
    except BaseException as hata:
        try:
            with open(os.path.join(BURASI, "hatalar.log"), "a",
                      encoding="utf-8") as dosya:
                dosya.write("%s  YAKALANMAYAN HATA: %r\n%s\n" % (
                    datetime.now().isoformat(" ", "seconds"),
                    hata,
                    traceback.format_exc(),
                ))
        except Exception:
            pass
        _calisma_kaydi("BEKLENMEDIK KAPANMA: %r" % hata)
        raise
    else:
        _calisma_kaydi("NORMAL KAPANMA")
