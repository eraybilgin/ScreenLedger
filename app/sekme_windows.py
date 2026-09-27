"""Tarayıcı sekme şeridini Windows erişilebilirlik ağacından okur.

Yalnızca pencerenin kendi erişilebilirlik öğelerini kabul eder; sayfanın
içindeki veya geliştirici araçlarındaki sahte sekme öğelerini atlar.
"""
import re

from adres import TARAYICILAR

TAB_ITEM = 50019
CONTROL_TYPE = 30003
IS_SELECTED = 30079
DESCENDANTS = 4

_MEMORY = re.compile(r'\s+-\s+(?:Bellek kullanımı|Memory usage)\s+-\s+[^\n]+$', re.I)


def baslik_ayikla(name):
    return _MEMORY.sub('', (name or '').strip())[:4096]


class SekmeOkuyucu:
    def __init__(self):
        self.uia = None
        self.condition = None
        self.error = ''

    def _hazirla(self):
        if self.uia is not None:
            return True
        try:
            import comtypes.client
            comtypes.client.GetModule('UIAutomationCore.dll')
            from comtypes.gen import UIAutomationClient as U
            self.uia = comtypes.client.CreateObject(U.CUIAutomation, interface=U.IUIAutomation)
            self.condition = self.uia.CreatePropertyCondition(CONTROL_TYPE, TAB_ITEM)
            self.error = ''
            return True
        except Exception as exc:
            self.error = repr(exc)
            return False

    def tara(self, windows):
        """(sekme listesi, başarıyla taranan pencere kimlikleri) döndürür."""
        if not self._hazirla():
            return [], set()
        tabs, checked = [], set()
        for w in windows:
            if w['exe'].lower() not in TARAYICILAR:
                continue
            hwnd = int(w['hwnd'])
            try:
                root = self.uia.ElementFromHandle(hwnd)
                if not root:
                    continue
                items = root.FindAll(DESCENDANTS, self.condition)
                if items is None:
                    continue
                found = []
                for i in range(min(items.Length, 500)):
                    element = items.GetElement(i)
                    runtime = list(element.GetRuntimeId())
                    # Chrome'un kendi sekmeleri pencerenin HWND kimliğini taşır.
                    # Web içeriği ve geliştirici araçları farklı HWND taşır.
                    if len(runtime) < 3 or runtime[1] != hwnd:
                        continue
                    name = baslik_ayikla(element.CurrentName)
                    if not name:
                        continue
                    selected = element.GetCurrentPropertyValue(IS_SELECTED) is True
                    found.append({'hwnd': hwnd, 'pid': w['pid'], 'exe': w['exe'],
                                  'ad': w['ad'], 'id': '.'.join(map(str, runtime)),
                                  'title': name, 'selected': selected})
                # En az bir seçili sekme görülmediyse örnek tamamlanmamıştır.
                if found and sum(t['selected'] for t in found) != 1:
                    continue
                # Bazı Chromium pencereleri (ör. kurulu web uygulaması) sekme
                # şeridi içermez. Boş listeyi kapanış kanıtı saymayız.
                if found:
                    checked.add(hwnd)
                    tabs.extend(found)
            except Exception as exc:
                self.error = repr(exc)
        return tabs, checked
