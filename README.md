# MindCare Psikoloji — Klinik Web Sitesi

Psikoloji kliniği için çok terapistli randevu sistemi, blog ve admin paneli içeren web uygulaması.

## Özellikler

- **Klinik tanıtım sitesi** — Ana sayfa, hakkımızda, iletişim
- **Çoklu terapist profilleri** — Her terapistin kendi profil sayfası
- **Randevu panelleri** — Her terapist için ayrı randevu formu
- **Blog** — Psikoloji yazıları
- **Admin paneli** — Terapist, randevu, blog ve widget yönetimi
- **Widget sistemi** — Ana sayfaya modüler bileşenler (hero, istatistik, SSS, referanslar vb.)

## Kurulum

### Gereksinimler

- Python 3.9+
- pip

### Adımlar

```bash
cd ~/Projects/psikoloji-klinik

# Sanal ortam oluştur
python3 -m venv .venv
source .venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı başlat
python app.py
```

Tarayıcıda açın: **http://localhost:5000**

## Admin Paneli

- URL: **http://localhost:5000/admin/giris**
- Kullanıcı adı: `admin`
- Şifre: `admin123`

> İlk çalıştırmada veritabanı otomatik oluşturulur ve örnek veriler yüklenir.

## Sayfa Yapısı

| Sayfa | URL |
|-------|-----|
| Ana Sayfa | `/` |
| Terapistler | `/terapistler` |
| Terapist Profili | `/terapist/<slug>` |
| Randevu | `/randevu` veya `/randevu/<slug>` |
| Blog | `/blog` |
| Admin | `/admin` |

## Widget Türleri

Admin panelinden ana sayfaya eklenebilir widget türleri:

- `hero` — Hero banner
- `stats` — İstatistik kartları
- `testimonials` — Danışan referansları
- `faq` — Sık sorulan sorular
- `cta` — Çağrı butonu
- `hours` — Çalışma saatleri
- `text` — Serbest metin bloğu

## Proje Yapısı

```
psikoloji-klinik/
├── app.py              # Ana Flask uygulaması
├── models.py           # Veritabanı modelleri
├── requirements.txt
├── static/
│   ├── css/
│   └── js/
└── templates/
    ├── admin/          # Admin panel şablonları
    └── partials/       # Ortak bileşenler
```

## Sonraki Adımlar

- E-posta bildirimleri (randevu onayı)
- Terapist takvim entegrasyonu
- Online ödeme
- Çoklu dil desteği
- Üretim ortamı için PostgreSQL geçişi
