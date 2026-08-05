# web2code — Proje Sunumu

> Ekran görüntüsünden HTML/CSS üreten modüler pipeline'ın kapsamlı anlatımı:
> mimari, dosya dosya veri akışı, model seçim gerekçeleri ve sonraki adımlar.

---

## 1. Proje ne yapıyor?

**Girdi:** bir web sayfası ekran görüntüsü (veya bir URL)
**Çıktı:** o ekran görüntüsünü görsel olarak yeniden üreten, kendi kendine yeten (offline çalışan) `index.html` + `assets/` klasörü.

**Mimari felsefe:** Tek bir dev VLM'e "gör + planla + kodla" dedirtmek yerine, görevi **modüler bir pipeline'a** bölmek. Referans: ScreenCoder (arXiv:2507.22827). Repo'da `ScreenCoderClone/` klasörü zaten duruyor — kod bunun basitleştirilmiş bir yeniden implementasyonu.

### Önemli bir netleştirme: bu projede "eğitim" aşaması YOK

Pipeline'ı "veri önişleme, eğitim, test" diye bölmek isterken kodun gerçeğini bilmek gerekiyor: **hiçbir yerde fine-tuning/training kodu yok.** `model/checkpoints/` klasörü boş, LoRA yok, optimizer yok, dataset loader yok. İki model de kullanılıyor ama ikisi de **zero-shot**:

- **Qwen3-VL-8B** → yerel GPU'da, hiç eğitilmeden, sadece prompt ile
- **Claude Sonnet** → API üzerinden, sadece prompt ile

`web2code-oldplan.md` §4'te detaylı bir eğitim planı var (LoRA r=32, α=64, curriculum, pilot run vb.) ama bu **henüz yazılmamış bir plan**, kod değil. Yani gerçek pipeline şöyle bölünüyor:

| Klasik tabirle | Projedeki gerçek karşılığı |
|---|---|
| Veri önişleme | Aşama 0 — `src/preprocessing/` ✅ var |
| Eğitim | ❌ **yok** (plan var, kod yok) |
| Çıkarım (inference) | Aşama 1–4 — grounding → regions → generation → assets ✅ var |
| Test / değerlendirme | Aşama 6 — `src/evaluation/` ✅ var (CLIP score) |

---

## 2. Pipeline haritası

```
URL / PNG
   │
   ▼  [Aşama 0]  src/preprocessing/
stage0/normalized/upload_0000.png
   │
   ▼  [Aşama 1]  src/grounding/     ← QWEN3-VL burada (tek yerel model)
stage1/upload_0000_detections.json   (en fazla 4 kaba bbox)
   │
   ▼  [Aşama 2]  src/regions/       ← model yok, saf kural
stage2/upload_0000_regions.json      (piksel bbox'lı region listesi)
   │
   ▼  [Aşama 3]  src/generation/    ← CLAUDE burada, her region için 1 API çağrısı
stage3/upload_0000.html              (gri .img-placeholder'lı HTML)
   │
   ▼  [Aşama 4]  src/assets/        ← model yok, Playwright + PIL
final/upload_0000/index.html + assets/ph0.png...
   │
   ▼  [Aşama 6]  src/evaluation/    ← CLIP
eval_results/clip_scores.json
```

