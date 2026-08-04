# PROJE BRİFİ (LLM Context Prompt): Web Arayüzü → HTML/CSS Agentic Pipeline

> **Bu dosyanın amacı:** Bu doküman, bu projeye devam edecek herhangi bir LLM instance'ının (Claude veya başka bir asistan) sohbet geçmişine ihtiyaç duymadan doğrudan bağlamı yakalaması için yazılmıştır. Aşağıdaki bilgileri **verili/karar verilmiş gerçekler** olarak kabul et, aksi belirtilmedikçe sorgulama — sadece açıkça "⬜ AÇIK KARAR" işaretli maddeler tartışmaya/karara açıktır.

---

## 1. PROJE TANIMI

**Görev:** Bir web arayüzü ekran görüntüsünü (içindeki tüm UI component'leriyle birlikte — navbar, kart, form, buton vb.) HTML/CSS koduna çeviren bir sistem geliştirmek.

**Mimari yaklaşım:** Tek bir monolitik VLM'in uçtan uca fine-tune edilmesi **DEĞİL** — görevi ayrı uzman modüllere/aşamalara bölen **modüler pipeline** mimarisi.

**Neden bu mimari seçildi:** Literatür (özellikle ScreenCoder, arXiv:2507.22827), tek bir modele "hem gör hem planla hem kodla" görevini vermenin element atlama/bozulma/yanlış yerleşim hatalarına yol açtığını gösteriyor. Modüler ayrım (block-match: 0.755) uçtan uca GPT-4o'dan (0.730) daha iyi sonuç veriyor.

**Kaynak kısıtı:** Google Colab A100 (tek GPU).

**Metodoloji ilkeleri (tüm kararlarda geçerli):**
- Mekanik-önce öğrenme — önce küçük pilot, sonra ölçekle
- İç/dış validasyon ayrımı — dış test setleri (Design2Code-HARD, ScreenBench) asla eğitimde kullanılmaz
- Pozitif/negatif sonuçları şeffaf raporla
- Büyük veri setiyle direkt eğitime girme — önce mekanik doğrulama, sonra kademeli ölçekleme

---

## 2. MİMARİ AKIŞ VE GÜNCEL KARARLAR

```
0. Ön İşleme         → görüntü yakalama + normalizasyon                    [KARAR: Playwright + PIL/OpenCV]
1. Grounding          → component tespiti/etiketleme                       [KARAR: Qwen3-VL]
2a. Planning          → uzamsal hiyerarşi kurma                            [KARAR: LLM'siz, kural-tabanlı — fallback: LLM]
2b. Formatting        → hiyerarşiyi kod modeline uygun temsile çevirme      [KARAR: klasik front-end mühendislik mantığıyla JSON şeması]
3. Asset Extraction   → gerçek görsellerin (logo/foto) kırpılıp yerleştirilmesi  [KARAR: PIL/OpenCV crop]
4. Generation         → HTML/CSS kodu üretimi                              [KARAR: Claude API, bölge bazlı]
5. Doğrulama Döngüsü  → render → görsel karşılaştırma → iteratif düzeltme   [Opsiyonel, zaman kalırsa]
```

### Aşama 0 — Ön İşleme (KARAR VERİLDİ)

**Araçlar:** Playwright (headless browser, screenshot yakalama) + PIL/OpenCV (çözünürlük normalizasyonu).

**Zorunlu kontroller:**
- Full-page mi viewport mu — net ve tutarlı olmalı
- DPR (device pixel ratio) sabitlenmeli, Retina simülasyonu kapalı
- Browser chrome (adres çubuğu, scrollbar) dahil edilmemeli
- Viewport genişliği sabit tutulmalı (örn. 1280px)
- Çıktı formatı: PNG (kayıpsız) — JPEG asla kullanılmamalı (küçük yazı/ikon kenarlarını bozuyor)
- Qwen3-VL'in resmi önerilen `min_pixels`/`max_pixels` aralığı kullanılmalı (mimari tavan değil)
- Resize sonrası boyutlar Qwen3-VL patch boyutunun (32px) katına yuvarlanmalı
- Renk augmentasyonu (jitter/hue/brightness) KESİNLİKLE yapılmamalı — CSS renk kodları piksel-hassas doğru olmalı
- Büyük sayfalar DOM/section sınırlarına göre bölünmeli (DCGen'in "divide and conquer" mantığı), rastgele piksel aralıklarına göre değil
- pHash ile deduplication yapılmalı, eğitim/dış-test seti görsel örtüşmesi kontrol edilmeli

### Aşama 1 — Grounding (KARAR VERİLDİ: Qwen3-VL)

**Neden Qwen3-VL seçildi:** En zengin bilgiyi tek seferde veriyor (konum + içerik/OCR + bağlam), esneklik en yüksek (sabit component sözlüğüne bağlı değil), Aşama 2a'daki hiyerarşi kurma işine ek bağlamsal veri sağlayabiliyor.

**Bilinen risk:** Genel VLM'ler piksel-hassas koordinat tahmininde zayıf olabiliyor; aynı kategoriden çoklu nesnede (örn. 5 buton varsa) tek kutu döndürme bilinen bir sorun.

**Uygulama adımları:**
1. Zero-shot pilot test — hiç fine-tune etmeden birkaç örnek üzerinde dene
2. Prompt tasarımı: "Locate **each/every** UI component..." şeklinde açık çoğul ifade kullan; kategori bazlı ayrı ayrı sorgulamayı da test et
3. Koordinat dönüşümü: model çıktısı 0-1000 normalize skalada → `x_piksel = (bbox_değeri/1000) × görsel_genişliği`
4. Zero-shot sonuçlarını değerlendir: recall, precision, "tek kutu" sorununun sıklığı
5. Fine-tune kararı: yukarıdaki sorunlar prompt mühendisliğiyle çözülemiyorsa devreye al (LoRA r=32/α=64 başlangıcı, değerlendirme metriği IoU)

**Model çıktı formatı:**
```json
[
  {"bbox_2d": [42, 118, 310, 165], "label": "navbar"},
  {"bbox_2d": [50, 200, 280, 240], "label": "button"}
]
```
Verir: konum (bbox) + serbest metin etiket. Vermez: hiyerarşi, stil bilgisi, tam tutarlılık (deduplication/çakışma temizleme pipeline'da ayrıca yapılmalı).

### Aşama 2a — Planning (KARAR VERİLDİ: Önce LLM'siz, Kural-Tabanlı)

**Karar:** İlk aşamada **LLM/VLM kullanılmayacak**. Uzamsal hiyerarşi (hangi component hangisinin içinde/yanında, CSS Grid/Flexbox yapısı) tamamen **kural-tabanlı geometrik algoritma** ile çözülecek:
- Bbox'ların x/y/genişlik/yükseklik ilişkilerinden iç içelik ve komşuluk çıkarımı
- CSS Grid/Flexbox konvansiyon kurallarına dayalı, önceden tanımlanmış if/else mantığı (ScreenCoder'ın Planning Agent'ının yaptığı gibi — o da kural-tabanlı, model değil)

**Fallback koşulu:** Kural-tabanlı yaklaşım pilot testlerde yetersiz kalırsa (karmaşık/iç içe geçmiş layout'larda hiyerarşi yanlış çıkarılıyorsa), bir sonraki adım bir LLM'in bu hiyerarşi kurma işini üstlenmesi olacak. **Bu geçiş henüz gerçekleşmedi — önce kural-tabanlı yaklaşım denenmeli, LLM'e geçiş yalnızca kanıtlanmış bir yetersizlik durumunda yapılmalı.**

**Not:** Kural-tabanlı yaklaşımın yetersizliğini nasıl tespit edeceğin: birkaç pilot örnekte üretilen hiyerarşi ağacını gözle/otomatik olarak orijinal görselle karşılaştır — component'ler yanlış iç içe yerleştiriliyorsa (örn. bir navbar item'ı yanlışlıkla footer'ın altına konuyorsa) bu bir yetersizlik sinyalidir.

### Aşama 2b — Formatting (KARAR VERİLDİ: Klasik Front-End Mühendislik Mantığıyla Tasarım)

**Karar:** JSON şeması, **klasik front-end mühendislik konvansiyonlarını** (semantik HTML5 etiketleri, CSS Grid/Flexbox terminolojisi, BEM benzeri isimlendirme mantığı) yansıtacak şekilde tasarlanmalı — LLM'in (Aşama 4'teki kod üretici model) bu şemayı, kendi eğitiminde zaten gördüğü front-end kavramlarıyla doğrudan eşleştirebilmesi hedefleniyor. Yani şema, "özel/keyfi bir format" değil, bir front-end geliştiricinin doğal olarak düşüneceği kavramlara (`header`, `nav`, `main`, `section`, `flex-row`, `grid-cols` gibi) sadık kalmalı.

**bu prensipler kesinleşti:**
- Component tipi (Aşama 1'in etiketinden, normalize edilmiş/standartlaştırılmış — semantik HTML5 karşılığına yakın isimlendirmeyle: `nav`, `header`, `button`, `form` vb.)
- Bbox / konum bilgisi
- İç içelik derinliği ve ebeveyn-çocuk ilişkisi (Aşama 2a'nın çıktısı)
- Layout tipi ipucu (flex/grid, yön: row/column) — Aşama 2a'nın CSS Grid/Flexbox kural çıkarımından
- Stil bilgisi (renk/font — varsa)

**KESİN KARAR Şema:** 
json {
  "$schema": "ui-to-code-formatting-schema-v1",
  "meta": {
    "source_image": "screenshot_0001.png",
    "canvas": { "width": 1280, "height": 2140 },
    "viewport_type": "full_page"
  },
  "root": {
    "id": "n0",
    "tag": "body",
    "layout": {
      "display": "flex",
      "direction": "column",
      "justify": "flex-start",
      "align": "stretch",
      "gap": 0
    },
    "bbox": [0, 0, 1280, 2140],
    "style": {
      "bg_color": "#ffffff"
    },
    "children": [
      {
        "id": "n1",
        "tag": "header",
        "role": "navbar",
        "layout": {
          "display": "flex",
          "direction": "row",
          "justify": "space-between",
          "align": "center",
          "gap": 16
        },
        "bbox": [0, 0, 1280, 72],
        "style": {
          "bg_color": "#1e293b",
          "padding": [16, 32]
        },
        "children": [
          {
            "id": "n1a",
            "tag": "img",
            "role": "logo",
            "bbox": [32, 20, 120, 52],
            "content": null,
            "asset_ref": "assets/n1a_logo.png"
          },
          {
            "id": "n1b",
            "tag": "nav",
            "layout": { "display": "flex", "direction": "row", "gap": 24 },
            "bbox": [700, 20, 1100, 52],
            "children": [
              {
                "id": "n1b1",
                "tag": "a",
                "bbox": [700, 20, 760, 52],
                "content": "Home",
                "style": { "color": "#ffffff", "font_weight": "500" }
              },
              {
                "id": "n1b2",
                "tag": "a",
                "bbox": [780, 20, 840, 52],
                "content": "Pricing",
                "style": { "color": "#ffffff", "font_weight": "500" }
              }
            ]
          },
          {
            "id": "n1c",
            "tag": "button",
            "role": "cta-button",
            "bbox": [1120, 16, 1248, 56],
            "content": "Sign Up",
            "style": {
              "bg_color": "#3b82f6",
              "text_color": "#ffffff",
              "border_radius": 8,
              "font_weight": "600"
            }
          }
        ]
      },
      {
        "id": "n2",
        "tag": "main",
        "role": "content",
        "layout": {
          "display": "grid",
          "grid_cols": 3,
          "gap": 24
        },
        "bbox": [0, 72, 1280, 900],
        "style": { "padding": [48, 32] },
        "children": [
          {
            "id": "n2a",
            "tag": "section",
            "role": "card",
            "layout": { "display": "flex", "direction": "column", "gap": 12 },
            "bbox": [32, 120, 400, 480],
            "style": {
              "bg_color": "#f8fafc",
              "border_radius": 12,
              "padding": [24, 24]
            },
            "children": [
              {
                "id": "n2a1",
                "tag": "h3",
                "bbox": [56, 144, 300, 176],
                "content": "Feature One",
                "style": { "font_size": 20, "font_weight": "700", "color": "#0f172a" }
              },
              {
                "id": "n2a2",
                "tag": "p",
                "bbox": [56, 184, 376, 260],
                "content": "Kısa açıklama metni buraya gelir.",
                "style": { "font_size": 14, "color": "#475569" }
              }
            ]
          }
        ]
      },
      {
        "id": "n3",
        "tag": "footer",
        "bbox": [0, 2000, 1280, 2140],
        "layout": { "display": "flex", "direction": "row", "justify": "center" },
        "style": { "bg_color": "#0f172a" },
        "children": []
      }
    ]
  }
}

### Aşama 3 — Asset Extraction (KARAR VERİLDİ)

PIL/OpenCV ile crop — placeholder'lar orijinal screenshot'tan kırpılan gerçek görsellerle değiştirilecek (ScreenCoder'ın `image_replacer.py` mantığı). Model gerektirmiyor.

### Aşama 4 — Generation (KARAR GÜNCELLENDİ: Claude API, bölge bazlı)

**Önceki karar (artık geçerli değil):** Qwen2.5-VL-7B (yerel, Colab GPU'sunda çalışan açık kaynak VLM) → sonra Gemini API'ye geçildi.

**Neden Gemini'den de vazgeçildi:** Gemini API gerçek denemede **503 (servis kullanılamıyor)** hatası verdi. Claude API'ye geçildi. Gemini entegrasyonu koddan SİLİNMEDİ (`src/generation/model.py`'de `load_gemini_model`, `src/generation/inference.py`'de `run_region_generation_gemini`) — gerekirse dosyaların sonundaki tek satırlık atama değiştirilerek hızlıca geri dönülebilir.

**Qwen2.5-VL-7B → Gemini/Claude geçişinin asıl gerekçesi (değişmedi):** Qwen2.5-VL-7B ile gerçek Colab testlerinde tekrarlayan, farklı biçimlerde ortaya çıkan ama aynı kök soruna işaret eden bug'lar gözlemlendi: geçersiz CSS property adları (`direction`/`justify`/`align` yerine `flex-direction`/`justify-content`/`align-items`), görünür metnin (`content`) bir HTML attribute'una gömülüp render'da hiç görünmemesi, iç içe `<html>/<body>` sarmalayıcı üretilmesi, `position:absolute` kullanılması (prompt'ta yasaklanmış olsa bile). Her birini hem prompt hem deterministik `src/generation/repair.py` onarımıyla düzelttik, ama bu tekrarlayan örüntü aynı temel soruyu gösteriyor: 7B'lik açık modelin talimatlara güvenilir uyup uymadığı şüpheli. Bunun gerçekten model kaynaklı mı yoksa mimari kaynaklı mı olduğunu ayırt etmek için, daha güçlü kapalı bir modelle karşılaştırma yapılıyor.

**Yeni karar — aynı ScreenCoder tarzı bölge bazlı mimari, Claude API ile:**
1. Root'un doğrudan çocukları (`src/generation/regions.py`, `select_regions`) birer "bölge" sayılıyor; bir bölgenin alt-ağacı çok büyükse (>15 node, `DEFAULT_MAX_REGION_NODES`) kendi çocuklarına bölünüyor — gerçek pilot testte "ana içerik" gibi tek bir bölgenin ~38 node'a kadar büyüyüp hem modelin görsel kapsamını büyüttüğü hem üretimin token limitinde yarıda kesildiği gözlemlendi.
2. Her bölge kendi bbox'ından kırpılıyor, kendi JSON alt-ağacıyla birlikte Claude'a (`anthropic` SDK, `client.messages.create`, görüntü base64 PNG olarak) ayrı bir çağrıda veriliyor.
3. Root'un kendisi hiçbir çağrıya dahil değil — etiketi/layout/style'ı doğrudan şemadan deterministik kodla (`src/generation/assembly.py`) üretiliyor.
4. Üretilen bölge HTML'leri root'un içine sırayla yerleştiriliyor.

**Model:** Claude Sonnet 5 (`anthropic` SDK) — API key `ANTHROPIC_API_KEY` ortam değişkeninden okunuyor, koda hiçbir zaman gömülmüyor. Yerel GPU/model indirmesi gerekmiyor (Aşama 1'in Qwen3-VL'inden bağımsız).

**Bu değişiklik henüz gerçek Colab çalıştırmasıyla doğrulanmadı** — sıradaki test turunda gözlemlenecek; asıl soru Claude'un da aynı talimat-atlama örüntüsünü gösterip göstermeyeceği (gösterirse sorun modelden değil mimariden kaynaklanıyor demektir).

### Aşama 5 — Görsel Doğrulama / İteratif Düzeltme (Opsiyonel)

Playwright ile render + CLIP score/CW-SSIM ile karşılaştırma + Aşama 4'teki modele fark bildirimi (VF-Coder "Coding with Eyes" yaklaşımı). Zaman kalırsa eklenir, ana pipeline'ın parçası değil.

---

## 3. VLM'İN PROJE GENELİNDEKİ ROLÜ

| Aşama | VLM kullanımı | Fine-tune gerekli mi? |
|---|---|---|
| 1 — Grounding | ✅ Birincil (Qwen3-VL) | Muhtemelen hayır, zero-shot pilot ile başla |
| 2a — Planning | ❌ Kullanılmıyor (kural-tabanlı) — fallback olarak LLM eklenebilir | N/A |
| 2b — Formatting | ❌ Model yok, şema tasarımı | N/A |
| 4 — Generation | ✅ Claude API, bölge bazlı (görüntü + JSON alt-ağacı) | Kapalı model, fine-tune yok — prompt engineering ile sınırlı |
| 5 — Doğrulama | ✅ Opsiyonel, doğal dil fark analizi | Hayır |

**Genel ilke:** Hassas/kalibre edilmiş çıktı gerektiren görevler (koordinat tespiti) fine-tune'dan fayda görüyor; tanımlayıcı/kural-tabanlı görevler zero-shot veya model-siz çözümlerle zaten yeterli.

---

## 4. MODEL EĞİTİMİ YAKLAŞIMI (Fine-Tuning Gerektiren Her Aşama İçin Geçerli)

> Kaynak: `model-egitimi-yaklasimi.md` — bu bölüm o dosyanın özetlenmiş halidir, ayrıntı için o dosyaya bakılabilir.

**Ana ilke:** Büyük veri setiyle direkt eğitime girme. Sıralama:
```
plan → küçük pilot run (%1-2 veri) → mekanik doğrulama → kademeli ölçek büyütme → düzenli gerçek-çıktı kontrolü → tam ölçekli eğitim
```

**Sekiz kural:**
1. Önce küçük pilot run — veri formatı, loss davranışı, gözle örnek kontrolü doğrulanmadan büyük veriye geçilmez
2. Veri kalitesi miktardan önemli — dedupe + çeşitlilik kontrolü şart (sentetik veriye aşırı uyum riski var)
3. Kademeli zorluk (curriculum): DOM derinliği/token uzunluğuna göre kolay→zor sıralama
4. LoRA konfigürasyonu kör kopyalanmaz, küçük sweep ile belirlenir
5. Checkpoint/resume zorunlu (Colab oturum limitleri nedeniyle)
6. Sadece loss'a değil, gerçek üretime (CLIP score ile) bakılır
7. Genel amaçlı instruction verisi karıştırılır (%5-10, catastrophic forgetting'e karşı)
8. Veri sızıntısı disiplini: dış test setleri (Design2Code-HARD, ScreenBench) fiziksel olarak izole klasörde tutulur, eğitim scriptinin erişemeyeceği şekilde

**LoRA Başlangıç Konfigürasyonu (fine-tune edilecek herhangi bir model için):**

| Parametre | Değer | Gerekçe |
|---|---|---|
| Rank (r) | 32 (gerekirse 64) | Kod üretimi/kalibre görevlerde düşük rank (8-16) yetersiz |
| Alpha (α) | 2r (64) | α/r oranı ~2 stabil |
| Target modules | Tüm linear katmanlar (attention + MLP) | Sadece attention yetersiz |
| Learning rate | ~1e-4 (vision encoder donduruluysa biraz daha düşük) | Görsel-metin hizalaması hassas |
| Epoch | 2-3 (5-50K veri için) | Fazlası overfit riski |
| Batch size (etkin) | 16-64 (gradient accumulation) | Colab VRAM kısıtına göre |
| DoRA | Değerlendirilmeye değer | Karmaşık görevlerde yakınsama iyileştirebilir |

**Karar süreci:** Pilot run'da r={16,32,64} ve lr={5e-5,1e-4,2e-4} kombinasyonlarından 3-4'ünü dene, hem eval loss hem gerçek çıktı kalitesine bakarak seç.

---

## 5. DATASET ENVANTERİ

**Ana eğitim verisi adayları:** Web2Code (1.179.700 çift, arXiv:2406.20098), WebSight (~2M/823K, arXiv:2403.09029), WebCode2M (arXiv:2404.06369).

**Dış değerlendirme (ASLA eğitimde kullanılmaz):** Design2Code (484, arXiv Si et al. 2024), Design2Code-HARD (80), ScreenBench (1000, ScreenCoder'ın kendi seti).

---

## 6. DEĞERLENDİRME (EVALUATION)

- Görsel benzerlik: CLIP score, CW-SSIM
- Yapısal benzerlik: TreeBLEU, DOM tag eşleşme oranı
- Referans: Web2Code'un WCGB metrikleri, ScreenCoder'ın block-match metriği
- İç test seti ve dış test seti sonuçları **ayrı** raporlanır
- Halüsinasyon kontrolü: üretilen HTML'in görselde olmayan element eklemediğinden ayrıca emin olunmalı

---

## 7. AÇIK KARARLAR (Sonraki Oturumda Netleştirilecek)

1. ~~**Aşama 4 (Generation):** Hangi model/API kullanılacak~~ — KARAR GÜNCELLENDİ: Claude Sonnet 5 (API), ScreenCoder tarzı bölge bazlı (görüntü + JSON alt-ağacı birlikte) — önce Gemini denendi ama 503 hatası verdi; Qwen2.5-VL-7B'nin tekrarlayan talimat-atlama sorununun model mi mimari mi kaynaklı olduğunu test etmek için kapalı bir modele geçildi
2. **Aşama 2b:** Tam JSON şema tasarımı (alan adları, iç içe format) — prensipler belirlendi (front-end mühendislik mantığı), somut şema yok
3. **Aşama 2a fallback:** Kural-tabanlı yaklaşımın ne zaman "yetersiz" sayılacağına dair somut eşik/test seti henüz tanımlanmadı
4. Web2Code dataset erişim/lisans doğrulaması ve Colab A100 kapasitesine göre alt-küme boyutu
5. Aşama 5 (doğrulama döngüsü) kapsama alınacak mı
6. Hedeflenen component yoğunluğu (basit landing page mi, karmaşık dashboard mı) — context window ve tiling stratejisini belirleyecek

---

## 8. KAYNAKÇA

- Jiang, Y. et al. "ScreenCoder: Advancing Visual-to-Code Generation for Front-End Automation via Modular Multimodal Agents." arXiv:2507.22827
- Yun, S. et al. "Web2Code." NeurIPS 2024. arXiv:2406.20098
- Laurençon, H. et al. "WebSight." arXiv:2403.09029
- Si, C. et al. "Design2Code." (2024)
- WebCode2M: arXiv:2404.06369
- MulongXie/UIED (GitHub)
- WebPAI/DCGen (GitHub)
- Qwen2.5-VL / Qwen3-VL teknik dokümantasyonu

## 9. PROJE KLASÖRÜNDE İÇERİSİNE GİRİLMİCEK DOSYALAR

- md klasörü - **YASAK**.
