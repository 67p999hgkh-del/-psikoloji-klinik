# Cursor Devretme Paketi — PsikoHukuk Klinik

Bu klasörü Cursor’da **File → Open Folder** ile aç. Aşağıdaki adımları sırayla yap.

## 1) Ortamı kur (ilk açılışta bir kez)

Terminalde proje kökünde:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

İsteğe bağlı `.env` (üretim / e-posta için). Şablon: `.env.example`

## 2) Uygulamayı çalıştır

```bash
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
python app.py
```

- Site: http://127.0.0.1:5000  
- Admin: http://127.0.0.1:5000/admin/giris  
- Kullanıcı: `admin` / Şifre: `admin123`

> Not: `/admin/` (sonda `/`) 404 verir. Doğru adres: `/admin` veya `/admin/giris`.

## 3) Pakette ne var?

| İçerik | Açıklama |
|--------|----------|
| Kaynak kod | Flask app, modeller, şablonlar, CSS/JS |
| `instance/klinik.db` | Güncel SQLite veritabanı (demo + geliştirme verisi) |
| `requirements.txt` | Python bağımlılıkları |
| `GODADDY_YUKLEME.md` | Canlıya alma notları |
| Bu dosya | Cursor kurulum ve bağlam |

Pakete **dahil edilmedi:** `.venv`, `__pycache__`, `.env` (gizli anahtarlar).

## 4) Önemli dosyalar (Cursor’a bağlam için)

- `app.py` — Ana route’lar, seed, admin randevular/kullanıcılar
- `routes_extra.py` — Seanslar, notlar, faturalar, PsikoPlan, danışan portalı
- `models.py` — SQLAlchemy modelleri
- `psikoplan.py` — Analiz KPI’ları, sync, AI seans özeti kuralları
- `static/css/admin.css` — Admin panel UI
- `templates/admin/` — Admin şablonları (`sessions.html` = Seans Kayıtları)

## 5) Son yapılan işler (devam noktası)

- Hukuk / avukat özellikleri kaldırıldı; odak klinik.
- Admin paneli kurumsal hale getirildi (topbar, sidebar kategorileri).
- Kullanıcılar: Danışanlar / Terapistler / Yöneticiler sekmeleri.
- PsikoPlan Analiz gerçek verilerle bağlandı.
- **Seans Kayıtları** modernize edildi: filtreler, özet kartlar, badge’ler, satır tıklanınca sağ drawer, CSV dışa aktarma, yazdırma.
- Randevular sayfası filtre + sayfalama ile düzenlendi.

## 6) Cursor’da nasıl çalışılsın?

Arkadaşa önerilen ilk prompt örneği:

> “Bu PsikoHukuk Flask klinik paneli. Önce `CURSOR_DEVRET.md` ve `README.md` oku. `python app.py` ile ayağa kaldır. Sonra Seans Kayıtları sayfasındaki X özelliğini geliştir.”

Kısa kural: Mevcut yapı ve admin CSS dilini bozma; UI değişikliklerinde `static/css/admin.css` + ilgili `templates/admin/*.html` + gerekirse `routes_extra.py` / `app.py` birlikte güncellenir.

## 7) Canlı (GoDaddy)

Ayrıntı: `GODADDY_YUKLEME.md` — `passenger_wsgi.py` ile Python App.

---

Sorun çıkarsa: önce `.venv` + `pip install -r requirements.txt`, sonra `python app.py`. Veritabanı bozuksa `instance/klinik.db` silinince ilk çalıştırmada yeniden seed oluşur (demo veriler yenilenir).
