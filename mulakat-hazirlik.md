# web2code — Teknik Mülakat Hazırlık

> Bu projeyle mülakata girerken sorulması muhtemel sorular ve cevap iskeletleri.
> ⚠️ işaretli yerler projenin **gerçek zayıf noktaları** — savunmaya geçme, önce sen söyle.
>
> İlgili dokümanlar: [sunum.md](sunum.md) (proje anlatımı), [web2code-oldplan.md](web2code-oldplan.md) (karar geçmişi)

---

## BÖLÜM 1 — Açılış: "Projeni anlat"

**S1. Projeyi 2 dakikada anlat.**

> Ekran görüntüsü → HTML/CSS. Tek bir VLM'e uçtan uca yaptırmak yerine 5 aşamalı modüler pipeline. Gerekçe: ScreenCoder (arXiv:2507.22827) modüler ayrımın block-match'te 0.755, uçtan uca GPT-4o'nun 0.730 aldığını gösteriyor. Aşamalar: ön işleme (Playwright+PIL) → kaba bölge tespiti (Qwen3-VL) → kural-tabanlı bölge çözümleme → bölge bazlı kod üretimi (Claude) → gerçek görsel yerleştirme → CLIP ile değerlendirme.

**S2. Neden modüler pipeline? Uçtan uca tek model neden olmadı?**

> Tek model "gör + planla + kodla" görevinde element atlama/bozulma/yanlış yerleşim yapıyor. Ayrıca modülerlik **hata izolasyonu** veriyor: bir sayfa bozuk çıktığında hangi aşamanın suçlu olduğunu görebiliyorum.
>
> ⚠️ Dürüst ol: bunu **henüz ölçmedin** — bu bir literatür varsayımı, senin ablation'ın değil. Mülakatçı buraya girerse S58'e bak.

**S3. Bu projede en gurur duyduğun mühendislik kararı ne?**

> Grounding prompt'unun pivotu. Başta her UI elemanını tek tek tespit ediyorduk → hiyerarşi kuruyorduk → zengin JSON şemaya çeviriyorduk → koda veriyorduk. Hata her katmanda birikiyordu. VLM'lerin piksel-hassas koordinatta zayıf olduğu bilinen bir zaaf; **onunla savaşmak yerine görevi ona uydurdum** — Qwen'den sadece 4 kaba bölge iste, ince işi kod modeline bırak. İki katman komple silindi.

**S4. En büyük teknik zorluk neydi?**

> Model talimatlara güvenilir uymuyor. Prompt'ta "position:absolute kullanma" yazmasına rağmen kullanıyor, "fragment üret" demene rağmen `<html>` sarıyor, avatar için uydurma dış URL üretiyor. Öğrendiğim şey: **prompt bir garanti değil, bir öneri.** Her prompt kuralının arkasına deterministik bir savunma katmanı (`postprocess.py`) koymak zorunda kaldım.

---

## BÖLÜM 2 — Ön işleme

**S5. Neden PNG zorunlu, JPEG neden kodda hata fırlatıyor?**

> JPEG kayıplı; blok artefaktları küçük yazı ve ikon kenarlarını bozuyor. Ama asıl kritik olan: **CSS renk kodu piksel değerinden okunuyor.** JPEG chroma subsampling düz renk alanlarını kaydırıyor → `#3b82f6` yerine `#3a81f5` üretiyorsun. Bu bir sınıflandırma değil, birebir reprodüksiyon görevi.

**S6. Neden hiç data augmentation yok? Bu ML projesi değil mi?**

> Bilinçli. Renk augmentasyonu (jitter/hue/brightness) bu görevde **doğru cevabı bozar** — çıktı CSS renk kodu, girdinin rengi değişirse ground truth değişir. Geometrik augmentasyon da layout'u bozar. Augmentation, invaryans istediğin görevlerde işe yarar; burada tam tersine **ekivaryans** istiyorsun.

**S7. `smart_resize` ne yapıyor, 32 sayısı nereden geliyor?**

> Qwen3-VL'in ViT patch boyutu 32px. Boyut 32'nin katı değilse padding/kırpma oluyor, bu da koordinat hizasını bozuyor. `min_pixels=256×32×32`, `max_pixels=1280×32×32` → bu aslında **görsel token bütçesi**: 256-1280 arası patch, yani 256-1280 görsel token.

**S8. Çok uzun bir sayfada (1280×8000) ne olur?**

