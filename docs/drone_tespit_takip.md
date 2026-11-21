# Drone Tespit ve Takip Sistemi

Bu proje, görüntüler ve videolar üzerinden drone tespiti ve takibi gerçekleştirmek amacıyla geliştirilmektedir.

Proje kapsamında YOLO11s nesne tespit modeli eğitilmiş, ByteTrack algoritmasıyla nesne takibi gerçekleştirilmiş ve Python tabanlı test uygulamaları hazırlanmıştır.

Çalışmaların bu bölümü bilgisayar ortamında gerçekleştirilmiştir. Raspberry Pi, motor kontrolü ve fiziksel donanım entegrasyonu bu prototipin kapsamı dışındadır.

## 1. Kullanılan Teknolojiler

- **Python:** Model eğitimi, görüntü işleme ve test uygulamaları
- **YOLO11s:** Drone tespiti
- **Ultralytics:** Model eğitimi, tahmin ve takip işlemleri
- **PyTorch:** Derin öğrenme altyapısı ve GPU desteği
- **OpenCV:** Kamera ve video işlemleri
- **ByteTrack:** Tespit edilen drone'ların takip edilmesi
- **CUDA:** GPU üzerinde model çalıştırma

## 2. Veri Seti

Modelin eğitimi için Roboflow üzerinde yayımlanan *Drones Detect* veri setinin 29. sürümü kullanılmıştır.

Veri seti YOLO formatındadır ve tek bir nesne sınıfı içermektedir:

- `drone`

Veri seti dağılımı:

| Veri grubu | Görüntü sayısı |
|---|---:|
| Eğitim | 2347 |
| Doğrulama | 135 |
| Test | 29 |

Veri setinin kullanılan sürümü CC BY 4.0 lisansı altında sunulmaktadır. Yeniden kullanımda veri setinin kaynağına ve lisans koşullarına uyulmalıdır.

Veri seti dosyaları bu GitHub deposuna eklenmemektedir.

## 3. Model Eğitimi

Drone tespiti için önceden eğitilmiş YOLO11s modeli kullanılmış ve drone veri setiyle yeniden eğitilmiştir.

Eğitim yapılandırması:

| Parametre | Değer |
|---|---|
| Model | YOLO11s |
| Epoch | 50 |
| Görüntü boyutu | 640 |
| Batch size | 16 |
| GPU | NVIDIA RTX 4080 Laptop GPU |
| Sınıf sayısı | 1 |

Eğitim sonunda en iyi model ağırlıkları `best.pt` dosyasına kaydedilmiştir.

### Model değerlendirme sonuçları

| Ölçüt | Doğrulama | Test |
|---|---:|---:|
| Precision | %98,0 | %99,8 |
| Recall | %95,3 | %92,9 |
| mAP50 | %96,3 | %96,1 |
| mAP50-95 | %77,3 | %75,8 |

Bu sonuçlar kullanılan veri seti üzerinde elde edilmiştir. Test kümesinin küçük olması nedeniyle sonuçlar modelin bütün gerçek dünya koşullarında aynı performansı göstereceği anlamına gelmez.

## 4. Drone Tespiti ve Takibi

### Görüntü ve video tespiti

Eğitilen YOLO11s modeliyle video dosyalarında ve bilgisayar kamerasında drone tespiti gerçekleştirilmiştir.

### ByteTrack ile nesne takibi

Drone tespitlerine takip kimliği (ID) atanması için ByteTrack algoritması kullanılmıştır.

Takip uygulamalarında:

- Drone'un sınırlayıcı kutusu gösterilir.
- Takip ID'si görüntülenir.
- Merkez koordinatları hesaplanır.
- Drone'un hareket izi çizilir.
- Takip sonuçları CSV dosyasına kaydedilebilir.

Drone görüntüden çıktığında veya tespit geçici olarak kaybolduğunda takip ID'si değişebilir.

Bu durum, takip algoritmasının mevcut sınırlamalarından biridir.

## 5. Performans Testi

YOLO11s ve ByteTrack sisteminin işlem performansı, 412 kareden oluşan 25 FPS'lik bir video üzerinde ölçülmüştür.

Test yapılandırması:

- Görüntü boyutu: 960
- Güven eşiği: 0.40
- İşlem birimi: CUDA
- Takip algoritması: ByteTrack

### Benchmark sonuçları

| Ölçüt | Sonuç |
|---|---:|
| İşlenen kare | 412 |
| Takip bulunan kare | 376 |
| Takip kapsamı | %91,26 |
| Ortalama işleme hızı | 91,51 FPS |
| Ortalama kare işlem süresi | 10,93 ms |
| Medyan kare işlem süresi | 10,42 ms |
| Ortalama güven skoru | %57,43 |
| Farklı takip ID'si | 1 |
| Ardışık karelerde ölçülen ID değişimi | 0 |

