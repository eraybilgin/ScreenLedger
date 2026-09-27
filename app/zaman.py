"""Pencere ve sekme durum aralıkları. Eski saatlik kayıtlara dokunmaz."""
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid
from datetime import datetime


def tarih(t):
    return datetime.fromtimestamp(t).isoformat(' ', 'milliseconds')


class Zaman:
    def __init__(self, dosya, config=None):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(dosya, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS zaman_aralik (
          id INTEGER PRIMARY KEY, kaynak TEXT NOT NULL, kimlik TEXT NOT NULL,
          uygulama TEXT NOT NULL, baslik TEXT NOT NULL, adres TEXT NOT NULL,
          durum TEXT NOT NULL, kullanim TEXT NOT NULL, baslangic TEXT NOT NULL,
          son_gorulme TEXT NOT NULL, bitis TEXT, bitis_nedeni TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS zaman_tarih ON zaman_aralik(baslangic,son_gorulme);
        ''')
        self.db.execute("UPDATE zaman_aralik SET bitis=son_gorulme, bitis_nedeni='Takip kesildi; kesin kapanış bilinmiyor' WHERE bitis IS NULL")
        self.db.commit()
        self.run = uuid.uuid4().hex
        self.open = {}
        self.streams = {}
        self.windows = []
        self.locked = False
        self.idle = False
        self.last_tick = None
        self.native_last = None
        self.native_count = 0
        self.native_error = ''
        self.last_commit = time.monotonic()
        if config:
            if os.path.exists(config):
                with open(config, encoding='utf-8') as f:
                    self.token = json.load(f)['token']
            else:
                self.token = secrets.token_urlsafe(32)
                os.makedirs(os.path.dirname(config), exist_ok=True)
                with open(config, 'x', encoding='utf-8') as f:
                    json.dump({'token': self.token}, f)
        else:
            self.token = secrets.token_urlsafe(32)

    def _close(self, key, stamp, reason):
        old = self.open.pop(key, None)
        if old:
            self.db.execute('UPDATE zaman_aralik SET bitis=?,son_gorulme=?,bitis_nedeni=? WHERE id=?',
                            (stamp, stamp, reason, old[0]))

    def _set(self, key, source, app, title, url, state, usage, now):
        stamp = tarih(now)
        values = (source, app, title, url, state, usage)
        old = self.open.get(key)
        if old and old[1] == values:
            self.open[key] = (old[0], values, stamp)
            return
        self._close(key, stamp, 'Durum veya sayfa değişti')
        row = self.db.execute('INSERT INTO zaman_aralik(kaynak,kimlik,uygulama,baslik,adres,durum,kullanim,baslangic,son_gorulme) VALUES(?,?,?,?,?,?,?,?,?)',
                              (source, key, app, title, url, state, usage, stamp, stamp))
        self.open[key] = (row.lastrowid, values, stamp)

    def _usage(self, active):
        return 'Kilitli' if self.locked else 'Kullanıcı boşta' if self.idle else 'Seçili pencere' if active else 'Seçili değil'

    def observe(self, windows, locked=False, idle=False, now=None, is_window=None):
        now = time.time() if now is None else now
        with self.lock:
            if self.last_tick is not None and (now-self.last_tick > 8 or now < self.last_tick):
                for key, old in list(self.open.items()):
                    self._close(key, old[2], 'Ölçüm kesildi; uyku veya kapanış kesin değil')
            self.last_tick = now
            self.windows, self.locked, self.idle = windows, locked, idle
            seen = set()
            for w in windows:
                key = 'p:' + self.run + ':' + str(w['hwnd']) + ':' + str(w['pid'])
                seen.add(key)
                state = 'Kilitli' if locked else w['state']
                self._set(key, 'Pencere', w['ad'], w['baslik'], w.get('url', ''), state, self._usage(w['on_planda']), now)
            for key, old in list(self.open.items()):
                if key.startswith('p:') and key not in seen:
                    hwnd = int(key.split(':')[-2])
                    reason = 'Pencere kapandı' if is_window and not is_window(hwnd) else 'Pencere izleme dışında; kapanış doğrulanmadı'
                    self._close(key, tarih(now), reason)
            for session, stream in self.streams.items():
                if now-stream['received'] > 90:
                    for key, old in list(self.open.items()):
                        if key.startswith('s:'+session+':'):
                            self._close(key, old[2], 'Tarayıcı bağlantısı kesildi; kapanış bilinmiyor')
                else:
                    self._tabs(session, now)
            if self.db.in_transaction or time.monotonic()-self.last_commit >= 15:
                self.flush()

    def receive(self, payload, now=None):
        now = time.time() if now is None else now
        session = payload['session']
        if not isinstance(session, str) or len(session) > 100 or ':' in session:
            raise ValueError('Geçersiz oturum')
        seq = int(payload['seq'])
        tabs = payload['tabs']
        if not isinstance(tabs, list) or len(tabs) > 3000:
            raise ValueError('Geçersiz sekme listesi')
        cleaned = []
        for t in tabs:
            cleaned.append({'id': int(t['id']), 'window': int(t['window']),
                            'title': str(t.get('title',''))[:4096], 'url': str(t.get('url',''))[:16000],
                            'active': bool(t.get('active')), 'focused': bool(t.get('focused')),
                            'minimized': bool(t.get('minimized')), 'discarded': bool(t.get('discarded'))})
        with self.lock:
            old = self.streams.get(session)
            if old and seq <= old['seq']:
                return
            if old and now-old['received'] > 90:
                for key, value in list(self.open.items()):
                    if key.startswith('s:'+session+':'):
                        self._close(key, value[2], 'Bağlantı kesintisi; ara hareketler bilinmiyor')
            browser = payload.get('browser','chrome.exe')
            if browser not in ('chrome.exe','msedge.exe','brave.exe','vivaldi.exe','opera.exe'):
                raise ValueError('Desteklenmeyen tarayıcı')
            stream = {'seq':seq, 'tabs':cleaned, 'received':now, 'browser':browser}
            self.streams[session] = stream
            closed = {int(i) for i in payload.get('closed', [])}
            seen = {str(t['id']) for t in cleaned}
            for key, value in list(self.open.items()):
                if key.startswith('s:'+session+':') and key.split(':')[-1] not in seen:
                    reason = 'Sekme kapandı' if int(key.split(':')[-1]) in closed else 'Sekme listeden çıktı; kapanış doğrulanmadı'
                    self._close(key, tarih(now), reason)
            self._tabs(session, now)
            self.flush()

    def observe_native_tabs(self, tabs, checked, windows, now=None, is_window=None):
        """Yerleşik Windows okumasından gelen sekmeleri zaman çizelgesine işler."""
        now = time.time() if now is None else now
        with self.lock:
            by_handle = {int(w['hwnd']): w for w in windows}
            seen = set()
            for t in tabs:
                hwnd = int(t['hwnd'])
                w = by_handle.get(hwnd)
                if not w:
                    continue
                key = 'n:' + self.run + ':' + str(hwnd) + ':' + str(t['pid']) + ':' + t['id']
                seen.add(key)
                selected = t['selected']
                state = ('Kilitli' if self.locked else
                         w['state'] if selected else
                         'Arka planda — başka sekme seçili')
                url = w.get('url', '') if selected else ''
                old = self.open.get(key)
                # Seçiliyken okunan adres, aynı sekme arka plandayken de bilinir.
                if not url and old:
                    url = old[1][3]
                self._set(key, 'Sekme (Windows)', t['exe'], t['title'], url,
                          state, self._usage(selected and w['on_planda']), now)
            for key, old in list(self.open.items()):
                if not key.startswith('n:') or key in seen:
                    continue
                hwnd = int(key.split(':')[2])
                if is_window and not is_window(hwnd):
                    self._close(key, tarih(now), 'Tarayıcı penceresi kapandı')
                elif hwnd in checked:
                    self._close(key, tarih(now), 'Sekme listeden çıktı; kapandı veya taşındı')
                elif self.native_last is not None and now-self.native_last > 15:
                    self._close(key, old[2], 'Sekme okuması kesildi; kapanış bilinmiyor')
            if checked:
                self.native_last = now
                self.native_count = len(tabs)
            self.flush()

    def _tabs(self, session, now):
        stream = self.streams[session]
        # Başlığı tekil eşleşmeyen pencerelerde görünürlük tahmin edilmez.
        native = [w for w in self.windows if w['exe'].lower() == stream['browser']]
        selected_titles = [t['title'] for t in stream['tabs'] if t['active']]
        for t in stream['tabs']:
            state, active = 'Arka planda — başka sekme seçili', False
            if self.locked:
                state = 'Kilitli'
            elif t['minimized']:
                state = 'Arka planda — pencere küçültülmüş'
            elif t['discarded']:
                state = 'Arka planda — sekme bellekte bekletilmiyor'
            elif t['active']:
                candidates = [w for w in native if w['baslik'] == t['title'] or w['baslik'].startswith(t['title']+' - ') or w['baslik'].startswith(t['title']+' — ')] if t['title'] else []
                if selected_titles.count(t['title']) == 1 and len(candidates) == 1:
                    w = candidates[0]
                    state, active = w['state'], w['on_planda']
                elif t['focused'] and any(w['on_planda'] for w in native):
                    state, active = 'Ekranda görünür', True
                else:
                    state = 'Seçili sekme — pencere görünürlüğü doğrulanamadı'
            key = 's:'+session+':'+str(t['id'])
            self._set(key, 'Sekme', stream['browser'], t['title'], t['url'], state, self._usage(active), now)

    def flush(self):
        with self.lock:
            self.db.executemany('UPDATE zaman_aralik SET son_gorulme=? WHERE id=?', [(v[2],v[0]) for v in self.open.values()])
            self.db.commit()
            self.last_commit = time.monotonic()

    def status(self):
        with self.lock:
            live = [s for s in self.streams.values() if time.time()-s['received'] <= 90]
            native_live = self.native_last is not None and time.time()-self.native_last <= 15
            return {'connected':bool(live), 'tabs':sum(len(s['tabs']) for s in live),
                    'windows_connected':native_live,
                    'windows_tabs':self.native_count if native_live else 0}

    def intervals(self, bas, bit, limit=1000):
        with self.lock:
            self.flush()
            rows = self.db.execute('''
                SELECT kaynak,uygulama,baslik,adres,durum,kullanim,baslangic,
                       son_gorulme,bitis,bitis_nedeni
                FROM zaman_aralik WHERE baslangic < ? AND son_gorulme >= ?
                ORDER BY baslangic DESC,id DESC LIMIT ?''', (bit, bas, limit)).fetchall()
            return [dict(row) for row in rows]

    def close(self):
        with self.lock:
            for k, old in list(self.open.items()):
                self._close(k, old[2], 'Takip programı durdu; pencere kapanışı değil')
            self.db.commit()
            self.db.close()