> ⚠️ Zayıf nokta, dürüst cevapla: `max_pixels` sınırı devreye girer, görsel ~1280×1024'e sıkışır — 8× dikey sıkışma. Metin okunamaz hale gelir. Çözüm olarak `splitter.py` var ama o **sadece URL yolunda** çalışıyor (canlı DOM'un `getBoundingClientRect()`'ine ihtiyaç duyuyor). Doğrudan PNG yüklendiğinde bölme yok. Bu kapatılmamış bir gedik.

**S9. `splitter.py` neden DOM sınırlarından bölüyor, sabit piksel aralığından değil?**

> Sabit aralık bir kartı/bölümü ortadan ikiye böler; model yarım kartı görüp anlamsız kod üretir. DCGen'in "divide and conquer" mantığı. `body`'nin doğrudan çocuklarının gerçek render sınırlarını JS ile okuyorum — bunlar semantik kesme noktaları.

**S10. pHash nedir, MD5'ten farkı ne? Neden Hamming eşiği 5?**

> MD5 kriptografik: 1 piksel değişse hash tamamen değişir. pHash **algısal**: DCT ile düşük frekans bileşenlerini alır, görsel olarak benzer görüntüler benzer hash üretir. Hamming mesafesi 64-bit hash üzerinde ≤5 ≈ "neredeyse aynı görsel". Eşik literatürden gelen bir konvansiyon — ⚠️ dürüst ol: bu projede **kalibre edilmedi**, bir ROC eğrisi çizmedim.

**S11. Neden dedup silmiyor, sadece raporluyor?**

> Hangi kopyanın tutulacağı içerik kalitesine bağlı (biri lazy-load tamamlanmadan çekilmiş olabilir). Otomatik silme sessiz veri kaybı riski. Karar çağırana bırakıldı.

**S12. `check_train_external_overlap` neden yorum satırında?**

> Eğitim olmadığı için şu an ölü kod — sızıntı kontrolü yapacak bir eğitim seti yok. Ama fine-tune'a geçilirse **ilk geri açılacak şey bu**: Design2Code-HARD/ScreenBench'ten bir görsel eğitim setine sızarsa tüm değerlendirme sonuçları geçersiz olur.

---

## BÖLÜM 3 — Grounding / VLM

**S13. Neden Qwen3-VL? Alternatifleri neden elemedin?**

> Dört ayrı gerekçe:
>
> - **Yerel + açık ağırlık:** Pipeline'ın fine-tune edilmesi planlanan tek noktası burası; kapalı API'yi eğitemezsin.
> - **Şema esnekliği:** Klasik CV (UIED) sadece kutu verir, ne olduğunu bilmez; kapalı detection modelleri sabit sınıf sözlüğüne bağlı. Qwen prompt'la istediğim şemayı veriyor — nitekim tekil elemandan 4 kaba bölgeye geçerken **tek satır kod değişmedi**, sadece prompt.
> - **Altyapı kalibrasyonu:** `normalize.py`'nin tamamı (patch 32, min/max_pixels) Qwen3-VL spesifikasyonu. Model değişimi = ön işleme katmanını yeniden yazmak.
> - **Donanım:** 8B, bf16'da ~16GB → Colab A100 40GB'de rahat; `--load-in-4bit` ile daha küçük GPU'ya iner.

**S14. Qwen3-VL'in bilinen zayıflığı ne, sen nasıl ele aldın?**

> Genel VLM'ler piksel-hassas koordinatta zayıf; aynı kategoriden çok nesne varken (5 buton) tek kutu döndürme meşhur bir sorun. Ele alışım: **problemi modele uydurdum.** 4 büyük dikdörtgenin kadrajında birkaç piksel kayma sonucu bozmuyor — hassasiyet gereksinimini düşürdüm.

**S15. Neden `do_sample=False`?**

> Greedy decoding. Koordinat üretimi kalibrasyon görevi, yaratıcılık görevi değil — sampling burada sadece varyans ekler. Ayrıca tekrarlanabilirlik: aynı görsel her çalıştırmada aynı bbox'ı vermeli, yoksa bir değişikliğin etkisini ölçemezsin.

**S16. Model 0-1000 skalada koordinat veriyor. Neden piksel değil?**

> Qwen'in eğitim konvansiyonu. Mantığı: model görselin gerçek piksel boyutunu bilmiyor (resize ediliyor), normalize skala çözünürlükten bağımsız. Dönüşüm `coords.py`: `x_px = bbox/1000 × genişlik`.