Orkestratör: [src/pipeline.py](src/pipeline.py) — `run_full_pipeline()` bu 5 adımı sırayla çağırır. Her ağır import (`torch`, `playwright`, `transformers`) bilerek fonksiyon içinde yapılıyor ki bir aşama çalışırken diğerinin bağımlılığı yüklenmesin. Ayrıca grounding bitince `del model` + `torch.cuda.empty_cache()` yapılıyor ([pipeline.py:113-115](src/pipeline.py#L113-L115)) — Colab'ın tek GPU'sunda Qwen'in VRAM'i tutmaması için.

---

## 3. Dosya dosya: ne oluyor, ne çıkıyor, sonra nereye gidiyorum?

### AŞAMA 0 — Ön İşleme (`src/preprocessing/`)

#### [capture.py](src/preprocessing/capture.py)

**Ne yapar:** Playwright headless Chromium ile bir URL'nin full-page screenshot'ını alır.

**Kritik ayarlar ve nedenleri:**

- `device_scale_factor = 1.0` — Retina simülasyonu kapalı, yoksa koordinatlar 2× kayar
- `viewport_width = 1280` sabit — responsive breakpoint'lerin tutarlı olması için
- PNG zorunlu, JPEG kodda **hata fırlatıyor** ([capture.py:44](src/preprocessing/capture.py#L44)) — JPEG artefaktları küçük yazı/ikon kenarlarını bozar, CSS renk kodu çıkarımını yanlışlar
- `wait_until="networkidle"` — lazy-load görseller yüklensin diye

**Çıktı:** `stage0/raw/screenshot_0000.png`
**Sonra:** → `splitter.py` (uzunsa) veya doğrudan `normalize.py`

#### [splitter.py](src/preprocessing/splitter.py)

**Ne yapar:** Sayfa 4000px'den uzunsa, **canlı DOM'dan** `body`'nin doğrudan çocuklarının `getBoundingClientRect()`'ini JS ile okur ve screenshot'ı bu semantik sınırlardan dikey olarak keser.

**Neden böyle:** Rastgele piksel aralığından kesmek bir kartı/bölümü ortadan ikiye böler. DCGen'in "divide and conquer" mantığı. Not: bu yalnızca **URL yolunda** çalışır — canlı `Page` nesnesi gerekiyor. Doğrudan PNG yüklendiğinde DOM olmadığı için bölme yapılmaz.

**Çıktı:** `stage0/sections/screenshot_0000/section_000_header.png` ...
**Sonra:** → `normalize.py`

#### [normalize.py](src/preprocessing/normalize.py)

**Ne yapar:** `smart_resize()` — görseli Qwen3-VL'in beklediği boyuta getirir:

- Boyutlar **32'nin katına** yuvarlanır (Qwen3-VL patch boyutu)
- `min_pixels = 256×32×32`, `max_pixels = 1280×32×32` aralığına sıkıştırılır → bu görsel token bütçesini kontrol eder
- Sadece LANCZOS resize; **hiçbir renk augmentasyonu yok** (jitter/hue/brightness). Sebep: üretilecek CSS renk kodları piksel-hassas doğru olmalı — bu bir sınıflandırma değil, reprodüksiyon görevi.

**Çıktı:** `stage0/normalized/upload_0000.png` ← **pipeline'ın geri kalanının tek gerçek referansı bu dosya.** Aşama 3'teki crop'lar da, Aşama 4'teki asset crop'ları da, Aşama 6'daki CLIP karşılaştırması da hep bu normalize edilmiş görselle yapılır. Ölçek tutarlılığı buradan geliyor.

**Sonra:** → `dedup.py` (sadece batch modunda) → Aşama 1

#### [dedup.py](src/preprocessing/dedup.py)

**Ne yapar:** pHash (perceptual hash) ile Hamming mesafesi ≤ 5 olan çiftleri "neredeyse aynı" sayar. **Silmez**, sadece raporlar.

**Durum:** `check_train_external_overlap()` fonksiyonu **yorum satırına alınmış** ([dedup.py:69-95](src/preprocessing/dedup.py#L69-L95)) — "önemsiz" notuyla. Bu fonksiyon eğitim/dış-test sızıntısını kontrol edecekti; eğitim olmadığı için şu an gerçekten gereksiz, ama **fine-tune'a geçilirse ilk geri açılması gereken şey bu.**

#### [preprocessing/pipeline.py](src/preprocessing/pipeline.py)

Yukarıdaki 4'ünü bir CLI'da birleştirir. Tek bir browser oturumu açıp tüm URL'leri gezer (her URL için browser açıp kapatmaz — bu önemli bir hız kazancı).

---

### AŞAMA 1 — Grounding (`src/grounding/`) — **Qwen3-VL burada**

#### [model.py](src/grounding/model.py)

`AutoModelForImageTextToText.from_pretrained("Qwen/Qwen3-VL-8B-Instruct", device_map="auto")`. `--load-in-4bit` bayrağıyla bitsandbytes NF4 quantization opsiyonel (A100 40GB'de gerekmiyor, T4/L4'te gerekir).

#### [prompts.py](src/grounding/prompts.py) ← **projedeki en önemli tasarım kararı**

Prompt modelden **sadece 4 kaba bölge** istiyor: `sidebar`, `header`, `navigation`, `main_content`. Her bölgeden **en fazla bir kutu**. Çıktı 0-1000 normalize skalada JSON.

Bu bir **pivot**. Eski tasarımda (bkz. `web2code-oldplan.md` §2) Qwen her tekil elemanı (buton, başlık, li...) tespit edecekti, sonra kural-tabanlı bir algoritma bunlardan hiyerarşi kuracaktı (Aşama 2a), sonra zengin bir JSON şemasına dönüştürülecekti (Aşama 2b). **Bu iki katman tamamen silindi.** Docstring nedenini açıkça yazıyor: hataların asıl kaynağı bu katmanlardı. Tekil eleman tespiti → hatalı bbox → hatalı hiyerarşi → hatalı JSON → hatalı kod; hata her katmanda büyüyordu.

Yeni felsefe: **Qwen'e sadece "kaba kadraj" işi ver, ince işi Claude'un görsel yorumuna bırak.**

#### [inference.py](src/grounding/inference.py)

`run_grounding()` — chat template ile mesajı kurar, `do_sample=False` (deterministik, greedy — koordinat üretiminde sampling istemezsin), `max_new_tokens=4096`. Ham metin döner.

`run_grounding_with_tiling()` — uzun sayfaları parçalayıp ayrı ayrı sorar. **Ama artık varsayılan olarak KAPALI** ([pipeline.py:112](src/pipeline.py#L112) `use_tiling=False`). CLI'daki help metni nedenini söylüyor: her tile kendi `main_content`'ini üretir, sonuçta 3 tane çakışan main_content elde edersin. Tiling tekil-eleman tespiti için mantıklıydı, kaba bölge tespiti için zararlı.

#### [parsing.py](src/grounding/parsing.py)

Regex `\{[^{}]*\}` ile ham metinden tek seviyeli JSON objelerini yakalar, `json.loads` ile doğrular, `bbox_2d`+`label` yoksa atar, aynı (bbox,label) çiftini tekrar eklemez.

**Neden regex + tek tek parse:** model bazen JSON'un önüne/arkasına açıklama metni yazıyor, ya da liste kapanışını unutuyor. `json.loads(tüm_metin)` kırılgan olurdu; bu yaklaşım bozuk kayıtları atlayıp geri kalanı kurtarıyor.

#### [coords.py](src/grounding/coords.py)

`denormalize_bbox`: `x_piksel = bbox/1000 × genişlik`. `compute_iou`: kutu çakışma oranı.

#### [visualize.py](src/grounding/visualize.py)

matplotlib ile kutuları görselin üstüne kırmızı çizer → `_annotated.png`. **Pipeline'ın çıktısını etkilemez, tamamen insan denetimi için.** Qwen'in kadrajı doğru mu, gözle bakılacak dosya bu.

#### [grounding/pipeline.py](src/grounding/pipeline.py)

**Çıktı — her görsel için 3 dosya:**

| Dosya | İçerik | Kime lazım |
|---|---|---|
| `upload_0000_raw.txt` | Qwen'in ham metin çıktısı | Debug: parse mi bozuk, model mi bozuk? |
| `upload_0000_detections.json` | Temizlenmiş `[{bbox_2d, label}]` | **Aşama 2'nin girdisi** |
| `upload_0000_annotated.png` | Kutulu görsel | Gözle denetim |

**Sonra:** → `src/regions/pipeline.py`

---

### AŞAMA 2 — Regions (`src/regions/`) — model yok

#### [resolve.py](src/regions/resolve.py)

İki iş:

1. `resolve_containment()` — bir bbox diğerini **tamamen kapsıyorsa küçüğü atar.** Neden: Qwen sık sık aynı bölgeyi iki kez, biri geniş biri dar olarak tespit ediyor. Kaba düzen bölgeleri iç içe olamaz, o yüzden içerilen kutu kesinlikle bir hatadır.
2. `build_regions()` — 0-1000 normalize bbox'ları **piksel** koordinatına çevirir, `region_0`, `region_1`... id'leri verir.

⚠️ Buradaki `resolve_containment` implementasyonu O(n²) döngüde `removed` set'ini iterasyon sırasında kontrol ediyor; hangi kutunun atılacağı **liste sırasına bağlı** — `_contains(i,j) or _contains(j,i)` koşulu sağlanınca her durumda `j` atılıyor, yani "küçük olan atılır" garantisi aslında yok, "sonra gelen atılır" oluyor. n≤4 olduğu için pratikte problem çıkarmıyor ama davranış docstring'in söylediği şey değil.

**Çıktı:** `stage2/upload_0000_regions.json` → `[{"id":"region_0","label":"header","bbox":[x1,y1,x2,y2]}]` (piksel)
**Sonra:** → `src/generation/pipeline.py`

---

### AŞAMA 3 — Generation (`src/generation/` + `src/skeleton.py`) — **Claude burada**

#### [skeleton.py](src/skeleton.py)

Region bbox'larından **stilsiz, boş bir iskelet** üretir: yüzde-bazlı `position:absolute` div'ler. Renk yok, içerik yok, sadece kadraj.

```html
<div class="canvas">
  <div id="region_0" class="region" style="left:0%;top:0%;width:100%;height:8.2%;"></div>
  <div id="region_1" class="region" style="left:0%;top:8.2%;width:15%;height:91.8%;"></div>
</div>
```

`inject_region_html()` — BeautifulSoup ile `id`'li div'in **içine** üretilen fragment'i ekler.

**Neden yüzde:** iskelet piksele sabitlenmiş olsaydı farklı viewport'ta bozulurdu. Neden `absolute`: bölgelerin birbirine göre konumu Qwen'den geliyor, akışa bırakılırsa kaybolur.

#### [prompts.py](src/generation/prompts.py) ← **ikinci en önemli dosya**

Claude'a **JSON verilmiyor.** Sadece o bölgenin kırpılmış görseli + bölge tipine özel doğal dil talimatı. Yapı, renk, metin — hepsi modelin kendi görsel yorumundan geliyor.

`_SHARED_RULES` — tüm bölgelerde ortak, her kuralı bir gerçek bug'dan doğmuş:

| Kural | Hangi bug'ı çözüyor |
|---|---|
| Bare fragment, `<html>/<body>` yok | Bölge fragment'ı root'un body'sine girince iç içe `<body>` oluşuyordu |
| `<style>` bloğu yok, CDN yok, sadece inline `style=""` | Tailwind CDN kullanınca render internete bağımlı oluyordu; CLIP değerlendirmesi offline çalışmalı |
| `position:absolute/fixed` yasak | Model bölge içinde absolute kullanınca iskeletin kadrajından taşıyordu |
| Non-void elemanlar `/>` ile self-close edilemez | `<div/>` üretince tarayıcı DOM'u yanlış yorumluyordu |
| "Görmediğin şeyi uydurma" | Halüsinasyon kontrolü |

`_IMAGE_PLACEHOLDER_RULE` — gerçek fotoğraf/avatar/thumbnail için model **çizmeye çalışmasın**, `class="img-placeholder"` boş gri div koysun. Docstring'de kayıtlı gerçek bug: YouTube sidebar'ında model avatarlar için `https://i.pravatar.cc/40?img=1` gibi **uydurma dış URL** üretti — hem sahte görsel hem internet bağımlılığı. İlk versiyonda bu kural sadece `main_content`'te vardı, artık **4 bölge tipinin hepsinde.**

#### [model.py](src/generation/model.py) & [inference.py](src/generation/inference.py)

Claude client (`ANTHROPIC_API_KEY` ortam değişkeninden, koda asla gömülmüyor). Görsel base64 PNG olarak `client.messages.create()`'e gidiyor.

**Gemini implementasyonu silinmemiş**, dosyanın sonunda tek satırlık atama var:

```python
run_region_generation = run_region_generation_claude   # ← Gemini'ye dönmek için bu satırı değiştir
```

Bu bilinçli bir tasarım: sağlayıcı değişimi tek satır. Tarihçe: Qwen2.5-VL-7B (yerel) → Gemini 2.5 Flash (503 hatası) → Claude Sonnet.

#### [postprocess.py](src/generation/postprocess.py)

Üç aşamalı savunma: (1) ```` ```html ```` bloğunu ayıkla, (2) `<body>` varsa içini al, (3) yoksa DOCTYPE/html/head/body etiketlerini regex ile sil. Docstring dürüstçe yazıyor: *"model buna güvenilir uymayabiliyor"* — prompt'ta yasak olan şeyi model yine de yapıyor, o yüzden **deterministik temizlik şart.**

#### [generation/pipeline.py](src/generation/pipeline.py)

Akış: iskeleti kur → her region için crop al → Claude'a gönder → HTML'i ayıkla → iskelete enjekte et.
**Her bölge için ayrı API çağrısı** — bir sayfa = 1-4 çağrı.

**Çıktı:**

- `stage3/upload_0000.html` — tam HTML, ama fotoğraf yerleri hâlâ gri `.img-placeholder` div'leri
- `stage3/upload_0000_raw.txt` — Claude'un ham cevapları, `---` ile ayrılmış (debug)

**Sonra:** → `src/assets/pipeline.py`

---

### AŞAMA 4 — Görsel Yerleştirme (`src/assets/`) — model yok

#### [placeholders.py](src/assets/placeholders.py) ← **en zarif fikir burada**

1. `find_placeholder_boxes()` — üretilen HTML'i Playwright ile **render eder**, JS ile her `.img-placeholder`'ın gerçek `getBoundingClientRect()`'ini ve toplam layout boyutunu okur.
2. `replace_placeholders()` — bu render bbox'ını `original.width / layout_width` oranıyla **orijinal screenshot'a ölçekler**, oradan crop alır, `assets/phN.png` olarak kaydeder, BeautifulSoup ile div'i `<img>` ile değiştirir.

**Neden bu kadar basit:** ScreenCoder'ın orijinali burada UIED (klasik CV component tespiti, TensorFlow'lu CNN) + CIoU/Hungarian eşleme kullanıyor — ağır ve kırılgan bir bağımlılık. Bu proje o katmanı tamamen atıyor. Mantık: modele zaten "görselin kendi boyutunu koru" dendiği için, **render'daki placeholder'ın olduğu yer ile orijinaldeki görselin olduğu yer zaten hizalı olur.** Ayrı bir tespit + eşleme adımına gerek yok.

⚠️ Bu varsayımın kırıldığı yer: eşleştirme **döküman sırasına** göre (`elements[i] ↔ boxes[i]`). Model bir placeholder'ı yanlış yere koyarsa yanlış crop girer, hata sessizce geçer.

**Çıktı:** `final/upload_0000/index.html` + `final/upload_0000/assets/ph0.png ... ph5.png`
**Sonra:** → değerlendirme

---

### AŞAMA 6 — Değerlendirme (`src/evaluation/`)

#### [render.py](src/evaluation/render.py)

Üretilen HTML'i **Aşama 0'ın birebir aynı Playwright ayarlarıyla** render eder — `capture_screenshot()`'ı yeniden kullanıyor, tek fark kaynak (`file://` URI). Bu kasıtlı: karşılaştırmanın adil olması için DPR/viewport/format aynı kalmalı.

#### [clip_score.py](src/evaluation/clip_score.py)

CLIP ViT-B/32 ile iki görselin embedding'i arasında kosinüs benzerliği.
İki detay bug fix olarak kayıtlı:

- `use_safetensors=True` — CVE-2025-32434, eski torch'ta `.bin` pickle yüklemesi engelli
- `get_image_features()` yerine `vision_model` + `visual_projection` **elle çağrılıyor** — bazı transformers sürümlerinde `get_image_features` projekte edilmemiş 768-d pooler_output döndürüyor, 512-d CLIP embedding'i değil; bu da benzerliği anlamsızlaştırıyor

#### [evaluation/pipeline.py](src/evaluation/pipeline.py)

Hem `final/<stem>/index.html` hem `stage3/<stem>.html` düzenini destekler.
**Çıktı:** `eval_results/<stem>_render.png` + `eval_results/clip_scores.json` + konsola ortalama.

---

## 4. Neden Qwen (özellikle Qwen3-VL)?

Burada iki ayrı Qwen kararı var, karıştırılmaması lazım.

### A) Grounding'de Qwen3-VL-8B — hâlâ kullanılıyor ✅

**1. Yerel ve açık — grounding çok çağrılan bir adım.** Her görsel için çalışıyor ve ileride fine-tune edilmesi planlanan tek bileşen bu. Kapalı bir API'yi fine-tune edemezsin. Ağırlıklara erişim, bu aşamanın **gelecekteki tek eğitilebilir noktası** olması için şart.

**2. Tek seferde en zengin bilgi.** Klasik CV (UIED gibi) sadece kutu verir, ne olduğunu bilmez. Kapalı bir detection modeli sabit bir sınıf sözlüğüne bağlıdır. Qwen3-VL aynı anda konum + semantik etiket + istenirse içerik/OCR veriyor, üstelik **sabit bir component sözlüğüne bağlı olmadan** — prompt'u değiştirerek istediğin şemayı isteyebiliyorsun. Nitekim proje tam da bunu yaptı: prompt'u tekil elemandan 4 kaba bölgeye çevirdi, **tek satır kod değişmeden.**

**3. Bilinen zayıflığı, mimariyi şekillendirdi.** Genel VLM'ler piksel-hassas koordinatta zayıf; aynı kategoriden çok nesne varken tek kutu döndürme meşhur bir sorun. Proje bu zayıflıkla **savaşmak yerine ona teslim oldu**: madem Qwen ince koordinatta güvenilmez, ondan sadece kabası istenir. 4 büyük bölgenin kadrajı için piksel hassasiyeti gerekmiyor — birkaç piksel kayma sonucu bozmuyor. Bu, projenin en olgun mühendislik kararı.

**4. Altyapı zaten Qwen'e göre kalibre.** `normalize.py`'deki `PATCH_SIZE=32`, `min_pixels`/`max_pixels`, `smart_resize` — hepsi Qwen3-VL'in resmi spesifikasyonu. Başka bir model, tüm ön işleme katmanının yeniden yazılması demek.

**5. Colab A100 tek GPU kısıtı.** 8B parametre bfloat16'da ~16GB — A100 40GB'de rahat sığıyor, gerekirse 4-bit ile daha küçük GPU'ya da iniyor.

### B) Generation'da Qwen2.5-VL-7B — terk edildi ❌

Bu ayrı bir hikâye ve `web2code-oldplan.md` §2 Aşama 4'te ayrıntılı kayıtlı. Gerçek Colab testlerinde tekrarlayan bug'lar:

- Geçersiz CSS property adları (`direction` yerine `flex-direction`, `justify` yerine `justify-content`)
- Görünür metni bir HTML attribute'una gömüp render'da hiç göstermeme
- İç içe `<html>/<body>` sarmalayıcı üretme
- Prompt'ta açıkça yasaklanmasına rağmen `position:absolute` kullanma

Her biri ayrı ayrı prompt + deterministik onarım koduyla düzeltildi, ama **örüntü aynı kök soruna işaret ediyordu: 7B'lik açık model talimatlara güvenilir uymuyor.**

Kritik nokta — bu bir "Qwen kötü" kararı değil, bir **kontrollü deney**: sorun modelden mi kaynaklanıyor, yoksa mimariden mi? Daha güçlü kapalı bir model aynı hataları yapıyorsa suç mimarinin, yapmıyorsa modelin. Sonuç: Gemini 2.5 Flash denendi → 503 hatası → Claude Sonnet'e geçildi. Ve `postprocess.py`'nin docstring'i itiraf ediyor ki **Claude bile hâlâ ara ara `<html>` sarmalıyor** — yani sorunun bir kısmı gerçekten mimariden geliyormuş.

---

## 5. Bir sonraki adım için ne yapılabilir?

Önem sırasına göre.

### Kısa vade — ölçüm altyapısını düzelt

**1. Tek metrik yetersiz.** Şu an sadece CLIP score var. CLIP **global semantik benzerlik** ölçer; "sayfa genel olarak bir YouTube'a benziyor mu" der, "navbar'daki 5 link doğru mu" demez. Layout kaydığında bile yüksek skor verebilir. Plandaki §6 daha fazlasını istiyordu ama sadece CLIP yazıldı. Eklenecekler:

- **CW-SSIM** — piksel/yapısal hizalama, CLIP'in kaçırdığı kaymaları yakalar
- **TreeBLEU / DOM tag eşleşme oranı** — yapısal doğruluk
- **Metin recall** — ekrandaki metin OCR ile çıkarılıp üretilen DOM'un `textContent`'i ile karşılaştırılır. Hem eksik metni hem **halüsinasyonu** (görselde olmayan metin) yakalar. Uygulaması ucuz, bilgi getirisi yüksek — ilk yapılacak bu.

**2. Grounding'i ayrı ölç.** Şu an uçtan uca tek skor var, hata nerede oluştu bilinmiyor. Birkaç sayfa için elle 4 bölgeyi işaretle, Qwen'in bbox'larıyla **IoU** hesapla. Ancak bundan sonra "Qwen mi Claude mu bozuyor" sorusuna cevap verilebilir.

**3. Şu an tek bir gözlem noktası var.** `pipeline_output/`'ta 4 örnek işlenmiş. Herhangi bir mimari değişikliğin işe yaradığını iddia etmek için bu çok az. **En az 20-30 sayfalık sabit bir iç test seti** kurulmalı, her değişiklikte aynı sette çalıştırılmalı. Şu an bir değişikliğin iyileştirme mi bozma mı olduğu ölçülemiyor — bu en acil eksik.

### Orta vade — bilinen kırılganlıkları kapat

**4. Doğrulama döngüsü (Aşama 5).** Plandaki §2 Aşama 5, "zaman kalırsa" diye bırakılmış ama **altyapısı zaten hazır**: `render.py` render alıyor, `clip_score.py` karşılaştırıyor, Claude client duruyor. Eksik olan tek şey döngü: skor eşiğin altındaysa (orijinal + render + üretilen HTML)'i Claude'a geri ver, "farkı düzelt" de, 1-2 iterasyon. Mevcut parçalarla yazılabilecek **en yüksek getirili özellik bu.**

**5. Placeholder eşleşmesini sağlamlaştır.** `placeholders.py` döküman sırasına güveniyor. Bir güvenlik ağı: crop ile placeholder'ın en-boy oranını karşılaştır, sapma büyükse uyar. Ya da modelden placeholder'a `data-idx` attribute'u istet.

**6. `resolve_containment` sırasal davranışını düzelt.** Docstring "küçük olan atılır" diyor, kod "sonra gelen atılır" yapıyor. n≤4'te zararsız ama sessiz bir tuzak — alanları karşılaştırıp gerçekten küçüğü atacak şekilde düzeltilmeli.

**7. Bölge kapsama kontrolü.** Qwen bir bölgeyi hiç bulamazsa (örn. footer hiçbir bölgeye girmediyse) o içerik **sessizce kayboluyor**. Deterministik kontrol: 4 region'ın birleşimi görselin ne kadarını kaplıyor? %90'ın altındaysa uyar veya kalan alanı ek bir `main_content` bölgesi say.

### Uzun vade — asıl açık soru: eğitim

**8. Fine-tune kararını nihayet ver.** Plandaki tüm eğitim altyapısı (§4: LoRA r=32/α=64, curriculum, checkpoint/resume, %5-10 genel instruction karışımı) yazılı ama **hiç kod yok.** Karar için önce (2) numaralı IoU ölçümü lazım: Qwen'in kaba bölge tespiti zaten iyiyse fine-tune **gereksiz** — ve muhtemelen iyidir, çünkü 4 büyük dikdörtgen bulmak kolay bir görev. Bu durumda dürüst sonuç şu: *"görevi yeterince basitleştirdiğimizde fine-tune'a gerek kalmadı"* — bu negatif değil, **değerli bir bulgu** ve projenin metodoloji ilkeleri (§1: "pozitif/negatif sonuçları şeffaf raporla") tam da bunu istiyor.

**9. Fine-tune'a girilirse ilk iş:** `dedup.py`'de yorumlanmış `check_train_external_overlap()`'i geri aç. Şu an "önemsiz" çünkü eğitim yok — eğitim başladığı an **kritik** hale gelir (Design2Code-HARD / ScreenBench sızıntısı tüm sonuçları geçersiz kılar).

**10. Mimari sadeleştirmenin sınırını test et.** Proje sürekli sadeleşerek buraya geldi: tekil eleman tespiti silindi, hiyerarşi katmanı silindi, JSON şema silindi, UIED silindi. Doğal bir sonraki soru: **grounding katmanı da gerekli mi?** Kontrol deneyi — aynı sayfaları tek seferde, kırpmadan, doğrudan Claude'a ver ve CLIP skorlarını karşılaştır. Modüler pipeline kazanıyorsa mimarinin değeri kanıtlanmış olur; kazanmıyorsa Qwen katmanı 8B'lik bir GPU maliyetini boşuna ödüyor demektir. Bu deney ucuz ve projenin **temel tezini** test ediyor — mutlaka yapılmalı.

---

## Özet

Pipeline **çalışan ve mimarisi olgunlaşmış** durumda, ama şu an **kör uçuyor** — 4 örnek ve tek bir zayıf metrikle ilerleniyor. Bir sonraki adım yeni özellik değil, **ölçüm altyapısı** olmalı; ondan sonra hangi iyileştirmenin gerçekten işe yaradığı görülebilir.
