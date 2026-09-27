# -*- coding: utf-8 -*-
"""
kur.py -- Kurulum yardimcisi.

Yaptiklari:
  1. "baslat.vbs" dosyasini olusturur. Bu dosya, takip programini
     HIC PENCERE ACMADAN, sessizce baslatir.
  2. Windows'un "Baslangic" klasorune bir kisayol koyar. Boylece
     bilgisayar her acildiginda takip kendiliginden calismaya baslar.

Kaldirmak icin:  kaldir.bat
"""
import os
import subprocess
import sys
import time
import venv

BURASI = os.path.dirname(os.path.abspath(__file__))
BASLANGIC = os.path.join(os.environ["APPDATA"],
                         r"Microsoft\Windows\Start Menu\Programs\Startup")
BASLANGIC_DOSYASI = os.path.join(BASLANGIC, "EkranTakip.vbs")
BASLAT_VBS = os.path.join(BURASI, "baslat.vbs")
ORTAM = os.path.join(BURASI, ".venv")
ORTAM_PYTHON = os.path.join(ORTAM, "Scripts", "python.exe")
ORTAM_PYTHONW = os.path.join(ORTAM, "Scripts", "pythonw.exe")


def pythonw_yolu():
    """
    pythonw.exe = Python'un 'siyah komut penceresi acmayan' surumu.
    Normal python.exe her acildiginda ekranda bir konsol penceresi cikar;
    pythonw.exe cikarmaz. Arka planda calisan program icin dogrusu budur.
    """
    if os.path.isfile(ORTAM_PYTHONW):
        return ORTAM_PYTHONW
    aday = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return aday if os.path.isfile(aday) else sys.executable


def bagimliliklari_kur():
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 veya üzeri gerekli")
    if not os.path.isfile(ORTAM_PYTHON):
        print("  Program için ayrı çalışma ortamı hazırlanıyor...")
        venv.EnvBuilder(with_pip=True).create(ORTAM)
    print("  Gereken parçalar kuruluyor...")
    subprocess.check_call([ORTAM_PYTHON, "-m", "pip", "install", "-r",
                           os.path.join(BURASI, "requirements.txt")])


def vbs_yaz():
    icerik = (
        "' Ekran Takip - bu bilgisayarda kurulum sırasında oluşturulur\r\n"
        'Set kabuk = CreateObject("WScript.Shell")\r\n'
        'Set dosyaSistemi = CreateObject("Scripting.FileSystemObject")\r\n'
        'kabuk.CurrentDirectory = "%s"\r\n'
        'logYolu = "%s"\r\n'
        'komut = """%s"" ""%s"""\r\n'
        'On Error Resume Next\r\n'
        'Set kayit = dosyaSistemi.OpenTextFile(logYolu, 8, True, 0)\r\n'
        'kayit.WriteLine Now & "  START"\r\n'
        'kayit.Close\r\n'
        'cikisKodu = kabuk.Run(komut, 0, True)\r\n'
        'hataNo = Err.Number\r\n'
        'hataMetni = Err.Description\r\n'
        'Set kayit = dosyaSistemi.OpenTextFile(logYolu, 8, True, 0)\r\n'
        'If hataNo <> 0 Then\r\n'
        '  kayit.WriteLine Now & "  LAUNCH_ERROR code=" & hataNo & " message=" & hataMetni\r\n'
        'Else\r\n'
        '  kayit.WriteLine Now & "  PROCESS_EXIT code=" & cikisKodu\r\n'
        'End If\r\n'
        'kayit.Close\r\n'
        % (BURASI, os.path.join(BURASI, "baslatma.log"), pythonw_yolu(),
           os.path.join(BURASI, "takip.py"))
    )
    with open(BASLAT_VBS, "w", encoding="utf-16") as dosya:
        dosya.write(icerik)
    return BASLAT_VBS


def baslangica_ekle():
    icerik = (
        '\' Ekran Takip - bilgisayar acilinca calisir\r\n'
        'CreateObject("WScript.Shell").Run """%s""", 0, False\r\n'
        % BASLAT_VBS
    )
    os.makedirs(BASLANGIC, exist_ok=True)
    with open(BASLANGIC_DOSYASI, "w", encoding="utf-16") as dosya:
        dosya.write(icerik)
    return BASLANGIC_DOSYASI


def baslangictan_cikar():
    if os.path.isfile(BASLANGIC_DOSYASI):
        os.remove(BASLANGIC_DOSYASI)
        return True
    return False


def simdi_baslat():
    subprocess.Popen(["wscript.exe", BASLAT_VBS], cwd=BURASI)


def kur():
    print("Ekran Takip kuruluyor...\n")
    bagimliliklari_kur()
    print("  Python        :", pythonw_yolu())
    print("  Klasor        :", BURASI)
    print("  Baslatici     :", vbs_yaz())
    print("  Otomatik acma :", baslangica_ekle())
    simdi_baslat()
    print("\nTAMAM. Takip su anda calisiyor ve bilgisayar her acildiginda")
    print("kendiliginden baslayacak.")
    print("\nRaporu gormek icin tarayicida:  http://localhost:8777")


def kaldir():
    print("Ekran Takip kaldiriliyor...\n")
    if baslangictan_cikar():
        print("  Otomatik acilma kapatildi.")
    else:
        print("  Otomatik acilma zaten kapaliydi.")
    # Yalnızca bu klasördeki uygulamayı bul; kendi verisini yazıp kapanmasını iste.
    cevre = dict(os.environ, EKRAN_TAKIP_DOSYA=os.path.join(BURASI, "takip.py"))
    komut = ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
             "Where-Object { $_.CommandLine -and "
             "$_.CommandLine.Contains($env:EKRAN_TAKIP_DOSYA) } | "
             "ForEach-Object { $_.ProcessId }"]
    def surecler():
        sonuc = subprocess.run(komut, capture_output=True, text=True, env=cevre)
        if sonuc.returncode:
            raise RuntimeError("Çalışan program denetlenemedi: " + sonuc.stderr.strip())
        return sonuc.stdout.strip()

    if surecler():
        with open(os.path.join(BURASI, "durdur.isaret"), "w", encoding="ascii") as isaret:
            isaret.write("dur\n")
        son = time.monotonic() + 15
        while surecler() and time.monotonic() < son:
            time.sleep(0.5)
        if surecler():
            print("  UYARI: Çalışan program güvenle kapatılamadı; zorla kapatılmadı.")
        else:
            print("  Çalışan program kayıtlarını yazıp kapandı.")
    else:
        print("  Çalışan program yoktu.")
    print("\nNOT: Toplanan veriler 'veri.db' dosyasinda duruyor, silinmedi.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kaldir":
        kaldir()
    else:
        kur()
    input("\nKapatmak icin Enter'a bas...")