**S17. Neden JSON'u `json.loads` ile tek seferde parse etmiyorsun?**

> Model JSON'un önüne/arkasına açıklama yazıyor, bazen liste kapanışını unutuyor. Tek seferde parse ederse **tüm çıktı çöpe gider**. `\{[^{}]*\}` regex'i tek tek obje yakalayıp `json.loads` ile doğruluyor — bozuk kaydı atlayıp geri kalanı kurtarıyorum. Kısmi başarı > toptan başarısızlık.

**S18. Bu regex'in kırıldığı yer neresi?**

> `[^{}]` iç içe süslü parantez kabul etmiyor — nested JSON gelirse patlar. Bu tasarımın **kabul edilmiş sınırı**: şemam düz, iç içe olmasın diye zaten. Ama şema derinleşirse regex'i bir bracket-matching parser'a çevirmek gerekir.

**S19. Tiling neden yazıldı ama neden kapalı?**

> Tekil eleman tespiti döneminde yazıldı — uzun sayfayı overlap'li parçalara bölüp her parçayı ayrı sorup IoU ile birleştiriyor. Kaba bölge tespitine geçince **zararlı** hale geldi: her tile kendi `main_content`'ini üretir, 3 çakışan main_content elde edersin. Kod duruyor çünkü tekil tespite dönülürse gerekecek.

**S20. `merge_tile_detections` IoU eşiği 0.5 — neden bu değer?**

> Object detection NMS konvansiyonu. ⚠️ Dürüst ol: bu projede **ölçülerek seçilmedi**, taşındı. Zaten kapalı olduğu için etkisi yok.

**S21. Grounding'in doğruluğunu nasıl ölçüyorsun?**

> ⚠️ **Ölçmüyorum — projenin en büyük eksiği bu.** Sadece `visualize.py` ile kutuları görselin üstüne çizip gözle bakıyorum. Uçtan uca tek bir CLIP skoru var, hata hangi aşamada oluştu ayırt edemiyorum. Yapılması gereken: birkaç sayfada elle bölge işaretle, IoU hesapla. Bu benim bir sonraki adımım.

---

## BÖLÜM 4 — Regions

**S22. Bu aşamada neden model yok?**

> Çözdüğü problem tamamen geometrik: bir kutu diğerini tamamen kapsıyorsa biri fazlalık. Bunun için model çağırmak hem maliyet hem belirsizlik ekler. **Deterministik çözülebilen şeyi modele sorma** — projenin genel ilkesi.

**S23. `resolve_containment` neden gerekli?**

> Qwen sık sık aynı bölgeyi iki kez tespit ediyor — biri geniş, biri dar. Kaba düzen bölgeleri tanım gereği iç içe olamaz, dolayısıyla içerilen kutu kesinlikle hata.

**S24. (Zor) Bu fonksiyonda bir bug var mı?**

> ⚠️ **Evet, kabul et — bu soru gelirse dürüstlük puan kazandırır.** Docstring "küçük olan atılır" diyor ama kod `_contains(i,j) or _contains(j,i)` koşulu sağlanınca **her durumda `j`'yi** atıyor. Yani gerçek davranış "sonra gelen atılır" — liste sırasına bağlı. n≤4 olduğu için pratikte zarar vermiyor ama davranış dokümantasyondan farklı. Düzeltmesi: alanları karşılaştır, gerçekten küçüğü at.

**S25. Bir bölge hiç tespit edilmezse ne olur?**

> ⚠️ **Sessizce kaybolur.** Footer hiçbir bölgeye girmediyse o içerik final HTML'de hiç yok — ve bunu size hiçbir şey söylemiyor. Çözüm: region'ların birleşim alanı / toplam alan oranını hesapla, %90 altındaysa uyar ya da kalanı ek bölge say. Yazılmadı.

---

## BÖLÜM 5 — Generation / Prompt engineering

**S26. Neden Claude'a JSON şeması vermiyorsun? Bu bilgiyi atmak değil mi?**

> Eskiden veriyordum — zengin JSON şema (renk, font, layout, hiyerarşi) tam olarak silinen Aşama 2b'ydi. Sorun: **JSON'daki her alan bir hata kaynağı.** Şemanın rengi yanlışsa modelin gözü doğru görse bile yanlış yazıyordu; şema modelin görüşünü **override ediyordu**. Şimdi model kırpılmış görseli doğrudan görüyor ve kendi yorumunu yazıyor. Bilgiyi atmadım — **bilginin daha güvenilir bir kaynağına geçtim.**

