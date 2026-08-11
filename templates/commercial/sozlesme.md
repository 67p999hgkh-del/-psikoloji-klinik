# HİZMET SÖZLEŞMESİ — Klinik Yönetim Platformu

**Sözleşme No:** {{ contract_no }}  
**Teklif Ref:** {{ quote.quote_no }}  
**Tarih:** {{ quote_date }}

---

## 1. Taraflar

**Hizmet Sağlayıcı ("Sağlayıcı")**  
Unvan: **{{ company.legal_name }}**  
Marka: {{ company.brand_name }}  
Adres: {{ company.address }}  
Vergi Dairesi / No: {{ company.tax_office }} / **{{ company.tax_number }}**  
MERSİS: {{ company.mersis }}  
Ticaret Sicil: {{ company.trade_registry }}  
E-posta: {{ company.email }} · Satış: {{ company.sales_email }}  
Tel: {{ company.phone }} · Web: {{ company.website }}  
Yetkili: **{{ company.authorized_person }}** — {{ company.authorized_title }}

**Müşteri ("Klinik")**  
Unvan: **{{ quote.customer_name }}**  
Yetkili: {{ quote.customer_contact }}  
E-posta: {{ quote.customer_email }} · Tel: {{ quote.customer_phone }}  
Adres: `[Müşteri adresi]`

---

## 2. Sözleşmenin Konusu

Sağlayıcı, Klinik'e **{{ company.brand_name }}** yazılımının kurulumu, lisanslanması, barındırılması, bakımı ve destek hizmetlerini sunar.

**Seçilen paket:** **{{ plan.label }}**  
**Aylık hizmet bedeli:** {{ monthly_display }} (KDV hariç)  
**Kurulum bedeli:** {{ setup_display }} (KDV hariç)

Teklif Formu ({{ quote.quote_no }}) bu sözleşmenin ayrılmaz parçasıdır.

---

## 3. Hizmet Kapsamı

### 3.1 Yazılım modülleri
{{ plan.label }} paketi kapsamındaki modüller Platform fiyatlandırma sayfasında ve teklif formunda listelenmiştir.

### 3.2 Kurulum
- Sunucu / barındırma hazırlığı
- Domain & SSL yapılandırması
- Tema ve marka uyarlaması
- İlk veri girişi (teklif kapsamında)
- {{ quote.training_hours }} saat uzaktan eğitim
- Tahmini süre: {{ quote.setup_weeks }}

### 3.3 Sürekli hizmetler
Hosting, SSL, yedekleme, güvenlik güncellemeleri, teknik destek (paket SLA'sına göre).

---

## 4. Ücret ve Ödeme

| Kalem | Tutar |
|-------|-------|
| Kurulum | {{ setup_display }} |
| Aylık abonelik | {{ monthly_display }}/ay |
| Yıllık peşin indirim | %15 |

**Banka:** {{ company.bank_name }}  
**IBAN:** {{ company.bank_iban }}

Geciken ödemelerde Sağlayıcı, 7 gün yazılı ihtar sonrası hizmeti askıya alabilir.

---

## 5. Süre ve Yenileme

- **İlk süre:** 12 ay (go-live tarihinden itibaren)
- Otomatik yenileme: 30 gün önceden fesih bildirilmezse 1 yıl uzar
- Yıllık fiyat artışı: en fazla TÜFE + %5 (60 gün önceden bildirim)

---

## 6. KVKK ve Veri İşleme

- **Veri sorumlusu:** Klinik
- **Veri işleyen:** {{ company.legal_name }}
- **Veri lokasyonu:** {{ company.data_location }}
- **Teknik tedbirler:** SSL/TLS, rol tabanlı erişim, günlük yedek, denetim logları (Kurumsal paket)
- **İhlal bildirimi:** 72 saat içinde Klinik bilgilendirilir
- **Saklama:** Sözleşme süresi + fesih sonrası 90 gün export, ardından silme
- **Aydınlatma metni:** Klinik sorumluluğundadır

---

## 7. SLA (Hizmet Seviyesi)

| Paket | Destek | Yanıt | Uptime |
|-------|--------|-------|--------|
| Başlangıç | {{ company.support_hours }} | 48 saat | %99 |
| Profesyonel | {{ company.support_hours }} | 24 saat | %99,5 |
| Kurumsal | {{ company.support_hours }} + acil | 4 saat | %99,5 |

Planlı bakım: ayda max 4 saat, 48 saat önceden bildirilir.

---

## 8. Fikri Mülkiyet

Platform yazılımının tüm hakları {{ company.legal_name }}'ne aittir. Klinik'e sözleşme süresince münhasır olmayan kullanım lisansı verilir. Klinik içerikleri Klinik'e aittir.

---

## 9. Gizlilik

Ticari sırlar sözleşme bitiminden sonra **3 yıl** gizli tutulur.

---

## 10. Sorumluluk Sınırı

Sağlayıcı'nın toplam sorumluluğu son 12 ayda ödenen bedeli aşmaz. Platform tıbbi karar destek aracıdır; terapi süreçlerinden Klinik sorumludur.

---

## 11. Fesih

**Klinik erken fesih:** Kalan sürenin %50'si veya min. 3 aylık bedel. Kurulum iade edilmez.  
**Sağlayıcı fesih:** 30 gün ödeme gecikmesi veya kötüye kullanım.  
**Fesih sonrası:** 30 gün veri export, 90 gün içinde silme.

---

## 12. Uyuşmazlık

**{{ company.dispute_city }}** Mahkemeleri ve İcra Daireleri yetkilidir.

---

## 13. İmza

| **Sağlayıcı** | **Klinik** |
|---------------|------------|
| {{ company.legal_name }} | {{ quote.customer_name }} |
| {{ company.authorized_person }} — {{ company.authorized_title }} | {{ quote.customer_contact }} |
| İmza: _________________ | İmza: _________________ |
| Tarih: _______________ | Tarih: _______________ |

---

*{{ company.legal_name }} · {{ company.address }} · {{ company.phone }} · {{ company.email }}*