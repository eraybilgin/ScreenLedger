# -*- coding: utf-8 -*-
"""
pencere.py -- Windows'a "su an ekranda ne var?" diye soran katman.

Buradaki her fonksiyon, Windows'un kendi hazir kod kutuphanelerine
(user32.dll, gdi32.dll, kernel32.dll) soru sorar. Disaridan hicbir
ek kutuphane kullanmaz, bu yuzden cok hafiftir.
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")
version = ctypes.WinDLL("version")

user32.SetProcessDPIAware()

# ---- Windows sabitleri (Windows'un kendi numaralari) ----
GW_HWNDNEXT = 2            # "bir alttaki pencere"
GWL_EXSTYLE = -20          # "pencerenin ek ozellikleri"
WS_EX_TOOLWINDOW = 0x80    # "arac penceresi, gorev cubugunda gorunmez"
DWMWA_CLOAKED = 14         # "pencere gizlenmis mi?" sorusu
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


# =====================================================================
#  Kullanicinin klavye/fareye en son ne zaman dokundugu
# =====================================================================
def bosta_gecen_saniye():
    """Klavye veya fareye en son dokunulmasindan bu yana gecen saniye."""
    bilgi = LASTINPUTINFO()
    bilgi.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(bilgi)):
        return 0.0
    simdi = kernel32.GetTickCount()
    fark = (simdi - bilgi.dwTime) & 0xFFFFFFFF   # sayac tasmasina karsi
    return fark / 1000.0


# =====================================================================
#  Monitorler
# =====================================================================
_MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
    ctypes.POINTER(RECT), wintypes.LPARAM)


def ekranlari_getir():
    """Bagli butun monitorlerin ekrandaki koordinatlarini dondurur."""
    sonuc = []

    def geri_cagri(hmon, hdc, lprc, lparam):
        r = lprc.contents
        sonuc.append((r.left, r.top, r.right, r.bottom))
        return True

    user32.EnumDisplayMonitors(0, None, _MONITORENUMPROC(geri_cagri), 0)
    return sonuc


# =====================================================================
#  Surec (calisan program) bilgileri -- bir kez ogrenilir, saklanir
# =====================================================================
_yol_onbellek = {}   # pid -> exe yolu
_ad_onbellek = {}    # exe yolu -> insan okuyabilir ad


def _surec_yolu(pid):
    if pid in _yol_onbellek:
        return _yol_onbellek[pid]
    tutamac = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    yol = ""
    if tutamac:
        try:
            arabellek = ctypes.create_unicode_buffer(1024)
            boyut = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(tutamac, 0, arabellek,
                                                   ctypes.byref(boyut)):
                yol = arabellek.value
        finally:
            kernel32.CloseHandle(tutamac)
    _yol_onbellek[pid] = yol
    return yol


def _dosya_aciklamasi(yol):
    """exe dosyasinin icindeki 'Google Chrome' gibi okunakli adi cikarir."""
    if not yol:
        return ""
    if yol in _ad_onbellek:
        return _ad_onbellek[yol]
    ad = ""
    try:
        boyut = version.GetFileVersionInfoSizeW(yol, None)
        if boyut:
            veri = ctypes.create_string_buffer(boyut)
            if version.GetFileVersionInfoW(yol, 0, boyut, veri):
                isaretci = ctypes.c_void_p()
                uzunluk = wintypes.UINT()
                ok = version.VerQueryValueW(veri, "\\VarFileInfo\\Translation",
                                            ctypes.byref(isaretci),
                                            ctypes.byref(uzunluk))
                if ok and uzunluk.value >= 4:
                    ham = ctypes.cast(
                        isaretci, ctypes.POINTER(ctypes.c_uint16 * 2)).contents
                    anahtar = "\\StringFileInfo\\%04x%04x\\FileDescription" % (
                        ham[0], ham[1])
                    ok2 = version.VerQueryValueW(veri, anahtar,
                                                 ctypes.byref(isaretci),
                                                 ctypes.byref(uzunluk))
                    if ok2 and uzunluk.value:
                        ad = ctypes.wstring_at(isaretci, uzunluk.value)
                        ad = ad.split("\x00")[0].strip()
    except Exception:
        ad = ""
    _ad_onbellek[yol] = ad
    return ad


def surec_bilgisi(pid):
    """(exe_adi, okunakli_ad) ciftini dondurur. Ornek: chrome.exe / Google Chrome"""
    yol = _surec_yolu(pid)
    exe = yol.rsplit("\\", 1)[-1] if yol else "bilinmiyor"
    ad = _dosya_aciklamasi(yol) or exe.replace(".exe", "")
    return exe, ad


def onbellek_temizle():
    """Kapanan programlarin kayitlari birikmesin diye ara ara temizlenir."""
    _yol_onbellek.clear()


# =====================================================================
#  Pencere listesi
# =====================================================================
_ENUMWINDOWSPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND,
                                      wintypes.LPARAM)

# Sayilmamasi gereken sistem pencereleri
_ATLANACAK_SINIFLAR = {
    "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
    "Windows.UI.Core.CoreWindow", "MultitaskingViewFrame",
    "ForegroundStaging", "XamlExplorerHostIslandWindow",
}
_ATLANACAK_EXE = {
    "TextInputHost.exe", "SearchHost.exe", "StartMenuExperienceHost.exe",
    "ShellExperienceHost.exe", "SystemSettingsBroker.exe", "LockApp.exe",
}
# Gercek bir uygulama olmayan, sistemin acilir menu/ipucu pencereleri
_ATLANACAK_BASLIKLAR = {
    "PopupHost", "Program Manager", "Windows Giris Deneyimi",
    "Windows Input Experience", "Jump List", "Baslat", "Start",
}


def _gizli_mi(hwnd):
    deger = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), DWMWA_CLOAKED,
                                 ctypes.byref(deger), ctypes.sizeof(deger))
    return deger.value != 0


def _sinif_adi(hwnd):
    arabellek = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, arabellek, 256)
    return arabellek.value


def _baslik(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    arabellek = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, arabellek, n + 1)
    return arabellek.value


def _gercek_pid(hwnd, pid, exe):
    """
    Windows Magazasi uygulamalari 'ApplicationFrameHost.exe' adiyla gorunur.
    Gercek uygulamayi bulmak icin icindeki alt pencereye bakariz.
    """
    if exe.lower() != "applicationframehost.exe":
        return pid
    bulunan = [pid]

    def geri_cagri(alt, lparam):
        alt_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(alt, ctypes.byref(alt_pid))
        if alt_pid.value != pid:
            bulunan[0] = alt_pid.value
            return False
        return True

    user32.EnumChildWindows(hwnd, _ENUMWINDOWSPROC(geri_cagri), 0)
    return bulunan[0]


def _sayilir_mi(hwnd):
    if not user32.IsWindowVisible(hwnd):
        return False
    if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW:
        return False
    if _sinif_adi(hwnd) in _ATLANACAK_SINIFLAR:
        return False
    if _gizli_mi(hwnd):
        return False
    baslik = _baslik(hwnd)
    if not baslik or baslik in _ATLANACAK_BASLIKLAR:
        return False
    return True


def pencereleri_getir():
    """
    Ekrandaki pencereleri EN USTTEKINDEN EN ALTTAKINE dogru sirali dondurur.
    Bu sira, hangi pencerenin hangisinin ustunu kapattigini bulmak icin sart.
    Donen deger: (acik_pencereler, simge_durumundakiler)
    """
    on_plan = user32.GetForegroundWindow()
    acik, simge = [], []

    hwnd = user32.GetTopWindow(0)
    while hwnd:
        if _sayilir_mi(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            exe, _ = surec_bilgisi(pid.value)
            gercek = _gercek_pid(hwnd, pid.value, exe)
            exe_adi, okunakli = surec_bilgisi(gercek)
            if exe_adi not in _ATLANACAK_EXE:
                kayit = {"hwnd": hwnd, "pid": gercek, "exe": exe_adi,
                         "ad": okunakli, "baslik": _baslik(hwnd),
                         "on_planda": (hwnd == on_plan)}
                if user32.IsIconic(hwnd):
                    simge.append(kayit)
                else:
                    r = RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(r))
                    if r.right > r.left and r.bottom > r.top:
                        kayit["kutu"] = (r.left, r.top, r.right, r.bottom)
                        acik.append(kayit)
        hwnd = user32.GetWindow(hwnd, GW_HWNDNEXT)

    return acik, simge


# =====================================================================
#  "Ustu kapali mi?" hesabi
# =====================================================================
def gorunur_yuzde(kutu, ustundekiler, ekranlar=None):
    """
    Bir pencerenin, ustundeki pencereler tarafindan kapatilmayan alaninin
    yuzdesi. 100 = hic kapanmamis, 0 = tamamen baska pencerelerin altinda.
    """
    toplam = (kutu[2] - kutu[0]) * (kutu[3] - kutu[1])
    if toplam <= 0:
        return 0.0
    if ekranlar is not None:
        # Pencerenin monitör dışında kalan bölümleri görünür sayılmaz.
        gorunen = 0.0
        for e in ekranlar:
            parca = (max(kutu[0],e[0]), max(kutu[1],e[1]), min(kutu[2],e[2]), min(kutu[3],e[3]))
            alan = max(0,parca[2]-parca[0])*max(0,parca[3]-parca[1])
            if alan:
                gorunen += alan*gorunur_yuzde(parca,ustundekiler)/100.0
        return min(100.0, gorunen*100.0/toplam)
    if not ustundekiler:
        return 100.0

    # Sadece gercekten kesisen pencereleri hesaba kat
    engeller = [b for b in ustundekiler
                if b[0] < kutu[2] and b[2] > kutu[0]
                and b[1] < kutu[3] and b[3] > kutu[1]]
    if not engeller:
        return 100.0

    # Kesme cizgileri cikar, olusan kucuk dikdortgenleri tek tek kontrol et
    x_ler = {kutu[0], kutu[2]}
    y_ler = {kutu[1], kutu[3]}
    for b in engeller:
        for x in (b[0], b[2]):
            if kutu[0] < x < kutu[2]:
                x_ler.add(x)
        for y in (b[1], b[3]):
            if kutu[1] < y < kutu[3]:
                y_ler.add(y)
    x_ler = sorted(x_ler)
    y_ler = sorted(y_ler)

    gorunen = 0
    for i in range(len(x_ler) - 1):
        sol, sag = x_ler[i], x_ler[i + 1]
        orta_x = (sol + sag) / 2
        for j in range(len(y_ler) - 1):
            ust, alt = y_ler[j], y_ler[j + 1]
            orta_y = (ust + alt) / 2
            kapali = False
            for b in engeller:
                if b[0] <= orta_x <= b[2] and b[1] <= orta_y <= b[3]:
                    kapali = True
                    break
            if not kapali:
                gorunen += (sag - sol) * (alt - ust)
    return gorunen * 100.0 / toplam


def hangi_ekran(kutu, ekranlar):
    """Pencerenin merkezi hangi monitorde duruyor? (1, 2, ...)"""
    orta_x = (kutu[0] + kutu[2]) // 2
    orta_y = (kutu[1] + kutu[3]) // 2
    for sira, e in enumerate(ekranlar, 1):
        if e[0] <= orta_x < e[2] and e[1] <= orta_y < e[3]:
            return sira
    return 0
