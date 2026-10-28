"""Eşiği yalnız doğrulamada seçer; ayrılmış test ve negatifleri raporlar."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.ultralytics')
import argparse
import csv
import json
import time
import numpy as np
import torch
DEVICE=0 if torch.cuda.is_available() else 'cpu'
from PIL import Image,ImageDraw
from ultralytics import YOLO


def labels(image,split):
    with Image.open(image) as im: width,height=im.size
    boxes=[]
    for line in (ROOT/'data/labels'/split/(image.stem+'.txt')).read_text().splitlines():
        cls,xc,yc,w,h=map(float,line.split())
        assert cls==0
        boxes.append([(xc-w/2)*width,(yc-h/2)*height,(xc+w/2)*width,(yc+h/2)*height])
    return boxes


def iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda x:(x[2]-x[0])*(x[3]-x[1])
    return inter/(area(a)+area(b)-inter) if inter else 0.0


def match(predictions,truth,threshold):
    kept=sorted((p for p in predictions if p[4]>=threshold),key=lambda p:-p[4])
    used=set(); matches=[]
    for number,pred in enumerate(kept):
        candidates=[(iou(pred,box),i) for i,box in enumerate(truth) if i not in used]
        overlap,index=max(candidates,default=(0,-1))
        if overlap>=0.5:
            used.add(index); matches.append((number,index,overlap))
    return kept,matches,len(matches),len(kept)-len(matches),len(truth)-len(matches)


def predict(model,images):
    records=[]
    for path in images:
        result=model.predict(str(path),imgsz=640,conf=0.001,iou=0.7,device=DEVICE,verbose=False)[0]
        predictions=[[*box,float(conf)] for box,conf in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
        records.append((path,predictions))
    return records


def main():
    from yollari_ayarla import main as yollari_ayarla
    yollari_ayarla()
    (ROOT/"weights").mkdir(exist_ok=True)
    (ROOT/"raporlar").mkdir(exist_ok=True)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['validation','test'])
    args=parser.parse_args()
    model=YOLO(ROOT/'weights/best.pt')
    if args.mode=='validation':
        records=predict(model,sorted((ROOT/'data/images/val').iterdir()))
        trials=[]
        for threshold in [.05,.10,.15,.20,.25,.30,.40,.50,.60,.70,.80,.90]:
            tp=fp=fn=0
            for path,preds in records:
                _,_,a,b,c=match(preds,labels(path,'val'),threshold); tp+=a;fp+=b;fn+=c
            precision=tp/(tp+fp) if tp+fp else 0
            recall=tp/(tp+fn) if tp+fn else 0
            f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0
            trials.append({'conf':threshold,'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':f1})
        best=max(trials,key=lambda r:(r['f1'],r['precision'],r['conf']))
        settings={'imgsz':640,'iou_nms':0.7,'iou_eslesme':0.5,'confidence':best['conf'],'secim_kurali':'Doğrulama F1; eşitlikte precision, sonra yüksek eşik. Test sonuçları kullanılmadı.','dogrulama':best}
        (ROOT/'raporlar/esik-denemeleri.json').write_text(json.dumps(trials,indent=2),encoding='utf-8')
        (ROOT/'inference.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(settings,ensure_ascii=False)); return
    settings=json.loads((ROOT/'inference.json').read_text())
    threshold=settings['confidence']
    metrics=model.val(data=str(ROOT/'data.yaml'),split='test',imgsz=640,batch=8,device=DEVICE,workers=0,conf=0.001,iou=0.7,plots=True,project=str(ROOT/'runs'),name='test',exist_ok=False)
    output=ROOT/'test-ornekleri'; output.mkdir(exist_ok=True)
    images=sorted((ROOT/'data/images/test').iterdir())+sorted((ROOT/'negatif-test').glob('*.jpg'))
    rows=[]; prediction_rows=[]; small_total=small_tp=0
    for path,preds in predict(model,images):
        negative=path.parent.name=='negatif-test'
        truth=[] if negative else labels(path,'test')
        kept,matches,tp,fp,fn=match(preds,truth,threshold)
        small={i for i,b in enumerate(truth) if (b[2]-b[0])*(b[3]-b[1])<1024}
        found={m[1] for m in matches}
        small_total+=len(small); small_tp+=len(small&found)
        rows.append({'dosya':path.name,'tur':'negatif' if negative else 'pozitif','gercek_kutu':len(truth),'tahmin':len(kept),'tp':tp,'fp':fp,'fn':fn,'kucuk_kutu':len(small),'kucuk_tp':len(small&found)})
        with Image.open(path) as im:
            view=im.convert('RGB')
        draw=ImageDraw.Draw(view)
        for box in truth: draw.rectangle(box,outline='lime',width=3)
        for n,box in enumerate(kept):
            draw.rectangle(box[:4],outline='red',width=3)
            draw.text((max(0,box[0]),max(0,box[1]-14)),f'drone {box[4]:.2f}',fill='red',stroke_width=1,stroke_fill='white')
            prediction_rows.append({'dosya':path.name,'xmin':box[0],'ymin':box[1],'xmax':box[2],'ymax':box[3],'guven':box[4],'tp_eslesmesi':any(m[0]==n for m in matches)})
        view.save(output/(path.stem+'.jpg'),quality=92)
    for filename,data,fields in [('test-dosya-sonuclari.csv',rows,list(rows[0])),('test-tahminleri.csv',prediction_rows,['dosya','xmin','ymin','xmax','ymax','guven','tp_eslesmesi'])]:
        with (ROOT/'raporlar'/filename).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
    totals={key:sum(r[key] for r in rows) for key in ['tp','fp','fn']}
    tp,fp,fn=[totals[k] for k in ['tp','fp','fn']]
    summary={'confidence':threshold,'iou_eslesme':.5,'pozitif_goruntu':len([r for r in rows if r['tur']=='pozitif']),'negatif_goruntu':len([r for r in rows if r['tur']=='negatif']),'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'small_tp':small_tp,'small_total':small_total,'negatif_yanlis_kutu':sum(r['fp'] for r in rows if r['tur']=='negatif'),'ultralytics_pozitif_test':{k:float(v) for k,v in metrics.results_dict.items()},'ultralytics_hiz_ms':{k:float(v) for k,v in metrics.speed.items()},'not':'Standart mAP yalnız 11 pozitif test üzerinde. Sabit eşik sayımı ayrıca 2 negatif içerir; kamera testi değildir.'}
    (ROOT/'raporlar/test-ozeti.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
