"""Yerel rapor ekranı için şifre ve geçici oturum yönetimi."""

import hashlib
import json
import os
import secrets
import threading
import time


class Kimlik:
    def __init__(self, dosya):
        self.dosya = dosya
        self.kilit = threading.RLock()
        self.oturumlar = {}
        self.hatalar = 0
        self.engel_sonu = 0.0
        self.kayit = None
        if os.path.exists(dosya):
            with open(dosya, encoding="utf-8") as kaynak:
                self.kayit = json.load(kaynak)
            if (self.kayit.get("version") != 1
                    or not isinstance(self.kayit.get("salt"), str)
                    or not isinstance(self.kayit.get("hash"), str)):
                raise ValueError("Şifre dosyası okunamadı; güvenlik için yeni kurulum başlatılmadı")

    def kurulu_mu(self):
        with self.kilit:
            return self.kayit is not None

    def kur(self, sifre):
        if not isinstance(sifre, str) or not sifre:
            raise ValueError("Şifre boş olamaz")
        with self.kilit:
            if self.kayit is not None or os.path.exists(self.dosya):
                raise ValueError("Şifre zaten oluşturulmuş")
            salt = secrets.token_bytes(16)
            ozet = hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), salt, 600_000)
            kayit = {"version": 1, "salt": salt.hex(), "hash": ozet.hex()}
            # Başka bir işlem aynı anda oluşturursa üzerine yazma.
            with open(self.dosya, "x", encoding="utf-8") as hedef:
                json.dump(kayit, hedef)
            self.kayit = kayit
            return self._oturum_ac()

    def gir(self, sifre):
        if not isinstance(sifre, str):
            raise ValueError("Şifre geçersiz")
        with self.kilit:
            if self.kayit is None:
                return None
            if time.monotonic() < self.engel_sonu:
                raise ValueError("Çok fazla yanlış deneme. Bir dakika sonra tekrar deneyin")
            try:
                salt = bytes.fromhex(self.kayit["salt"])
                beklenen = bytes.fromhex(self.kayit["hash"])
            except ValueError:
                raise ValueError("Şifre dosyası bozuk")
            gelen = hashlib.pbkdf2_hmac("sha256", str(sifre).encode("utf-8"), salt, 600_000)
            if not secrets.compare_digest(gelen, beklenen):
                self.hatalar += 1
                if self.hatalar >= 5:
                    self.engel_sonu = time.monotonic() + 60
                    self.hatalar = 0
                return None
            self.hatalar = 0
            self.engel_sonu = 0.0
            return self._oturum_ac()

    def _oturum_ac(self):
        simdi = time.monotonic()
        self.oturumlar = {k: v for k, v in self.oturumlar.items() if v > simdi}
        if len(self.oturumlar) >= 128:
            en_eski = min(self.oturumlar, key=self.oturumlar.get)
            del self.oturumlar[en_eski]
        anahtar = secrets.token_urlsafe(32)
        self.oturumlar[anahtar] = simdi + 12 * 3600
        return anahtar

    def gecerli_mi(self, anahtar):
        with self.kilit:
            if not anahtar:
                return False
            son = self.oturumlar.get(anahtar)
            if son is None:
                return False
            if son <= time.monotonic():
                del self.oturumlar[anahtar]
                return False
            return True

    def cik(self, anahtar):
        with self.kilit:
            self.oturumlar.pop(anahtar, None)
