"""Eğitimde kullanılan kamera negatiflerindeki uyumu ayrıca gösterir."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.ultralytics')
import json
import torch
from PIL import Image,ImageDraw,ImageOps
from ultralytics import YOLO


def main():
    rows=json.loads((ROOT/'raporlar/kamera-onay.json').read_text(encoding='utf-8'))
    settings=json.loads((ROOT/'inference.json').read_text(encoding='utf-8'))
    old=YOLO(ROOT.parent/'task04-model-egitimi/weights/best.pt')
    new=YOLO(ROOT/'weights/best.pt')
    output=ROOT/'karsilastirma/kamera-egitim-kareleri';output.mkdir(parents=True,exist_ok=True)
    results=[]
    for i,row in enumerate(rows):
        path=ROOT/row['dosya']
        canvas=Image.new('RGB',(1280,400),'white');draw=ImageDraw.Draw(canvas)
        record={'dosya':path.name}
        for col,(name,model,conf) in enumerate([('eski',old,.05),('yeni',new,settings['confidence'])]):
            result=model.predict(str(path),imgsz=640,conf=conf,iou=.7,device=0 if torch.cuda.is_available() else 'cpu',verbose=False)[0]
            view=Image.fromarray(result.plot()[:,:,::-1])
            view=ImageOps.contain(view,(635,360))
            canvas.paste(view,(col*640,35))
            draw.text((col*640+5,8),f'{name} conf={conf} | {len(result.boxes)} yanlis kutu',fill='black')
            record[name+'_kutu']=len(result.boxes)
        canvas.save(output/f'karsilastirma_{i:02d}.jpg',quality=92)
        results.append(record)
    report={'not':'Bu beş kare yeni modelin eğitiminde kullanılmıştır; bağımsız başarı kanıtı değildir. Eski eşik 0.05, yeni eşik yalnız doğrulamada seçildi.','kareler':results}
    (ROOT/'raporlar/kamera-egitim-uyumu.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
