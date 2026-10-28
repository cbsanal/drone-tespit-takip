"""Bilgisayar kamerasında canlı kutu/güven gösterimi ve elle işaretlenen denemeler."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.ultralytics')
import argparse
from datetime import datetime,timezone
import json
import time
print('Kamera kutuphaneleri yukleniyor...',flush=True)
import cv2
import numpy as np
import torch
from ultralytics import YOLO


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera',type=int,default=0)
    parser.add_argument('--url',help='İsteğe bağlı canlı HTTP/MJPEG kamera akışı')
    parser.add_argument('--device',default='0' if torch.cuda.is_available() else 'cpu',help='GPU için 0, GPU yoksa cpu')
    args=parser.parse_args()
    settings=json.loads((ROOT/'inference.json').read_text())
    print('Model yukleniyor...',flush=True)
    model=YOLO(ROOT/'weights/best.pt')
    capture=None
    backends=(cv2.CAP_FFMPEG,) if args.url else ((cv2.CAP_DSHOW,cv2.CAP_MSMF,cv2.CAP_ANY) if os.name=='nt' else (cv2.CAP_ANY,))
    for backend in backends:
        print(f'Kamera aciliyor: aygit {args.camera}, backend {backend}',flush=True)
        if args.url:
            candidate=cv2.VideoCapture(args.url,backend,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,10000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,10000])
        else:
            candidate=cv2.VideoCapture(args.camera,backend)
        ok,_=candidate.read() if candidate.isOpened() else (False,None)
        if ok:
            capture=candidate
            break
        candidate.release()
    if capture is None:
        raise RuntimeError('Kameradan görüntü alınamadı. Bağlantıyı/izinleri, DroidCam aktarımını ve --camera numarasını kontrol edin.')
    output=ROOT/'kamera-test'/datetime.now().strftime('%Y%m%d-%H%M%S');output.mkdir(parents=True,exist_ok=True)
    events=[];timings=[];frames=0
    cases={ord('1'):'merkez',ord('2'):'sol',ord('3'):'sag',ord('4'):'kucuk',ord('5'):'drone_fotografi_yok'}
    print('Eğitimde kullanılmamış test fotoğrafını gösterin. 1:merkez 2:sol 3:sağ 4:küçük 5:fotoğraf yok. Q:çıkış.')
    print('Yalnız bu tuşlara bastığınız anın görüntüsü kaydedilir; otomatik video kaydı yoktur.')
    try:
        while True:
            start=time.perf_counter();ok,frame=capture.read()
            if not ok:
                print('Kameradan kare alınamadı.');break
            result=model.predict(frame,imgsz=settings['imgsz'],conf=settings['confidence'],iou=settings['iou_nms'],device=args.device,verbose=False)[0]
            view=result.plot()
            elapsed=(time.perf_counter()-start)*1000
            if frames>=5: timings.append(elapsed)
            frames+=1
            cv2.putText(view,f'{elapsed:.1f} ms | 1:merkez 2:sol 3:sag 4:kucuk 5:negatif Q:cikis',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,255),1)
            cv2.imshow('Drone kamera denemesi',view)
            key=cv2.waitKey(1)&255
            if key==ord('q') or key==27:break
            if key in cases:
                case=cases[key];stamp=datetime.now().strftime('%H%M%S-%f')
                cv2.imencode('.jpg',view)[1].tofile(str(output/f'{case}-{stamp}.jpg'))
                cv2.imencode('.jpg',frame)[1].tofile(str(output/f'{case}-{stamp}-orijinal.jpg'))
                events.append({'durum':case,'zaman_utc':datetime.now(timezone.utc).isoformat(),'goruntu':f'{case}-{stamp}.jpg','kutu_sayisi':len(result.boxes),'kutular':result.boxes.xyxy.cpu().tolist(),'guvenler':result.boxes.conf.cpu().tolist(),'sure_ms':elapsed})
                print(case,':',len(result.boxes),'kutu kaydedildi.')
    finally:
        capture.release();cv2.destroyAllWindows()
        summary={'kamera':'HTTP canlı akış' if args.url else args.camera,'kare_sayisi':frames,'conf':settings['confidence'],'denemeler':events,'medyan_ms':float(np.median(timings)) if timings else None,'p95_ms':float(np.percentile(timings,95)) if timings else None,'sure_kapsami':'Kamera okuma + tahmin + kutu çizimi; ekranın gösterimi ve tuş bekleme hariç. İlk 5 kare hariç.','not':'Kutuların fotoğraftaki drone üzerinde olup olmadığı görsel incelemeyle doğrulanmalı; kutu sayısı tek başına başarı değildir.'}
        (output/'sonuc.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Kayıt:',output)

if __name__=='__main__':
    main()