Benchmark, görüntü gösterimi ve video kaydetme işlemleri olmadan gerçekleştirilmiştir. Bu nedenle ölçülen FPS, canlı kamera uygulamasının FPS değeriyle birebir aynı değildir.

Takip kapsamı da modelin genel doğruluk oranı olarak değerlendirilmemelidir.

## 6. Kurulum

### Gereksinimler

- Python 3.12
- pip
- OpenCV
- Ultralytics
- PyTorch
- İsteğe bağlı CUDA destekli NVIDIA GPU

### Projeyi indirme

```bash
git clone https://github.com/cbsanal/drone-tespit-takip.git
cd drone-tespit-takip
```

Geliştirme branch'ine geçmek için:

```bash
git checkout drone-detection-prototype
```

### Sanal ortam oluşturma

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Bağımlılıkları yükleme

PyTorch ve torchvision paketleri, kullanılacak donanım ve CUDA sürümüne uygun olarak kurulmalıdır.

Kurulum yönergeleri:

https://pytorch.org/get-started/locally/

Ardından:

```powershell
python -m pip install -r requirements.txt
```

### Model dosyası

Eğitilmiş model ağırlıkları GitHub deposuna dahil edilmemektedir.

Uygulamaları çalıştırmak için `best.pt` dosyasının aşağıdaki konuma yerleştirilmesi gerekir:

```text
runs/drone_yolo11s/weights/best.pt
```

Model ağırlıkları ekip içerisinde ayrıca paylaşılmalıdır.

## 7. Kullanım

Komutlar projenin ana klasöründen çalıştırılmalıdır.

### Kamera üzerinden drone tespiti

```powershell
python .\src\camera_detect.py
```

### Video üzerinden drone tespiti

```powershell
python .\src\video_detect.py --source ".\videos\drone_test.mp4" --conf 0.60
```

### Video üzerinden drone takibi

```powershell
python .\src\video_track.py --source ".\videos\drone_test.mp4" --conf 0.40
```

### Kamera üzerinden drone takibi

```powershell
python .\src\camera_track.py
```

Kamera takip uygulamasında:

| Tuş | İşlem |
|---|---|
| `+` veya `=` | Güven eşiğini artırma |
| `-` | Güven eşiğini azaltma |
| `R` | Video ve CSV kaydını başlatma/durdurma |
| `C` | Hareket izini temizleme |
| `Q` | Uygulamadan çıkma |

### Benchmark çalıştırma

```powershell
python .\src\benchmark.py --source ".\videos\drone_test.mp4" --conf 0.40 --imgsz 960
```

Benchmark sonuçları `runs/benchmark/` klasörüne kaydedilir.

## 8. Proje Dosyaları

```text
drone-tespit-takip/
├── config/
│   └── bytetrack_drone.yaml
├── src/
│   ├── benchmark.py
│   ├── camera_detect.py
│   ├── camera_track.py
│   ├── check_labels.py
│   ├── train.py
│   ├── video_detect.py
│   └── video_track.py
├── README.md
├── requirements.txt
└── .gitignore
```

Yerel çalışma sırasında `datasets/`, `runs/` ve `videos/` klasörleri de kullanılmaktadır. Bu klasörlerin içerikleri GitHub'a gönderilmemektedir.

## 9. Bilinen Sınırlamalar

- Drone çok küçük göründüğünde tespit başarısı düşebilir.
- Düşük görüntü kalitesi ve ışık koşulları tespiti zorlaştırabilir.
- Drone görüntüden çıkıp tekrar geldiğinde takip ID'si değişebilir.
- Yanlış pozitif tespitler oluşabilir.
- Birden fazla gerçek drone ile kapsamlı takip testleri henüz yapılmamıştır.
- Raspberry Pi ve fiziksel motor kontrolü entegrasyonu bu çalışma kapsamında gerçekleştirilmemiştir.
- Modelin farklı veri setleri üzerindeki genelleme başarısı henüz kapsamlı olarak doğrulanmamıştır.

## 10. Gizlilik ve Paylaşım

Kişisel kamera kayıtları, videolar, fotoğraflar ve yerel takip çıktıları GitHub deposuna eklenmemektedir.

Veri seti ve eğitilmiş model ağırlıkları da depo dışında tutulmaktadır.

## 11. Gelecek Çalışmalar

- Farklı drone görüntüleriyle kapsamlı testler
- Küçük nesne tespitinin iyileştirilmesi
- Takip ID kararlılığının geliştirilmesi
- Gerektiğinde veri setinin genişletilmesi ve modelin yeniden eğitilmesi
- Raspberry Pi ve fiziksel donanım entegrasyonu
- Gerçek drone ile saha testleri

Bu çalışmaların donanım gerektiren bölümleri ayrı geliştirme aşamalarında ele alınacaktır.