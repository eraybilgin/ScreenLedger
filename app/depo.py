# -*- coding: utf-8 -*-
"""
depo.py -- Olculen surelerin kaydedildigi yer.

Veritabani olarak SQLite kullanilir: tek bir dosyadan ibaret, kurulum
istemeyen kucuk bir veritabani. Python ile birlikte hazir gelir.
Butun veri "veri.db" adli tek dosyada durur.

Disk yormamak icin her 2 saniyede bir DEGIL, biriktirilip dakikada
bir kez yazilir.

Butun sorgular TARIH ARALIGI ile calisir: tek gun icin baslangic ve
bitis ayni tarih verilir; bu hafta / bu ay / son 3 ay icin aralik genisler.
"""
import os
import sqlite3
import threading

# Bir pencerenin icinde bulunabilecegi durumlar
DURUM_GORUNUR = "gorunur"          # ekranda ve ustu acik
DURUM_USTU_KAPALI = "ustu_kapali"  # ekranda ama baska pencerelerin altinda
DURUM_SIMGE = "simge"              # gorev cubuguna kucultulmus

_SEMA = """
CREATE TABLE IF NOT EXISTS kayit (
    gun          TEXT    NOT NULL,
    saat         INTEGER NOT NULL,
    exe          TEXT    NOT NULL,
    ad           TEXT    NOT NULL,
    baslik       TEXT    NOT NULL,
    url          TEXT    NOT NULL DEFAULT '',
    alan         TEXT    NOT NULL DEFAULT '',
    durum        TEXT    NOT NULL,
    saniye       REAL    NOT NULL DEFAULT 0,
    aktif_saniye REAL    NOT NULL DEFAULT 0,
    PRIMARY KEY (gun, saat, exe, baslik, url, durum)
);
CREATE INDEX IF NOT EXISTS kayit_gun  ON kayit (gun);
CREATE INDEX IF NOT EXISTS kayit_alan ON kayit (alan);

CREATE TABLE IF NOT EXISTS ozet (
    gun           TEXT PRIMARY KEY,
    acik_saniye   REAL NOT NULL DEFAULT 0,
    etkin_saniye  REAL NOT NULL DEFAULT 0,
    bosta_saniye  REAL NOT NULL DEFAULT 0
);
"""