**S27. `_SHARED_RULES`'taki her kural neyi çözüyor?**

> Hepsi gerçek bug'lardan doğdu:
>
> | Kural | Bug |
> |---|---|
> | Bare fragment | Fragment root'un body'sine girince iç içe `<body>` |
> | CDN/`<style>` yasak, sadece inline | Tailwind CDN → render internete bağımlı, offline CLIP değerlendirmesi çalışmıyor |
> | `position:absolute` yasak | Model bölge içinde absolute kullanınca iskelet kadrajından taşıyordu |
> | `<div/>` self-close yasak | Tarayıcı DOM'u yanlış yorumluyordu |
> | "Görmediğini uydurma" | Halüsinasyon |

**S28. Placeholder kuralının hikâyesini anlat.**

> Başta kural sadece `main_content`'teydi (ScreenCoder da öyle yapıyor). Gerçek testte YouTube sidebar'ında model avatarlar için `https://i.pravatar.cc/40?img=1` **uydurdu** — hem sahte görsel hem render'ın internete bağımlı hale gelmesi. Öğrenilen ders: **kuralı bir bölge tipine kısıtlamak, diğerlerinde modelin serbest kalması demek.** Kural 4 tipin hepsine yayıldı.

**S29. `postprocess.py`'de neden 3 katmanlı temizlik var?**

> Model prompt'ta açıkça yasaklanan şeyi yine de yapıyor. Katmanlar: (1) ` ```html ` bloğunu ayıkla, (2) `<body>` varsa içini al, (3) yoksa DOCTYPE/html/head/body'yi regex ile sil. **Prompt bir garanti değil; kritik invaryantlar deterministik kodla zorlanmalı.**

**S30. Claude bile hâlâ `<html>` sarıyorsa, "sorun modelde mi mimaride mi" deneyinin cevabı ne?**

> Kısmen mimaride. Qwen2.5-VL-7B'yi bırakma gerekçem "talimat takibi zayıf"tı; Claude'un da aynı şeyi ara ara yapması gösteriyor ki **bir fragment üretme talebi, modelin eğitim dağılımındaki "tam sayfa HTML" önyargısına karşı savaşıyor.** Yani sorunun bir kısmı model kapasitesi değil, görev formülasyonu. Bu benim için değerli bir negatif bulgu.

**S31. Model geçmişini anlat: Qwen2.5-VL-7B → Gemini → Claude.**

> Qwen2.5-VL-7B'de tekrarlayan bug'lar: geçersiz CSS property adları (`direction` yerine `flex-direction`), görünür metni HTML attribute'una gömüp render'da hiç göstermeme, iç içe `<html>` sarma, yasaklanmış `position:absolute`. Her birini prompt + onarım koduyla düzelttim ama örüntü aynı köke işaret ediyordu. **Bu bir "Qwen kötü" kararı değil, kontrollü deney:** güçlü kapalı model de aynı hataları yapıyorsa suç mimarinin. Gemini 2.5 Flash denendi, 503 aldı; Claude Sonnet'e geçildi.

**S32. Gemini kodunu neden silmedin?**

> Sağlayıcı değişimi tek satırlık atama (`run_region_generation = run_region_generation_claude`). Bu bilinçli bir soyutlama — API sağlayıcısı bu projede **değişken**, sabit değil. Ölü kod değil, sıcak yedek.

**S33. Bir sayfa kaç API çağrısı? Maliyet nedir?**

> Bölge başına 1 çağrı, yani 1-4. Her çağrıda base64 PNG + ~600 token prompt, `max_tokens=4096`. ⚠️ Ölçmedin — mülakatta "ölçmedim ama şu şekilde hesaplarım" de: görsel token maliyeti crop boyutuna bağlı, sayfa başına kaba tahmin.

**S34. (Zor) Bir API çağrısı hata verirse ne olur?**

> ⚠️ **Kabul et:** hiç try/except yok. Tek bir 429/503 tüm batch'i öldürür ve o ana kadarki bölgeler diske yazılmadığı için kaybolur. Rate limit backoff'u da yok. Production'a yakın hale getirmek için ilk eklenecek şey bu.

**S35. Claude çağrısında `temperature` set edilmiş mi? Sonuç ne?**

