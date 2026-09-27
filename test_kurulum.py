"""Genel kurulum dosyaları kişisel yolları ve verileri yayımlamaz."""
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import kur


KOK = Path(__file__).resolve().parent


class KurulumTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('git'), 'Git kurulu değil')
    def test_gercek_klasorde_paylasilacaklar(self):
        with tempfile.TemporaryDirectory() as klasor:
            git_yolu = Path(klasor) / '.git'
            subprocess.run(['git', 'init', '-q', klasor], check=True)
            sonuc = subprocess.run(['git', f'--git-dir={git_yolu}',
                                    f'--work-tree={KOK}', 'ls-files',
                                    '--others', '--exclude-standard'],
                                   check=True, capture_output=True, text=True)
            dosyalar = set(sonuc.stdout.splitlines())
            self.assertIn('README.md', dosyalar)
            self.assertIn('takip.py', dosyalar)
            self.assertIn('sekme-eklentisi/manifest.json', dosyalar)
            for ad in dosyalar:
                self.assertFalse(ad.endswith(('.db', '.db-wal', '.db-shm', '.log', '.vbs')),
                                 ad)
                self.assertNotIn('yedek-', ad)
                self.assertNotIn('sekme-eklentisi/ayar.json', ad)
                self.assertNotIn('.venv/', ad)

    def test_baslatici_yolu_kuruldugu_yerden_uretilir(self):
        with tempfile.TemporaryDirectory() as klasor:
            hedef = Path(klasor) / 'baslat.vbs'
            with patch.object(kur, 'BURASI', klasor), \
                 patch.object(kur, 'BASLAT_VBS', str(hedef)), \
                 patch.object(kur, 'pythonw_yolu', return_value=r'C:\Python\pythonw.exe'):
                kur.vbs_yaz()
            metin = hedef.read_text(encoding='utf-16')
            self.assertIn(klasor, metin)
            self.assertIn(r'C:\Python\pythonw.exe', metin)
            self.assertIn('PROCESS_EXIT', metin)

    def test_kisisel_dosyalar_paylasim_disi(self):
        with tempfile.TemporaryDirectory() as klasor:
            yol = Path(klasor)
            (yol / '.gitignore').write_bytes((KOK / '.gitignore').read_bytes())
            subprocess.run(['git', 'init', '-q'], cwd=yol, check=True)
            ozel = ['veri.db', 'veri.db-wal', 'veri-sekme-oncesi.db',
                     'hatalar.log', 'baslat.vbs', 'kimlik.json',
                     'sekme-eklentisi/ayar.json', 'yedek-20260913/veri.db',
                     '__pycache__/takip.pyc', '.venv/Scripts/python.exe']
            for ad in ozel:
                sonuc = subprocess.run(['git', 'check-ignore', '-q', ad], cwd=yol)
                self.assertEqual(sonuc.returncode, 0, ad)
            for ad in ['README.md', 'takip.py', 'sekme-eklentisi/manifest.json']:
                sonuc = subprocess.run(['git', 'check-ignore', '-q', ad], cwd=yol)
                self.assertEqual(sonuc.returncode, 1, ad)


if __name__ == '__main__':
    unittest.main()
