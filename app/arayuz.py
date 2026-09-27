# -*- coding: utf-8 -*-
"""
arayuz.py -- Tarayicidan bakilan rapor ekrani.

Python'un kendi icinde hazir gelen kucuk bir web sunucusu kullanir
(http.server). Disaridan hicbir kutuphane gerektirmez.

Sadece 127.0.0.1 (bu bilgisayarin kendisi) uzerinden dinler; aga acilmaz,
yani baska kimse goremez.

Sayfada uc sekme var:
  Uygulamalar -- secilen tarih araliginda en cok kullanilan programlar
  Sayfalar    -- en cok bakilan pencereler / internet sayfalari
  Siteler     -- en cok vakit gecirilen internet siteleri (youtube.com gibi)
"""
import base64
import hashlib
import json
import os
import re
import secrets
import urllib.parse
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie

from kimlik import Kimlik
from yollar import KIMLIK_DOSYASI

_takipci = None
_kimlik = None

GIRIS_SAYFASI = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Ekran Takip — Giriş</title>
<style>
:root{color-scheme:dark;--vurgu:#77a9ff;--yazi:#f5f7fb;--soluk:#aab5c6}
*{box-sizing:border-box}
body{font:16px/1.5 system-ui;background:radial-gradient(circle at 15% 15%,#203e70 0,transparent 35%),radial-gradient(circle at 90% 85%,#153d4a 0,transparent 32%),#0c111c;color:var(--yazi);min-height:100vh;display:grid;place-items:center;margin:0;padding:24px}
main{width:min(100%,440px);background:#172232e8;border:1px solid #52698766;box-shadow:0 28px 80px #0007;padding:36px;border-radius:24px;animation:giris .5s both}
.dil-secimi{position:fixed;right:24px;top:18px;display:flex;gap:5px;z-index:2}
.dil-secimi button{width:auto;margin:0;padding:6px 10px;background:#172232;color:#cbd5e1;border:1px solid #53647b;box-shadow:none;font-size:13px}
.dil-secimi button.secili{color:#fff;border-color:#77a9ff;background:#28466f}
.amblem{width:46px;height:46px;display:grid;place-items:center;border-radius:14px;background:linear-gradient(135deg,#7eb1ff,#5b7bf0);color:#101a2a;font-weight:800;box-shadow:0 10px 30px #5485ff55;margin-bottom:22px}
h1{font-size:30px;letter-spacing:-.04em;line-height:1.1;margin:0 0 12px}
input,button{width:100%;padding:13px 15px;margin:8px 0;border-radius:12px;font:inherit}
input{background:#101927;color:white;border:1px solid #53647b;outline:none}
input:focus-visible,button:focus-visible{outline:3px solid #a2c6ff;outline-offset:2px}
button{background:linear-gradient(135deg,#85b6ff,#5d87ed);color:#10213a;border:0;cursor:pointer;font-weight:700;box-shadow:0 10px 25px #3665d844;transition:transform .18s,box-shadow .18s}
button:hover{transform:translateY(-2px);box-shadow:0 14px 30px #3665d866}button:disabled{opacity:.6;cursor:wait}
p{color:var(--soluk);line-height:1.55}#durum{color:#ffc3c3;min-height:24px;margin-bottom:0}
@keyframes giris{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@media(prefers-reduced-motion:reduce){main{animation:none}button{transition:none}}
</style></head>
<body><div class="dil-secimi" role="group" aria-label="Language / Dil">
<button type="button" data-dil="tr">TR</button><button type="button" data-dil="en">EN</button></div>
<main><div class="amblem" aria-hidden="true">E</div><h1 id="girisBaslik">Ekran Takip</h1><p id="aciklama"></p><form id="form">
<input id="sifre" type="password" autocomplete="current-password" placeholder="Şifre" required>
<input id="tekrar" type="password" autocomplete="new-password" placeholder="Şifreyi tekrar yazın" hidden>
<button id="dugme" type="submit">Giriş yap</button></form><p id="durum"></p></main>
<script>
const ilk = __ILK_KURULUM__;
const girisCeviri={
  'Ekran Takip':'ScreenLedger','Şifre':'Password','Şifreyi tekrar yazın':'Repeat password',
  'Giriş yap':'Sign in','Şifre oluştur':'Create password',
  'Raporu açmak için istediğiniz şifreyi oluşturun.':'Create a password to open your report.',
  'Raporunuzu açmak için şifrenizi yazın.':'Enter your password to open your report.',
  'Şifreler eşleşmiyor.':'Passwords do not match.',
  'Giriş yapılamadı':'Sign-in failed.','Şifre yanlış':'Incorrect password.',
  'Şifre boş olamaz':'Password cannot be empty.',
  'Şifre zaten oluşturulmuş':'A password has already been created.',
  'Çok fazla yanlış deneme. Bir dakika sonra tekrar deneyin':'Too many attempts. Try again in one minute.',
  'Şifre dosyası bozuk':'The password file is damaged.',
  'Şifre gerekli':'A password is required.','Şifre geçersiz':'Invalid password.',
  'İstek reddedildi':'Request denied.','İstek boyutu geçersiz':'Invalid request size.'
};
let dil='tr';try{dil=localStorage.getItem('screenledger-language')==='en'?'en':'tr';}catch(e){}
function gm(metin){return dil==='en'?(girisCeviri[metin]||metin):metin;}
const aciklama=document.getElementById('aciklama'), tekrar=document.getElementById('tekrar');
function girisiCevir(){
 document.documentElement.lang=dil;
 document.title=gm('Ekran Takip')+' — '+(dil==='en'?'Sign in':'Giriş');
 document.getElementById('girisBaslik').textContent=gm('Ekran Takip');
 document.getElementById('sifre').placeholder=gm('Şifre');
 tekrar.placeholder=gm('Şifreyi tekrar yazın');
 aciklama.textContent=gm(ilk?'Raporu açmak için istediğiniz şifreyi oluşturun.':'Raporunuzu açmak için şifrenizi yazın.');
 document.getElementById('dugme').textContent=gm(ilk?'Şifre oluştur':'Giriş yap');
 document.querySelectorAll('[data-dil]').forEach(b=>{
   b.classList.toggle('secili',b.dataset.dil===dil);
   b.setAttribute('aria-pressed',String(b.dataset.dil===dil));
 });
}
if(ilk){tekrar.hidden=false;tekrar.required=true;document.getElementById('sifre').autocomplete='new-password';}
document.querySelectorAll('[data-dil]').forEach(b=>b.addEventListener('click',()=>{
 dil=b.dataset.dil;try{localStorage.setItem('screenledger-language',dil);}catch(e){}
 girisiCevir();document.getElementById('durum').textContent='';
}));
girisiCevir();
document.getElementById('form').addEventListener('submit',async e=>{
 e.preventDefault();const sifre=document.getElementById('sifre').value;
 if(ilk&&sifre!==tekrar.value){document.getElementById('durum').textContent=gm('Şifreler eşleşmiyor.');return;}
 const dugme=document.getElementById('dugme');dugme.disabled=true;
 try{const r=await fetch(ilk?'/auth/kur':'/auth/gir',{method:'POST',
  headers:{'Content-Type':'application/json','X-Ekran-Form':'1'},body:JSON.stringify({sifre})});
  const j=await r.json();if(!r.ok)throw new Error(gm(j.hata||'Giriş yapılamadı'));location.replace('/');
 }catch(hata){document.getElementById('durum').textContent=hata.message;dugme.disabled=false;}
});</script></body></html>"""


SAYFA = r"""<!doctype html>
<html lang="tr"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ekran Takip</title>
<style>
:root{
  --zemin:#f5f6f8; --kart:#ffffff; --yazi:#14171a; --soluk:#6b7280;
  --cizgi:#e4e7eb; --vurgu:#2563eb; --vurgu-zemin:#eff4ff;
  --gorunur:#2563eb; --kapali:#f59e0b; --simge:#9ca3af;
}
@media (prefers-color-scheme:dark){:root{
  --zemin:#0e1014; --kart:#161920; --yazi:#e8eaed; --soluk:#98a1ad;
  --cizgi:#242932; --vurgu:#60a5fa; --vurgu-zemin:#18243a;
  --gorunur:#60a5fa; --kapali:#fbbf24; --simge:#6b7280;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--zemin);color:var(--yazi);
  font:14px/1.55 -apple-system,"Segoe UI",Roboto,sans-serif}
.sarmal{max-width:1180px;margin:0 auto;padding:26px 20px 70px}
h1{font-size:21px;margin:0 0 3px;letter-spacing:-.02em}
.altbaslik{color:var(--soluk);font-size:13px;margin-bottom:18px}

.araclar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}
button,input[type=date]{font:inherit;padding:7px 12px;border:1px solid var(--cizgi);
  border-radius:9px;background:var(--kart);color:var(--yazi);cursor:pointer}
button:hover{border-color:var(--vurgu)}
#excelIndir{background:#2563eb;color:white;font-weight:600;border-color:#2563eb}
#excelIndir:disabled{opacity:.6;cursor:wait}
button.secili{background:var(--vurgu-zemin);border-color:var(--vurgu);
  color:var(--vurgu);font-weight:600}
.ayirac{width:1px;height:24px;background:var(--cizgi);margin:0 4px}
.ozelAralik{display:flex;gap:6px;align-items:center;color:var(--soluk);font-size:13px}

.kartlar{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:12px;margin:18px 0 6px}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;
  padding:13px 15px}
.kart .etiket{color:var(--soluk);font-size:12px;margin-bottom:3px}
.kart .deger{font-size:21px;font-weight:650;letter-spacing:-.02em}
.kart .ek{color:var(--soluk);font-size:11px;margin-top:2px}

.grafik{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;
  padding:14px 16px;margin:12px 0 20px}
.grafik .baslik{font-size:12px;color:var(--soluk);margin-bottom:10px}
.sutunlar{display:flex;align-items:flex-end;gap:2px;height:90px}
.sutun{flex:1;min-width:3px;background:var(--vurgu);border-radius:2px 2px 0 0;
  opacity:.85;position:relative}
.sutun:hover{opacity:1}
.sutun span{display:none;position:absolute;bottom:100%;left:50%;
  transform:translateX(-50%);background:var(--yazi);color:var(--zemin);
  font-size:11px;padding:3px 7px;border-radius:6px;white-space:nowrap;z-index:5}
.sutun:hover span{display:block}

.sekmeler{display:flex;gap:4px;margin:0 0 12px;border-bottom:1px solid var(--cizgi)}
.sekme{padding:9px 15px;border:none;border-radius:0;background:none;
  color:var(--soluk);border-bottom:2px solid transparent;font-weight:500}
.sekme:hover{color:var(--yazi);border-color:transparent}
.sekme.secili{color:var(--vurgu);border-bottom-color:var(--vurgu);font-weight:650}

table{width:100%;border-collapse:collapse;background:var(--kart);
  border:1px solid var(--cizgi);border-radius:12px;overflow:hidden}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--cizgi);
  vertical-align:middle}
th{font-size:11px;color:var(--soluk);font-weight:650;text-transform:uppercase;
  letter-spacing:.05em;white-space:nowrap}
tr:last-child td{border-bottom:none}
td.sag,th.sag{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ad{font-weight:600}
.kucuk{color:var(--soluk);font-size:12px;word-break:break-all}
.sira{color:var(--soluk);font-variant-numeric:tabular-nums;width:34px}
.cubuk{height:6px;border-radius:3px;background:var(--cizgi);display:flex;
  overflow:hidden;min-width:90px}
.cubuk i{display:block;height:100%}
.g{background:var(--gorunur)} .k{background:var(--kapali)} .s{background:var(--simge)}
.acilir{cursor:pointer}
.acilir:hover{background:var(--vurgu-zemin)}
.alt td{padding-left:26px;font-size:13px;color:var(--soluk);
  border-bottom:1px dashed var(--cizgi);background:transparent}
.aciklama{display:flex;gap:16px;flex-wrap:wrap;color:var(--soluk);font-size:12px;
  margin:10px 2px 14px}
.aciklama span{display:flex;align-items:center;gap:6px}
.aciklama b{font-weight:normal}
.nokta{width:10px;height:10px;border-radius:3px;display:inline-block}
.bos{padding:44px;text-align:center;color:var(--soluk)}
.dipnot{color:var(--soluk);font-size:12px;margin-top:18px;text-align:center}
.sarmal{max-width:1240px;padding:24px 24px 80px}
body{background:radial-gradient(circle at 85% -10%,#c9dfff 0,transparent 34%),var(--zemin)}
@media(prefers-color-scheme:dark){body{background:radial-gradient(circle at 85% -10%,#173052 0,transparent 32%),var(--zemin)}}
.ust{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin:0 0 20px;padding:28px 30px;border:1px solid var(--cizgi);border-radius:22px;background:linear-gradient(130deg,var(--kart),var(--vurgu-zemin));box-shadow:0 16px 44px #1424470c}
.ust .eyebrow{color:var(--vurgu);font-size:11px;font-weight:750;letter-spacing:.15em;text-transform:uppercase;margin:0 0 9px}
h1{font-size:clamp(28px,4vw,42px);line-height:1.08;letter-spacing:-.045em;margin:0 0 10px}
.ust .altbaslik{font-size:14px;margin:0;color:var(--soluk)}
.ust-sag{display:grid;gap:8px;justify-items:end;min-width:220px}
.ust .dil-secimi{display:flex;gap:5px;justify-self:end}
.ust .dil-secimi button{padding:5px 10px;font-size:12px;font-weight:700}
.durum-rozet{display:inline-flex;gap:8px;align-items:center;padding:8px 12px;border:1px solid var(--cizgi);border-radius:999px;background:var(--kart);font-size:12px;font-weight:650;max-width:100%}
.durum-rozet::before{content:"";width:8px;height:8px;flex:none;border-radius:50%;background:#10b981;box-shadow:0 0 0 4px #10b98122}
.durum-rozet.bosta::before{background:#f59e0b;box-shadow:0 0 0 4px #f59e0b22}
.durum-rozet.kilitli::before{background:#94a3b8;box-shadow:0 0 0 4px #94a3b822}
#sekmeDurumu{max-width:300px;text-align:right;font-size:11px;color:var(--soluk)}
.araclar{gap:8px;margin:0 0 22px;padding:12px;border-radius:16px;background:var(--kart);border:1px solid var(--cizgi);box-shadow:0 9px 28px #14244709}
button,input[type=date]{transition:background-color .2s,border-color .2s,color .2s,transform .2s,box-shadow .2s}
button:hover{transform:translateY(-2px);box-shadow:0 5px 14px #14244715}
button:focus-visible,input:focus-visible,.acilir:focus-visible{outline:3px solid var(--vurgu);outline-offset:2px}
.araclar button{font-weight:600}
#indirmeDurumu{font-size:12px;color:var(--soluk)}
.kartlar{grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0 0 14px}
.kart{min-height:132px;border-radius:16px;padding:18px 19px;background:linear-gradient(160deg,var(--kart),var(--vurgu-zemin));box-shadow:0 10px 25px #14244709;transition:transform .24s,box-shadow .24s,border-color .24s}
.kart:hover{transform:translateY(-4px);box-shadow:0 18px 34px #14244717;border-color:var(--vurgu)}
.kart .etiket{font-size:12px;font-weight:650;margin-bottom:12px}
.kart .deger{font-size:clamp(21px,2.3vw,29px);line-height:1.15;white-space:nowrap}
.kart .ek{font-size:12px;margin-top:9px}
.kart.vurgulu{background:linear-gradient(140deg,#2563eb,#1c4ba7);color:white;border-color:#2563eb}
.kart.vurgulu .etiket,.kart.vurgulu .ek{color:#dce9ff}
.grafik{border-radius:16px;padding:20px 22px;margin:0 0 23px;box-shadow:0 10px 25px #14244709}
.grafik .baslik{font-size:14px;font-weight:700;color:var(--yazi)}
.sutunlar{height:128px;gap:3px}
.sutun{border-radius:5px 5px 0 0;opacity:.72;transition:opacity .2s,filter .2s}
.sutun:hover{filter:brightness(1.15)}
.sekmeler{gap:7px;margin:0 0 14px;border-bottom:1px solid var(--cizgi)}
.sekme{padding:12px 18px;border-radius:10px 10px 0 0;position:relative}
.sekme.secili{background:var(--vurgu-zemin);border-bottom-color:var(--vurgu)}
.sekme.secili::after{content:"";position:absolute;left:16px;right:16px;bottom:-2px;height:3px;background:var(--vurgu);border-radius:3px}
#icerik{min-height:120px;view-transition-name:icerik}
.tablo-kapsayici{overflow-x:auto;border:1px solid var(--cizgi);border-radius:16px;background:var(--kart);box-shadow:0 10px 25px #14244709}
table{border:0;border-radius:0;min-width:780px}
th,td{padding:13px 14px}
tbody tr{transition:background-color .18s}
tbody tr:hover{background:var(--vurgu-zemin)}
.bos{border:1px dashed var(--cizgi);border-radius:16px;background:var(--kart)}
.cubuk{height:8px;border-radius:6px}
.aciklama{margin:5px 2px 15px}
.dipnot{margin-top:24px}
.hareketli-kart{animation:kartGiris .48s both}
.hareketli-sutun{transform-origin:bottom;animation:sutunGiris .55s both}
.alt{animation:altGiris .26s both}
@keyframes kartGiris{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@keyframes sutunGiris{from{opacity:0;transform:scaleY(.08)}to{opacity:.72;transform:scaleY(1)}}
@keyframes altGiris{from{opacity:0;transform:translateY(-7px)}to{opacity:1;transform:translateY(0)}}
::view-transition-old(icerik),::view-transition-new(icerik){animation-duration:.24s;animation-timing-function:ease-out}
@media(max-width:1000px){.kartlar{grid-template-columns:repeat(3,minmax(0,1fr))}.araclar .ayirac{display:none}}
@media(max-width:700px){.sarmal{padding:14px 12px 54px}.ust{padding:22px;display:block}.ust-sag{justify-items:start;margin-top:18px;min-width:0}#sekmeDurumu{text-align:left}.araclar{padding:10px}.ozelAralik{width:100%;flex-wrap:wrap}.ozelAralik input{flex:1;min-width:120px}.kartlar{grid-template-columns:repeat(2,minmax(0,1fr))}.kart{min-height:114px;padding:15px}.kart .deger{font-size:22px}.grafik{padding:16px}.sekmeler{overflow-x:auto;white-space:nowrap}.sekme{flex:none;padding:11px 13px}.aciklama{gap:8px 14px}}
@media(max-width:700px){.tablo-kapsayici{border:0;background:transparent;box-shadow:none;overflow:visible}table,tbody,tr,td{display:block;width:100%;min-width:0}thead{display:none}tbody{display:grid;gap:10px}tbody tr{border:1px solid var(--cizgi);border-radius:14px;background:var(--kart);padding:11px 14px;box-shadow:0 7px 19px #14244709}td,td.sag{display:flex;justify-content:space-between;gap:16px;align-items:start;text-align:right;border:0;padding:5px 0;white-space:normal}td::before{content:attr(data-label);color:var(--soluk);font-size:11px;font-weight:700;text-align:left;flex:0 0 95px;text-transform:uppercase;letter-spacing:.03em}td:has(.ad){text-align:left}td:has(.ad)::before{display:none}td .ad{font-size:15px}td .cubuk{margin-left:auto;min-width:110px}.sira{display:none}.alt td{padding:5px 0;color:var(--yazi)}.alt td[colspan]::before{display:none}}
@media(max-width:390px){.kartlar{grid-template-columns:1fr 1fr}.kart .deger{font-size:19px}.araclar button{padding:7px 9px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}
</style></head><body>
<div class="sarmal">
  <header class="ust">
    <div><div class="eyebrow" data-metin="Kişisel kullanım raporu">Kişisel kullanım raporu</div><h1 data-metin="Ekran Takip">Ekran Takip</h1>
      <div class="altbaslik" id="donemBaslik">Kullanımınıza yakından bakın</div></div>
    <div class="ust-sag"><div class="dil-secimi" role="group" aria-label="Language / Dil">
      <button type="button" data-dil="tr">TR</button><button type="button" data-dil="en">EN</button></div>
      <div class="durum-rozet" id="durum" role="status" aria-live="polite">Veriler yükleniyor…</div>
      <div id="sekmeDurumu">Sekme bağlantısı kontrol ediliyor…</div></div>
  </header>

  <div class="araclar">
    <button data-hazir="bugun" data-metin="Bugün">Bugün</button>
    <button data-hazir="dun" data-metin="Dün">Dün</button>
    <button data-hazir="hafta" data-metin="Bu hafta">Bu hafta</button>
    <button data-hazir="son_yedi_gun" data-metin="Son 7 gün">Son 7 gün</button>
    <button data-hazir="ay" data-metin="Bu ay">Bu ay</button>
    <button data-hazir="uc_ay" data-metin="Son 3 ay">Son 3 ay</button>
    <button data-hazir="tumu" data-metin="Tümü">Tümü</button>
    <div class="ayirac"></div>
    <div class="ozelAralik">
      <input type="date" id="bas" data-aria-metin="Başlangıç tarihi" aria-label="Başlangıç tarihi"> <span>-</span> <input type="date" id="bit" data-aria-metin="Bitiş tarihi" aria-label="Bitiş tarihi">
      <button id="uygula" data-metin="Göster">Göster</button>
    </div>
    <button id="excelIndir" data-metin="Excel indir">Excel indir</button>
    <button id="cikis" data-metin="Çıkış yap">Çıkış yap</button>
    <span id="indirmeDurumu" role="status" aria-live="polite"></span>
  </div>

  <div class="kartlar" id="kartlar"></div>

  <div class="grafik" id="grafikKutu" hidden>
    <div class="baslik" id="grafikBaslik" data-metin="Günlük kullanım">Günlük kullanım</div>
    <div class="sutunlar" id="sutunlar"></div>
  </div>

  <div class="sekmeler">
    <button class="sekme secili" data-sekme="uygulamalar" data-metin="Uygulamalar">Uygulamalar</button>
    <button class="sekme" data-sekme="sayfalar" data-metin="Sayfalar">Sayfalar</button>
    <button class="sekme" data-sekme="siteler" data-metin="Siteler">Siteler</button>
    <button class="sekme" data-sekme="zaman" data-metin="Zaman çizelgesi">Zaman çizelgesi</button>
  </div>

  <div class="aciklama" id="renkAciklama">
    <span><i class="nokta g"></i> <b data-metin="Ekranda görünür">Ekranda görünür</b></span>
    <span><i class="nokta k"></i> <b data-metin="Ekranda ama üstü kapalı">Ekranda ama üstü kapalı</b></span>
    <span><i class="nokta s"></i> <b data-metin="Simge durumunda">Simge durumunda</b></span>
  </div>

  <div id="icerik"></div>
  <div class="dipnot" id="dipnot"></div>
</div>

<script>
const ingilizce={
  'Ekran Takip':'ScreenLedger','Kişisel kullanım raporu':'Personal activity report',
  'Kullanımınıza yakından bakın':'A closer look at your activity',
  'Veriler yükleniyor…':'Loading activity…',
  'Sekme bağlantısı kontrol ediliyor…':'Checking tab connection…',
  'Bugün':'Today','Dün':'Yesterday','Bu hafta':'This week',
  'Son 7 gün':'Last 7 days','Bu ay':'This month','Son 3 ay':'Last 3 months',
  'Tümü':'All time','Göster':'Show','Excel indir':'Download Excel',
  'Başlangıç tarihi':'Start date','Bitiş tarihi':'End date',
  'Çıkış yap':'Sign out','Günlük kullanım':'Daily activity',
  'Uygulamalar':'Apps','Sayfalar':'Pages','Siteler':'Sites',
  'Zaman çizelgesi':'Timeline','Ekranda görünür':'Visible on screen',
  'Ekranda ama üstü kapalı':'Open but covered','Simge durumunda':'Minimized',
  'Oturum sona erdi':'Your session has expired',
  'Bilgisayar kilitli':'Computer locked','Şu an boşta':'Currently idle',
  'pencere ekranda':'windows on screen','Son ölçüm:':'Last sample:',
  'Adres okuma':'Address reading','açık':'on','kapalı':'off',
  'kullanım özeti':'activity summary','Bilgisayar açık kaldı':'Computer on time',
  'gün kayıt':'days recorded','Aktif kullanım':'Active use',
  'Günde ort.':'Daily avg.','Boşta geçen':'Idle time',
  'Farklı uygulama':'Distinct apps','Kayıt boyutu':'Database size',
  'satır':'rows','Günlük aktif kullanım':'Daily active use',
  'gün':'days','Bu tarih aralığında ayrıntılı zaman kaydı yok.':'No detailed timeline records for this date range.',
  'Son 1000 durum aralığı gösterilir. Tam kayıt Excel indirmesinde bulunur. Boş bitiş: son gözlemde sürüyordu.':'The latest 1,000 state intervals are shown. The full record is in the Excel export. An empty end time means it was still ongoing at the last observation.',
  'Başlangıç':'Start','Bitiş':'End','Tür / uygulama':'Type / app',
  'Sekme / pencere':'Tab / window','Durum':'State','Bitiş açıklaması':'End reason',
  'Devam ediyor':'Ongoing','Adres seçilmeden okunamadı':'Address unavailable until selected',
  'Bu aralıkta kayıt yok.':'No records in this period.',
  'Uygulama':'App','Üstü kapalı':'Covered','Simge':'Minimized','Dağılım':'Breakdown',
  'Ayrıntı yok.':'No details available.','Sayfa / pencere':'Page / window',
  'Aktif':'Active','Görünür':'Visible','Gün':'Days',
  'Bu aralıkta adres kaydı yok.':'No website records in this period.',
  'Adres kaydı yeni açıldıysa veri birikmesi zaman alır.':'If address tracking was just enabled, data may take time to appear.',
  'Site':'Site','Ekranda':'On screen','Sayfa':'Pages',
  'Lütfen başlangıç ve bitiş tarihini seçin.':'Please select a start and end date.',
  'Dosya hazırlanıyor…':'Preparing file…',
  'Dosya hazırlanamadı. Lütfen tekrar deneyin.':'Could not prepare the file. Please try again.',
  'İndirme başlatıldı:':'Download started:',
  'Windows ile sekme takibi açık':'Windows tab tracking is on',
  'sekme görüldü':'tabs found',
  'Saatler Zaman çizelgesinde ve Excel indirmesinde.':'Times are in the Timeline and Excel export.',
  'Tarayıcı sekme bağlantısı açık':'Browser tab connection is on',
  'Sekme okuması henüz doğrulanamadı; pencere takibi devam ediyor.':'Tab reading has not been confirmed yet; window tracking continues.',
  'Pencere':'Window','Sekme':'Tab','Sekme (Windows)':'Tab (Windows)',
  'Kilitli':'Locked','Kullanıcı boşta':'User idle',
  'Seçili pencere':'Selected window','Seçili değil':'Not selected',
  'Arka planda — başka sekme seçili':'In background — another tab selected',
  'Arka planda — pencere küçültülmüş':'In background — window minimized',
  'Arka planda — sekme bellekte bekletilmiyor':'In background — tab discarded from memory',
  'Arka planda — üstü kapalı veya ekran dışında':'In background — covered or off-screen',
  'Seçili sekme — pencere görünürlüğü doğrulanamadı':'Selected tab — window visibility unconfirmed',
  'Takip kesildi; kesin kapanış bilinmiyor':'Tracking interrupted; exact end unknown',
  'Durum veya sayfa değişti':'State or page changed',
  'Ölçüm kesildi; uyku veya kapanış kesin değil':'Sampling interrupted; sleep or shutdown uncertain',
  'Pencere kapandı':'Window closed',
  'Pencere izleme dışında; kapanış doğrulanmadı':'Window no longer observed; closure unconfirmed',
  'Tarayıcı bağlantısı kesildi; kapanış bilinmiyor':'Browser connection lost; closure unknown',
  'Bağlantı kesintisi; ara hareketler bilinmiyor':'Connection interrupted; intervening activity unknown',
  'Sekme kapandı':'Tab closed',
  'Sekme listeden çıktı; kapanış doğrulanmadı':'Tab disappeared from list; closure unconfirmed',
  'Tarayıcı penceresi kapandı':'Browser window closed',
  'Sekme listeden çıktı; kapandı veya taşındı':'Tab disappeared from list; closed or moved',
  'Sekme okuması kesildi; kapanış bilinmiyor':'Tab reading interrupted; closure unknown'
};
let dil='tr';try{dil=localStorage.getItem('screenledger-language')==='en'?'en':'tr';}catch(e){}
function m(metin){return dil==='en'?(ingilizce[metin]||metin):metin;}
const asilFetch=window.fetch;
window.fetch=async (...args)=>{const sonuc=await asilFetch(...args);
  if(sonuc.status===401){location.replace('/');throw new Error(m('Oturum sona erdi'));}
  return sonuc;};
document.getElementById('cikis').addEventListener('click',async()=>{
  await fetch('/auth/cik',{method:'POST',headers:{'X-Ekran-Form':'1'}});location.replace('/');
});
// ---------- yardimcilar ----------
function sure(s){
  s=Math.round(s||0);
  var h=Math.floor(s/3600), d=Math.floor((s%3600)/60);
  if(h) return h+(dil==='en'?'h ':'s ')+String(d).padStart(2,"0")+(dil==='en'?'m':'dk');
  if(d) return d+(dil==='en'?'m':'dk');
  return s+(dil==='en'?'s':'sn');
}
function kacis(s){
  return String(s==null?"":s).replace(/[&<>"]/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});
}
function tarihMetni(t){
  return t.getFullYear()+"-"+String(t.getMonth()+1).padStart(2,"0")
         +"-"+String(t.getDate()).padStart(2,"0");
}
function gunEkle(t,n){ var y=new Date(t); y.setDate(y.getDate()+n); return y; }

// ---------- durum ----------
var D = { bas:"", bit:"", sekme:"uygulamalar", ilkGun:null, acikOlanlar:{}, istekSira:0, sekmeSira:0 };
function diliAyarla(yeni){
  dil=yeni==='en'?'en':'tr';
  try{localStorage.setItem('screenledger-language',dil);}catch(e){}
  document.documentElement.lang=dil;
  document.title=m('Ekran Takip');
  document.querySelectorAll('[data-metin]').forEach(function(oge){
    oge.textContent=m(oge.dataset.metin);
  });
  document.querySelectorAll('[data-aria-metin]').forEach(function(oge){
    oge.setAttribute('aria-label',m(oge.dataset.ariaMetin));
  });
  document.querySelectorAll('[data-dil]').forEach(function(dugme){
    var secili=dugme.dataset.dil===dil;
    dugme.classList.toggle('secili',secili);
    dugme.setAttribute('aria-pressed',String(secili));
  });
  document.getElementById('indirmeDurumu').textContent='';
  if(D.bas && D.bit){yukle(false);sekmeDurumunuGoster();}
  else{
    document.getElementById('donemBaslik').textContent=m('Kullanımınıza yakından bakın');
    document.getElementById('durum').textContent=m('Veriler yükleniyor…');
    document.getElementById('sekmeDurumu').textContent=m('Sekme bağlantısı kontrol ediliyor…');
  }
}
document.querySelectorAll('[data-dil]').forEach(function(dugme){
  dugme.onclick=function(){diliAyarla(dugme.dataset.dil);};
});
const azHareket=window.matchMedia('(prefers-reduced-motion: reduce)');
function gorunumGecisi(guncelle, hareketli){
  if(hareketli && !azHareket.matches && document.startViewTransition){
    document.startViewTransition(guncelle);
  }else guncelle();
}
function tabloEtiketle(kok){
  kok.querySelectorAll('table').forEach(function(tablo){
    var basliklar=Array.from(tablo.querySelectorAll('thead th'), x=>x.textContent.trim());
    tablo.querySelectorAll('tbody tr').forEach(function(satir){
      satir.querySelectorAll('td').forEach(function(hucre,i){
        hucre.dataset.label=basliklar[i]||'';
      });
    });
  });
}

function hazirAralik(ad){
  var bugun=new Date();
  if(ad=="bugun")  return [tarihMetni(bugun), tarihMetni(bugun)];
  if(ad=="dun"){ var d=gunEkle(bugun,-1); return [tarihMetni(d), tarihMetni(d)]; }
  if(ad=="hafta"){
    var g=(bugun.getDay()+6)%7;              // pazartesi = 0
    return [tarihMetni(gunEkle(bugun,-g)), tarihMetni(bugun)];
  }
  if(ad=="son_yedi_gun") return [tarihMetni(gunEkle(bugun,-6)), tarihMetni(bugun)];
  if(ad=="ay"){
    var ilk=new Date(bugun.getFullYear(),bugun.getMonth(),1);
    return [tarihMetni(ilk), tarihMetni(bugun)];
  }
  if(ad=="uc_ay") return [tarihMetni(gunEkle(bugun,-89)), tarihMetni(bugun)];
  if(ad=="tumu")  return [D.ilkGun || tarihMetni(bugun), tarihMetni(bugun)];
  return [tarihMetni(bugun), tarihMetni(bugun)];
}

// ---------- ana yukleme ----------
async function yukle(hareketli=false){
  var istek=++D.istekSira;
  ++D.sekmeSira;
  var r=await fetch("/api/aralik?bas="+D.bas+"&bit="+D.bit);
  var v=await r.json();
  if(istek!==D.istekSira) return;

  var d=v.durum;
  var durum=document.getElementById('durum');
  durum.className='durum-rozet'+(d.kilitli?' kilitli':d.bosta?' bosta':'');
  durum.textContent=d.kilitli?m('Bilgisayar kilitli'):d.bosta?m('Şu an boşta'):
    d.pencere_sayisi+' '+(dil==='en'&&d.pencere_sayisi===1?'window on screen':m('pencere ekranda'));
  durum.title=m('Son ölçüm:')+' '+d.son_olcum+' · '+m('Adres okuma')+' '+m(d.url_okuma?'açık':'kapalı');
  document.getElementById('donemBaslik').textContent=(D.bas===D.bit?D.bas:D.bas+' – '+D.bit)+' '+m('kullanım özeti');

  var gunSayisi = Math.max(v.ozet.gun_sayisi||0, 1);
  document.getElementById("kartlar").innerHTML =
      kart(m("Bilgisayar açık kaldı"), sure(v.ozet.acik_saniye),
           v.ozet.gun_sayisi+" "+(dil==='en'&&v.ozet.gun_sayisi===1?'day recorded':m("gün kayıt")),hareketli)
    + kart(m("Aktif kullanım"), sure(v.ozet.etkin_saniye),
           m("Günde ort.")+" "+sure(v.ozet.etkin_saniye/gunSayisi),hareketli,true)
    + kart(m("Boşta geçen"), sure(v.ozet.bosta_saniye), "",hareketli)
    + kart(m("Farklı uygulama"), v.uygulamalar.length, "",hareketli)
    + kart(m("Kayıt boyutu"), v.sistem.db_mb.toFixed(1)+" MB",
           v.sistem.satir.toLocaleString(dil==='en'?'en-US':'tr-TR')+" "+m("satır"),hareketli);

  grafikCiz(v.gunluk,hareketli);
  D.sonUygulamalar = v.uygulamalar;
  await sekmeCiz(hareketli);
  document.getElementById("dipnot").textContent = D.bas+" – "+D.bit+"  |  "+
    (dil==='en'?'Visible times can exceed elapsed time when several windows appear on screen at once.':
    'Aynı anda birden fazla pencere görünüyorsa toplam süre geçen gerçek zamandan uzun olabilir.');
}

function kart(etiket,deger,ek,hareketli,vurgulu=false){
  return '<div class="kart'+(vurgulu?' vurgulu':'')+(hareketli&&!azHareket.matches?' hareketli-kart':'')+'"><div class="etiket">'+etiket+'</div>'
       + '<div class="deger">'+deger+'</div>'
       + (ek?'<div class="ek">'+ek+'</div>':'')+'</div>';
}

function grafikCiz(gunluk,hareketli){
  var kutu=document.getElementById("grafikKutu");
  if(!gunluk || gunluk.length<2){ kutu.hidden=true; return; }
  kutu.hidden=false;
  var enBuyuk=1;
  gunluk.forEach(function(g){ enBuyuk=Math.max(enBuyuk,g.etkin_saniye); });
  document.getElementById("grafikBaslik").textContent =
    m("Günlük aktif kullanım")+" ("+gunluk.length+" "+(dil==='en'&&gunluk.length===1?'day':m("gün"))+")";
  document.getElementById("sutunlar").innerHTML = gunluk.map(function(g,i){
    var y=Math.max(g.etkin_saniye/enBuyuk*100, 2);
    return '<div class="sutun'+(hareketli&&!azHareket.matches?' hareketli-sutun':'')+'" style="height:'+y+'%;animation-delay:'+Math.min(i*18,360)+'ms">'
         + '<span>'+kacis(g.gun)+"  "+sure(g.etkin_saniye)+'</span></div>';
  }).join("");
}

// ---------- sekmeler ----------
async function sekmeCiz(hareketli=false){
  var istek=++D.sekmeSira;
  var icerik=document.getElementById("icerik");
  var renk=document.getElementById("renkAciklama");
  renk.style.display = (D.sekme=="siteler" || D.sekme=="zaman") ? "none" : "flex";

  if(D.sekme=="uygulamalar"){
    gorunumGecisi(function(){uygulamalariCiz(icerik,D.sonUygulamalar);tabloHazirla(icerik);},hareketli);
    return;
  }
  if(D.sekme=="sayfalar"){
    var r=await fetch("/api/sayfalar?bas="+D.bas+"&bit="+D.bit+"&adet=150");
    var sayfalar=(await r.json()).sayfalar;
    if(istek!==D.sekmeSira) return;
    gorunumGecisi(function(){sayfalariCiz(icerik,sayfalar);tabloHazirla(icerik);},hareketli);
    return;
  }
  if(D.sekme=="zaman"){
    var rz=await fetch('/api/zaman?bas='+encodeURIComponent(D.bas)+'&bit='+encodeURIComponent(D.bit));
    var rows=(await rz.json()).araliklar||[];
    if(istek!==D.sekmeSira) return;
    gorunumGecisi(function(){
      if(!rows.length){icerik.innerHTML='<div class="bos">'+m('Bu tarih aralığında ayrıntılı zaman kaydı yok.')+'</div>';return;}
      icerik.innerHTML='<div class="kucuk" style="margin:8px 0">'+m('Son 1000 durum aralığı gösterilir. Tam kayıt Excel indirmesinde bulunur. Boş bitiş: son gözlemde sürüyordu.')+'</div>'
      +'<div class="tablo-kapsayici"><table><thead><tr><th>'+m('Başlangıç')+'</th><th>'+m('Bitiş')+'</th><th>'+m('Tür / uygulama')+'</th><th>'+m('Sekme / pencere')+'</th><th>'+m('Durum')+'</th><th>'+m('Bitiş açıklaması')+'</th></tr></thead><tbody>'
      +rows.map(function(x){return '<tr><td>'+kacis(x.baslangic)+'</td><td>'
       +kacis(x.bitis||m('Devam ediyor'))+'</td><td>'+kacis(m(x.kaynak))+'<div class="kucuk">'+kacis(x.uygulama)+'</div></td>'
       +'<td>'+kacis(x.baslik)+'<div class="kucuk">'+kacis(x.adres||m('Adres seçilmeden okunamadı'))+'</div></td><td>'
       +kacis(m(x.durum))+'<div class="kucuk">'+kacis(m(x.kullanim))+'</div></td><td>'+kacis(m(x.bitis_nedeni||'—'))+'</td></tr>';}).join('')
      +'</tbody></table></div>';
      tabloHazirla(icerik);
    },hareketli);
    return;
  }
  var r2=await fetch("/api/siteler?bas="+D.bas+"&bit="+D.bit);
  var alanlar=(await r2.json()).alanlar;
  if(istek!==D.sekmeSira) return;
  gorunumGecisi(function(){sitelerCiz(icerik,alanlar);tabloHazirla(icerik);},hareketli);
}

function tabloHazirla(kok){
  kok.querySelectorAll('table').forEach(function(tablo){
    if(!tablo.parentElement.classList.contains('tablo-kapsayici')){
      var kapsayici=document.createElement('div');
      kapsayici.className='tablo-kapsayici';
      tablo.before(kapsayici);kapsayici.appendChild(tablo);
    }
  });
  tabloEtiketle(kok);
}

function uygulamalariCiz(icerik, liste){
  if(!liste || !liste.length){
    icerik.innerHTML='<div class="bos">'+m('Bu aralıkta kayıt yok.')+'</div>'; return; }
  var enBuyuk=1;
  liste.forEach(function(u){
    enBuyuk=Math.max(enBuyuk,u.gorunur+u.ustu_kapali+u.simge); });

  icerik.innerHTML =
    '<table><thead><tr><th class="sira">#</th><th>'+m('Uygulama')+'</th>'
    +'<th class="sag">'+m('Aktif kullanım')+'</th><th class="sag">'+m('Ekranda görünür')+'</th>'
    +'<th class="sag">'+m('Üstü kapalı')+'</th><th class="sag">'+m('Simge')+'</th>'
    +'<th style="width:120px">'+m('Dağılım')+'</th></tr></thead><tbody id="govde">'
    + liste.map(function(u,i){
        var t=u.gorunur+u.ustu_kapali+u.simge;
        return '<tr class="acilir" tabindex="0" role="button" aria-expanded="false" data-exe="'+kacis(u.exe)+'">'
          +'<td class="sira">'+(i+1)+'</td>'
          +'<td><div class="ad">'+kacis(u.ad)+'</div>'
            +'<div class="kucuk">'+kacis(u.exe)+' &middot; '+u.gun_sayisi+' '+m('gün')+'</div></td>'
          +'<td class="sag">'+sure(u.aktif)+'</td>'
          +'<td class="sag">'+sure(u.gorunur)+'</td>'
          +'<td class="sag">'+sure(u.ustu_kapali)+'</td>'
          +'<td class="sag">'+sure(u.simge)+'</td>'
          +'<td><div class="cubuk" style="width:'+Math.max(t/enBuyuk*100,5)+'%">'
            +'<i class="g" style="width:'+(t?u.gorunur/t*100:0)+'%"></i>'
            +'<i class="k" style="width:'+(t?u.ustu_kapali/t*100:0)+'%"></i>'
            +'<i class="s" style="width:'+(t?u.simge/t*100:0)+'%"></i>'
          +'</div></td></tr>';
      }).join("")
    + '</tbody></table>';

  document.querySelectorAll("#govde tr.acilir").forEach(function(satir){
    satir.onclick=function(){ detayAcKapa(satir, satir.dataset.exe); };
    satir.onkeydown=function(olay){if(olay.key==='Enter'||olay.key===' '){olay.preventDefault();satir.click();}};
    if(D.acikOlanlar[satir.dataset.exe]) detayGetir(satir, satir.dataset.exe);
  });
}

async function detayAcKapa(satir, exe){
  var sonraki=satir.nextElementSibling;
  if(sonraki && sonraki.classList.contains("alt")){
    var n=sonraki, sil=[];
    while(n && n.classList.contains("alt")){ sil.push(n); n=n.nextElementSibling; }
    sil.forEach(function(x){x.remove()});
    delete D.acikOlanlar[exe];
    satir.setAttribute('aria-expanded','false');
    return;
  }
  D.acikOlanlar[exe]=true;
  satir.setAttribute('aria-expanded','true');
  await detayGetir(satir, exe);
}

async function detayGetir(satir, exe){
  var r=await fetch("/api/sayfalar?bas="+D.bas+"&bit="+D.bit
                    +"&exe="+encodeURIComponent(exe)+"&adet=40");
  var liste=(await r.json()).sayfalar;
  var html=liste.map(function(b){
    return '<tr class="alt"><td></td><td>'+kacis(b.baslik)
      + (b.url?'<div class="kucuk">'+kacis(b.url)+'</div>':'')+'</td>'
      +'<td class="sag">'+sure(b.aktif)+'</td>'
      +'<td class="sag">'+sure(b.gorunur)+'</td>'
      +'<td class="sag">'+sure(b.ustu_kapali)+'</td>'
      +'<td class="sag">'+sure(b.simge)+'</td><td></td></tr>';
  }).join("");
  satir.insertAdjacentHTML("afterend", html ||
    '<tr class="alt"><td></td><td colspan="6">'+m('Ayrıntı yok.')+'</td></tr>');
  tabloEtiketle(satir.closest('table'));
}

function sayfalariCiz(icerik, liste){
  if(!liste || !liste.length){
    icerik.innerHTML='<div class="bos">'+m('Bu aralıkta kayıt yok.')+'</div>'; return; }
  icerik.innerHTML =
    '<table><thead><tr><th class="sira">#</th><th>'+m('Sayfa / pencere')+'</th>'
    +'<th>'+m('Uygulama')+'</th><th class="sag">'+m('Aktif')+'</th><th class="sag">'+m('Görünür')+'</th>'
    +'<th class="sag">'+m('Gün')+'</th></tr></thead><tbody>'
    + liste.map(function(b,i){
        return '<tr><td class="sira">'+(i+1)+'</td>'
          +'<td><div class="ad">'+kacis(b.baslik)+'</div>'
            + (b.url?'<div class="kucuk">'+kacis(b.url)+'</div>':'')+'</td>'
          +'<td class="kucuk">'+kacis(b.ad)+'</td>'
          +'<td class="sag">'+sure(b.aktif)+'</td>'
          +'<td class="sag">'+sure(b.gorunur)+'</td>'
          +'<td class="sag">'+b.gun_sayisi+'</td></tr>';
      }).join("")
    + '</tbody></table>';
}

function sitelerCiz(icerik, liste){
  if(!liste || !liste.length){
    icerik.innerHTML='<div class="bos">'+m('Bu aralıkta adres kaydı yok.')+'<br>'
      +'<span class="kucuk">'+m('Adres kaydı yeni açıldıysa veri birikmesi zaman alır.')+'</span></div>';
    return; }
  var enBuyuk=1;
  liste.forEach(function(a){ enBuyuk=Math.max(enBuyuk,a.aktif); });
  icerik.innerHTML =
    '<table><thead><tr><th class="sira">#</th><th>'+m('Site')+'</th>'
    +'<th class="sag">'+m('Aktif kullanım')+'</th><th class="sag">'+m('Ekranda')+'</th>'
    +'<th class="sag">'+m('Sayfa')+'</th><th class="sag">'+m('Gün')+'</th>'
    +'<th style="width:130px"></th></tr></thead><tbody>'
    + liste.map(function(a,i){
        return '<tr><td class="sira">'+(i+1)+'</td>'
          +'<td class="ad">'+kacis(a.alan)+'</td>'
          +'<td class="sag">'+sure(a.aktif)+'</td>'
          +'<td class="sag">'+sure(a.gorunur)+'</td>'
          +'<td class="sag">'+a.sayfa_sayisi+'</td>'
          +'<td class="sag">'+a.gun_sayisi+'</td>'
          +'<td><div class="cubuk" style="width:'+Math.max(a.aktif/enBuyuk*100,4)+'%">'
            +'<i class="g" style="width:100%"></i></div></td></tr>';
      }).join("")
    + '</tbody></table>';
}

// ---------- olaylar ----------
document.getElementById('excelIndir').onclick=async function(){
  var dugme=this, durum=document.getElementById('indirmeDurumu');
  var bas=document.getElementById('bas').value, bit=document.getElementById('bit').value;
  if(!bas||!bit){ durum.textContent=m('Lütfen başlangıç ve bitiş tarihini seçin.'); return; }
  if(bas>bit){ var t=bas; bas=bit; bit=t; }
  dugme.disabled=true; durum.textContent=m('Dosya hazırlanıyor…');
  try{
    var r=await fetch('/api/excel?bas='+encodeURIComponent(bas)+'&bit='+encodeURIComponent(bit));
    if(!r.ok || !(r.headers.get('Content-Type')||'').includes('spreadsheetml'))
      throw new Error(m('Dosya hazırlanamadı. Lütfen tekrar deneyin.'));
    var blob=await r.blob(), url=URL.createObjectURL(blob), a=document.createElement('a');
    a.href=url; a.download='Ekran-Takip-Hizali_'+bas+'_'+bit+'.xlsx';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function(){URL.revokeObjectURL(url);},60000);
    durum.textContent=m('İndirme başlatıldı:')+' '+bas+' – '+bit;
  }catch(hata){ durum.textContent=hata.message; }
  finally{ dugme.disabled=false; }
};
document.querySelectorAll("[data-hazir]").forEach(function(d){
  d.onclick=function(){
    document.querySelectorAll("[data-hazir]").forEach(function(x){
      x.classList.remove("secili"); });
    d.classList.add("secili");
    var a=hazirAralik(d.dataset.hazir);
    D.bas=a[0]; D.bit=a[1];
    document.getElementById("bas").value=D.bas;
    document.getElementById("bit").value=D.bit;
    D.acikOlanlar={};
    yukle(true);
  };
});
document.getElementById("uygula").onclick=function(){
  D.bas=document.getElementById("bas").value;
  D.bit=document.getElementById("bit").value;
  if(!D.bas||!D.bit) return;
  if(D.bas>D.bit){ var t=D.bas; D.bas=D.bit; D.bit=t;
    document.getElementById("bas").value=D.bas;
    document.getElementById("bit").value=D.bit; }
  document.querySelectorAll("[data-hazir]").forEach(function(x){
    x.classList.remove("secili"); });
  D.acikOlanlar={};
  yukle(true);
};
document.querySelectorAll(".sekme").forEach(function(s){
  s.onclick=function(){
    document.querySelectorAll(".sekme").forEach(function(x){
      x.classList.remove("secili"); });
    s.classList.add("secili");
    D.sekme=s.dataset.sekme;
    sekmeCiz(true);
  };
});

// ---------- baslangic ----------
async function sekmeDurumunuGoster(){
  try{
    var r=await fetch('/api/sekme-durum'), s=await r.json();
    document.getElementById('sekmeDurumu').textContent=s.windows_connected
      ? m('Windows ile sekme takibi açık')+' · '+s.windows_tabs+' '+m('sekme görüldü')+' · '+m('Saatler Zaman çizelgesinde ve Excel indirmesinde.')
      : s.connected ? m('Tarayıcı sekme bağlantısı açık')+' · '+s.tabs+' '+m('sekme görüldü')+'.'
      : m('Sekme okuması henüz doğrulanamadı; pencere takibi devam ediyor.');
  }catch(e){}
}
diliAyarla(dil);
sekmeDurumunuGoster(); setInterval(sekmeDurumunuGoster,15000);
(async function(){
  var r=await fetch("/api/gunler"); var g=await r.json();
  D.ilkGun=g.ilk_gun;
  document.querySelector('[data-hazir="bugun"]').click();
  setInterval(function(){ if(D.bit>=g.bugun) yukle(); }, 20000);
})();
</script></body></html>"""


class _Islemci(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, bicim, *args):
        pass   # konsolu kirletmesin

    def _yerel_adres_mi(self):
        adresler = self.headers.get_all('Host', [])
        port = self.server.server_port
        return len(adresler) == 1 and adresler[0].lower() in (
            '127.0.0.1:%s' % port, 'localhost:%s' % port)

    def _kaynak_uygun_mu(self):
        kaynaklar = self.headers.get_all('Origin', [])
        if len(kaynaklar) > 1:
            return False
        if kaynaklar:
            port = self.server.server_port
            if kaynaklar[0].lower() not in (
                    'http://127.0.0.1:%s' % port, 'http://localhost:%s' % port):
                return False
        return self.headers.get('Sec-Fetch-Site', '').lower() != 'cross-site'

    def _reddet(self, durum=403):
        self.close_connection = True
        self._gonder('{"hata":"İstek reddedildi"}', durum=durum)

    def do_POST(self):
        if not self._yerel_adres_mi():
            return self._reddet(421)
        if self.path in ('/auth/kur', '/auth/gir', '/auth/cik'):
            return self._kimlik_istegi()
        if self.path != '/api/sekme':
            self.send_error(404)
            return
        if not secrets.compare_digest(self.headers.get('X-Ekran-Token',''), _takipci.zaman.token):
            self.send_error(403)
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            return self._reddet(415)
        try:
            boyut = int(self.headers.get('Content-Length','0'))
            if not 0 < boyut <= 8_000_000:
                raise ValueError('İstek boyutu geçersiz')
            veri = json.loads(self.rfile.read(boyut).decode('utf-8'))
            _takipci.zaman.receive(veri)
            self._gonder('{"ok":true}')
        except (ValueError, TypeError, KeyError):
            self.send_error(400)
        except Exception as hata:
            _takipci._hata_yaz(hata)
            self.send_error(500)

    def _gonder(self, govde, tur="application/json; charset=utf-8", durum=200, cerez=None):
        veri = govde.encode("utf-8")
        self.send_response(durum)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(veri)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        if tur.startswith('text/html'):
            scriptler = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', govde, re.I | re.S)
            izinler = ["'sha256-%s'" % base64.b64encode(
                hashlib.sha256(script.encode('utf-8')).digest()).decode('ascii')
                for script in scriptler]
            self.send_header('Content-Security-Policy',
                "default-src 'none'; script-src %s; style-src 'unsafe-inline'; "
                "connect-src 'self'; img-src 'self' blob:; object-src 'none'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'" % ' '.join(izinler))
        if cerez:
            self.send_header("Set-Cookie", cerez)
        self.end_headers()
        self.wfile.write(veri)

    def _oturum_anahtari(self):
        cerez = SimpleCookie()
        try:
            cerez.load(self.headers.get('Cookie', ''))
            return cerez['ekran_oturum'].value if 'ekran_oturum' in cerez else ''
        except Exception:
            return ''

    def _kimlik_istegi(self):
        if not self._kaynak_uygun_mu():
            return self._reddet()
        if self.headers.get('X-Ekran-Form') != '1':
            return self._gonder(json.dumps({'hata': 'İstek reddedildi'}), durum=403)
        if self.path != '/auth/cik' and self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            return self._reddet(415)
        if self.path == '/auth/cik':
            _kimlik.cik(self._oturum_anahtari())
            return self._gonder('{"ok":true}', cerez='ekran_oturum=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')
        try:
            boyut = int(self.headers.get('Content-Length', '0'))
            if not 0 < boyut <= 4096:
                raise ValueError('İstek boyutu geçersiz')
            sifre = json.loads(self.rfile.read(boyut).decode('utf-8')).get('sifre')
            if not isinstance(sifre, str):
                raise ValueError('Şifre gerekli')
            if self.path == '/auth/kur':
                anahtar = _kimlik.kur(sifre)
            else:
                anahtar = _kimlik.gir(sifre)
                if not anahtar:
                    return self._gonder(json.dumps({'hata': 'Şifre yanlış'}), durum=403)
            return self._gonder('{"ok":true}', cerez='ekran_oturum=' + anahtar + '; Path=/; HttpOnly; SameSite=Strict')
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as hata:
            return self._gonder(json.dumps({'hata': str(hata)}, ensure_ascii=False), durum=400)

    def do_GET(self):
        if not self._yerel_adres_mi():
            return self._reddet(421)
        parca = urllib.parse.urlparse(self.path)
        sorgu = urllib.parse.parse_qs(parca.query)
        yol = parca.path

        def al(anahtar, varsayilan=""):
            return sorgu.get(anahtar, [varsayilan])[0]

        try:
            if yol == "/":
                if not _kimlik.gecerli_mi(self._oturum_anahtari()):
                    sayfa = GIRIS_SAYFASI.replace('__ILK_KURULUM__',
                                               'true' if not _kimlik.kurulu_mu() else 'false')
                    return self._gonder(sayfa, "text/html; charset=utf-8")
                return self._gonder(SAYFA, "text/html; charset=utf-8")

            if not _kimlik.gecerli_mi(self._oturum_anahtari()):
                return self._gonder('{"hata":"Giriş gerekli"}', durum=401)

            if yol == '/api/sekme-durum':
                return self._gonder(json.dumps(_takipci.zaman.status()))

            if yol == '/api/zaman':
                bas, bit = date.fromisoformat(al('bas')), date.fromisoformat(al('bit'))
                if bas > bit:
                    raise ValueError('Geçersiz tarih aralığı')
                return self._gonder(json.dumps({'araliklar': _takipci.zaman.intervals(
                    bas.isoformat() + ' 00:00:00',
                    (bit + timedelta(days=1)).isoformat() + ' 00:00:00')}))

            if yol == "/api/gunler":
                return self._gonder(json.dumps({
                    "ilk_gun": _takipci.depo.ilk_gun(),
                    "bugun": date.today().strftime("%Y-%m-%d"),
                }))

            # Ekranda anlik dogru veri gorunsun diye once tamponu diske bosalt
            _takipci.diske_yaz()
            bas, bit = al("bas"), al("bit")

            if yol == "/api/excel":
                from excel_rapor import olustur
                try:
                    veri = olustur(_takipci.depo.dosya, bas, bit)
                except ValueError:
                    self.send_error(400, 'Invalid date range')
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                self.send_header('Content-Disposition', 'attachment; filename="Ekran-Takip-Hizali_%s_%s.xlsx"' % (bas, bit))
                self.send_header('Content-Length', str(len(veri)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('X-Frame-Options', 'DENY')
                self.end_headers()
                self.wfile.write(veri)
                return

            if yol == "/api/aralik":
                return self._gonder(json.dumps({
                    "ozet": _takipci.depo.ozet(bas, bit),
                    "uygulamalar": _takipci.depo.uygulamalar(bas, bit),
                    "gunluk": _takipci.depo.gunluk_seri(bas, bit),
                    "durum": _takipci.durum_bilgisi,
                    "sistem": {
                        "db_mb": _takipci.depo.veritabani_boyutu() / 1048576.0,
                        "satir": _takipci.depo.satir_sayisi(),
                    },
                }))

            if yol == "/api/sayfalar":
                exe = al("exe") or None
                adet = min(int(al("adet", "100") or 100), 500)
                return self._gonder(json.dumps({
                    "sayfalar": _takipci.depo.sayfalar(bas, bit, exe, adet),
                }))

            if yol == "/api/siteler":
                return self._gonder(json.dumps({
                    "alanlar": _takipci.depo.alanlar(bas, bit),
                }))
        except (ValueError, TypeError, OverflowError):
            return self._gonder('{"hata":"Geçersiz istek"}', durum=400)
        except Exception as hata:
            _takipci._hata_yaz(hata)
            return self._gonder('{"hata":"İşlem tamamlanamadı"}', durum=500)

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()


def baslat(takipci, port):
    global _takipci, _kimlik
    _takipci = takipci
    os.makedirs(os.path.dirname(KIMLIK_DOSYASI), exist_ok=True)
    _kimlik = Kimlik(KIMLIK_DOSYASI)
    sunucu = ThreadingHTTPServer(("127.0.0.1", port), _Islemci)
    sunucu.daemon_threads = True
    sunucu.serve_forever()