> ⚠️ Edilmemiş — varsayılan kullanılıyor. Yani generation **deterministik değil**, aynı görsel iki farklı HTML üretebiliyor. Grounding'de `do_sample=False` ile determinizmi zorlarken burada zorlamamak bir tutarsızlık. A/B karşılaştırması yapacaksan `temperature=0` şart, yoksa gördüğün fark model varyansı mı senin değişikliğin mi bilemezsin.

**S36. Bölgeleri paralel işlesen olur mu?**

> Evet — bölgeler birbirinden tamamen bağımsız, ortak state yok. Şu an seri, yani 4 bölgeli bir sayfa 4× latency. `asyncio` veya thread pool ile 4× hızlanır. Sınır: API rate limit.

---

## BÖLÜM 6 — Skeleton (buradan zor sorular gelir)

**S37. Skeleton neden yüzde-bazlı, piksel değil?**

> Piksele sabitlenmiş iskelet farklı viewport'ta bozulur. Yüzde ile bölgelerin **göreli** konumu korunur.

**S38. Neden `position:absolute`? Prompt'ta modele absolute'u yasaklamışsın, çelişki değil mi?**

> Çelişki değil, **katman ayrımı.** Bölgelerin birbirine göre konumu Qwen'in bbox'ından geliyor — bu bilgi normal akışa bırakılırsa kaybolur, o yüzden iskelet seviyesinde absolute. Ama bölge **içinde** absolute kullanılırsa içerik kendi kadrajından taşar, o yüzden modele yasak. Dış çerçeve mutlak, iç akış normal.

**S39. (Çok zor) `.region`'da `overflow:hidden` var. Model region'ın sığdığından fazla içerik üretirse ne olur?**

> ⚠️ **Sessizce kırpılır.** Ne hata, ne uyarı — sadece içeriğin bir kısmı görünmez olur. Ve CLIP score bunu yakalayamaz çünkü genel görünüm hâlâ benziyor. Bu, projede **fark edilmesi en zor hata sınıfı.** Tespiti için `scrollHeight > clientHeight` kontrolü render sırasında yapılabilir — yazılmadı.

**S40. (Çok zor) `html, body { height: 100% }` ve `.canvas { height: 100% }`. Orijinal görsel 1280×2400 ise, render edilen sayfanın yüksekliği ne olur?**

> ⚠️ **Bu soruyu bekle, en teknik açık burası.** `height:100%` = **viewport** yüksekliği = 800px. Region'lar absolute olduğu için doküman büyümüyor. Yani 1280×2400'lük bir sayfa 1280×800'e **sıkışıyor** — en-boy oranı korunmuyor, dikey 3× ezilme.
>
> Cevabın: "Bu gerçek bir hata ve düzeltmesi net — `build_skeleton` zaten `canvas_height` parametresini alıyor ama sadece yüzde hesabında kullanıyor; canvas'a `height: {canvas_height}px` (veya `aspect-ratio`) vermek gerekiyordu. Bunu ölçemedim çünkü CLIP processor zaten her iki görseli de 224×224'e resize ediyor, yani metriğim bu hataya **kör**."
>
> Bu cevap seni kurtarır: hatayı da görüyorsun, neden yakalanmadığını da açıklıyorsun.

---

## BÖLÜM 7 — Asset yerleştirme

**S41. ScreenCoder burada UIED + Hungarian matching kullanıyor. Sen neden kullanmadın?**

