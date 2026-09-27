# ScreenLedger (Ekran Takip)

**Windows için kişisel ekran süresi, uygulama ve tarayıcı sekmesi takibi.**
**A private screen-time, app-usage, and browser-tab tracker for Windows.**

Bilgisayar başında zamanınızın nereye gittiğini, yalnızca günlük toplamlarla değil, **hangi uygulamanın ve sayfanın ne zaman ekranda olduğunu** görerek anlayın. Veriler kendi bilgisayarınızda kalır; seçtiğiniz tarih aralığını ayrıntılı bir Excel dosyası olarak indirebilirsiniz.

Understand where your computer time goes beyond daily totals: see **which apps and pages were on screen, and when**. Your records stay on your computer, and you can export a detailed Excel report for any selected date range.

[🇹🇷 Türkçe](#turkce) · [🇬🇧 English](#english)

---

<a id="turkce"></a>
## 🇹🇷 Türkçe

### Ekran Takip ne işe yarar?

“Bugün bilgisayarı kaç saat kullandım?” sorusu çoğu zaman yeterli değildir. Asıl merak edilen, bu sürenin **hangi uygulamalara, sitelere ve sayfalara dağıldığıdır**. Ekran Takip, Windows bilgisayarınızda açık pencereleri ve tarayıcı sekmelerini izleyerek bunu anlaşılır bir rapora dönüştürür.

Örneğin gün sonunda bir uygulamanın ne kadar süre seçili kaldığını, bir toplantı sayfasının hangi saatlerde göründüğünü veya bir sekmenin ne zaman arka plana geçtiğini inceleyebilirsiniz. Zaman çizelgesi, tek bir toplam yerine gün içindeki değişimi gösterir. Tarayıcıdaki rapor sekmesini açık tutmanız gerekmez; takip ayrı bir program olarak çalışır.

Bu proje **kişisel kullanım** içindir. Kayıtları çevrimiçi bir hesaba göndermez ve başka birinin bilgisayarını uzaktan izlemez.

### Neler görebilirsiniz?

- **Uygulamalar:** Hangi program ne kadar kullanılmış, ekranda görünmüş, başka pencerelerin altında kalmış veya simge durumuna küçültülmüş?
- **Sayfalar ve siteler:** Tarayıcıda hangi sayfa ve site ne kadar süreyle görülmüş? Desteklenen durumlarda sekmeler arası geçiş ve arka planda kalma süreleri de gösterilir.
- **Zaman çizelgesi:** Uygulama veya sekmenin durumunun gün içinde ne zaman değiştiği. Böylece yalnızca “2 saat” değil, “hangi saat aralıklarında?” sorusuna da bakabilirsiniz.
- **Esnek tarihler:** Bugün, dün, pazartesiden başlayan bu hafta, son yedi gün, bu ay, son üç ay, tüm kayıtlar veya seçtiğiniz iki tarih.
- **Ayrıntılı Excel indirmesi:** Seçilen aralık için uygulama toplamları, uygulama içindeki sayfalar, gün ve saat ayrıntıları, sekme saatleri ve zaman çizelgesi ayrı çalışma sayfalarında yer alır.

### Hızlı başlangıç

**Gerekenler:** Windows, Python 3.11 veya üzeri ve ilk kurulumda gerekli paketleri indirmek için internet bağlantısı. Proje Python 3.11 ile geliştirilip denenmiştir. Yönetici izni gerekmez.

1. GitHub üzerinde **Code → Download ZIP** seçeneğiyle kaynak dosyaları indirin ve kalıcı, yazma izniniz olan bir klasöre çıkarın. Kayıtlar da bu klasörde tutulacağı için klasörü kullanırken silmeyin veya taşımayın.
2. Python kurulu değilse [resmî Windows indirme sayfasından](https://www.python.org/downloads/windows/) kurun.
3. Çıkardığınız klasörde `kur.bat` dosyasını çift tıklayın. Gerekli paketler uygulamaya ait ayrı bir çalışma ortamına kurulur; takip başlar ve Windows hesabınızla oturum açtığınızda otomatik başlatılacak şekilde ayarlanır.
4. Tarayıcıda `http://127.0.0.1:8777/` adresini açın. İlk girişte boş olmayan bir rapor şifresi oluşturun ve güvenli bir yerde saklayın.

Sonraki günlerde raporu açmak için `raporu-ac.bat` dosyasını kullanabilirsiniz. Bu dosya yalnızca rapor sayfasını açar; takibi başlatmaz veya kurmaz. Bilgisayar yeniden açıldığında takip, **Windows hesabınızla oturum açmanızın ardından** otomatik başlar. Rapor sekmesinin açık kalması gerekmez.

Sayfa açılmıyorsa kurulum klasöründeki `baslatma.log`, `calisma.log` ve `hatalar.log` dosyalarını kontrol edin. Hata paylaşırken dosya yollarınızı ve ziyaret ettiğiniz adresleri gizleyin.

### Süreler nasıl okunur?

| Rapordaki ad | Anlamı |
| --- | --- |
| Aktif kullanım | O anda seçili olan pencerenin süresi. Her saniye fare veya klavye hareketi yapmanız gerekmez. |
| Ekranda görünür | Pencerenin ekranda görüldüğü süre. Birden fazla pencere aynı anda görünüyorsa hepsine süre yazılabilir. |
| Üstü kapalı | Pencere açıktır, fakat başka pencerelerin altında veya ekranın dışında kalmıştır. |
| Simge durumunda | Pencere görev çubuğuna küçültülmüştür. |
| Boşta | Uzun süre klavye, fare veya ekran hareketi algılanmazsa kullanım sayımı durur. Kilitli veya uyuyan bilgisayarda süre sayılmaz. |

**Önemli:** Görünür pencere sürelerinin toplamı, aynı anda birden fazla pencere görülebildiği için geçen gerçek zamandan büyük olabilir. Hareketli video genellikle bilgisayarın boşta sayılmasını önler; bu, videonun başında aktif olarak çalıştığınız anlamına gelmez.

### Tarayıcı sekmeleri

Ekran Takip, Chrome ve Edge sekmelerini Windows'un sağladığı pencere/erişilebilirlik bilgileri üzerinden **eklentisiz** okuyabilir. Bu yöntem bazı tarayıcı durumlarında sekme geçişlerini veya hiç seçilmemiş arka plan sekmelerinin tam adreslerini gösteremeyebilir.

Daha kesin oluşturulma, seçilme ve kapanma bilgisi isterseniz `sekme-eklentisi` klasöründeki **isteğe bağlı** tarayıcı eklentisini kurabilirsiniz. Önce ana uygulamayı bir kez çalıştırın; bu bilgisayara ait bağlantı ayarı otomatik oluşur. Ardından Chrome veya Edge eklenti yönetiminde **Geliştirici modu → Paketlenmemiş öğe yükle** seçeneğiyle `sekme-eklentisi` klasörünü seçin. Eklenti bilgileri yalnızca bilgisayarınızdaki uygulamaya iletir; gizli pencereleri bilerek izlemez.

Eklenti olmadan kullanılan Windows okuması, tarayıcı görünür hâle getiriyorsa gizli pencere başlıklarını okuyabilir. Gizli gezinmenin hiçbir şekilde kaydedilmediğini varsaymayın. Tarayıcı kapalıyken veya takip çalışmıyorken gerçekleşen olaylar sonradan eksiksiz oluşturulamaz.

### Gizlilik ve verileriniz

- Rapor sayfası yalnızca **bu bilgisayarda** `127.0.0.1:8777` adresinde dinler. Uygulama kayıtlarınızı bulut hesabına göndermez.
- Kullanım kayıtları kurulum klasöründeki `veri.db` dosyasındadır. Çalışma sırasında `veri.db-wal` ve `veri.db-shm` yardımcı dosyaları oluşabilir. Program açıkken bu dosyaları silmeyin.
- `kimlik.json` şifrenizin açık metnini değil, doğrulamada kullanılan tuzlu özetini saklar. Rapor şifresi **veritabanını şifrelemez**: bilgisayarınızdaki kayıt dosyasına erişimi olan başka bir kullanıcı veya program içeriğini ayrıca okuyabilir.
- İsteğe bağlı eklentinin yerel bağlantı anahtarı `sekme-eklentisi/ayar.json` dosyasındadır. Bu dosyayı veya günlükleri paylaşmayın.
- Ziyaret edilen sayfaların başlıkları ve adresleri özel toplantı ya da hesap bağlantıları içerebilir. İndirdiğiniz Excel dosyalarını paylaşmadan önce gözden geçirin.
- Ekrandaki hareketi anlamak için görüntünün çok küçük bir örneği karşılaştırılır; ekran görüntüsü dosyaya kaydedilmez.

Şifreyi unutursanız e-posta ile kurtarma yoktur. `kimlik.json` dosyasını silmek yeni şifre oluşturma ekranını açar ve `veri.db` içindeki kullanım kayıtlarını silmez. Bu nedenle bilgisayardaki dosya erişim izinleri önemlidir.

### Yedekleme, güncelleme ve kaldırma

**Yedekleme:** `kaldir.bat` dosyasını çalıştırıp uygulamanın güvenle kapandığını doğrulayın. Sonra `veri.db`, `kimlik.json` ve eklenti kullanıyorsanız `sekme-eklentisi/ayar.json` dosyalarını güvenli bir yere kopyalayın. Uygulama açıkken yalnızca ana veritabanı dosyasını kopyalamak son kayıtları kaçırabilir. Takibi yeniden başlatmak için `kur.bat` dosyasını çalıştırın.

**Güncelleme:** Önce yedek alın. Yeni kod dosyalarını mevcut klasöre aktarırken `veri.db`, `kimlik.json` ve `sekme-eklentisi/ayar.json` dosyalarının üzerine yazmayın. Sonra `kur.bat` dosyasını çalıştırın. Yeni bir klasöre geçiyorsanız kayıt dosyalarını eski kurulum kapalıyken taşıyın; iki kopyayı aynı anda çalıştırmayın.

**Kaldırma:** `kaldir.bat` otomatik başlamayı kaldırır ve uygulamayı kapatır; kişisel kayıtlarınızı silmez. Tamamen kaldırmadan önce verilerinizi yedekleyin. Uygulamanın güvenle kapanamadığına dair uyarı varsa klasörü silmeyin.

### Teknik ayrıntılar

Bu bölüm, kaynak kodunu incelemek veya geliştirmek isteyenler içindir.

- Takip programı yaklaşık **iki saniyede bir** açık pencereleri ölçer. Kısa aralıklı durum değişimlerinin saatleri bu yüzden yaklaşık olabilir. Uyku veya beklenmedik kapanış sırasında kesin bitiş saati bilinemeyebilir.
- Klavye/fare hareketi yokken ekrandaki hareket de aralıklarla denetlenir. Yaklaşık **on dakika** boyunca etkinlik algılanmazsa bilgisayar boşta sayılır. Ölçüm aralığı ve eşikler `takip.py` dosyasının başındaki ayarlardır.
- Kayıtlar yerel bir SQLite veritabanında tutulur. Rapor için tarayıcıda çalışan yerel bir arayüz, Excel çıktısı için `openpyxl`, Windows erişilebilirlik okuması için `comtypes` kullanılır. Paket listesi `requirements.txt` dosyasındadır.
- Başlıca dosyalar: `takip.py` (ölçüm döngüsü), `depo.py` (kayıt saklama), `arayuz.py` (yerel rapor), `excel_rapor.py` (Excel çıktısı), `kimlik.py` (rapor girişi), `kur.py` (kurulum/otomatik başlangıç) ve `sekme-eklentisi` (isteğe bağlı tarayıcı desteği).
- Kaynak kodunda değişiklik yapıyorsanız temel denemeleri `py -3 -m unittest test_kurulum test_kimlik test_zaman test_sekme_windows` komutuyla çalıştırabilirsiniz. Excel denemesi için `py -3 test_excel_rapor.py` kullanılabilir. Proje diğer işletim sistemlerinde denenmemiştir.

**Bilinen sınırlar:** Pencere örtüşmesi dikdörtgen alanlar üzerinden yaklaşık hesaplanır; şeffaf veya alışılmadık pencerelerde sapma olabilir. Bazı tam ekran oyunlar pencere başlığını sağlamaz. Her tarayıcı, sekme bilgisini Windows üzerinden aynı ayrıntıda sunmaz.

**Herkese açık paylaşım notu:** `.gitignore` yerel kayıtları, günlükleri, şifre/eklenti ayarlarını ve çalışma ortamını kaynak kodu paketinin dışında tutmak için hazırlanmıştır. Yine de GitHub'a dosya göndermeden önce gönderilecek dosyaları elle kontrol edin; bu liste önceden eklenmiş dosyaları geriye dönük olarak kaldırmaz.

---

<a id="english"></a>
## 🇬🇧 English

### What is ScreenLedger?

“How long was I on my computer today?” is only the beginning. The more useful questions are **which apps, websites, and pages used that time**, and **when** they were on screen. ScreenLedger turns open Windows windows and browser tabs into a readable, local activity report.

At the end of the day, you can inspect how long an app was selected, when a meeting page appeared, and when a tab moved into the background. The timeline shows changes throughout the day instead of just one total. The report tab does not need to stay open: tracking runs separately.

This is a **personal-use** tool. It does not send your activity history to an online account or remotely monitor another computer.

### What can you see?

- **Apps:** Time spent selected, visible on screen, covered by other windows, or minimized.
- **Pages and websites:** Time associated with browser pages and sites. When available, tab switches and background-tab periods are included.
- **Timeline:** When an app or tab changed state, so you can answer “at what times?” rather than seeing only a daily total.
- **Date ranges:** Today, yesterday, this calendar week (starting Monday), the last seven days, this month, the last three months, all recorded time, or your own date range.
- **Detailed Excel export:** App totals, pages within apps, daily/hourly detail, tab times, and a detailed timeline are organized into separate worksheets for the selected period.

### Quick start

**Requirements:** Windows, Python 3.11 or newer, and an internet connection for downloading dependencies during first-time setup. Development and testing were done with Python 3.11. Administrator rights are not required.

1. On GitHub, choose **Code → Download ZIP** and extract the source into a permanent folder where you can write files. Your records will live there too, so do not delete or move the folder while using the app.
2. If Python is not installed, get it from the [official Windows download page](https://www.python.org/downloads/windows/).
3. Double-click `kur.bat` in the extracted folder. It installs dependencies into a separate environment for this app, starts tracking, and sets it to start after you sign in to Windows.
4. Open `http://127.0.0.1:8777/` in your browser. On first use, create a non-empty report password and keep it somewhere safe.

Later, `raporu-ac.bat` opens the report page. It does not install or start tracking. After a reboot, tracking starts automatically **once you sign in to your Windows account**. You do not need to leave the report tab open.

If the page does not open, check `baslatma.log`, `calisma.log`, and `hatalar.log` in the installation folder. Redact personal paths and visited URLs before sharing logs in a bug report.

### Understanding the time categories

| Report label | Meaning |
| --- | --- |
| Active use (`Aktif kullanım`) | Time for the selected window. It does **not** require a mouse or keyboard action every second. |
| Visible (`Ekranda görünür`) | Time the window is visible on screen. Multiple windows can be visible at once. |
| Covered (`Üstü kapalı`) | The window is open but behind other windows or outside the visible area. |
| Minimized (`Simge durumunda`) | The window is minimized to the taskbar. |
| Idle (`Boşta`) | Counting stops after an extended period without keyboard, mouse, or screen movement. Locked and sleeping time is not counted. |

**Important:** Visible-time totals can exceed elapsed wall-clock time because several windows may be visible together. A moving video usually prevents the computer from being considered idle; that does not necessarily mean you were actively working.

### Browser tabs

Without an extension, ScreenLedger can read Chrome and Edge tab information exposed through Windows window/accessibility interfaces. Some browser states do not expose every tab switch or the full address of a background tab that has never been selected.

For more precise tab-created, tab-selected, and tab-closed events, you can install the **optional** browser extension in `sekme-eklentisi`. Run the main app once first so it creates this computer's local connection settings. Then open Chrome or Edge extension management, enable **Developer mode**, choose **Load unpacked**, and select the `sekme-eklentisi` folder. The extension sends events only to the app running on your computer. It deliberately does not track incognito windows.

The extension-free Windows reader may still see incognito window titles if the browser exposes them. Do not assume private browsing is entirely excluded from recording. Events that happened while the browser or tracker was not running cannot be perfectly reconstructed later.

### Privacy and your data

- The report server listens only at `127.0.0.1:8777` **on your computer**. Activity records are not uploaded to a cloud account.
- Records are stored in `veri.db` inside the installation folder. While the app runs, `veri.db-wal` and `veri.db-shm` helper files may also exist. Do not delete these files while the app is running.
- `kimlik.json` stores a salted password verifier, not your plaintext password. The report password **does not encrypt the database**: another user or program with access to the file can read it separately.
- The optional extension's local connection key is in `sekme-eklentisi/ayar.json`. Do not share that file or logs.
- Page titles and URLs can contain private meeting or account links. Review exported Excel files before sharing them.
- A tiny sample of the screen is compared to detect motion; screenshots are not saved to disk.

There is no email-based password recovery. Deleting `kimlik.json` allows a new password to be set without deleting the activity history in `veri.db`. This is why operating-system file permissions still matter.

### Backup, updates, and removal

**Backup:** Run `kaldir.bat` and confirm the app has shut down safely. Copy `veri.db`, `kimlik.json`, and, if you use the extension, `sekme-eklentisi/ayar.json` to a secure location. Copying only the main database while the app is running may miss recent records. Run `kur.bat` to resume tracking.

**Update:** Back up first. Copy the new source files into the existing folder without overwriting `veri.db`, `kimlik.json`, or `sekme-eklentisi/ayar.json`. Then run `kur.bat`. If you move to a new folder, move those user-data files while the old installation is stopped; do not run both copies simultaneously.

**Remove:** `kaldir.bat` removes automatic startup and stops the app, but does not delete your records. Back up before deleting the installation folder yourself. Do not delete it if shutdown reports an error.

### Technical details

This section is for people who want to inspect or develop the source code.

- The tracker samples open windows about **every two seconds**. State-change times are therefore approximate. Sleep or an unexpected shutdown may leave the exact end time unknown.
- When keyboard/mouse input stops, screen motion is checked periodically too. The computer is considered idle after roughly **ten minutes** without detected activity. Sampling and idle thresholds are defined near the top of `takip.py`.
- Records live in a local SQLite database. The report is served by a local browser interface; `openpyxl` creates Excel files, and `comtypes` reads Windows accessibility information. Dependencies are listed in `requirements.txt`.
- Main files: `takip.py` (sampling loop), `depo.py` (storage), `arayuz.py` (local report), `excel_rapor.py` (Excel export), `kimlik.py` (report authentication), `kur.py` (setup and startup), and `sekme-eklentisi` (optional browser integration).
- Run the core tests with `py -3 -m unittest test_kurulum test_kimlik test_zaman test_sekme_windows`. The Excel test can be run with `py -3 test_excel_rapor.py`. Other operating systems have not been tested.

**Known limits:** Window occlusion is estimated with rectangles, so transparent or unusual windows can differ from what you perceive. Some fullscreen games do not expose a window title. Browsers vary in how much tab information they expose through Windows.

**Before making the repository public:** `.gitignore` is intended to exclude local records, logs, password/extension settings, and the working environment from source control. Still inspect the actual files you are about to upload: ignore rules do not retroactively remove files that were already added.
