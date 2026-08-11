# GoDaddy Deluxe — Yükleme Rehberi

Bu paket **GoDaddy Linux Web Hosting (cPanel)** için hazırlanmıştır.
cPanel içinde **Setup Python App** (Python Uygulaması Kur) aracı olmalıdır.

> Windows Hosting (Plesk) bu Flask uygulamasını desteklemez. Linux + cPanel seçin.

---

## 1) Bu zip’i yükleyin

1. GoDaddy → **Hosting** → **cPanel’e Git**
2. **Dosya Yöneticisi** (File Manager) açın
3. `public_html` veya ayrı bir klasör oluşturun, örn. `psikoloji-klinik`
4. Zip’i yükleyip **Extract** edin  
   (veya bilgisayarınızdan **FTP / FileZilla** ile klasörü yükleyin)

Önerilen yapı:

```
/home/KULLANICIADI/psikoloji-klinik/
  app.py
  passenger_wsgi.py
  requirements.txt
  models.py
  templates/
  static/
  instance/
  tmp/
  ...
```

Alan adı köküne (`/`) bağlayacaksanız uygulama kökünü `public_html` yapabilirsiniz.
Mevcut WordPress varsa çakışır; ayrı alt alan adı kullanın (örn. `app.siteniz.com`).

---

## 2) cPanel → Setup Python App

1. **SOFTWARE** → **Setup Python App**
2. **Create Application**
3. Ayarlar:
   - **Python version:** `3.9` veya üzeri (mümkünse 3.11)
   - **Application root:** `psikoloji-klinik` (zip’i açtığınız klasör)
   - **Application URL:** domain’iniz (`/` veya alt yol)
   - **Application startup file:** `passenger_wsgi.py`
   - **Application Entry point:** `application`
4. **Create**

cPanel bir sanal ortam oluşturur ve `.htaccess` yazar — silmeyin.

---

## 3) Paketleri kurun

Setup Python App ekranında:

1. **Configuration files** → `requirements.txt` seçin
2. **Run Pip Install**

veya SSH ile:

```bash
source ~/virtualenv/psikoloji-klinik/3.11/bin/activate
cd ~/psikoloji-klinik
pip install -r requirements.txt
```

*(virtualenv yolu cPanel’de uygulama satırında görünür.)*

---

## 4) Ortam değişkenleri (önerilir)

Setup Python App → **Environment variables**:

| Değişken | Örnek |
|----------|--------|
| `SECRET_KEY` | uzun rastgele bir metin |
| `EMAIL_ENABLED` | `true` (e-posta kullanacaksanız) |

E-posta ayarlarını daha sonra admin panelinden de girebilirsiniz.

---

## 5) Yazma izinleri

Dosya Yöneticisi’nde şu klasörlere yazma izni verin (`755` veya `775`):

- `instance/` (SQLite veritabanı)
- `static/uploads/`
- `static/uploads/therapists/`
- `tmp/`

---

## 6) Uygulamayı başlatın / yeniden başlatın

Setup Python App → **Restart**

veya SSH:

```bash
mkdir -p ~/psikoloji-klinik/tmp
touch ~/psikoloji-klinik/tmp/restart.txt
```

---

## 7) İlk giriş

Site açıldıktan sonra:

- Admin: `https://SITENIZ.com/admin/giris`
- Kullanıcı: `admin`
- Şifre: `admin123`

**Mutlaka şifreyi değiştirin** (Admin → Kullanıcılar).

İlk açılışta veritabanı otomatik oluşur / seed edilir.

---

## Sorun giderme

| Belirti | Ne yapın |
|---------|----------|
| 503 / Passenger hatası | `passenger_wsgi.py` ve entry point `application` olduğundan emin olun; Restart |
| Boş sayfa / 500 | Setup Python App → log; `requirements.txt` kurulu mu bakın |
| CSS/JS yok | `static/` klasörünün yüklendiğini kontrol edin |
| Veritabanı hatası | `instance/` yazılabilir mi? |
| Python App yok | Hosting Linux cPanel mi? Destek’e “Setup Python App” sorun |

---

## Bu pakette olmayanlar

- `.venv` (sunucuda cPanel oluşturur)
- `.git`
- `__pycache__`

`instance/klinik.db` varsa yedek verinizle gelir; yoksa ilk çalıştırmada yeniden oluşur.