> UIED ağır ve kırılgan bir bağımlılık (TensorFlow'lu CNN, `cnn-rico-1.h5`). Benim gözlemim: modele zaten "görselin kendi boyutunu koru" dendiği için, **render'daki placeholder'ın konumu ile orijinaldeki görselin konumu zaten hizalı çıkıyor.** Ayrı bir tespit + eşleme adımı gereksiz. Bir bağımlılığı ve bir hata kaynağını komple eledim.

**S42. Placeholder'ın konumunu nasıl buluyorsun?**

> Statik HTML parse ile bulunmaz — inline CSS layout'un nereye oturacağını ancak tarayıcı bilir. O yüzden HTML'i **Playwright ile render edip** JS'te `getBoundingClientRect()` okuyorum. Sonra `original.width / layout_width` oranıyla orijinal screenshot'a ölçekleyip crop alıyorum.

**S43. Bu yaklaşım ne zaman kırılır?**

> Eşleştirme **döküman sırasına** göre: `elements[i] ↔ boxes[i]`. Model bir placeholder'ı yanlış yere koyarsa yanlış crop girer ve **hata sessiz geçer**. Güvenlik ağı: crop ile placeholder'ın en-boy oranını karşılaştır, sapma büyükse uyar. Ya da modelden `data-idx` attribute'u istet. İkisi de yazılmadı.

**S44. `scale_x` ve `scale_y` neden ayrı hesaplanıyor?**

> Layout genişliği ile orijinal genişlik oranı, yükseklikteki oranla aynı olmayabiliyor (bkz. S40'taki sıkışma). Ayrı ölçek en azından crop'un **doğru yeri** bulmasını sağlıyor — ama crop'un kendisi distorsiyona uğramış bir layout'tan geliyor.

---

## BÖLÜM 8 — Değerlendirme (en çok baskı burada gelecek)

**S45. CLIP score nedir, neden onu seçtin?**

> İki görselin CLIP görsel embedding'leri arasındaki kosinüs benzerliği. Seçme gerekçem: referans HTML gerektirmiyor (ground truth kodum yok, sadece görselim var) ve literatürde web2code işlerinde yaygın.

**S46. (Kritik) CLIP score bu görev için iyi bir metrik mi?**

> ⚠️ **"Evet" deme — bu tuzak soru.** Cevap: **Hayır, yetersiz.** Üç somut sebep:
>
> 1. CLIPProcessor girdiyi **224×224'e resize ediyor.** 1280×2400'lük bir sayfa 224×224'e iniyor — metin tamamen kayboluyor, ince layout farkları yok oluyor. Metriğim aslında "bu iki şey genel olarak aynı tür sayfa mı" diyor.
> 2. CLIP **image-text** kontrastif eğitimle öğrenildi, layout hizalaması için değil. Semantik benzerliğe duyarlı, geometrik kaymaya kör.
> 3. 512 boyuta sıkıştırılmış bir temsilde "navbar'da 5 link var mı" bilgisi zaten yok.
>
> Bunu bilmek, kullanmaktan daha değerli — takip sorusuna S47 ile cevap ver.

**S47. Yerine ne kullanırdın?**

> Katmanlı ölçüm:
>
> - **Metin recall/precision** — orijinali OCR'la, üretilen DOM'un `textContent`'iyle karşılaştır. Hem eksik metni hem **halüsinasyonu** yakalar. Ucuz, yüksek bilgi getirisi, ilk yapılacak.
> - **CW-SSIM** — piksel/yapısal hizalama, CLIP'in kaçırdığı kaymaları görür.
> - **TreeBLEU / DOM tag eşleşme** — yapısal doğruluk.
> - **Blok bazlı IoU** — ScreenCoder'ın block-match metriği; benim mimarime doğrudan uyuyor.

**S48. Şu an kaç örnek üzerinde ölçtün?**

> ⚠️ **4.** Ve tek metrik. Bu, herhangi bir iddia için istatistiksel olarak anlamsız. Dürüst çerçeve: "Bu bir mekanik doğrulama, bir değerlendirme değil — pipeline uçtan uca çalışıyor mu onu gösteriyor. Performans iddiası için en az 20-30 sayfalık sabit bir iç test seti kurmam gerek, o benim bir sonraki adımım."

**S49. Render ayarlarını Aşama 0 ile aynı tutman neden önemli?**

> `render.py` doğrudan `capture_screenshot()`'ı yeniden kullanıyor — tek fark kaynak (`file://` URI). DPR, viewport genişliği, PNG, chrome yokluğu birebir aynı. Farklı olsaydı ölçtüğüm fark modelin hatası mı render ayarı mı ayırt edemezdim. **Karşılaştırmanın tek serbest değişkeni içerik olmalı.**

**S50. `clip_score.py`'de `get_image_features` yerine neden elle `vision_model` + `visual_projection` çağırıyorsun?**

> Bazı transformers sürümlerinde `get_image_features` **projekte edilmemiş** 768-d `pooler_output` döndürüyor, 512-d CLIP embedding'i değil. Projeksiyon öncesi uzayda kosinüs benzerliği anlamsız — tüm görseller birbirine benzer çıkıyor. Elle çağrı sürümden bağımsız doğru embedding'i garantiliyor. Bunu skorlar şüpheli derecede yüksek gelince fark ettim.

**S51. `use_safetensors=True` neden var?**

> CVE-2025-32434 — `torch.load` pickle deserialization açığı; yeni torch sürümleri `.bin` ağırlık yüklemesini engelliyor. safetensors bu sınıra tabi değil ve CLIP repo'sunda zaten mevcut.

---

## BÖLÜM 9 — ML temelleri (proje dışı ama sorulur)

**S52. LoRA nedir, neden full fine-tuning yerine?**

> Ağırlık güncellemesini düşük ranklı iki matrisin çarpımı olarak parametrize eder: `W + BA`, B∈R^{d×r}, A∈R^{r×k}. Sadece B ve A eğitilir. Kazanç: eğitilebilir parametre sayısı ~%0.1'e iner, optimizer state küçülür → tek GPU'ya sığar; base model dokunulmaz kaldığı için birden çok adapter takılabilir.

**S53. Planında r=32, α=64 var. Bu sayılar ne anlama geliyor?**

> `r` = adaptasyonun kapasitesi. Düşük rank (8-16) stil/ton adaptasyonu için yeterli ama **kod üretimi ve koordinat kalibrasyonu gibi kesin çıktı gereken görevlerde yetersiz** — o yüzden 32'den başlanıyor. `α` ölçekleme: efektif katkı `(α/r)·BA`. α/r ≈ 2 oranı stabil kabul ediliyor; oranı sabit tutunca r'yi değiştirdiğinde learning rate'i yeniden ayarlaman gerekmiyor.

**S54. Neden sadece attention değil, tüm linear katmanlar hedefleniyor?**

> Orijinal LoRA makalesi attention'a odaklanmıştı ama sonraki çalışmalar MLP katmanlarının da dahil edilmesinin özellikle **yeni format/görev** öğrenirken belirgin fark yarattığını gösterdi. Burada model yeni bir çıktı formatı öğreniyor, sadece stil değiştirmiyor.

**S55. Catastrophic forgetting nedir, planında nasıl ele alınmış?**

> Dar bir görevde eğitim, modelin genel yeteneklerini bozar. Plandaki karşı önlem: eğitim verisine **%5-10 genel amaçlı instruction verisi karıştırmak.** Ayrıca 2-3 epoch sınırı — fazlası hem overfit hem forgetting.

**S56. 4-bit NF4 quantization ne yapıyor, ne kaybediyorsun?**

> Ağırlıkları 4-bit'e sıkıştırır; NF4 normal dağılımlı ağırlıklar için bilgi-teorik olarak optimal quantile dağılımı kullanır. Hesap bf16'da yapılır (`bnb_4bit_compute_dtype`), yani dequantize-on-the-fly. Kayıp: bir miktar doğruluk + **daha yavaş inference** (dequantization overhead'i). A100'de gereksiz, T4'te zorunlu.

**S57. IoU nedir, neden 0-1?**

> Kesişim alanı / birleşim alanı. Detection'da standart çünkü hem konum hem boyut hatasını tek sayıda birleştiriyor ve ölçek-invaryant.

---

## BÖLÜM 10 — Savunma soruları (en tehlikeliler)

**S58. Modüler pipeline'ın uçtan uca yaklaşımdan iyi olduğunu kanıtladın mı?**

> ⚠️ **En tehlikeli soru bu.** Dürüst cevap: **Hayır.** Literatüre dayanan bir varsayım, benim ablation'ım değil. Ve deney çok ucuz: aynı sayfaları kırpmadan doğrudan Claude'a ver, skorları karşılaştır. Sonuç modüler pipeline lehine değilse Qwen katmanı 8B'lik bir GPU maliyetini boşuna ödüyor demektir. **Bunu yapmadım ve yapmam gerekiyor — projenin temel tezini test eden deney bu.**
>
> Bu soruya "kanıtladım" diye cevap verirsen ve üstüne gelirlerse batarsın; "kanıtlamadım, deneyi de biliyorum" dersen olgun görünürsün.

**S59. Proje adı "web2code" ve elinde Web2Code datasetinden 1.1M çift var. Neden hiç eğitim yapmadın?**

> Mimari sadeleştikçe eğitim ihtiyacı ortadan kalktı. Başlangıçta Qwen'in her UI elemanını hassas tespit etmesi gerekiyordu — bu fine-tune gerektirebilirdi. Şimdi ondan istenen şey **4 büyük dikdörtgen**; bunun için zero-shot muhtemelen zaten yeterli. Fine-tune kararını vermeden önce grounding IoU'sunu ölçmem gerekiyor: zaten iyiyse fine-tune gereksiz bir maliyet olur. *"Görevi yeterince basitleştirince eğitime gerek kalmadı"* — bu negatif değil, raporlanmaya değer bir bulgu.

**S60. Bu projenin en zayıf noktası ne?** *(kesin sorulur)*

> **Ölçüm.** 4 örnek, tek ve zayıf bir metrik. Şu an kör uçuyorum: bir değişiklik yaptığımda iyileştirme mi bozma mı olduğunu **söyleyemem**. Mimari olgunlaştı ama doğrulama altyapısı geride kaldı. O yüzden sıradaki işim yeni özellik değil, ölçüm altyapısı.
>
> Bunu **onlar söylemeden sen söyle** — inisiyatif kazandırır.

**S61. Yarın production'a çıkacak, hangi 3 şeyi yaparsın?**

> 1. **API hata yönetimi** — retry + exponential backoff + kısmi sonuçları diske yazma (S34).
> 2. **Canvas yükseklik hatası** — en-boy oranı distorsiyonu (S40); şu an her uzun sayfa bozuk render ediliyor.
> 3. **Bölge kapsama + overflow kontrolü** — sessiz içerik kaybını görünür yap (S25, S39).

**S62. 1 milyon sayfa işlemen gerekse mimaride ne değişir?**

> - Grounding batch inference'a çevrilir (şu an tek tek), vLLM/TGI ile serving.
> - Generation paralelleştirilir (bölgeler bağımsız) + prompt caching — sistem prompt'u ve kuralları her çağrıda yeniden göndermek israf.
> - Playwright browser instance'ları havuzlanır (şu an her `replace_placeholders` çağrısı yeni browser açıyor — çok pahalı).
> - Aşamalar arası dosya sistemi yerine bir kuyruk/obje deposu; her aşama bağımsız ölçeklenebilir worker.
> - **Ve asıl soru:** bu ölçekte API maliyeti dayanılmaz olur → o noktada generation için açık bir modeli fine-tune etmek ekonomik olarak anlamlı hale gelir. İşte eğitim aşaması buraya girer.

**S63. Aynı projeye baştan başlasan neyi farklı yapardın?**

> **Ölçümü ilk gün kurardım.** 20-30 sayfalık sabit bir test seti ve metrik paketi olsaydı, tekil-eleman tespitinden kaba bölgeye pivotun gerçekten iyileştirme olduğunu **kanıtlayabilirdim** — şu an sadece "daha iyi hissettirdi" diyebiliyorum. Mimari kararların doğruluğunu ölçemediğin sürece o kararlar mühendislik değil, tercih.

---

## BÖLÜM 11 — Sen onlara ne sorarsın

Mülakat sonunda soru sormamak kötü sinyal. Bu projeden doğal olarak çıkanlar:

1. Burada model seçimlerini nasıl doğruluyorsunuz — ablation kültürü var mı, yoksa çoğunlukla literatüre mi güveniliyor?
2. Kapalı API mi kendi modelinizi mi çalıştırıyorsunuz? Bu kararı ne belirledi — maliyet, gecikme, veri gizliliği?
3. Prompt'a gömülü kuralları nasıl versiyonluyorsunuz? Bir prompt değişikliğinin regresyon yaratmadığını nasıl test ediyorsunuz?
4. Değerlendirmesi zor (ground truth'u olmayan) görevlerde metrik seçimine nasıl yaklaşıyorsunuz?

---

## Hazırlık taktiği

**Ezberleme, üç hikâyeyi anlat:**

1. **Pivot hikâyesi** (S3) — karmaşıklığı silerek problemi çözmek
2. **Model geçiş hikâyesi** (S31) — model değiştirmeyi kontrollü deney olarak kurgulamak
3. **Placeholder bug hikâyesi** (S28) — gerçek çıktıya bakınca ortaya çıkan hata

**Zayıflıkları önce sen söyle.** S46, S58, S60 senaryolarında savunmaya geçme — eksiği adlandır, nedenini açıkla, çözümünü söyle. Mülakatçı zaten bulacak; önce sen bulursan bu bir eksik değil, **öz-değerlendirme yeteneği** olur.

**S40'a özel çalış.** En derin teknik soru orası ve CSS bilgisi + hata ayıklama + metrik körlüğü farkındalığı üçünü aynı anda test ediyor.
