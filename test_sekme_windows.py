import os
import tempfile
import unittest
from datetime import datetime

from depo import Depo
from sekme_windows import SekmeOkuyucu, baslik_ayikla
from zaman import Zaman


class FakeElement:
    def __init__(self, name, runtime, selected):
        self.CurrentName = name
        self.runtime = runtime
        self.selected = selected

    def GetRuntimeId(self):
        return self.runtime

    def GetCurrentPropertyValue(self, property_id):
        return self.selected


class FakeItems:
    def __init__(self, items):
        self.items = items
        self.Length = len(items)

    def GetElement(self, index):
        return self.items[index]


class FakeRoot:
    def __init__(self, items):
        self.items = FakeItems(items)

    def FindAll(self, scope, condition):
        return self.items


class FakeUia:
    def __init__(self, items):
        self.root = FakeRoot(items)

    def ElementFromHandle(self, hwnd):
        return self.root


class NativeTabTests(unittest.TestCase):
    def test_only_browser_native_tabs(self):
        reader = SekmeOkuyucu()
        reader.uia = FakeUia([
            FakeElement('Elements', [42, 999, 4, 1], True),
            FakeElement('Video - Bellek kullanımı - 50 MB', [42, 123, 4, 2], True),
            FakeElement('Belge - Bellek kullanımı - 40 MB', [42, 123, 4, 3], False),
        ])
        reader.condition = object()
        window = dict(hwnd=123, pid=11, exe='chrome.exe', ad='Google Chrome')
        tabs, checked = reader.tara([window])
        self.assertEqual(checked, {123})
        self.assertEqual([t['title'] for t in tabs], ['Video', 'Belge'])
        self.assertEqual([t['selected'] for t in tabs], [True, False])

    def test_no_selection_is_not_close_evidence(self):
        reader = SekmeOkuyucu()
        reader.uia = FakeUia([FakeElement('Video', [42, 123, 4, 2], False)])
        reader.condition = object()
        tabs, checked = reader.tara([dict(hwnd=123, pid=11, exe='chrome.exe', ad='Chrome')])
        self.assertEqual((tabs, checked), ([], set()))

    def test_switch_and_disappearance(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = os.path.join(tmp, 'test.db')
            depo = Depo(file)
            depo.kapat()
            z = Zaman(file)
            try:
                self._check_switch(z)
            finally:
                z.close()

    def _check_switch(self, z):
            start = datetime(2026, 9, 15, 9).timestamp()
            w = dict(hwnd=123, pid=11, exe='chrome.exe', ad='Chrome',
                     baslik='Video - Chrome', state='Ekranda görünür',
                     on_planda=True, url='site.test/video')
            def tab(id, title, selected):
                return dict(hwnd=123, pid=11, exe='chrome.exe', ad='Chrome',
                            id=str(id), title=title, selected=selected)
            z.observe([w], now=start)
            z.observe_native_tabs([tab(1, 'Video', True), tab(2, 'Belge', False)],
                                  {123}, [w], now=start)
            z.observe_native_tabs([tab(1, 'Video', False), tab(2, 'Belge', True)],
                                  {123}, [dict(w, url='site.test/belge')], now=start+2)
            z.observe_native_tabs([tab(2, 'Belge', True)], {123},
                                  [dict(w, url='site.test/belge')], now=start+4)
            rows = list(z.db.execute("SELECT * FROM zaman_aralik WHERE kaynak='Sekme (Windows)' ORDER BY id"))
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]['adres'], 'site.test/video')
            self.assertEqual(rows[2]['adres'], 'site.test/video')
            self.assertEqual(rows[2]['bitis_nedeni'], 'Sekme listeden çıktı; kapandı veya taşındı')
            self.assertIsNone(rows[-1]['bitis'])


if __name__ == '__main__':
    unittest.main()