class Depo:
    def __init__(self, dosya):
        self.dosya = dosya
        klasor = os.path.dirname(os.path.abspath(dosya))
        if klasor and not os.path.isdir(klasor):
            os.makedirs(klasor, exist_ok=True)
        self._kilit = threading.Lock()
        self._baglanti = sqlite3.connect(dosya, check_same_thread=False)
        self._baglanti.row_factory = sqlite3.Row
        # WAL = yazma sirasinda okumayi engellemeyen guvenli kayit yontemi
        self._baglanti.execute("PRAGMA journal_mode=WAL")
        self._baglanti.execute("PRAGMA synchronous=NORMAL")
        self._gucellestir()
        self._baglanti.executescript(_SEMA)
        self._baglanti.commit()

    def _gucellestir(self):
        """
        Eski surumden gelen veritabanina 'url' ve 'alan' sutunlarini ekler.
        Eski kayitlar silinmez, adresleri bos kalir.
        """
        var_mi = self._baglanti.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='kayit'"
        ).fetchone()
        if not var_mi:
            return
        sutunlar = [s[1] for s in
                    self._baglanti.execute("PRAGMA table_info(kayit)").fetchall()]
        if "url" in sutunlar:
            return
        # Tabloyu yeniden kur ve eski veriyi tasi
        self._baglanti.executescript("""
            ALTER TABLE kayit RENAME TO kayit_eski;
            CREATE TABLE kayit (
                gun TEXT NOT NULL, saat INTEGER NOT NULL, exe TEXT NOT NULL,
                ad TEXT NOT NULL, baslik TEXT NOT NULL,
                url TEXT NOT NULL DEFAULT '', alan TEXT NOT NULL DEFAULT '',
                durum TEXT NOT NULL, saniye REAL NOT NULL DEFAULT 0,
                aktif_saniye REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (gun, saat, exe, baslik, url, durum)
            );
            INSERT INTO kayit (gun, saat, exe, ad, baslik, url, alan,
                               durum, saniye, aktif_saniye)
                SELECT gun, saat, exe, ad, baslik, '', '',
                       durum, saniye, aktif_saniye FROM kayit_eski;
            DROP TABLE kayit_eski;
        """)
        self._baglanti.commit()

    # ---------------- yazma ----------------
    def yaz(self, satirlar, ozet_satiri):
        """
        satirlar: (gun,saat,exe,ad,baslik,url,alan,durum,saniye,aktif) listesi
        ozet_satiri: (gun, acik_saniye, etkin_saniye, bosta_saniye)
        Ayni anahtar zaten varsa sureler USTUNE EKLENIR.
        """
        with self._kilit:
            if satirlar:
                self._baglanti.executemany("""
                    INSERT INTO kayit (gun, saat, exe, ad, baslik, url, alan,
                                       durum, saniye, aktif_saniye)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (gun, saat, exe, baslik, url, durum) DO UPDATE SET
                        saniye       = saniye       + excluded.saniye,
                        aktif_saniye = aktif_saniye + excluded.aktif_saniye,
                        ad           = excluded.ad
                """, satirlar)
            if ozet_satiri:
                self._baglanti.execute("""
                    INSERT INTO ozet (gun, acik_saniye, etkin_saniye, bosta_saniye)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (gun) DO UPDATE SET
                        acik_saniye  = acik_saniye  + excluded.acik_saniye,
                        etkin_saniye = etkin_saniye + excluded.etkin_saniye,
                        bosta_saniye = bosta_saniye + excluded.bosta_saniye
                """, ozet_satiri)
            self._baglanti.commit()

    # ---------------- okuma ----------------
    def _sorgu(self, sql, parametreler=()):
        with self._kilit:
            return [dict(s) for s in
                    self._baglanti.execute(sql, parametreler).fetchall()]

    def ilk_gun(self):
        s = self._sorgu("SELECT MIN(gun) AS g FROM ozet")
        return s[0]["g"] if s and s[0]["g"] else None

    def gunler(self, adet=400):
        s = self._sorgu(
            "SELECT gun FROM ozet ORDER BY gun DESC LIMIT ?", (adet,))
        return [x["gun"] for x in s]

    def ozet(self, bas, bit):
        """Secilen tarih araliginin toplam sureleri."""
        s = self._sorgu("""
            SELECT COALESCE(SUM(acik_saniye), 0)  AS acik_saniye,
                   COALESCE(SUM(etkin_saniye), 0) AS etkin_saniye,
                   COALESCE(SUM(bosta_saniye), 0) AS bosta_saniye,
                   COUNT(*) AS gun_sayisi
            FROM ozet WHERE gun BETWEEN ? AND ?
        """, (bas, bit))
        return s[0]

    def uygulamalar(self, bas, bit, adet=200):
        """Aralikta en cok kullanilan uygulamalar."""
        return self._sorgu("""
            SELECT exe, MAX(ad) AS ad,
                SUM(CASE WHEN durum='gorunur'     THEN saniye ELSE 0 END) AS gorunur,
                SUM(CASE WHEN durum='ustu_kapali' THEN saniye ELSE 0 END) AS ustu_kapali,
                SUM(CASE WHEN durum='simge'       THEN saniye ELSE 0 END) AS simge,
                SUM(aktif_saniye) AS aktif,
                COUNT(DISTINCT gun) AS gun_sayisi
            FROM kayit WHERE gun BETWEEN ? AND ?
            GROUP BY exe
            ORDER BY aktif DESC, gorunur DESC
            LIMIT ?
        """, (bas, bit, adet))

    def sayfalar(self, bas, bit, exe=None, adet=100):
        """Aralikta en cok bakilan sayfalar/pencereler (baslik + adres)."""
        kosul = "gun BETWEEN ? AND ?"
        parametreler = [bas, bit]
        if exe:
            kosul += " AND exe = ?"
            parametreler.append(exe)
        parametreler.append(adet)
        return self._sorgu("""
            SELECT baslik, MAX(url) AS url, MAX(alan) AS alan,
                   MAX(exe) AS exe, MAX(ad) AS ad,
                SUM(CASE WHEN durum='gorunur'     THEN saniye ELSE 0 END) AS gorunur,
                SUM(CASE WHEN durum='ustu_kapali' THEN saniye ELSE 0 END) AS ustu_kapali,
                SUM(CASE WHEN durum='simge'       THEN saniye ELSE 0 END) AS simge,
                SUM(aktif_saniye) AS aktif,
                COUNT(DISTINCT gun) AS gun_sayisi
            FROM kayit WHERE """ + kosul + """
            GROUP BY exe, baslik
            ORDER BY aktif DESC, gorunur DESC
            LIMIT ?
        """, parametreler)

    def alanlar(self, bas, bit, adet=60):
        """Aralikta en cok vakit gecirilen internet siteleri (youtube.com gibi)."""
        return self._sorgu("""
            SELECT alan,
                SUM(CASE WHEN durum='gorunur' THEN saniye ELSE 0 END) AS gorunur,
                SUM(aktif_saniye) AS aktif,
                COUNT(DISTINCT baslik) AS sayfa_sayisi,
                COUNT(DISTINCT gun) AS gun_sayisi
            FROM kayit
            WHERE gun BETWEEN ? AND ? AND alan <> ''
            GROUP BY alan
            ORDER BY aktif DESC
            LIMIT ?
        """, (bas, bit, adet))

    def gunluk_seri(self, bas, bit):
        """Aralik icindeki her gunun toplami -- grafik cizmek icin."""
        return self._sorgu("""
            SELECT gun, acik_saniye, etkin_saniye, bosta_saniye
            FROM ozet WHERE gun BETWEEN ? AND ?
            ORDER BY gun
        """, (bas, bit))

    def veritabani_boyutu(self):
        try:
            toplam = os.path.getsize(self.dosya)
            for ek in ("-wal", "-shm"):
                if os.path.exists(self.dosya + ek):
                    toplam += os.path.getsize(self.dosya + ek)
            return toplam
        except OSError:
            return 0

    def satir_sayisi(self):
        s = self._sorgu("SELECT COUNT(*) AS n FROM kayit")
        return s[0]["n"] if s else 0

    def kapat(self):
        with self._kilit:
            self._baglanti.commit()
            self._baglanti.close()
