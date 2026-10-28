# Drone tespiti ve takibi için yöntem karşılaştırması

[Issue #27](https://github.com/cbsanal/drone-tespit-takip/issues/27) · Kaynak kontrolü: **26.10.2026** · Hedef: gündüz gökyüzü, pan-tilt kamera, Raspberry Pi 5.

**Başlangıç önerisi: drone verisiyle uyarlanacak YOLO26n, ardından ByteTrack.** YOLO11n aynı koşullarda karşılaştırma modeli olmalıdır. MOG2 hareketli kamerada doğrudan drone algılayıcısı yerine geçmez. Bu aşama literatür karşılaştırmasıdır; eğitim ve cihaz ölçümü yapılmadı.

## Yöntemlerin çalışma mantığı

**YOLO26n:** Görüntüden nesne kutusu, sınıf ve güven skoru üreten küçük bir sinir ağıdır. NMS gerektirmeyen uçtan uca çıkarım seçeneği bulunur; güncel belgede NMS kullanan başlık da vardır, bu nedenle çalıştırma seçeneği kaydedilmelidir. Küçük nesnelere yönelik STAL eğitim yaklaşımı, küçük drone başarısının kanıtı değildir. [Model belgesi](https://docs.ultralytics.com/models/yolo26/)

**YOLO11n:** Aynı tespit görevini yapan nano modeldir; aday kutuların çakışması NMS ile giderilir. Hazır ağırlıkları başlangıç sağlar ancak drone için etiketli veriye uyarlama gerekir. [Model belgesi](https://docs.ultralytics.com/models/yolo11/)

**MOG2:** Her pikselin geçmişini Gauss karışımıyla modelleyip arka plandan ayrılan pikselleri ön plan maskesi olarak verir. Etiketli drone eğitimi istemez; zamana yayılan arka plan öğrenmesi gerekir ve sonuç nesnenin sınıfını söylemez. [OpenCV açıklaması](https://docs.opencv.org/4.13.0/d1/dc5/tutorial_background_subtraction.html), [MOG2 API](https://docs.opencv.org/4.13.0/d7/d7b/classcv_1_1BackgroundSubtractorMOG2.html)

**ByteTrack:** Tespit kutularını Kalman hareket tahmini ve eşleştirmeyle kareler arasında aynı kimliğe bağlar. Önce yüksek güvenli, sonra uygun düşük güvenli kutulardan yararlanarak kesintileri azaltır; kendisi drone bulmaz ve ayrı bir sınıflandırıcı eğitmez. [Makale](https://arxiv.org/abs/2110.06864), [takip rehberi](https://docs.ultralytics.com/modes/track/)

## İşlev ve Raspberry Pi uygunluğu

| Yöntem | İhtiyaç ve çıktı | İşlem/bellek ve kurulum | Projedeki başlıca sınır | Kaynak |
|---|---|---|---|---|
| YOLO26n | Drone etiketleriyle ek eğitim; kutu/sınıf/güven | Fused model: 2,4 milyon parametre, 5,5 GFLOPs (640). CPU ve NCNN seçeneği; ek hızlandırıcı zorunlu değil. | Küçük/silik drone kaçabilir; kuş karışması ve kutu doğruluğu drone verisinde ölçülmeli. | [YOLO26](https://docs.ultralytics.com/models/yolo26/), [NCNN](https://github.com/Tencent/ncnn) |
| YOLO11n | Aynı etiket ve değerlendirme ihtiyacı | 2,6 milyon parametre, 6,5 GFLOPs (640). Aynı Ultralytics araç zinciri; NCNN dışa aktarımı değerlendirilebilir. | Daha büyük parametre sayısından doğrudan Pi hızı veya drone doğruluğu çıkarılamaz. | [YOLO11](https://docs.ultralytics.com/models/yolo11/), [Pi rehberi](https://docs.ultralytics.com/guides/raspberry-pi/) |
| MOG2 | Sıralı görüntüler; ön plan maskesi | OpenCV CPU uygulaması; piksel başına karışım modeli tutar. Çözünürlük ve karışım sayısı bellek/iş yükünü etkiler. | Kamera dönüşü, bulut, kuş ve aydınlık değişimi yanlış ön plan oluşturabilir. | [MOG2 API](https://docs.opencv.org/4.13.0/d7/d7b/classcv_1_1BackgroundSubtractorMOG2.html) |
| ByteTrack | Ardışık tespit kutuları; kimlik ve iz | Ultralytics içinde `bytetrack.yaml` ile seçilir. İz durumu ve eşleştirme maliyeti vardır; Pi RAM/FPS ölçümü gerekli. | Dahili kamera hareketi telafisi ve görünüş tabanlı yeniden kimliklendirme yok; hızlı dönüş/uzun kayıp kimliği bozabilir. | [Takip rehberi](https://docs.ultralytics.com/modes/track/) |
| KCF (isteğe bağlı) | Başlangıç kutusundan korelasyon filtresiyle takip | OpenCV tracking API; çevrimiçi hedef modeli, ayrı drone veri eğitimi gerekmez. Pi hızı/RAM ölçümü gerekli. | Küçük/dokusuz hedef, ölçek değişimi ve örtülme sonrası sürüklenme riski; yeniden tespit gerekir. | [KCF](https://docs.opencv.org/4.13.0/d2/dff/classcv_1_1TrackerKCF.html) |
| CSRT (isteğe bağlı) | Kanal ve uzamsal güvenilirlik kullanan korelasyon filtresi | Başlangıç kutusu gerekir; OpenCV tracking API. Kurulu pakette sınıfın varlığı kontrol edilir; Pi ölçümü gerekli. | Başlangıç kutusu hatası taşınabilir; hedef görünüm dışına çıkınca kendiliğinden sınıf bazlı yeniden tespit yapmaz. | [CSRT](https://docs.opencv.org/4.13.0/d2/da2/classcv_1_1TrackerCSRT.html) |

Parametre/model dosyası boyutu çalışma anındaki RAM değildir. Tüm yöntemlerde tepe RAM, işlemci yükü ve ısıl kısılma ayrıca ölçülmelidir. NCNN mobil/ARM çıkarımı için optimize bir çalışma ortamıdır; eğitim yöntemi değildir. Kurulumda işletim sistemi, Python, Ultralytics/OpenCV ve NCNN sürümleri sabitlenmelidir. [NCNN projesi](https://github.com/Tencent/ncnn)

## Kaynaklardaki hız ve başarı değerleri

| Model / yöntem | Donanım, girdi ve sürüm | Bildirilen süre / FPS | Ölçümün kapsamı ve başarı | Kaynak |
|---|---|---|---|---|
| YOLO26n ONNX | Pi 5; 640 girdi; Ultralytics 8.4.14 | 128,42 ms; yaklaşık 7,79 FPS | Çıkarım; kamera dahil toplam süre değil. Rehberde genel mAP50–95: 40,1. | [Pi karşılaştırması](https://docs.ultralytics.com/guides/raspberry-pi/#yolo26-performance-improvements-over-yolo11) |
| YOLO11n ONNX | Pi 5; 640 girdi; Ultralytics 8.4.14 | 147,20 ms; yaklaşık 6,79 FPS | Aynı kaynak tablosu; genel mAP50–95: 39,5. | [Tablonun kaynak metni](https://raw.githubusercontent.com/ultralytics/ultralytics/main/docs/en/guides/raspberry-pi.md) |
| YOLO26n NCNN | Pi 5; 640, FP32; Ultralytics 8.4.108 | 67,03 ms; yaklaşık 14,92 FPS | Ön/son işleme hariç çıkarım. Tekrarlama örneği COCO128 kullanıyor; ayrı ölçüm serisi. | [Pi ayrıntılı tablo](https://docs.ultralytics.com/guides/raspberry-pi/#detailed-comparison-table) |
| ByteTrack + YOLOX-X | Tek NVIDIA V100; 1440×800; makale v3 (2022), özgün uygulama | MOT17 test: 29,6 FPS (özette yaklaşık 30) | Tespit ve eşleştirmeli sistem; yalnız takip süresi değil. MOTA 80,3; IDF1 77,3; HOTA 63,1. İnsan takibi sonucu, drone/Pi sonucu değil. | [Makale, Tablo 3 ve deney düzeni](https://arxiv.org/html/2110.06864v3) |
| MOG2 | OpenCV 4.13.0 API; Pi 5 hedefi | **Ölçüm gerekli** | Kaynaklarda bu proje koşulları için karşılaştırılabilir FPS/başarı yok. | [OpenCV rehberi](https://docs.opencv.org/4.13.0/d1/dc5/tutorial_background_subtraction.html) |
| KCF / CSRT | OpenCV 4.13.0 API; Pi 5 hedefi | **Ölçüm gerekli** | Girdi çözünürlüğü ve hedef alanı sabitlenerek ayrı ölçülmeli. | [KCF](https://docs.opencv.org/4.13.0/d2/dff/classcv_1_1TrackerKCF.html), [CSRT](https://docs.opencv.org/4.13.0/d2/da2/classcv_1_1TrackerCSRT.html) |

FPS dönüşümleri `1000 / ms` ile hesaplanmıştır; canlı sistem garantisi değildir. İlk iki satırda hassasiyet, iş parçacığı sayısı ve ayrıntılı ölçüm veri bölümü açık verilmediğinden aynı kaynak koşullarıyla sınırlı yorum yapılmalıdır. 8.4.108 NCNN sonucu ile 8.4.14 YOLO11 sonucundan doğrudan model üstünlüğü çıkarılmaz. Aynı 8.4.14 ONNX tablosunda YOLO26n daha düşük gecikmelidir. [Pi rehberi](https://docs.ultralytics.com/guides/raspberry-pi/)

Güncel model sayfası YOLO26n için COCO mAP50–95 değerlerini normal başlıkta **40,9**, uçtan uca başlıkta **40,1** olarak ayırır; YOLO11n değeri **39,5**'tir. Bu genel COCO sonuçları küçük drone recall değeri değildir; farklı başlıkların değerleri karıştırılmamalıdır. [YOLO26](https://docs.ultralytics.com/models/yolo26/), [YOLO11](https://docs.ultralytics.com/models/yolo11/)

## Hareketli kamera ve veri sınırlamaları

MOG2 sabit görüntü koordinatlarında arka plan öğrenir. Pan-tilt hareketi sırasında önce kareleri hizalamak veya hareket bittikten sonra arka planı yeniden öğrenmek gerekir. OpenCV ECC ile geometrik hizalama sağlayabilir; büyük dönüşlerde başlangıç tahmini ve örtüşen görüntü alanı gerekir, yakınsama başarısız olabilir. **Proje açısından çıkarım:** dokusuz gökyüzü, değişen bulutlar, yeni açılan görüş alanı ve paralaks telafiyi zorlaştırır; hizalama ek işlem yükü getirir. Bu nedenle MOG2 ana yöntem olarak önerilmez. [OpenCV arka plan rehberi](https://docs.opencv.org/4.13.0/d1/dc5/tutorial_background_subtraction.html), [ECC](https://docs.opencv.org/4.13.0/dc/d6b/group__video__track.html)

Kuşlar hareket maskesine girebilir; ışık değişimi çok sayıda pikseli etkileyebilir. Havada duran veya kamera takibi sayesinde görüntüde sabit kalan drone, öğrenme açıkken arka plana karışabilir. Öğrenme hızını sıfırlamak bunu sınırlar fakat arka planın değişime uyumunu da durdurur. [MOG2 API](https://docs.opencv.org/4.13.0/d7/d7b/classcv_1_1BackgroundSubtractorMOG2.html)

Hazır YOLO26n/YOLO11n COCO ağırlıklarında **drone sınıfı yoktur**; `bird` veya `airplane` çıktısını drone diye yorumlamak doğru değildir. [Resmî COCO sınıf listesi](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/datasets/coco.yaml)

Task 02'nin seçilmiş paketinde 70 görüntü, 71 kutu, alanı 1.024 piksel² altında yalnızca 3 kutu ve 0 doğrulanmış negatif vardır. Bunlar başlangıç verisidir; küçük drone ve kuş/boş gökyüzü çeşitliliği artırılmalı, etiket kutuları ve kaynak/sahne ayrımları doğrulanmalıdır. XML'den YOLO biçimine dönüşüm ve ek eğitim sonraki görevin konusudur. Bağımsız resimler ByteTrack, MOG2, KCF veya CSRT'nin zamansal başarısını ölçmez. [Task 02 sonuçları](../task02-veri-hazirligi/raporlar/secim-ozeti.json)

İleride aynı ayrılmış drone test kümesinde precision/recall, küçük hedef recall ve kutu IoU; sıralı görüntülerde kimlik değişimi, hedef kaybı ve yeniden bulma süresi ölçülmelidir. Pi'de kamera okuma, ön işleme, çıkarım, son işleme ve takip süreleri ayrı; toplam gecikmenin medyanı ve %95 yüzdeliği birlikte kaydedilmelidir. Bu ölçütler önerilen deney planıdır; burada sonuç üretilmemiştir.

## İlk deneme önerisi

İlk tespit denemesinde, veri eksikleri giderildikten sonra drone sınıfına uyarlanacak **YOLO26n** ile başlayıp **YOLO11n**'i aynı veri, çözünürlük ve çalışma ortamında karşılaştıralım. Pi 5 dağıtımı için **NCNN** seçeneğini deneyelim; yayınlanan çıkarım hızını kamera dahil sistem hızı kabul etmeyelim. Tespit yeterli hale geldiğinde **ByteTrack** ekleyelim ve kamera dönüşlerinde kayıp/kimlik değişimini ölçelim. Uzun hedef kaybında yeni tespit bekleyelim; yalnız hareket tahminini doğrulanmış hedef konumu olarak kullanmayalım. **MOG2'yi** sabit kamera yardımcı deneyi olarak tutalım; mevcut statik resimlerle takip başarısı ilan etmeyelim. [Pi rehberi](https://docs.ultralytics.com/guides/raspberry-pi/), [ByteTrack rehberi](https://docs.ultralytics.com/modes/track/), [MOG2](https://docs.opencv.org/4.13.0/d1/dc5/tutorial_background_subtraction.html)
