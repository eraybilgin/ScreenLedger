"""Şifre ve oturum sınırları; gerçek kullanıcı dosyalarına dokunmaz."""
import tempfile
import unittest
from pathlib import Path

from kimlik import Kimlik


class KimlikTest(unittest.TestCase):
    def test_ilk_kurulum_ve_yeniden_baslatma(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = str(Path(klasor) / 'kimlik.json')
            kimlik = Kimlik(yol)
            self.assertFalse(kimlik.kurulu_mu())
            with self.assertRaises(ValueError):
                kimlik.kur('')
            anahtar = kimlik.kur('kisa')
            self.assertTrue(kimlik.gecerli_mi(anahtar))
            with self.assertRaises(ValueError):
                kimlik.kur('ikinci-bir-deneme')
            yeni = Kimlik(yol)
            self.assertTrue(yeni.kurulu_mu())
            self.assertFalse(yeni.gecerli_mi(anahtar))
            self.assertIsNone(yeni.gir('yanlis'))
            oturum = yeni.gir('kisa')
            self.assertTrue(yeni.gecerli_mi(oturum))
            yeni.cik(oturum)
            self.assertFalse(yeni.gecerli_mi(oturum))

    def test_uzun_sifre_kisitlanmaz(self):
        with tempfile.TemporaryDirectory() as klasor:
            kimlik = Kimlik(str(Path(klasor) / 'kimlik.json'))
            sifre = 'ş' * 257
            kimlik.kur(sifre)
            self.assertIsNotNone(kimlik.gir(sifre))

    def test_bozuk_dosya_yeni_kuruluma_donmez(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor) / 'kimlik.json'
            yol.write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                Kimlik(str(yol))
