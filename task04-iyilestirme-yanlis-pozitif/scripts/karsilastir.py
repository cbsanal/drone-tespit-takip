"""Doğrulamada eşik seçer, sonra eski ve yeni modeli aynı testte karşılaştırır."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'.ultralytics')
import argparse
import csv
import json
import torch
from PIL import Image,ImageDraw
from ultralytics import YOLO

DEVICE=0 if torch.cuda.is_available() else 'cpu'
OLD=ROOT.parent/'task04-model-egitimi'

def overlap(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda x:(x[2]-x[0])*(x[3]-x[1])
    return intersection/(area(a)+area(b)-intersection) if intersection else 0

def ground_truth(path,split):
    label=ROOT/'data/labels'/split/(path.stem+'.txt')
    if not label.exists(): return []
    with Image.open(path) as image: width,height=image.size
    boxes=[]
    for line in label.read_text().splitlines():
        cls,x,y,w,h=map(float,line.split())
        assert cls==0
        boxes.append([(x-w/2)*width,(y-h/2)*height,(x+w/2)*width,(y+h/2)*height])
    return boxes

def predict(weights,split):
    model=YOLO(weights)
    paths=sorted((ROOT/'data/images'/split).glob('*'))
    if split=='test': paths+=sorted((OLD/'negatif-test').glob('*.jpg'))
    rows=[]
    for path in paths:
        result=model.predict(str(path),imgsz=640,conf=.001,iou=.7,device=DEVICE,verbose=False)[0]
        predictions=[[*b,float(c)] for b,c in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.conf.cpu().tolist())]
        rows.append({'file':path.name,'path':str(path),'truth':ground_truth(path,split),'predictions':predictions})
    return rows

def score(records,threshold):
    rows=[]
    for item in records:
        predictions=sorted((p for p in item['predictions'] if p[4]>=threshold),key=lambda p:-p[4])
        truth=item['truth'];found=set()
        for p in predictions:
            iou,index=max(((overlap(p,b),i) for i,b in enumerate(truth) if i not in found),default=(0,-1))
            if iou>=.5: found.add(index)
        small={i for i,b in enumerate(truth) if (b[2]-b[0])*(b[3]-b[1])<1024}
        rows.append({'dosya':item['file'],'pozitif':bool(truth),'tp':len(found),'fp':len(predictions)-len(found),'fn':len(truth)-len(found),'kucuk_tp':len(small & found),'kucuk_toplam':len(small)})
    tp,fp,fn=[sum(r[k] for r in rows) for k in ('tp','fp','fn')]
    summary={'conf':threshold,'tp':tp,'fp':fp,'fn':fn,'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,'negatif_goruntu':sum(not r['pozitif'] for r in rows),'negatif_yanlis_kutu':sum(r['fp'] for r in rows if not r['pozitif']),'yanlis_alarmli_negatif':sum(not r['pozitif'] and r['fp']>0 for r in rows),'kucuk_tp':sum(r['kucuk_tp'] for r in rows),'kucuk_toplam':sum(r['kucuk_toplam'] for r in rows)}
    return summary,rows

def main():
    from yollari_ayarla import main as yollari_ayarla
    yollari_ayarla()
    (ROOT/"weights").mkdir(exist_ok=True)
    (ROOT/"raporlar").mkdir(exist_ok=True)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['validation','test'])
    args=parser.parse_args()
    models={'eski':OLD/'weights/best.pt','yeni':ROOT/'weights/best.pt'}
    if args.mode=='validation':
        selection={}
        trials={}
        for name,weights in models.items():
            records=predict(weights,'val')
            trials[name]=[score(records,t)[0] for t in [.05,.10,.15,.20,.25,.30,.40,.50,.60,.70,.80,.90]]
            selection[name]=max(trials[name],key=lambda r:(r['f1'],r['precision'],r['conf']))
        (ROOT/'raporlar/dogrulama-esikleri.json').write_text(json.dumps(trials,indent=2),encoding='utf-8')
        (ROOT/'raporlar/secim.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
        settings={'imgsz':640,'iou_nms':.7,'confidence':selection['yeni']['conf'],'secim':'Yalnız pozitif+negatif doğrulama F1; eşitlikte precision, sonra yüksek eşik.'}
        (ROOT/'inference.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(selection,indent=2));return
    selection=json.loads((ROOT/'raporlar/secim.json').read_text())
    summaries={};all_rows=[]
    for name,weights in models.items():
        records=predict(weights,'test')
        (ROOT/'raporlar'/f'{name}-test-tahminleri.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        variants=[(name+'_sabit_005',.05),(name+'_kalibre',selection[name]['conf'])]
        for variant,threshold in variants:
            summaries[variant],rows=score(records,threshold)
            all_rows += [{'model':variant,**row} for row in rows]
            output=ROOT/'karsilastirma'/variant;output.mkdir(parents=True,exist_ok=True)
            for item in records:
                with Image.open(item['path']) as im: view=im.convert('RGB')
                draw=ImageDraw.Draw(view)
                for box in item['truth']: draw.rectangle(box,outline='lime',width=3)
                for box in item['predictions']:
                    if box[4]>=threshold:
                        draw.rectangle(box[:4],outline='red',width=3)
                        draw.text((box[0],max(0,box[1]-12)),f'drone {box[4]:.2f}',fill='red',stroke_width=1,stroke_fill='white')
                view.save(output/(Path(item['file']).stem+'.jpg'),quality=90)
    with (ROOT/'raporlar/karsilastirma.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    (ROOT/'raporlar/test-ozeti.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':
    main()
