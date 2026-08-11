# HİZMET SÖZLEŞMESİ — Klinik Yönetim Platformu

**Sözleşme No:** `[SOZ-2026-001]`  
**Tarih:** `[GG.AA.YYYY]`

---

## 1. Taraflar

**Hizmet Sağlayıcı ("Sağlayıcı")**  
Unvan: `[Şirket Adı]`  
Adres: `[Adres]`  
Vergi Dairesi / No: `[VD / VKN]`  
MERSİS: `[MERSİS No]`  
E-posta: `[e-posta]` · Tel: `[telefon]`

**Müşteri ("Klinik")**  
Unvan: `[Klinik Adı]`  
Adres: `[Adres]`  
Vergi Dairesi / No: `[VD / VKN]` (varsa)  
Yetkili: `[Ad Soyad — Unvan]`  
E-posta: `[e-posta]` · Tel: `[telefon]`

---

## 2. Sözleşmenin Konusu

Bu sözleşme; Sağlayıcı'nın Klinik'e psikoloji klinik yönetim yazılımı ("Platform") kurulumu, lisanslama, barındırma, bakım ve destek hizmetlerinin sunulmasına ilişkin hak ve yükümlülükleri düzenler.

**Seçilen paket:** `[Başlangıç / Profesyonel / Kurumsal / Özel]`  
**Ek No (varsa):** Teklif formu `[TEKLIF-2026-001]` bu sözleşmenin ayrılmaz parçasıdır.

---

## 3. Hizmet Kapsamı

### 3.1 Yazılım modülleri
Paket kapsamındaki modüller Teklif Formu'nda listelenmiştir. Paket dışı modüllere erişim, ayrı yazılı onay ve ek ücret karşılığında sağlanır.

### 3.2 Kurulum hizmetleri
- Sunucu/ barındırma ortamı hazırlığı
- Domain & SSL yapılandırması
- Tema ve marka uyarlaması
- İlk veri girişi (Teklif'te belirtilen kapsamda)
- Kullanıcı eğitimi (Teklif'te belirtilen saat)

### 3.3 Sürekli hizmetler (abonelik)
- Platform barındırma ve SSL
- Güvenlik güncellemeleri
- Yedekleme
- Teknik destek (paket SLA'sına göre)
- Hata giderme

---

## 4. Ücret ve Ödeme

### 4.1 Kurulum bedeli
Tek seferlik kurulum bedeli: **`[XXX.XXX ₺]`** (KDV hariç)

### 4.2 Aylık hizmet bedeli
Aylık abonelik: **`[X.XXX ₺/ay]`** (KDV hariç)

### 4.3 Ödeme takvimi
Teklif Formu'ndaki ödeme planı geçerlidir. Geciken ödemelerde Sağlayıcı, 7 gün yazılı ihtar sonrası hizmeti askıya alma hakkını saklı tutar.

### 4.4 Yıllık ödeme indirimi
12 aylık peşin ödemede **%15 indirim** uygulanır.

### 4.5 Fiyat güncellemesi
Sağlayıcı, yıllık abonelik yenilemelerinde fiyatı en fazla **TÜFE + %5** oranında artırabilir. Artış en az **60 gün önce** yazılı bildirilir.

---

## 5. Süre ve Yenileme

- **İlk süre:** 12 ay (kurulum tamamlanma tarihinden itibaren)
- **Yenileme:** Süre bitiminden 30 gün önce yazılı fesih bildirilmezse, aynı koşullarla **1 yıl** otomatik yenilenir
- **Deneme / pilot:** Taraflarca kararlaştırılırsa ilk 30 gün içinde modül kapsamı sınırlı tutulabilir

---

## 6. KVKK ve Veri İşleme

### 6.1 Veri sorumlusu
Klinik, danışan ve personel kişisel verileri bakımından **veri sorumlusu**dur.

Sağlayıcı, Platform'un işletilmesi kapsamında **veri işleyen** sıfatıyla hareket eder.

### 6.2 Veri işleme amacı
Kişisel veriler yalnızca:
- Randevu ve seans yönetimi
- Danışan portalı hizmetleri
- E-posta bildirimleri
- Platform güvenliği ve yedekleme

amaçlarıyla işlenir.

### 6.3 Teknik ve idari tedbirler
Sağlayıcı aşağıdaki tedbirleri uygular:
- SSL/TLS şifreleme
- Rol tabanlı erişim kontrolü
- Günlük yedekleme
- Denetim logları (Kurumsal paket)
- Sunucu erişim kısıtlaması

### 6.4 Veri saklama yeri
Veriler `[Türkiye / AB — belirtiniz]` lokasyonlu sunucularda saklanır.

### 6.5 Saklama süresi
Sözleşme süresince + fesih sonrası **90 gün** (veri export süresi). 90 gün sonunda veriler silinir; yasal saklama yükümlülükleri saklıdır.

### 6.6 Veri ihlali bildirimi
Kişisel veri ihlali durumunda Sağlayıcı, **72 saat** içinde Klinik'i bilgilendirir.

### 6.7 Alt veri işleyenler
Barındırma, e-posta ve analitik sağlayıcıları alt veri işleyen olarak kullanılabilir. Liste talep üzerine paylaşılır.

### 6.8 Aydınlatma yükümlülüğü
Danışan aydınlatma metni, açık rıza ve KVKK başvuru süreçlerinden **Klinik** sorumludur.

---

## 7. SLA (Hizmet Seviyesi Taahhüdü)

| Paket | Destek saatleri | Yanıt süresi | Uptime hedefi |
|-------|-----------------|--------------|---------------|
| Başlangıç | İş saatleri | 48 saat | %99 |
| Profesyonel | İş saatleri | 24 saat | %99,5 |
| Kurumsal | İş saatleri + acil hat | 4 saat | %99,5 |
| Özel | SLA ekine göre | `[X saat]` | `%[XX]` |

**Planlı bakım:** Ayda en fazla 4 saat, en az 48 saat önceden bildirilir.  
**Force majeure:** Doğal afet, savaş, genel internet kesintisi SLA dışındadır.

---

## 8. Fikri Mülkiyet

- Platform yazılımının tüm fikri mülkiyet hakları Sağlayıcı'ya aittir
- Klinik'e, sözleşme süresince **münhasır olmayan kullanım lisansı** verilir
- Klinik'in girdiği içerik (metin, görsel, logo) Klinik'e aittir
- Sözleşme sona erdiğinde lisans otomatik sona erer

---

## 9. Gizlilik

Taraflar, sözleşme kapsamında edindikleri ticari sır niteliğindeki bilgileri üçüncü kişilerle paylaşmaz. Bu yükümlülük sözleşme bitiminden sonra **3 yıl** devam eder.

---

## 10. Sorumluluk Sınırı

Sağlayıcı'nın toplam sözleşmesel sorumluluğu, son **12 ayda** Klinik tarafından ödenen toplam bedeli aşamaz.

Sağlayıcı; Klinik'in tıbbi kararları, terapi süreçleri veya danışana verilen hizmet kalitesinden sorumlu değildir. Platform karar destek aracıdır.

---

## 11. Fesih ve İptal

### 11.1 Klinik tarafından fesih
- İlk 12 ay içinde erken fesih: kalan aylık bedelin **%50**'si veya minimum **3 aylık** bedel (yüksek olan) tahsil edilir
- Kurulum bedeli iade edilmez

### 11.2 Sağlayıcı tarafından fesih
- 30 gün üst üste ödeme yapılmaması
- Platform'un kötüye kullanımı veya yasadışı amaçla kullanım

### 11.3 Fesih sonrası
- Klinik'e **30 gün** veri export süresi tanınır (JSON/CSV)
- Export sonrası veriler 90 gün içinde silinir

---

## 12. Mücbir Sebep

Tarafların kontrolü dışındaki olağanüstü durumlarda yükümlülükler askıya alınır.

---

## 13. Uyuşmazlık Çözümü

Bu sözleşmeden doğan uyuşmazlıklarda **`[İstanbul]`** Mahkemeleri ve İcra Daireleri yetkilidir.

---

## 14. Yürürlük

Bu sözleşme `[X]` nüsha düzenlenmiş, `[GG.AA.YYYY]` tarihinde taraflarca imzalanarak yürürlüğe girmiştir.

---

## İmza Alanları

| **Sağlayıcı** | **Klinik** |
|---------------|------------|
| Ad Soyad: | Ad Soyad: |
| Unvan: | Unvan: |
| İmza: | İmza: |
| Tarih: | Tarih: |

---

## Ekler
1. Teklif Formu `[TEKLIF-2026-001]`
2. Paket modül listesi (Platform `/fiyatlandirma` sayfası)
3. KVKK Veri İşleme Protokolü (ayrı imza)
4. SLA detay tablosu (Kurumsal / Özel paketler)